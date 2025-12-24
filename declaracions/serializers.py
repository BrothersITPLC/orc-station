from rest_framework import serializers

from drivers.models import Driver
from drivers.serializers import DriverSerializer
from exporters.models import Exporter
from exporters.serializers import ExporterSerializer
from path.serializers import PathSerializer
from trucks.models import Truck
from trucks.serializers import TruckSerializer
from users.models import CustomUser
from users.serializers import UserSerializer
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from .models import ChangeTruck, Checkin, Commodity, Declaracion, PaymentMethod


class CommoditySerializer(serializers.ModelSerializer):

    class Meta:
        model = Commodity
        fields = "__all__"

    def to_internal_value(self, data):
        # Convert the incoming unit_price data to integer
        if "unit_price" in data:
            try:
                # Multiply by 100 and convert to integer
                data["unit_price"] = int(float(data["unit_price"]) * 100)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {"unit_price": "A valid integer is required."}
                )
        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Divide the unit_price by 100 when serializing
        if "unit_price" in representation:
            representation["unit_price"] = representation["unit_price"] / 100

        return representation


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class DeclaracionSerializer(serializers.ModelSerializer):
    register_by = UserSerializer(required=False, read_only=True)
    driver = DriverSerializer(read_only=True)
    truck = TruckSerializer(read_only=True)
    exporter = ExporterSerializer(read_only=True)
    destination_point = WorkStationSerializer(read_only=True)
    truck_id = serializers.PrimaryKeyRelatedField(
        queryset=Truck.objects.all(), source="truck", write_only=True
    )
    starting_point = WorkStationSerializer(read_only=True)
    destination_point_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkStation.objects.all(), source="destination_point", write_only=True
    )
    driver_id = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.all(), source="driver", write_only=True
    )
    exporter_id = serializers.PrimaryKeyRelatedField(
        queryset=Exporter.objects.all(), source="exporter", write_only=True
    )
    commodity = CommoditySerializer(read_only=True)
    Commodity_id = serializers.PrimaryKeyRelatedField(
        queryset=Commodity.objects.all(), source="commodity", write_only=True
    )
    path_journey = PathSerializer(read_only=True, source="path")

    class Meta:
        model = Declaracion
        fields = "__all__"


class CheckinSerializer(serializers.ModelSerializer):
    station = WorkStationSerializer(read_only=True)
    station_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkStation.objects.all(), source="station", write_only=True
    )
    employee = UserSerializer(required=False, read_only=True)
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="employee", write_only=True
    )
    declaracion = DeclaracionSerializer(read_only=True)
    declaracion_id = serializers.PrimaryKeyRelatedField(
        queryset=Declaracion.objects.all(), source="declaracion", write_only=True
    )

    class Meta:
        model = Checkin
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if "unit_price" in representation:
            representation["unit_price"] = representation["unit_price"] / 100

        return representation


class ChangeTruckSerializer(serializers.ModelSerializer):
    new_truck = TruckSerializer(read_only=True)
    new_truck_id = serializers.PrimaryKeyRelatedField(
        queryset=Truck.objects.all(), source="new_truck"
    )
    latest_station = serializers.ReadOnlyField(source="latest_station.name")

    original_truck = TruckSerializer(read_only=True)
    original_truck_id = serializers.PrimaryKeyRelatedField(
        queryset=Truck.objects.all(), source="original_truck"
    )
    station = serializers.ReadOnlyField(source="station.name")
    created_by = serializers.ReadOnlyField(source="created_by.username")
    declaracion = DeclaracionSerializer(read_only=True)
    declaracion_id = serializers.PrimaryKeyRelatedField(
        queryset=Declaracion.objects.all(), source="declaracion"
    )

    class Meta:
        model = ChangeTruck
        fields = "__all__"
