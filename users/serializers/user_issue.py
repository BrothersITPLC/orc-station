from django.contrib.auth.models import Group
from rest_framework import serializers

from address.serializers import WoredaSerializer

from ..models import CustomUser, Department
from .department import DepartmentSerializer
from .group import GroupSerializer


class IssueUserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False
    )
    total_reports = serializers.IntegerField(read_only=True)
    unread_reports = serializers.IntegerField(read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=True
    )
    woreda_name = WoredaSerializer(source="woreda", required=False, read_only=True)

    role_name = GroupSerializer(read_only=True, source="role")
    department_name = DepartmentSerializer(read_only=True, source="department")

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "profile_image",
            "email_verified",
            "department",
            "role",
            "role_name",
            "total_reports",
            "woreda_name",
            "department_name",
            "gender",
            "unread_reports",
        ]

    def get_total_reports(self, obj):
        return obj.total_reports

    def get_unread_reports(self, obj):
        return obj.unread_reports
