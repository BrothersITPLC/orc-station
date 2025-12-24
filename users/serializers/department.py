from rest_framework import serializers

from ..models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "created_at", "updated_at", "created_by"]
        extra_kwargs = {
            "created_by": {"required": False},
        }

        def __str__(self):
            return self.name
