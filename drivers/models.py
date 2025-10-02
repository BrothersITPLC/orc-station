from django.db import models

from base.models import BaseModel


# Create your models here.
class Driver(BaseModel):
    first_name = models.CharField(max_length=400)

    last_name = models.CharField(max_length=400)

    email = models.CharField(max_length=400, unique=True, null=True)

    phone_number = models.CharField(max_length=400)

    woreda = models.ForeignKey(
        "address.Woreda",
        on_delete=models.SET_NULL,
        related_name="drivers",
        null=True,
        blank=True,
    )

    kebele = models.CharField(max_length=400, blank=True, null=True)

    license_number = models.CharField(max_length=400, unique=True)
    register_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.PROTECT, related_name="drivers", null=True
    )
    register_place = models.ForeignKey(
        "workstations.WorkStation",
        on_delete=models.PROTECT,
        related_name="drivers",
        null=True,
    )

    def __str__(self):
        return f"{self.first_name} {self.first_name} ({self.license_number})"
