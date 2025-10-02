# orcSync/functions/zoime_client.py (on STATION)

import json
import logging
import secrets

import requests
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from orcSync.models import ZoimeIntegrationConfig, ZoimeUserSyncStatus
from users.models import CustomUser

logger = logging.getLogger(__name__)


class ZoimeAPIClient:
    _config_cache = None  # Cache config for the singleton client

    def __init__(self):
        self._get_config()  # Ensure config is loaded

        if not self._config.is_enabled:
            raise ImproperlyConfigured(
                "Zoime integration is disabled in configuration."
            )
        if not self._config.base_url:
            raise ImproperlyConfigured("Zoime API base URL is not configured.")
        if not self._config.auth_token:
            raise ImproperlyConfigured(
                "Zoime API 'auth_token' is missing. Please provide a valid token manually."
            )

        self.base_url = self._config.base_url.rstrip("/")
        self.post_user_url = f"{self.base_url}/api/User/PostUser"
        self.auth_token = (
            self._config.auth_token
        )  # Use the manually provided token directly

    def _get_config(self):
        """Fetches and caches the Zoime integration configuration."""
        if ZoimeAPIClient._config_cache is None:
            try:
                config = ZoimeIntegrationConfig.objects.first()
                if config is None:
                    raise ZoimeIntegrationConfig.DoesNotExist
                ZoimeAPIClient._config_cache = config
            except ZoimeIntegrationConfig.DoesNotExist:
                raise ImproperlyConfigured(
                    "Zoime Integration Configuration is not set up. "
                    "Please create a ZoimeIntegrationConfig entry in the admin."
                )
        self._config = ZoimeAPIClient._config_cache
        return self._config

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def post_user(
        self, user_instance: CustomUser, zoime_sync_status: ZoimeUserSyncStatus
    ):
        """
        Posts user data to the Zoime API for a given CustomUser instance.
        Manages password generation and storage in ZoimeUserSyncStatus.
        """
        if not self.auth_token:
            logger.error("Zoime API 'auth_token' is not available. Cannot post user.")
            return False, "Authentication token missing"

        # Determine password to use
        plaintext_password = zoime_sync_status.zoime_password
        if not plaintext_password:
            # Generate a new password if none exists (e.g., first sync for this user)
            plaintext_password = secrets.token_urlsafe(16)
            zoime_sync_status.zoime_password = plaintext_password
            # Note: The zoime_sync_status instance will be saved by the calling task
            logger.info(
                f"Generated new random password for Zoime user '{user_instance.username}' (ID: {user_instance.pk}). "
                "This password is now stored in plaintext in ZoimeUserSyncStatus."
            )
        else:
            logger.info(
                f"Using stored plaintext password for Zoime user '{user_instance.username}'."
            )

        # Map CustomUser instance fields to Zoime's expected format
        zoime_user_data = {
            "id": user_instance.pk,
            "role": 2,  # Hardcoded as per requirement.
            "first_name": user_instance.first_name,
            "last_name": user_instance.last_name,
            "email": user_instance.email,
            "username": user_instance.username,
            "password": plaintext_password,  # Include the plaintext password
        }

        # Ensure ID is an int if Zoime expects it
        try:
            zoime_user_data["id"] = int(zoime_user_data["id"])
        except (ValueError, TypeError):
            logger.error(
                f"User ID from CustomUser instance ({user_instance.pk}) "
                f"is not convertible to integer for Zoime API. Skipping user post."
            )
            return False, "Invalid user ID format"

        try:
            response = requests.post(
                self.post_user_url,
                headers=self._get_headers(),
                json=[zoime_user_data],  # Zoime expects an array of user objects
                timeout=15,  # Timeout for the request
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            logger.info(
                f"Successfully posted user '{user_instance.username}' to Zoime API. Response: {response.json()}"
            )
            return True, response.json()
        except requests.RequestException as e:
            logger.error(
                f"Error posting user '{user_instance.username}' to Zoime API: {e}"
            )
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Zoime API Error Response: {e.response.text}")
            return False, str(e)
        except Exception as e:
            logger.error(
                f"Unexpected error while posting user '{user_instance.username}' to Zoime API: {e}"
            )
            return False, str(e)
