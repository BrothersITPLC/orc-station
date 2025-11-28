from rest_framework import serializers

from trucks.models import Truck
from trucks.serializers import TruckSerializer

from ..models import ChangeTruck, Declaracion
from .declaracion import DeclaracionSerializer


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
