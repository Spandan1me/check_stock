"""
Seeds the Material master list exactly as provided by the client, with
match_* hints pre-filled so uploaded consumption files auto-map onto them.

Usage:
    python manage.py seed_materials
"""
from django.core.management.base import BaseCommand
from inventory.models import Material

# (name, unit, group, band_or_length, connector, condition)
MATERIALS = [
    ("DROP WIRE 30 M", "meter", "DROPWIRE", "30", "", ""),
    ("DROP WIRE 40 M", "meter", "DROPWIRE", "40", "", ""),
    ("Drop Wire 50 APC/APC", "meter", "DROPWIRE", "50", "APC/APC", ""),
    ("Drop Wire 50 APC/UPC", "meter", "DROPWIRE", "50", "APC/UPC", ""),
    ("Drop Wire 75 APC/APC", "meter", "DROPWIRE", "75", "APC/APC", ""),
    ("Drop Wire 75 APC/UPC", "meter", "DROPWIRE", "75", "APC/UPC", ""),
    ("Drop Wire 100 APC/APC", "meter", "DROPWIRE", "100", "APC/APC", ""),
    ("Drop Wire 100 APC/UPC", "meter", "DROPWIRE", "100", "APC/UPC", ""),
    ("Drop Wire 125 APC/APC", "meter", "DROPWIRE", "125", "APC/APC", ""),
    ("Drop Wire 125 APC/UPC", "meter", "DROPWIRE", "125", "APC/UPC", ""),
    ("Drop Wire 150 APC/APC", "meter", "DROPWIRE", "150", "APC/APC", ""),
    ("Drop Wire 150 APC/UPC", "meter", "DROPWIRE", "150", "APC/UPC", ""),
    ("Drop Wire 175 APC/APC", "meter", "DROPWIRE", "175", "APC/APC", ""),
    ("Drop Wire 175 APC/UPC", "meter", "DROPWIRE", "175", "APC/UPC", ""),
    ("Drop Wire 200 APC/APC", "meter", "DROPWIRE", "200", "APC/APC", ""),
    ("Drop Wire 200 APC/UPC", "meter", "DROPWIRE", "200", "APC/UPC", ""),
    ("Drop Wire 225 APC/APC", "meter", "DROPWIRE", "225", "APC/APC", ""),
    ("Drop Wire 225 APC/UPC", "meter", "DROPWIRE", "225", "APC/UPC", ""),
    ("Drop Wire 250 APC/APC", "meter", "DROPWIRE", "250", "APC/APC", ""),
    ("Drop Wire 250 APC/UPC", "meter", "DROPWIRE", "250", "APC/UPC", ""),
    ("Drop Wire 275 APC/APC", "meter", "DROPWIRE", "275", "APC/APC", ""),
    ("Drop Wire 275 APC/UPC", "meter", "DROPWIRE", "275", "APC/UPC", ""),
    ("Drop Wire 300 APC/APC", "meter", "DROPWIRE", "300", "APC/APC", ""),
    ("Drop Wire 300 APC/UPC", "meter", "DROPWIRE", "300", "APC/UPC", ""),
    ("Dual Band Router(V5)", "pcs", "ROUTER", "DUAL BAND", "", "NEW"),
    ("Dual band router-Refurbished", "pcs", "ROUTER", "DUAL BAND", "", "REFURBISHED"),
    ("Singel Band Router(A5)", "pcs", "ROUTER", "SINGLE BAND", "", "NEW"),
    ("Single band router-Refurbished", "pcs", "ROUTER", "SINGLE BAND", "", "REFURBISHED"),
    ("Mess Router", "pcs", "ROUTER", "MESH", "", "NEW"),
    ("Wifi 6 Router(X6)", "pcs", "ROUTER", "WIFI 6", "", "NEW"),
    ("WiFi 6 Router-Refurbished", "pcs", "ROUTER", "WIFI 6", "", "REFURBISHED"),
    ("IPTV-REFURBISHED", "pcs", "IPTV", "SETUP BOX", "", "REFURBISHED"),
    ("IPTV Box", "pcs", "IPTV", "SETUP BOX", "", "NEW"),
]


class Command(BaseCommand):
    help = "Seed the Material master list with matching hints for consumption-file auto-import"

    def handle(self, *args, **options):
        created = 0
        for name, unit, group, band, connector, condition in MATERIALS:
            _, was_created = Material.objects.get_or_create(
                name=name,
                defaults=dict(
                    unit=unit,
                    match_material_group=group,
                    match_length_or_band=band,
                    match_connector=connector,
                    match_condition=condition,
                ),
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded materials: {created} new, {Material.objects.count()} total."))
