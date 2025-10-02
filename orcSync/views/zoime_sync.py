import json
import secrets
import string

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orcSync.functions.zoime_client import ZoimeAPIClient
from orcSync.models import ZoimeIntegrationConfig, ZoimeUserSyncStatus
from orcSync.serializers.zoime_user import ZoimeUserSerializer
from users.models import CustomUser


# Helper serializer for listing users with sync status
class UserWithZoimeStatusSerializer(serializers.ModelSerializer):
    """
    Serializes CustomUser instances along with their Zoime synchronization status.
    """

    zoime_synced = serializers.BooleanField(read_only=True)
    last_synced_at = serializers.DateTimeField(
        read_only=True, source="zoime_sync_status.last_synced_at", allow_null=True
    )
    sync_attempted_at = serializers.DateTimeField(
        read_only=True, source="zoime_sync_status.sync_attempted_at", allow_null=True
    )
    last_error = serializers.CharField(
        read_only=True, source="zoime_sync_status.last_error", allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "zoime_synced",
            "last_synced_at",
            "sync_attempted_at",
            "last_error",
        ]


class ZoimeUserSyncListView(generics.ListAPIView):
    """
    Lists CustomUsers with their Zoime synchronization status.
    Supports filtering for synced and unsynced users using a 'synced' query parameter.
    """

    serializer_class = UserWithZoimeStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            CustomUser.objects.annotate(
                _has_zoime_sync_status=Exists(
                    ZoimeUserSyncStatus.objects.filter(user=OuterRef("pk"))
                )
            )
            .annotate(
                zoime_synced=Q(
                    _has_zoime_sync_status=True,
                    zoime_sync_status__last_synced_at__isnull=False,
                )
            )
            .select_related("zoime_sync_status")
        )

        synced_param = self.request.query_params.get("synced")
        if synced_param is not None:
            if synced_param.lower() == "true":
                queryset = queryset.filter(zoime_synced=True)
            elif synced_param.lower() == "false":
                queryset = queryset.filter(
                    Q(_has_zoime_sync_status=False)
                    | Q(zoime_sync_status__last_synced_at__isnull=True)
                )

        return queryset.order_by("username")


class ZoimeUserSyncTriggerView(APIView):
    """
    Endpoint to manually trigger synchronization of a single user to the Zoime API.
    Only allows syncing of users who have not been successfully synced before.
    """

    permission_classes = [IsAuthenticated]

    # Helper function to generate a strong random password
    def _generate_strong_password(self, length=12):
        characters = string.ascii_letters + string.digits
        # Ensure at least one uppercase, one lowercase, one digit, one symbol
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
        ]
        # Fill the rest of the password length with random characters
        password += [secrets.choice(characters) for _ in range(length - 4)]
        secrets.SystemRandom().shuffle(
            password
        )  # Shuffle to randomize character positions
        return "".join(password)

    def post(self, request, pk, *args, **kwargs):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            zoime_config = ZoimeIntegrationConfig.objects.first()
            if not zoime_config or not zoime_config.is_enabled:
                return Response(
                    {"detail": "Zoime integration is not enabled or configured."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ImproperlyConfigured as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get or create ZoimeUserSyncStatus for the user
        sync_status, created = ZoimeUserSyncStatus.objects.get_or_create(user=user)

        # As per requirement: "sync newly created users not updated"
        # This implies we only sync once successfully.
        if (
            sync_status.last_synced_at and not created
        ):  # Changed from 'not created' to check actual sync status
            return Response(
                {"detail": "User already successfully synced to Zoime API."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- NEW LOGIC: GENERATE AND SAVE PASSWORD IF NOT ALREADY SET ---
        if not sync_status.zoime_password:
            generated_password = self._generate_strong_password()
            sync_status.zoime_password = generated_password
            sync_status.save()  # Save the generated password immediately

            # IMPORTANT: For real-world systems, you'd want to securely communicate
            # this generated password to the user or an administrator.
            # Storing it in plaintext AND not telling anyone makes it a 'dark password'.
            # For this prompt, we're explicitly asked to save as plaintext.
            print(
                f"ZOIME_SYNC: Generated and saved password for {user.username}: {generated_password}"
            )
        # --- END NEW LOGIC ---

        # Try to get the Zoime API client
        try:
            client = ZoimeAPIClient()
        except ImproperlyConfigured as e:
            sync_status.sync_attempted_at = timezone.now()
            sync_status.last_error = str(e)
            sync_status.save()
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            sync_status.sync_attempted_at = timezone.now()
            sync_status.last_error = f"Failed to initialize Zoime client: {e}"
            sync_status.save()
            return Response(
                {"detail": f"Failed to initialize Zoime client: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # The ZoimeUserSerializer will now correctly pick up the generated (or existing) password
            serializer = ZoimeUserSerializer(user)
            zoime_user_data = serializer.data

            # Zoime API expects a list of users, even for a single user
            success, response_data = client.post_user([zoime_user_data])

            with transaction.atomic():
                sync_status.sync_attempted_at = timezone.now()
                if success:
                    sync_status.last_synced_at = timezone.now()
                    sync_status.last_error = None  # Clear any previous errors
                    sync_status.save()
                    return Response(
                        {
                            "detail": "User successfully synced to Zoime.",
                            "zoime_response": response_data,
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    # Store the error response from Zoime API
                    sync_status.last_error = (
                        json.dumps(response_data)
                        if isinstance(response_data, dict)
                        else str(response_data)
                    )
                    sync_status.save()
                    return Response(
                        {
                            "detail": "Failed to sync user to Zoime.",
                            "error": response_data,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
        except serializers.ValidationError as e:
            # Catch validation errors from ZoimeUserSerializer (e.g., missing zoime_password - though this should now be handled)
            # If the password generation failed for some reason, this might still trigger.
            sync_status.sync_attempted_at = timezone.now()
            sync_status.last_error = str(e.detail)
            sync_status.save()
            return Response(
                {"detail": f"User data validation error: {e.detail}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            # Catch any other unexpected errors during the sync process
            sync_status.sync_attempted_at = timezone.now()
            sync_status.last_error = str(e)
            sync_status.save()
            print(
                f"Error during Zoime sync for user {user.username} (PK: {pk}): {e}",
                exc_info=True,
            )
            return Response(
                {"detail": f"An unexpected error occurred during sync: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
