from django.contrib import admin
from .models import (
    Region, Vendor, Warehouse, PODStation, Material,
    StockEntry, ConsumptionUpload, ConsumptionRecord,
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "region")
    list_filter = ("region", "vendor")
    search_fields = ("name",)


@admin.register(PODStation)
class PODStationAdmin(admin.ModelAdmin):
    list_display = ("name", "warehouse")
    search_fields = ("name",)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "min_stock_alert", "is_active", "match_material_group")
    list_filter = ("unit", "is_active", "match_material_group")
    search_fields = ("name",)


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "warehouse", "material", "opening", "received", "consumed", "closing")
    list_filter = ("warehouse", "material")
    date_hierarchy = "date"


@admin.register(ConsumptionUpload)
class ConsumptionUploadAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_at", "uploaded_by", "status", "total_rows", "matched_rows", "unmatched_rows")


@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "warehouse", "material", "quantity", "matched")
    list_filter = ("matched", "warehouse", "material")
    date_hierarchy = "date"
