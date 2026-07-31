import datetime as dt
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Avg
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    Region, Vendor, Warehouse, Material, StockEntry,
    ConsumptionUpload, ConsumptionRecord, PODStation,
)
from .forms import StockEntryForm, ConsumptionUploadForm
from .permissions import admin_required, vendor_or_admin_required
from .services.importer import process_upload


def today():
    return dt.date.today()


@login_required
def home(request):
    if request.user.is_admin_role:
        return redirect("inventory:admin_dashboard")
    return redirect("inventory:stock_entry")


# ---------------- Vendor: daily opening stock entry ----------------

@vendor_or_admin_required
def stock_entry(request):
    user = request.user
    if user.is_vendor_role:
        if not user.warehouse:
            messages.error(request, "Your account isn't linked to a warehouse yet. Contact the admin.")
            return render(request, "inventory/no_warehouse.html")
        warehouse = user.warehouse
    else:
        wh_id = request.GET.get("warehouse")
        warehouse = get_object_or_404(Warehouse, id=wh_id) if wh_id else Warehouse.objects.first()

    date = request.GET.get("date") or today().isoformat()

    if request.method == "POST":
        material_id = request.POST.get("material")
        material = get_object_or_404(Material, id=material_id)
        action = request.POST.get("action", "save")
        redirect_url = f"/stock/?date={date}" + (f"&warehouse={warehouse.id}" if user.is_admin_role else "")

        if action == "clear":
            if not user.is_admin_role:
                raise PermissionDenied("Only admin can clear an entry.")
            StockEntry.objects.filter(date=date, warehouse=warehouse, material=material).delete()
            messages.success(request, f"Cleared {material.name} for {date}.")
            return redirect(redirect_url)

        entry, _ = StockEntry.objects.get_or_create(
            date=date, warehouse=warehouse, material=material,
            defaults={"entered_by": user},
        )
        entry.opening = Decimal(request.POST.get("opening") or 0)
        entry.received = Decimal(request.POST.get("received") or 0)
        entry.consumed = Decimal(request.POST.get("consumed") or 0)
        entry.note = request.POST.get("note", "")
        entry.entered_by = user
        entry.save()
        messages.success(request, f"Saved entry for {material.name} on {date}.")
        return redirect(redirect_url)

    materials = Material.objects.filter(is_active=True)
    existing = {e.material_id: e for e in StockEntry.objects.filter(date=date, warehouse=warehouse)}

    rows = []
    for m in materials:
        entry = existing.get(m.id)
        if not entry:
            prior = (StockEntry.objects.filter(warehouse=warehouse, material=m, date__lt=date)
                     .order_by("-date").first())
            opening = prior.closing if prior else Decimal("0")
        else:
            opening = entry.opening
        rows.append({
            "material": m,
            "opening": opening,
            "received": entry.received if entry else Decimal("0"),
            "consumed": entry.consumed if entry else Decimal("0"),
            "closing": entry.closing if entry else opening,
            "note": entry.note if entry else "",
        })

    context = {
        "warehouse": warehouse,
        "date": date,
        "rows": rows,
        "all_warehouses": Warehouse.objects.select_related("vendor", "region") if request.user.is_admin_role else None,
    }
    return render(request, "inventory/stock_entry.html", context)


# ---------------- Stock register (report table) ----------------

@vendor_or_admin_required
def stock_register(request):
    qs = StockEntry.objects.select_related("warehouse", "warehouse__vendor", "material")
    if request.user.is_vendor_role:
        if not request.user.warehouse:
            raise PermissionDenied
        qs = qs.filter(warehouse=request.user.warehouse)

    region = request.GET.get("region")
    vendor = request.GET.get("vendor")
    warehouse_id = request.GET.get("warehouse")
    material_id = request.GET.get("material")
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    if region:
        qs = qs.filter(warehouse__region__name=region)
    if vendor:
        qs = qs.filter(warehouse__vendor__name=vendor)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if material_id:
        qs = qs.filter(material_id=material_id)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    qs = qs.order_by("-date")[:500]

    context = {
        "entries": qs,
        "regions": Region.objects.all(),
        "vendors": Vendor.objects.all(),
        "warehouses": Warehouse.objects.all() if request.user.is_admin_role else [request.user.warehouse],
        "materials": Material.objects.filter(is_active=True),
    }
    return render(request, "inventory/stock_register.html", context)


# ---------------- Admin: consumption file upload ----------------

