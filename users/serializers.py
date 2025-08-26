from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from address.models import Woreda
from address.serializers import WoredaSerializer
from workstations.models import WorkStation

from .models import CustomUser, Department, Report, UserStatus


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]
        kwargs = {"permissions": {"required": False}, "id": {"read_only": True}}


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "created_at", "updated_at", "created_by"]
        extra_kwargs = {
            "created_by": {"required": False},  # Optional relationship
        }

        def __str__(self):
            return self.name


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
            password=validated_data["password"],  # Write-only password
            phone_number=validated_data.get(
                "phone_number"
            ),  # Use get to avoid KeyError
            role=validated_data.get("role"),
            woreda=validated_data.get("woreda_id"),
            kebele=validated_data.get("kebele"),  # Handle optional role
            profile_image=validated_data.get("profile_image"),
            gender=validated_data.get("gender"),
        )

        return user

    def update(self, instance, validated_data):
        # Update user fields

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
        # Update password if provided
        # password = validated_data.get('password')
        # if password:
        #     instance.set_password(password)

        instance.save()
        return instance

    def validate(self, attrs):

        # Password is required for creation, but optional for updates
        if self.instance is None and "password" not in attrs:
            raise serializers.ValidationError({"password": "This field is ddrequired."})
        return attrs

    def get_latest_status(self, obj):
        latest_status = (
            UserStatus.objects.filter(user=obj).order_by("-created_at").first()
        )
        return latest_status.status if latest_status else None


class IssueUserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False
    )
    total_reports = serializers.IntegerField(read_only=True)
    unread_reports = serializers.IntegerField(read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=True
    )
    woreda_name = WoredaSerializer(source="woreda", required=False, read_only=True)

    role_name = GroupSerializer(read_only=True, source="role")
    department_name = DepartmentSerializer(read_only=True, source="department")

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "profile_image",
            "email_verified",
            "department",
            "role",
            "role_name",
            "total_reports",
            "woreda_name",
            "department_name",
            "gender",
            "unread_reports",
        ]

    def get_total_reports(self, obj):
        return obj.total_reports

    def get_unread_reports(self, obj):
        return obj.unread_reports


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        # if data["new_password"] != data["confirm_new_password"]:
        #     raise serializers.ValidationError(
        #         {"new_password": "New passwords must match."}
        #     )
        validate_password(data["new_password"], self.context["request"].user)
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def get_token(cls, user):
        token = super().get_token(user)
        # Customize token payload if needed
        return token

    def validate(self, attrs):

        data = super().validate(attrs)

        try:

            data.update({"username": self.user.username})
            data.update({"email": self.user.email})
            data.update({"first_name": self.user.first_name})
            data.update({"last_name": self.user.last_name})
            data.update({"id": self.user.id})
            if self.user.current_station:
                data.update({"current_station": (self.user.current_station)})
            else:
                data.update({"current_station": None})

            if self.user.role:

                data.update({"role": self.user.role.name})

            else:
                data.update({"role": None})

            return data
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename"]


class ReportSerializer(serializers.ModelSerializer):
    employee = UserSerializer()
    reporter = UserSerializer()
    station = serializers.StringRelatedField()

    class Meta:
        model = Report
        fields = "__all__"
