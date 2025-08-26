from rest_framework import serializers

from api.models import StationCredential
from workstations.models import WorkStation


class WorkStationSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkStation
        fields = ["id", "name"]


class StationCredentialSerializer(serializers.ModelSerializer):
    location = WorkStationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkStation.objects.all(), source="location", write_only=True
    )

    class Meta:
        model = StationCredential
        fields = [
            "id",
            "location",
            "location_id",
            "base_url",
            "api_key",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"api_key": {"write_only": True}}
