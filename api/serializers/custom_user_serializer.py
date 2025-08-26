from rest_framework import serializers

from users.models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    # role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "role",
            "first_name",
            "last_name",
            "email",
            "username",
            "password",
        ]
