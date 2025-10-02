from django.db import models

from base.models import BaseModel
from workstations.models import WorkStation


class LocalStationCredential(BaseModel):
    location = models.ForeignKey(
        WorkStation, related_name="workstation_for_sync", on_delete=models.PROTECT
    )
    url = models.CharField(max_length=255)

    api_key = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.location} ({self.api_key[:6]}...)"
