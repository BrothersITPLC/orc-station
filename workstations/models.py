from django.db import models, transaction
from django.db.models import F, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from base.models import BaseModel
from users.models import CustomUser


# Create your models here.
class WorkStation(BaseModel):
    name = models.CharField(max_length=400, unique=True)
    machine_number = models.CharField(max_length=400, unique=True)

    woreda = models.ForeignKey(
        "address.Woreda", on_delete=models.RESTRICT, related_name="workstations"
    )
    kebele = models.CharField(max_length=200)
    managed_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.RESTRICT,
        related_name="workstations",
        null=True,
    )

    def __str__(self):
        return self.name


class WorkedAt(BaseModel):
    station = models.ForeignKey(WorkStation, on_delete=models.RESTRICT)
    employee = models.ForeignKey(CustomUser, on_delete=models.RESTRICT)
    leave_time = models.DateTimeField(null=True)
    assigner = models.ForeignKey(
        CustomUser,
        on_delete=models.RESTRICT,
        related_name="assigned_workstations",
        null=True,
    )

    def __str__(self):
        return f"{self.employee.first_name} works at {self.station.name}"
