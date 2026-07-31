"""
Processes an uploaded daily consumption ticket file (.xlsx) end to end:

  1. Read each row (TicketId, VendorName, PODStationName, Region, CompletedDate,
     TicketStatusTypeName, Materials, Category, Type, ONTModel, Quantity, ...)
  2. Skip cancelled tickets (OSTCancelled) - nothing was actually consumed.
  3. Resolve Warehouse via (Vendor, POD Station) against our hierarchy.
  4. Resolve Material via the matcher service against the Material master list.
  5. Write one ConsumptionRecord per row (matched or not - unmatched rows are
     kept for the admin to review, not silently dropped).
  6. Roll matched records up into StockEntry.consumed per (date, warehouse,
     material), auto-carrying opening stock forward from the prior day's closing
     for any new StockEntry rows this creates.

Returns a summary dict; also updates the ConsumptionUpload row's counters/status.
"""
import datetime as dt
from decimal import Decimal

import openpyxl
from django.db import transaction

from inventory.models import (
    Region, Vendor, Warehouse, PODStation, Material,
    ConsumptionUpload, ConsumptionRecord, StockEntry,
)
from inventory.services.matcher import match_material

EXCLUDED_STATUSES = {"OSTCANCELLED"}


def _parse_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y  %I:%M%p", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return dt.datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def process_upload(upload: ConsumptionUpload):
    wb = openpyxl.load_workbook(upload.file.path, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}

    required = ["VendorName", "PODStationName", "Region", "CompletedDate",
                "TicketStatusTypeName", "Materials", "Category", "Type", "ONTModel", "Quantity"]
    missing = [c for c in required if c not in idx]
    if missing:
        upload.status = ConsumptionUpload.Status.FAILED
        upload.log = f"Missing expected columns: {', '.join(missing)}"
        upload.save()
        return {"error": upload.log}

    # Build a warehouse lookup keyed by (vendor name upper, pod station name upper)
    wh_lookup = {}
    for pod in PODStation.objects.select_related("warehouse", "warehouse__vendor").all():
        key = (pod.warehouse.vendor.name.strip().upper(), pod.name.strip().upper())
        wh_lookup[key] = pod.warehouse

    materials = list(Material.objects.filter(is_active=True))

    total = 0
    matched = 0
    unmatched = 0
    # daily rollup: {(date, warehouse_id, material_id): total_quantity}
    rollup = {}

    with transaction.atomic():
        # clear any previous records tied to this upload (in case of reprocessing)
        ConsumptionRecord.objects.filter(upload=upload).delete()

        for r in rows[1:]:
            if r is None or all(v is None for v in r):
                continue
            total += 1

            status = str(r[idx["TicketStatusTypeName"]] or "").strip().upper()
            if status in EXCLUDED_STATUSES:
                continue

            vendor_name = str(r[idx["VendorName"]] or "").strip()
            pod_name = str(r[idx["PODStationName"]] or "").strip()
            region_name = str(r[idx["Region"]] or "").strip()
            date = _parse_date(r[idx["CompletedDate"]])
            materials_text = r[idx["Materials"]]
            category_text = r[idx["Category"]]
            type_text = r[idx["Type"]]
            ont_model_text = r[idx["ONTModel"]]
            qty_raw = r[idx["Quantity"]]
            qty = Decimal(str(qty_raw)) if qty_raw not in (None, "") else Decimal("1")

            if not date or not materials_text:
                continue

            warehouse = wh_lookup.get((vendor_name.upper(), pod_name.upper()))
            vendor_obj = Vendor.objects.filter(name=vendor_name).first()
            region_obj = Region.objects.filter(name=region_name).first()

            mat = match_material(
                {"materials": materials_text, "category": category_text,
                 "type": type_text, "ont_model": ont_model_text},
                materials,
            )

            is_matched = bool(mat and warehouse)
            if is_matched:
                matched += 1
            else:
                unmatched += 1

            ConsumptionRecord.objects.create(
                upload=upload,
                ticket_id=str(r[idx.get("TicketId", 0)] or "") if "TicketId" in idx else "",
                date=date,
                region=region_obj,
                vendor=vendor_obj,
                warehouse=warehouse,
                pod_station_name=pod_name,
                material=mat,
                raw_material_text=" / ".join(str(x) for x in [materials_text, category_text, type_text] if x),
                raw_type_text=str(type_text or "").strip(),
                quantity=qty,
                matched=is_matched,
            )

            if is_matched:
                key = (date, warehouse.id, mat.id)
                rollup[key] = rollup.get(key, Decimal("0")) + qty

        # Roll matched consumption up into StockEntry rows
        for (date, warehouse_id, material_id), qty_total in rollup.items():
            entry = StockEntry.objects.filter(
                date=date, warehouse_id=warehouse_id, material_id=material_id
            ).first()
            if entry:
                entry.consumed = (entry.consumed or 0) + qty_total
                entry.save()
            else:
                prior = (StockEntry.objects
                         .filter(warehouse_id=warehouse_id, material_id=material_id, date__lt=date)
                         .order_by("-date").first())
                opening = prior.closing if prior else Decimal("0")
                StockEntry.objects.create(
                    date=date, warehouse_id=warehouse_id, material_id=material_id,
                    opening=opening, received=Decimal("0"), consumed=qty_total,
                )

        upload.total_rows = total
        upload.matched_rows = matched
        upload.unmatched_rows = unmatched
        upload.status = ConsumptionUpload.Status.DONE
        upload.log = f"Processed {total} rows: {matched} matched, {unmatched} unmatched."
        upload.save()

    return {
        "total": total, "matched": matched, "unmatched": unmatched,
        "warehouses_affected": len({k[1] for k in rollup}),
    }