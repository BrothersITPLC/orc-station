import json

import requests
from django.core.exceptions import ImproperlyConfigured

from orcSync.models import ZoimeIntegrationConfig


class ZoimeAPIClient:
    """
    A client for communicating with the Zoime third-party API.
    Handles authentication to get a Bearer token and posting user data.
    """

    _config = None
    _token_cache = None  # Internal cache for the authentication token

    def __init__(self):
        if self._config is None:
            try:
                # Fetch the singleton configuration for Zoime integration
                self._config = ZoimeIntegrationConfig.objects.first()
                if self._config is None:
                    raise ZoimeIntegrationConfig.DoesNotExist
                if not self._config.is_enabled:
                    raise ImproperlyConfigured(
                        "Zoime integration is disabled in settings."
                    )
            except ZoimeIntegrationConfig.DoesNotExist:
                raise ImproperlyConfigured(
                    "Zoime Integration Configuration is not set up. "
                    "Please create a ZoimeIntegrationConfig entry in the admin."
                )

        if not self._config.base_url:
            raise ImproperlyConfigured(
                "Zoime base URL is not configured in ZoimeIntegrationConfig."
            )

    def _get_base_url(self):
        """Ensures the base URL is correctly formatted."""
        return self._config.base_url.rstrip("/")

    def _authenticate(self):
        """
        Authenticates with the Zoime API to obtain a Bearer token.
        Caches the token for subsequent requests within the same client instance.
        """
        if self._token_cache:
            return self._token_cache  # Use cached token if available

        auth_url = f"{self._get_base_url()}/api/Token/Authenticate"
        # Hardcoded credentials as per the prompt
        auth_payload = {"UserName": "WBS", "Password": "WBS"}

        try:
            response = requests.post(auth_url, json=auth_payload, timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            token = data.get("Token") or data.get(
                "token"
            )  # Account for potential case variations
            if not token:
                raise ValueError(
                    "Authentication successful but no token received in response."
                )
            self._token_cache = token  # Cache the newly obtained token
            return token
        except requests.RequestException as e:
            print(f"Error authenticating with Zoime API at {auth_url}: {e}")
            raise  # Re-raise to be caught by the calling view
        except ValueError as e:
            print(f"Zoime API authentication response error: {e}")
            raise

    def _get_headers(self):
        """Constructs the authorization headers with the Bearer token."""
        token = self._authenticate()  # Ensures we have a valid token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def post_user(self, user_data_list):
        """
        Posts a list of user data to the Zoime API's /api/User/PostUser endpoint.
        `user_data_list` should be a list of dictionaries, each formatted
        as required by Zoime's API.
        """
        if not user_data_list:
            return True, "No user data to post."

        post_user_url = f"{self._get_base_url()}/api/User/PostUser"

        try:
            headers = self._get_headers()
            response = requests.post(
                post_user_url, headers=headers, json=user_data_list, timeout=30
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return True, response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error posting user to Zoime: {e.response.text}")
            # Return parsed error from Zoime API if available, else generic error
            try:
                return False, e.response.json()
            except json.JSONDecodeError:
                return False, {"detail": f"Zoime API error: {e.response.text}"}
        except requests.RequestException as e:
            print(f"Network Error posting user to Zoime: {e}")
            return False, {"detail": f"Network error during Zoime API call: {e}"}
        except Exception as e:
            print(f"An unexpected error occurred during Zoime API call: {e}")
            return False, {"detail": f"An unexpected error occurred: {e}"}