@admin_required
def upload_consumption(request):
    if request.method == "POST":
        form = ConsumptionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.uploaded_by = request.user
            upload.save()
            result = process_upload(upload)
            if result.get("error"):
                messages.error(request, result["error"])
            else:
                messages.success(
                    request,
                    f"Processed {result['total']} rows — {result['matched']} matched, "
                    f"{result['unmatched']} unmatched, across {result['warehouses_affected']} warehouses."
                )
            return redirect("inventory:upload_consumption")
    else:
        form = ConsumptionUploadForm()

    uploads = ConsumptionUpload.objects.select_related("uploaded_by")[:20]
    unmatched_preview = ConsumptionRecord.objects.filter(matched=False).select_related(
        "vendor", "region"
    ).order_by("-date")[:50]
    return render(request, "inventory/upload_consumption.html", {
        "form": form, "uploads": uploads, "unmatched_preview": unmatched_preview,
    })


# ---------------- Admin dashboard ----------------

@admin_required
def admin_dashboard(request):
    total_warehouses = Warehouse.objects.count()
    total_materials = Material.objects.count()
    recent_uploads = ConsumptionUpload.objects.all()[:5]
    todays_entries = StockEntry.objects.filter(date=today()).count()
    return render(request, "inventory/admin_dashboard.html", {
        "total_warehouses": total_warehouses,
        "total_materials": total_materials,
        "recent_uploads": recent_uploads,
        "todays_entries": todays_entries,
    })


# ---------------- Consumption analytics (daily/weekly/10-day/monthly avg) ----------------

@vendor_or_admin_required
def consumption_report(request):
    qs = ConsumptionRecord.objects.filter(matched=True)
    if request.user.is_vendor_role:
        if not request.user.warehouse:
            raise PermissionDenied
        qs = qs.filter(warehouse=request.user.warehouse)

    warehouse_id = request.GET.get("warehouse")
    material_id = request.GET.get("material")
    pod_station = request.GET.get("pod_station")
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if material_id:
        qs = qs.filter(material_id=material_id)
    if pod_station:
        qs = qs.filter(pod_station_name=pod_station)

    end = today()
    windows = {
        "Daily (today)": (end, end),
        "Weekly avg/day (last 7d)": (end - dt.timedelta(days=6), end),
        "10-Day avg/day": (end - dt.timedelta(days=9), end),
        "Monthly avg/day (last 30d)": (end - dt.timedelta(days=29), end),
    }
    summary = []
    for label, (start, stop) in windows.items():
        window_qs = qs.filter(date__gte=start, date__lte=stop)
        total = window_qs.aggregate(t=Sum("quantity"))["t"] or Decimal("0")
        days = (stop - start).days + 1
        avg_per_day = total / days if days else Decimal("0")
        summary.append({"label": label, "total": total, "avg_per_day": round(avg_per_day, 2), "days": days})

    daily_series = (
        qs.filter(date__gte=end - dt.timedelta(days=29))
        .values("date").annotate(total=Sum("quantity")).order_by("date")
    )
    by_material = (
        qs.filter(date__gte=end - dt.timedelta(days=29))
        .values("material__name").annotate(total=Sum("quantity")).order_by("-total")[:10]
    )

    by_type = (
        ConsumptionRecord.objects.filter(date__gte=end - dt.timedelta(days=29))
        .filter(warehouse=request.user.warehouse) if request.user.is_vendor_role else ConsumptionRecord.objects.filter(date__gte=end - dt.timedelta(days=29))
    )
    if warehouse_id:
        by_type = by_type.filter(warehouse_id=warehouse_id)
    if pod_station:
        by_type = by_type.filter(pod_station_name=pod_station)
    by_type = (
        by_type.exclude(raw_type_text="")
        .values("pod_station_name", "raw_type_text", "material__name")
        .annotate(total=Sum("quantity"))
        .order_by("pod_station_name", "raw_type_text", "-total")
    )

    pod_station_qs = PODStation.objects.select_related("warehouse")
    if request.user.is_vendor_role:
        pod_station_qs = pod_station_qs.filter(warehouse=request.user.warehouse)
    elif warehouse_id:
        pod_station_qs = pod_station_qs.filter(warehouse_id=warehouse_id)

    return render(request, "inventory/consumption_report.html", {
        "summary": summary,
        "daily_series": list(daily_series),
        "by_material": list(by_material),
        "by_type": list(by_type),
        "warehouses": Warehouse.objects.all() if request.user.is_admin_role else [request.user.warehouse],
        "materials": Material.objects.filter(is_active=True),
        "pod_stations": pod_station_qs.order_by("name"),
    })