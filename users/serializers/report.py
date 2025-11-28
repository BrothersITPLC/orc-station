from rest_framework import serializers

from ..models import Report
from .user import UserSerializer


class ReportSerializer(serializers.ModelSerializer):
    employee = UserSerializer()
    reporter = UserSerializer()
    station = serializers.StringRelatedField()

    class Meta:
        model = Report
        fields = "__all__"
