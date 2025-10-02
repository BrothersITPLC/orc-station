from django.db import models
from django.db.models import F, Max, Q

from base.models import BaseModel
from workstations.models import WorkStation


# Create your models here.
class Path(BaseModel):
    name = models.CharField(max_length=100, null=True)
    # start_station = models.ForeignKey(
    #     WorkStation, on_delete=models.RESTRICT, related_name="path_start"
    # )
    # destination_station = models.ForeignKey(
    #     WorkStation, on_delete=models.RESTRICT, related_name="path_destination"
    # )
    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.RESTRICT, related_name="path_created_by"
    )

    def __str__(self):
        return self.name


class PathStation(BaseModel):

    path = models.ForeignKey(
        Path, on_delete=models.CASCADE, related_name="path_stations"
    )

    station = models.ForeignKey(
        WorkStation, on_delete=models.RESTRICT, related_name="path_station"
    )
    order = models.PositiveBigIntegerField()

    class Meta:
        unique_together = (("path", "station"), ("path", "order"))

    def save(self, *args, **kwargs):
        # Prevent start and destination stations from being added to PathStation
        # if (
        #     self.station == self.path.start_station
        #     or self.station == self.path.destination_station
        # ):
        #     raise ValueError(
        #         "The station cannot be the start or destination station for the path."
        #     )

        # if self.path.start_station == self.path.destination_station:
        #     raise ValueError(
        #         "destination station and start station have same path can not have path in between."
        #     )

        if (
            not self.order
        ):  # Only set the order if it is not already set (i.e., during creation)
            max_order = PathStation.objects.filter(path=self.path).aggregate(
                Max("order")
            )["order__max"]
            self.order = (max_order or 0) + 1  # Set to 1 if no existing orders

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.path.name} - {self.station.name} (Sequence: {self.sequence})"
