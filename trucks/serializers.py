from rest_framework import serializers

from .models import Truck, TruckOwner


class TruckOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckOwner
        fields = [
            "first_name",
            "last_name",
            "woreda",
            "kebele",
            "phone_number",
            "home_number",
        ]

    def create(self, validated_data):
        owner = TruckOwner.objects.create(**validated_data)
        return owner

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.woreda = validated_data.get("woreda", instance.woreda)
        instance.kebele = validated_data.get("kebele", instance.kebele)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.home_number = validated_data.get("home_number", instance.home_number)

        instance.save()
        return instance


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

    # def create(self, validated_data):
    #     owner_data = validated_data.pop("owner")
    #     owner = TruckOwner.objects.create(**owner_data)
    #     truck = Truck.objects.create(owner=owner, **validated_data)
    #     return truck

    def create(self, validated_data):
        # TruckOwner instance is already available through the 'owner' field
        return Truck.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Handle updating the truck and the owner
        instance.owner = validated_data.get(
            "owner", instance.owner
        )  # Set owner directly as a TruckOwner instance

        # Update truck fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
