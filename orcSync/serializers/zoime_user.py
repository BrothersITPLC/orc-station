from rest_framework import serializers

from orcSync.models import ZoimeUserSyncStatus
from users.models import CustomUser


class ZoimeUserSerializer(serializers.ModelSerializer):
    """
    Serializes CustomUser instance data into the format expected by the
    Zoime /api/User/PostUser endpoint.
    """

    role = serializers.SerializerMethodField()
    password = serializers.SerializerMethodField()

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

    def get_role(self, obj):
        """
        Maps the CustomUser's role (Django Group) to a numerical role ID
        expected by the Zoime API.
        You MUST define your specific mapping logic here.
        """
        if obj.role:
            return 2
        return 2

    def get_password(self, obj):
        """
        Retrieves the plaintext password for the Zoime API from ZoimeUserSyncStatus.
        WARNING: Storing plaintext passwords in ZoimeUserSyncStatus is a significant
        security risk. Ensure this is understood and mitigated if deployed
        in a production environment. Consider alternative authentication methods
        with Zoime if possible (e.g., hash comparison, API tokens).
        """
        try:
            # Get the associated ZoimeUserSyncStatus for this CustomUser
            sync_status = ZoimeUserSyncStatus.objects.get(user=obj)
            if not sync_status.zoime_password:
                raise serializers.ValidationError(
                    f"Zoime password not set for user {obj.username}."
                )
            return sync_status.zoime_password
        except ZoimeUserSyncStatus.DoesNotExist:
            raise serializers.ValidationError(
                f"Zoime sync status not found for user {obj.username}. "
                "Ensure ZoimeUserSyncStatus is created and 'zoime_password' is set."
            )
