from rest_framework import serializers

from drivers.models import Driver
from drivers.serializers import DriverSerializer
from exporters.models import Exporter
from exporters.serializers import ExporterSerializer
from path.serializers import PathSerializer
from trucks.models import Truck
from trucks.serializers import TruckSerializer
from users.serializers import UserSerializer
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from ..models import Commodity, Declaracion
from .commodity import CommoditySerializer


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
