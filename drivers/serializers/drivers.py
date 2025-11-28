from rest_framework import serializers

from users.serializers import UserSerializer
from workstations.serializers import WorkStationSerializer

from ..models import Driver


class DriverSerializer(serializers.ModelSerializer):
    register_by = UserSerializer(read_only=True)
    register_place = WorkStationSerializer(read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "license_number",
            "register_by",
            "register_place",
            "created_at",
            "updated_at",
            "woreda",
            "kebele",
        ]
        extra_kwargs = {
            "email": {"required": False},
            "register_place": {"required": False},
        }
