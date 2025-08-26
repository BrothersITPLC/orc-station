from rest_framework import serializers

from declaracions.models import Commodity
from declaracions.serializers import CommoditySerializer
from exporters.models import Exporter
from exporters.serializers import ExporterSerializer
from path.serializers import PathSerializer
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from .models import JourneyWithoutTruck


class JourneyWithoutTruckSerializer(serializers.ModelSerializer):
    exporter = ExporterSerializer(read_only=True)
    destination_point = WorkStationSerializer(read_only=True)
    exporter_id = serializers.PrimaryKeyRelatedField(
        queryset=Exporter.objects.all(), source="exporter", write_only=True
    )
    path_journey = PathSerializer(read_only=True, source="path")

    commodity = CommoditySerializer(read_only=True)
    commodity_id = serializers.PrimaryKeyRelatedField(
        queryset=Commodity.objects.all(), source="commodity", write_only=True
    )

    class Meta:
        model = JourneyWithoutTruck
        fields = "__all__"
