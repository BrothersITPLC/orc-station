from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel


class TruckOwner(BaseModel):
    """
    Represents the owner of a truck, including personal details and contact information.
    """

    first_name = models.CharField(
        max_length=100, help_text=_("First name of the owner")
    )
    last_name = models.CharField(max_length=100, help_text=_("Last name of the owner"))
    woreda = models.ForeignKey(
        "address.Woreda",
        on_delete=models.RESTRICT,
        related_name="truck",
        null=True,
        blank=True,
        help_text=_("Woreda where the truck owner resides"),
    )
    kebele = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    phone_number = models.CharField(
        max_length=15, help_text=_("Phone number"), unique=True
    )
    home_number = models.CharField(
        max_length=100, null=True, blank=True, help_text=_("Home number")
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = _("Owner")
        verbose_name_plural = _("Owners")
        ordering = ["last_name", "first_name"]


class Truck(BaseModel):
    """
    Represents a truck, including details about its specifications, ownership, and status.
    """

    owner = models.ForeignKey(
        TruckOwner,
        on_delete=models.CASCADE,
        related_name="trucks",
        help_text=_("Owner of the truck"),
    )
    truck_id = models.IntegerField(null=True, unique=True)
    plate_number = models.CharField(
        max_length=100, unique=True, help_text=_("Current plate number of the truck")
    )
    truck_brand = models.CharField(
        max_length=100, null=True, blank=True, help_text=_("Brand of the truck")
    )
    country_of_origin = models.CharField(
        max_length=100, help_text=_("Country where the truck was made")
    )
    truck_model = models.CharField(max_length=100, help_text=_("Model of the truck"))
    year_of_manufacture = models.PositiveIntegerField(
        validators=[MinValueValidator(1886), MaxValueValidator(2024)],
        help_text=_("Year the truck was manufactured"),
    )
    chassis_number = models.CharField(
        max_length=100, unique=True, help_text=_("Chassis number of the truck")
    )
    engine_number = models.CharField(
        max_length=100, unique=True, help_text=_("Engine number of the truck")
    )
    color = models.CharField(max_length=50, help_text=_("Primary color of the truck"))
    oil_type = models.CharField(
        max_length=50, help_text=_("Type of oil used by the truck")
    )
    horse_power = models.PositiveIntegerField(help_text=_("Horsepower of the truck"))
    truck_weight = models.FloatField(
        null=True, blank=True, help_text=_("Weight of the truck in kilograms")
    )
    engine_displacement = models.PositiveIntegerField(
        help_text=_("Engine displacement in cubic centimeters (cc)")
    )
    truck_status = models.CharField(
        max_length=400, null=True, help_text=_("Status of the truck")
    )
    loading_capacity_kg = models.PositiveIntegerField(
        help_text=_("Loading capacity of the truck in kilograms")
    )
    truck_image = models.ImageField(
        upload_to="images/",
        null=True,
        help_text=_("Image of the truck"),
    )

    truck_plate_image = models.ImageField(
        upload_to="images/",
        null=True,
        help_text=_("Image of the truck_plate"),
    )

    def __str__(self):
        return self.plate_number

    class Meta:
        verbose_name = _("Truck")
        verbose_name_plural = _("Trucks")
        ordering = ["plate_number"]
