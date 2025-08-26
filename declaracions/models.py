from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


# Create your models here.
class Commodity(models.Model):
    name = models.CharField(max_length=400, unique=True)
    unit_price = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="commodities",
        null=True,
    )

    def __str__(self):
        return self.name


class Declaracion(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ON_GOING", "On Going"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    declaracio_number = models.CharField(
        max_length=400, unique=True, null=True, blank=True
    )
    register_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="declaracions",
        null=True,
    )

    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.PROTECT,
        related_name="declaracions",
        null=True,
    )
    truck = models.ForeignKey(
        "trucks.Truck", on_delete=models.PROTECT, related_name="declaracions"
    )
    exporter = models.ForeignKey(
        "exporters.Exporter",
        on_delete=models.PROTECT,
        related_name="declaracions",
        null=True,
    )

    status = models.CharField(max_length=400, choices=STATUS_CHOICES, default="PENDING")

    path = models.ForeignKey(
        "path.Path", on_delete=models.PROTECT, related_name="declaracions", null=True
    )

    commodity = models.ForeignKey(
        Commodity, on_delete=models.PROTECT, related_name="declaracions", null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.declaracio_number or "Unnamed Declaracion"


class PaymentMethod(models.Model):
    name = models.CharField(max_length=400, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Checkin(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("pass", "Pass"),
        ("unpaid", "Unpaid"),
        ("success", "Success"),
        ("paid", "Paid"),
    ]

    Tage = models.CharField(max_length=400, null=True, unique=True)
    receipt_number = models.CharField(
        max_length=500, null=True, blank=True, unique=True
    )
    deduction = models.PositiveBigIntegerField(default=0)
    checkin_time = models.DateTimeField(auto_now_add=True)
    declaracion = models.ForeignKey(
        Declaracion, on_delete=models.PROTECT, related_name="checkins", null=True
    )
    localJourney = models.ForeignKey(
        "localcheckings.JourneyWithoutTruck",
        on_delete=models.RESTRICT,
        related_name="checkins",
        null=True,
    )

    payment_accepter = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="checkins_accepter",
        null=True,
    )

    station = models.ForeignKey(
        "workstations.WorkStation", on_delete=models.PROTECT, related_name="checkins"
    )

    employee = models.ForeignKey(
        "users.CustomUser", on_delete=models.PROTECT, related_name="checkins", null=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default="unpaid")
    transaction_key = models.CharField(max_length=1000, null=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name="checkins", null=True
    )
    confirmation_code = models.CharField(max_length=500, null=True)
    net_weight = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(null=True)
    unit_price = models.PositiveBigIntegerField(default=0)
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(localJourney__isnull=False, declaracion__isnull=True)
                | Q(localJourney__isnull=True, declaracion__isnull=False),
                name="declaracion_or_localJourney_not_both",
            ),
            models.UniqueConstraint(
                fields=["station", "declaracion"],
                name="unique_station_declaracion",
                condition=Q(localJourney__isnull=True),
            ),
            models.UniqueConstraint(
                fields=["station", "localJourney"],
                name="unique_station_localJourney",
                condition=Q(declaracion__isnull=True),
            ),
        ]


class ManualPayment(models.Model):
    is_bank = models.BooleanField()
    bank_name = models.CharField(max_length=200, blank=True, null=False)
    payer_name = models.CharField(max_length=500, null=True, blank=True)
    bank_account = models.CharField(max_length=500, null=True, blank=True)
    checkin = models.OneToOneField(
        Checkin, on_delete=models.RESTRICT, related_name="manual_payment"
    )


class ChangeTruck(models.Model):
    declaracion = models.ForeignKey(
        "Declaracion",
        on_delete=models.PROTECT,
        related_name="truck_changes",
    )
    original_truck = models.ForeignKey(
        "trucks.Truck",
        on_delete=models.PROTECT,
        related_name="original_truck_changes",
    )
    new_truck = models.ForeignKey(
        "trucks.Truck",
        on_delete=models.PROTECT,
        related_name="new_truck_changes",
    )
    station = models.ForeignKey(
        "workstations.WorkStation",
        on_delete=models.PROTECT,
        related_name="change_station",
    )
    latest_station = models.ForeignKey(
        "workstations.WorkStation",
        on_delete=models.PROTECT,
        related_name="latest_station",
    )
    change_time = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.PROTECT,
        related_name="truck_changes",
        null=False,
    )

    def save(self, *args, **kwargs):
        # Ensure original_truck and new_truck are not the same
        if self.original_truck == self.new_truck:
            raise ValidationError(
                "The new truck cannot be the same as the original truck."
            )

        elif self.declaracion.status not in ["ON_GOING", "PENDING"]:
            raise ValidationError(
                "The  Journey  have journey which is already completed or canceled."
            )

        else:
            declaracion_exist = (
                Declaracion.objects.filter(truck=self.new_truck)
                .filter(status__in=["ON_GOING", "PENDING"])
                .exists()
            )

            if declaracion_exist:
                raise ValidationError(
                    "The new truck have journey which is not completed or canceled."
                )

        # Call the parent class's save method to save the object
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Truck change for Declaracion {self.declaracion.declaracio_number} at {self.station.name} from {self.original_truck} to {self.new_truck}"
