import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load fixture data from the fixtures directory"

    def handle(self, *args, **kwargs):
        fixtures_dir = os.path.join("fixtures")
        fixtures = [
            "paymentmethod.json",
            "super.json",
            "department.json",
            "groups.json",
            "regionorcity.json",
            "zoneorsubcity.json",
            "woreda.json",
            "workstation.json",
            "users.json",
            "commodity.json",
            "paymentmethod.json",
            "taxpayertype.json",
            "taxlevel.json",
            "trucks.json",
            "driver.json",
            "exporter.json",
            # "path.json",
            # "declaracion.json",
            # "checkin.json",
        ]

        for fixture in fixtures:
            fixture_path = os.path.join(fixtures_dir, fixture)
            if os.path.exists(fixture_path):
                call_command("loaddata", fixture_path)
                self.stdout.write(self.style.SUCCESS(f"Successfully loaded {fixture}"))
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"{fixture} does not exist in the fixtures directory"
                    )
                )
