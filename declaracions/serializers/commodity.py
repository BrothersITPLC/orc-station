from rest_framework import serializers

from ..models import Commodity


class CommoditySerializer(serializers.ModelSerializer):

    class Meta:
        model = Commodity
        fields = "__all__"

    def to_internal_value(self, data):
        if "unit_price" in data:
            try:
                data["unit_price"] = int(float(data["unit_price"]) * 100)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {"unit_price": "A valid integer is required."}
                )
        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if "unit_price" in representation:
            representation["unit_price"] = representation["unit_price"] / 100

        return representation
