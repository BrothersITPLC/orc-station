import hashlib
import time

from django.core.exceptions import ValidationError
from django.db import models

from base.models import BaseModel


def generate_time_based_hash_id(user_id):
    timestamp = str(time.time())
    combined_input = f"{user_id}-{timestamp}"
    hash_object = hashlib.sha256(combined_input.encode())
    short_hash = hash_object.hexdigest()[:8]
    unique_id = f"ORC{short_hash}"
    return unique_id


class TaxPayerType(BaseModel):
    name = models.CharField(max_length=400, unique=True)
    description = models.CharField(max_length=1000, null=True)
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="taxpayer_types",
        null=True,
    )

    def __str__(self):
        return self.name


class Exporter(BaseModel):
    GENDER_CHOICES = [
        ("Female", "Female"),
        ("Male", "Male"),
    ]
    first_name = models.CharField(max_length=100, help_text=("First name of the owner"))
    middle_name = models.CharField(
        max_length=100, null=True, help_text=("Middle name of the owner")
    )
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES, default="Male")
    mother_name = models.CharField(
        max_length=100, null=True, help_text=("Mother name of the owner")
    )
    last_name = models.CharField(max_length=100, help_text=("Last name of the owner"))
    unique_id = models.CharField(max_length=500, unique=True, null=True, blank=True)
    type = models.ForeignKey(
        TaxPayerType,
        on_delete=models.PROTECT,
        related_name="exporters",
        null=True,
        blank=True,
    )

    woreda = models.ForeignKey(
        "address.Woreda", on_delete=models.RESTRICT, related_name="exporters"
    )
    kebele = models.CharField(
        max_length=200,
        null=True,
    )

    phone_number = models.CharField(max_length=15, unique=True)

    tin_number = models.CharField(max_length=400, null=True, blank=True, unique=True)
    register_place = models.ForeignKey(
        "workstations.WorkStation",
        on_delete=models.PROTECT,
        related_name="exporters",
        null=True,
    )
    license_number = models.CharField(
        max_length=400, unique=True, blank=True, null=True
    )

    register_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="exporters",
        null=True,
    )

    def __str__(self):
        return f"{self.first_name} ({self.license_number})"

    def clean(self):
        super().clean()
        if self.tin_number:
            if not self.tin_number.isdigit() or len(self.tin_number) != 10:
                raise ValidationError(
                    {"tin_number": "TIN number must be exactly 10 digits."}
                )

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = generate_time_based_hash_id(self.id)
        self.clean()
        super(Exporter, self).save(*args, **kwargs)
