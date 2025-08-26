from rest_framework import serializers

from address.serializers import WoredaSerializer

from .models import Exporter, TaxPayerType


class TaxPayerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxPayerType
        fields = "__all__"


class ExporterSerializer(serializers.ModelSerializer):
    type = TaxPayerTypeSerializer(read_only=True)
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=TaxPayerType.objects.all(), write_only=True, source="type"
    )
    woreda_name = WoredaSerializer(read_only=True, source="woreda")

    tin_number = serializers.CharField(required=False, allow_null=True)
    license_number = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Exporter
        fields = "__all__"
        read_only_fields = ("created_by",)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
