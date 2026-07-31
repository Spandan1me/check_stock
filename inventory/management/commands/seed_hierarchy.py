"""
Loads Region / Vendor / Warehouse / POD Station from the vendor-warehouse
reference file (already parsed to JSON once during planning). Safe to re-run -
uses get_or_create throughout.

Usage:
    python manage.py seed_hierarchy
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from inventory.models import Region, Vendor, Warehouse, PODStation

HIERARCHY = [
  {"region":"BAG","vendor":"DMN BAG Onsite Support","warehouse":"DMN Bag_WH","podStations":["Banepa POD Station","Bhaktapur POD Station","Dakshindhoka POD Station","Gongabu POD Station","Kapan POD Station","Kathmandu POD Station","Mahalaxmi POD Station","Sitapaila POD Station","SNS Bhaktapur POD Station","STN POD Station","Unknown POD Station","Yekantakuna POD Station"]},
  {"region":"BAG","vendor":"Optinet","warehouse":"Optinet_sitapaila","podStations":["Bhaktapur POD Station","Dakshindhoka POD Station","Dhading POD Station","Gongabu POD Station","Kapan POD Station","Kathmandu POD Station","Mahalaxmi POD Station","Sitapaila POD Station","Unknown POD Station","Yekantakuna POD Station"]},
  {"region":"BAG","vendor":"Smarten","warehouse":"Mandikhatar","podStations":["Banepa POD Station","Bhaktapur POD Station","Dakshindhoka POD Station","Gongabu POD Station","Kapan POD Station","Kathmandu POD Station","Mahalaxmi POD Station","Sitapaila POD Station","STN POD Station","Unknown POD Station"]},
  {"region":"BAG","vendor":"Smarten","warehouse":"Adamghat","podStations":["Trishuli POD Station","Galchi POD Station"]},
  {"region":"BAG","vendor":"SNSCable","warehouse":"SNSCable (Direct)","podStations":["SNS Bhaktapur POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Bardibash","podStations":["Bardibas POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Birjung","podStations":["Birganj POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Chapur","podStations":["Chapur POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Hetauda","podStations":["Hetauda POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Lalbandi","podStations":["Lalbandi pod station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Malangwa","podStations":["Malangwa POD Station"]},
  {"region":"CDR","vendor":"FiberKing","warehouse":"Simara","podStations":["Simara POD Station"]},
  {"region":"CDR","vendor":"Smarten","warehouse":"Bharatpur","podStations":["Chitwan POD Station","Tandi pod station"]},
  {"region":"CDR","vendor":"Smarten","warehouse":"Jankapur","podStations":["Janakpur POD Station"]},
  {"region":"EDR","vendor":"Smarten","warehouse":"Gaighat","podStations":["Gaighat Pod Station"]},
  {"region":"EDR","vendor":"Smarten","warehouse":"Lahan","podStations":["Lahan POD Station"]},
  {"region":"EDR","vendor":"Smarten","warehouse":"Rajbiraj","podStations":["Rajbiraj POD Station"]},
  {"region":"EDR-KOSHI","vendor":"Optinet","warehouse":"Itahari","podStations":["Belbari POD Station","Biratnagar POD Station","Dharan POD Station","Inaruwa POD Station","Itahari POD Station"]},
  {"region":"EDR-MECHI","vendor":"FiberKing","warehouse":"Birtamode","podStations":["Baundangi POD Station","Birtamode POD Station","Damak POD Station","Haldibari POD Station","Kakadvitta POD Station","Surunga POD Station"]},
  {"region":"FWDR","vendor":"Optinet","warehouse":"Dhangadhi","podStations":["Attariya POD Station","Dhangadhi POD Station","Hasuliya POD Station"]},
  {"region":"FWDR","vendor":"Optinet","warehouse":"Mahendranaga","podStations":["Mahendranagar POD Station","Jhalari POD Station","Dodharachandani POD Station"]},
  {"region":"MWDR","vendor":"Smarten","warehouse":"Kohalpur","podStations":["Bansgadi POD station","Kohalpur POD Station","Nepalgunj POD Station"]},
  {"region":"MWDR","vendor":"Smarten","warehouse":"Surkhet","podStations":["Surkhet POD Station"]},
  {"region":"MWDR","vendor":"Smarten","warehouse":"Tulsipur","podStations":["Dang POD Station","Lamahi POD Station","Tulsipur POD Station"]},
  {"region":"WDR_BUT","vendor":"DMN WDR_BUT Onsite Support","warehouse":"DMN WDR_BUT Onsite Support (Direct)","podStations":["Bhairawa POD Station","Butwal POD Station","Devinagar POD station","Kawasoti POD Station","Nayagaun POD Station","Palpa POD Station"]},
  {"region":"WDR_POK","vendor":"Optinet","warehouse":"Damauli","podStations":["Damauli POD Station"]},
  {"region":"WDR_POK","vendor":"Optinet","warehouse":"Gorkha","podStations":["Gorkha POD Station"]},
  {"region":"WDR_POK","vendor":"Optinet","warehouse":"Pokhara","podStations":["Pokhara POD Station","Syangja POD Station"]}
]


class Command(BaseCommand):
    help = "Seed Region/Vendor/Warehouse/PODStation from the vendor-warehouse reference file"

    def handle(self, *args, **options):
        created_wh = 0
        for row in HIERARCHY:
            region, _ = Region.objects.get_or_create(name=row["region"])
            vendor, _ = Vendor.objects.get_or_create(name=row["vendor"])
            wh, wh_created = Warehouse.objects.get_or_create(
                vendor=vendor, name=row["warehouse"], defaults={"region": region}
            )
            if wh_created:
                created_wh += 1
            for pod_name in row["podStations"]:
                PODStation.objects.get_or_create(warehouse=wh, name=pod_name)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Region.objects.count()} regions, {Vendor.objects.count()} vendors, "
            f"{Warehouse.objects.count()} warehouses ({created_wh} new), "
            f"{PODStation.objects.count()} POD stations."
        ))
