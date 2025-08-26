# workstations/serializers.py

from rest_framework import serializers

from address.models import Woreda
from address.serializers import WoredaSerializer  # Assuming you have a WoredaSerializer
from users.models import CustomUser
from users.serializers import UserSerializer  # Assuming you have a UserSerializer

from .models import WorkedAt, WorkStation


class WorkStationSerializer(serializers.ModelSerializer):
    managed_by = UserSerializer(required=False, read_only=True)
    woreda_id = serializers.PrimaryKeyRelatedField(
        queryset=Woreda.objects.all(), source="woreda", write_only=True
    )
    woreda = WoredaSerializer(read_only=True)

    # managed_by_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), source='managed_by', write_only=True)
    class Meta:
        model = WorkStation
        fields = "__all__"


class WorkedAtSerializer(serializers.ModelSerializer):
    station = WorkStationSerializer(read_only=True)
    employee = UserSerializer(read_only=True)
    station_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkStation.objects.all(), source="station", write_only=True
    )
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="employee", write_only=True
    )

    class Meta:
        model = WorkedAt
        fields = "__all__"
