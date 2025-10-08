from decimal import Decimal

from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import annotate_revenue_on_checkins
from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def stats_overview(request):
    """
    Provides a high-level overview of key statistics including total revenue,
    total incremental weight, active check-in stations, and unique taxpayers.

    This endpoint aggregates data across all successful check-ins. It efficiently
    calculates total revenue and total incremental weight by leveraging
    the `annotate_revenue_on_checkins` helper function to perform these
    computations at the database level. It also identifies the number of
    workstations that have processed at least one check-in and counts distinct
    taxpayers (exporters) from both declaration-based and local journey check-ins.

    Returns:
        Response: A dictionary containing the aggregated statistics.
        Example:
        {
            "totalRevenue": 123456.78,
            "totalWeight": 987654.32,
            "activeStations": 5,
            "uniqueTaxpayers": 150,
        }
    """
    # 1. Fetch all relevant check-ins
    # Assuming "all" means all successful check-ins for the overview
    base_checkins_query = Checkin.objects.filter(status__in=["pass", "paid", "success"])

    # 2. Annotate check-ins with incremental weight and revenue using the helper
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 3. Aggregate total revenue and total incremental weight
    # This replaces the inefficient Python loop
    revenue_and_weight_aggregates = checkins_with_revenue.aggregate(
        total_revenue_sum=Sum("revenue"),
        total_incremental_weight_sum=Sum("incremental_weight"),
    )

    total_revenue = revenue_and_weight_aggregates.get(
        "total_revenue_sum", Decimal(0)
    ) or Decimal(0)
    total_weight = revenue_and_weight_aggregates.get(
        "total_incremental_weight_sum", Decimal(0)
    ) or Decimal(0)

    # 4. Calculate active stations
    # This filters WorkStation objects that have at least one associated Checkin record.
    active_stations = (
        WorkStation.objects.filter(checkins__isnull=False).distinct().count()
    )

    # 5. Calculate unique taxpayers (exporters)
    # Uses Coalesce to count unique exporters regardless of whether they are linked
    # via a 'declaracion' or 'localJourney'.
    unique_taxpayers = (
        checkins_with_revenue.annotate(
            exporter_id=Coalesce(
                "declaracion__exporter__id", "localJourney__exporter__id"
            )
        )
        .filter(
            exporter_id__isnull=False
        )  # Only count if an exporter is actually linked
        .values("exporter_id")
        .distinct()
        .count()
    )

    # 6. Response (unchanged structure to maintain frontend compatibility)
    return Response(
        {
            "totalRevenue": float(total_revenue),
            "totalWeight": float(total_weight),
            "activeStations": active_stations,
            "uniqueTaxpayers": unique_taxpayers,
        }
    )
