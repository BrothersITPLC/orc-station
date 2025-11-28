from rest_framework import serializers

from users.models import CustomUser
from users.serializers import UserSerializer
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from ..models import Checkin, Declaracion
from .declaracion import DeclaracionSerializer


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
