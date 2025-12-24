from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from ..models import CustomUser


class AdminPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for admin password reset.
    
    Allows admin to reset any user's password without requiring the old password.
    """
    user_id = serializers.UUIDField(required=True, help_text="ID of the user whose password will be reset")
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        help_text="New password for the user (minimum 8 characters)"
    )

    def validate_new_password(self, value):
        """
        Validate the new password using Django's password validators.
        """
        validate_password(value)
        return value

    def validate_user_id(self, value):
        """
        Validate that the user exists.
        """
        try:
            CustomUser.objects.get(id=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User with this ID does not exist.")
        return value
