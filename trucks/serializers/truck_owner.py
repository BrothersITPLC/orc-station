from rest_framework import serializers

from ..models import TruckOwner


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
