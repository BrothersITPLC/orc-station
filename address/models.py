from django.db import models


# Create your models here.
class RegionOrCity(models.Model):
    """
    Represents a region or city entity.

    Attributes:
        name (str): The name of the region or city, which must be unique.
        created_at (datetime): The timestamp when the region or city was created.
        updated_at (datetime): The timestamp when the region or city was last updated.
        created_by (ForeignKey): A reference to the user who created this region or city.
    """

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.RESTRICT, null=True
    )

    class Meta:
        def __str__(self) -> str:
            return self.name


class ZoneOrSubcity(models.Model):
    """
    Represents a zone or sub-city entity within a region or city.

    Attributes:
        name (str): The name of the zone or sub-city, which must be unique.
        region (ForeignKey): A reference to the region or city that this zone or sub-city belongs to.
        created_at (datetime): The timestamp when the zone or sub-city was created.
        updated_at (datetime): The timestamp when the zone or sub-city was last updated.
        created_by (ForeignKey): A reference to the user who created this zone or sub-city.
    """

    name = models.CharField(max_length=100, unique=True)
    region = models.ForeignKey(
        RegionOrCity, on_delete=models.CASCADE, related_name="zones"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.RESTRICT, null=True
    )

    class Meta:
        def __str__(self) -> str:
            return self.name


class Woreda(models.Model):
    """
    Represents a woreda entity within a zone or sub-city.

    Attributes:
        name (str): The name of the woreda, which must be unique.
        zone (ForeignKey): A reference to the zone or sub-city that this woreda belongs to.
        created_at (datetime): The timestamp when the woreda was created.
        updated_at (datetime): The timestamp when the woreda was last updated.
        created_by (ForeignKey): A reference to the user who created this woreda.
    """

    name = models.CharField(max_length=100, unique=True)
    zone = models.ForeignKey(
        ZoneOrSubcity, on_delete=models.RESTRICT, related_name="woredas"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.RESTRICT, null=True, related_name="woredas"
    )

    class Meta:
        def __str__(self) -> str:
            return self.name
