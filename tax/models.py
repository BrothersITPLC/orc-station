from django.db import models

from base.models import BaseModel
from declaracions.models import Commodity


# Create your models here.
class Tax(BaseModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    station = models.ForeignKey("workstations.WorkStation", on_delete=models.CASCADE)
    tax_payer_type = models.ForeignKey(
        "exporters.TaxPayerType", on_delete=models.CASCADE
    )
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)

    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.PROTECT, related_name="taxes", null=True
    )

    class Meta:
        unique_together = ("station", "tax_payer_type", "commodity")

    def __str__(self):
        return f"{self.commodity.name},{self.station.name},{self.tax_payer_type.name}"
