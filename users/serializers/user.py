from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from address.models import Woreda
from address.serializers import WoredaSerializer

from ..models import CustomUser, Department, UserStatus
from .department import DepartmentSerializer
from .group import GroupSerializer


class UserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False
    )

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=True
    )
    woreda_name = WoredaSerializer(source="woreda", required=False, read_only=True)
    woreda_id = serializers.PrimaryKeyRelatedField(
        queryset=Woreda.objects.all(), required=True, write_only=True
    )
    role_name = GroupSerializer(read_only=True, source="role")
    department_name = DepartmentSerializer(read_only=True, source="department")
    current_station = serializers.StringRelatedField()
    latest_status = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = "__all__"
        first_name: {"required": True}
        last_name: {"required": True}
        extra_kwargs = {"password": {"write_only": True, "required": True}}

    def create(self, validated_data):

        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            department=validated_data["department"],
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number"),
            role=validated_data.get("role"),
            woreda=validated_data.get("woreda_id"),
            kebele=validated_data.get("kebele"),
            profile_image=validated_data.get("profile_image"),
            gender=validated_data.get("gender"),
        )

        return user

    def update(self, instance, validated_data):

        instance.username = validated_data.get("username", instance.username)
        instance.email = validated_data.get("email", instance.email)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.department = validated_data.get("department", instance.department)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.gender = validated_data.get("gender", instance.gender)
        instance.role = validated_data.get("role", instance.role)
        instance.kebele = validated_data.get("kebele", instance.kebele)
        instance.woreda = validated_data.get("woreda_id", instance.woreda)
        print("instance.profile image", instance.profile_image)
        instance.profile_image = validated_data.get(
            "profile_image", instance.profile_image
        )

        instance.save()
        return instance

    def validate(self, attrs):

        if self.instance is None and "password" not in attrs:
            raise serializers.ValidationError({"password": "This field is ddrequired."})
        return attrs

    def get_latest_status(self, obj):
        latest_status = (
            UserStatus.objects.filter(user=obj).order_by("-created_at").first()
        )
        return latest_status.status if latest_status else None
