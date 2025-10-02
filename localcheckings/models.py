from django.db import models

from base.models import BaseModel
from declaracions.models import Commodity, PaymentMethod
from exporters.models import Exporter
from workstations.models import WorkStation


# Create your models here.
class JourneyWithoutTruck(BaseModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ON_GOING", "On Going"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    exporter = models.ForeignKey(
        Exporter, related_name="localJourneys", on_delete=models.RESTRICT
    )
    commodity = models.ForeignKey(
        Commodity, related_name="localJourneys", on_delete=models.RESTRICT, null=True
    )
    path = models.ForeignKey(
        "path.Path", on_delete=models.RESTRICT, null=True, related_name="localJourneys"
    )

    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.RESTRICT,
        related_name="local_journey",
        null=True,
    )
    status = models.CharField(
        max_length=400, null=True, choices=STATUS_CHOICES, default="PENDING"
    )
