import requests
from django.core.exceptions import ImproperlyConfigured

from orcSync.models import CentralServerCredential


class CentralAPIClient:
    """
    A client for communicating with the central server's sync API.
    Handles authentication and constructs requests.
    """

    _credentials = None

    def _get_credentials(self):
        """
        Fetches and caches the central server credentials.
        Raises an error if credentials are not configured.
        """
        if self._credentials is None:
            try:
                self._credentials = CentralServerCredential.objects.first()
                if self._credentials is None:
                    raise CentralServerCredential.DoesNotExist
            except CentralServerCredential.DoesNotExist:
                raise ImproperlyConfigured(
                    "Central Server Credentials are not configured. "
                    "Please create a CentralServerCredential entry in the admin."
                )
        return self._credentials

    def _get_headers(self):
        """Constructs the authorization headers."""
        # creds = self._get_credentials()
        return {
            "Authorization": f"Api-Key 123",
            "Content-Type": "application/json",
        }

    def _get_url(self, endpoint):
        """Constructs the full URL for a given API endpoint."""
        # creds = self._get_credentials()
        return f"{'http://host.docker.internal:8010'.rstrip('/')}/api/sync/{endpoint.lstrip('/')}"

    def get_pending_changes(self):
        """
        Fetches all pending changes for this workstation from the central server.
        """
        url = self._get_url("get-pending/")
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching pending changes: {e}")
            return None

    def push_changes(self, changes_payload):
        """
        Pushes a list of local changes to the central server.
        """
        if not changes_payload:
            return True, "No changes to push."

        url = self._get_url("push/")
        try:
            response = requests.post(
                url, headers=self._get_headers(), json=changes_payload, timeout=60
            )
            response.raise_for_status()
            return True, response.json()
        except requests.RequestException as e:
            print(f"Error pushing changes: {e}")
            return False, str(e)

    def acknowledge_changes(self, event_ids):
        """
        Acknowledges receipt and successful processing of a list of change event IDs.
        """
        if not event_ids:
            return True, "No events to acknowledge."

        url = self._get_url("acknowledge/")
        payload = {"acknowledged_events": event_ids}
        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=30
            )
            response.raise_for_status()
            return True, response.json()
        except requests.RequestException as e:
            print(f"Error acknowledging changes: {e}")
            return False, str(e)
