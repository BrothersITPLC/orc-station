from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from workstations.serializers import WorkStationSerializer

from .models import Path, PathStation


class PathStationSerializer(ModelSerializer):
    station = serializers.StringRelatedField()
    station_id = serializers.IntegerField(read_only=True, source="station.id")

    class Meta:
        model = PathStation
        fields = "__all__"
        ordering = ["order"]


class PathSerializer(ModelSerializer):
    path_stations = PathStationSerializer(many=True, read_only=True)

    class Meta:
        model = Path
        fields = ["id", "name", "path_stations", "created_by"]
