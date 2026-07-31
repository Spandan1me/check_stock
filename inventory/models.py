from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Region(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="warehouses")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="warehouses")
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["region__name", "vendor__name", "name"]
        unique_together = ("vendor", "name")

    def __str__(self):
        return f"{self.name} ({self.vendor})"


class PODStation(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="pod_stations")
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["name"]
        unique_together = ("warehouse", "name")

    def __str__(self):
        return self.name


class Material(models.Model):
    """Master list of trackable materials, defined by the admin.
    e.g. 'Drop Wire 100 APC/APC', 'Dual Band Router(V5)', 'IPTV Box'
    """
    class Unit(models.TextChoices):
        METER = "meter", "Meter"
        PCS = "pcs", "Pcs"
        ROLL = "roll", "Roll"
        BOX = "box", "Box"
        SET = "set", "Set"

    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.PCS)
    min_stock_alert = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Matching hints used to auto-map ticket rows (Materials / Category / Type / ONTModel)
    # from the daily consumption upload onto this master material. Optional but recommended.
    match_material_group = models.CharField(max_length=50, blank=True, help_text="e.g. Dropwire, Router, IPTV")
    match_length_or_band = models.CharField(max_length=50, blank=True, help_text="e.g. 100 Meter / Dual Band / Wifi 6")
    match_connector = models.CharField(max_length=20, blank=True, help_text="e.g. APC/APC, APC/UPC")
    match_condition = models.CharField(
        max_length=20, blank=True, choices=[("NEW", "New"), ("REFURBISHED", "Refurbished")],
        help_text="Leave blank if not applicable"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class StockEntry(models.Model):
    """One daily record per warehouse + material: opening, received, consumed, closing.
    Vendors edit only entries for their own warehouse. Consumption can arrive either
    manually or auto-populated from an admin's consumption file upload.
    """
    date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_entries")
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="stock_entries")

    opening = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    consumed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    note = models.CharField(max_length=255, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="stock_entries")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("date", "warehouse", "material")
        ordering = ["-date"]
        indexes = [models.Index(fields=["warehouse", "material", "date"])]

    def save(self, *args, **kwargs):
        self.closing = (self.opening or 0) + (self.received or 0) - (self.consumed or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} · {self.warehouse} · {self.material}"


class ConsumptionUpload(models.Model):
    """Log of each daily consumption file the admin uploads."""
    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    file = models.FileField(upload_to="consumption_uploads/%Y/%m/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    total_rows = models.IntegerField(default=0)
    matched_rows = models.IntegerField(default=0)
    unmatched_rows = models.IntegerField(default=0)
    log = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Upload {self.id} - {self.uploaded_at:%Y-%m-%d %H:%M}"


class ConsumptionRecord(models.Model):
    """One row of material actually consumed, derived from a ticket in an uploaded file.
    This is the raw/atomic record; StockEntry.consumed totals are rolled up from these
    per warehouse+material+date so daily/weekly/monthly averages can be computed directly.
    """
    upload = models.ForeignKey(ConsumptionUpload, on_delete=models.CASCADE, related_name="records")
    ticket_id = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    region = models.ForeignKey(Region, null=True, on_delete=models.SET_NULL)
    vendor = models.ForeignKey(Vendor, null=True, on_delete=models.SET_NULL)
    warehouse = models.ForeignKey(Warehouse, null=True, on_delete=models.SET_NULL, related_name="consumption_records")
    pod_station_name = models.CharField(max_length=150, blank=True)
    material = models.ForeignKey(Material, null=True, on_delete=models.SET_NULL, related_name="consumption_records")
    raw_material_text = models.CharField(max_length=255, blank=True, help_text="Materials/Category/Type as read from the file")
    raw_type_text = models.CharField(max_length=100, blank=True, help_text="The Type column exactly as read from the file")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    matched = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["warehouse", "material", "date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.date} · {self.raw_material_text} · qty {self.quantity}"  