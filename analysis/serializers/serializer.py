from rest_framework import serializers

from declaracions.models import Checkin
from drivers.models import Driver
from exporters.models import Exporter


class RevenueSerializer(serializers.Serializer):
    tin_number = serializers.CharField(allow_blank=True, required=False)
    exporter_first_name = serializers.CharField(allow_blank=True, required=False)
    exporter_last_name = serializers.CharField(allow_blank=True, required=False)
    commodity_name = serializers.CharField()
    payment_method = serializers.CharField(
        allow_blank=True, required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)

    def validate_amount(self, value):
        return round(value, 2)


class DriverSerializer(serializers.ModelSerializer):
    register_by = serializers.CharField(source="register_by.username")
    register_place = serializers.CharField(source="register_place.name")

    class Meta:
        model = Driver
        fields = "__all__"


class ExporterSerializer(serializers.ModelSerializer):
    register_by = serializers.CharField(source="register_by.username")
    register_place = serializers.CharField(source="register_place.name")
    tax_payer_type = serializers.CharField(source="type.name")

    class Meta:
        model = Exporter
        fields = "__all__"


class TopExportersSerializer(serializers.Serializer):
    tin_number = serializers.CharField(max_length=200, required=False)
    type = serializers.CharField(max_length=400)
    exporter_name = serializers.CharField(max_length=400)
    total_path = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    local_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class TopTrucksSerializer(serializers.Serializer):
    plate_number = serializers.CharField(max_length=100, required=False)
    make = serializers.CharField(max_length=200)
    owner_name = serializers.CharField(max_length=200)
    total_checkins = serializers.IntegerField()
    path_count = serializers.IntegerField()
    total_kg = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
