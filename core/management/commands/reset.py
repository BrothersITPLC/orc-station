from django.core.management.base import BaseCommand
from django.db import connection

from address.models import RegionOrCity, Woreda, ZoneOrSubcity
from declaracions.models import Checkin, Commodity, Declaracion, PaymentMethod
from drivers.models import Driver
from exporters.models import Exporter, TaxPayerType
from tax.models import Tax
from trucks.models import Truck, TruckOwner
from users.models import CustomUser, Department, Report
from workstations.models import WorkedAt, WorkStation


class Command(BaseCommand):
    help = "Deletes all entries in the tables and resets the primary key sequences"

    def handle(self, *args, **kwargs):
        models = [
            Checkin,
            Declaracion,
            Driver,
            Exporter,
            PaymentMethod,
            Commodity,
            TaxPayerType,
            Tax,
            Truck,
            TruckOwner,
            Report,
            WorkedAt,
            Woreda,
            ZoneOrSubcity,
            RegionOrCity,
            CustomUser,
            Department,
            WorkStation,
        ]
        Department.objects.update(created_by=None)
        RegionOrCity.objects.update(created_by=None)
        ZoneOrSubcity.objects.update(created_by=None)
        Woreda.objects.update(created_by=None)
        for model in models:
            model.objects.all().delete()

        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE declaracions_checkin RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE declaracions_declaracion RESTART IDENTITY CASCADE;"
            )
            cursor.execute("TRUNCATE TABLE drivers_driver RESTART IDENTITY CASCADE;")
            cursor.execute(
                "TRUNCATE TABLE exporters_exporter RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE declaracions_paymentmethod RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE declaracions_commodity RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE exporters_taxpayertype RESTART IDENTITY CASCADE;"
            )
            cursor.execute("TRUNCATE TABLE tax_tax RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE trucks_truckowner RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE trucks_truck RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE users_department RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE users_report RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE users_customuser RESTART IDENTITY CASCADE;")
            cursor.execute(
                "TRUNCATE TABLE workstations_workstation RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE workstations_workedat RESTART IDENTITY CASCADE;"
            )
            cursor.execute("TRUNCATE TABLE address_woreda RESTART IDENTITY CASCADE;")
            cursor.execute(
                "TRUNCATE TABLE address_zoneorsubcity RESTART IDENTITY CASCADE;"
            )
            cursor.execute(
                "TRUNCATE TABLE address_regionorcity RESTART IDENTITY CASCADE;"
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully reset tables and primary keys.")
        )
