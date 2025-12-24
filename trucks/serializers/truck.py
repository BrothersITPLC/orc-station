from rest_framework import serializers

from ..models import Truck, TruckOwner


class TruckSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=TruckOwner.objects.all())

    class Meta:
        model = Truck
        fields = "__all__"
        """[
            "owner","truck_id",
            "plate_number",
            "truck_brand",
            "country_of_origin",
            "truck_model",
            "year_of_manufacture",
            "chassis_number",
            "engine_number",
            "color",
            "oil_type",
            "horse_power",
            "truck_weight",
            "engine_displacement",
            "truck_status",
            "loading_capacity_kg",
            "truck_image",
            "truck_plate_image",
            "created_at",
            "updated_at",
        ]"""

    def create(self, validated_data):
        return Truck.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.owner = validated_data.get("owner", instance.owner)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
