from rest_framework import serializers

from ..models import RegionOrCity, Woreda, ZoneOrSubcity


class RegionOrCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionOrCity
        fields = "__all__"


class ZoneOrSubcitySerializer(serializers.ModelSerializer):
    region = RegionOrCitySerializer(read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=RegionOrCity.objects.all(),
        required=False,
        write_only=True,
        source="region",
    )

    class Meta:
        model = ZoneOrSubcity
        fields = "__all__"


class WoredaSerializer(serializers.ModelSerializer):
    zone = ZoneOrSubcitySerializer(read_only=True)
    zone_id = serializers.PrimaryKeyRelatedField(
        queryset=ZoneOrSubcity.objects.all(),
        required=False,
        write_only=True,
        source="zone",
    )

    class Meta:
        model = Woreda
        fields = "__all__"
