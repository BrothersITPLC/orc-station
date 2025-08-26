from rest_framework import serializers

from declaracions.models import Commodity
from declaracions.serializers import CommoditySerializer
from exporters.models import TaxPayerType
from exporters.serializers import TaxPayerTypeSerializer
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from .models import Tax


class TaxSerializer(serializers.ModelSerializer):
    commodity = CommoditySerializer(read_only=True)
    commodity_id = serializers.PrimaryKeyRelatedField(
        queryset=Commodity.objects.all(), source="commodity", write_only=True
    )
    station = WorkStationSerializer(read_only=True)
    station_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkStation.objects.all(), write_only=True, source="station"
    )
    tax_payer_type = TaxPayerTypeSerializer(read_only=True)
    tax_payer_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TaxPayerType.objects.all(), write_only=True, source="tax_payer_type"
    )

    class Meta:
        model = Tax
        fields = "__all__"
