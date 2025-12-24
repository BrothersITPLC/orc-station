from rest_framework import serializers

from ..models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = "__all__"


class TableNameSerializer(serializers.Serializer):
    table_name = serializers.CharField(max_length=255)
