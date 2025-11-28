from django.db import models

from workstations.models import WorkStation


class LocalStationCredential(models.Model):
    location = models.ForeignKey(
        WorkStation, related_name="workstation_for_sync", on_delete=models.PROTECT
    )
    url = models.CharField(max_length=255)

    api_key = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.location} ({self.api_key[:6]}...)"
