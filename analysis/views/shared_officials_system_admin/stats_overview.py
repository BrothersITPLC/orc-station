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
    # 3. Aggregate total revenue and total incremental weight (Python)
    # Also calculate unique taxpayers and active stations in the same loop to avoid re-iterating or extra queries
    total_revenue = Decimal(0)
    total_weight = Decimal(0)
    unique_exporter_ids = set()
    active_station_ids = set()

    for checkin in checkins_with_revenue:
        # Sum revenue and weight
        rev = checkin.revenue or Decimal(0)
        w = checkin.incremental_weight or Decimal(0)
        total_revenue += rev
        total_weight += w

        # Unique Taxpayers
        # Exporters can be linked via declaracion or localJourney
        # We need to check both paths.
        if checkin.declaracion and checkin.declaracion.exporter_id:
            unique_exporter_ids.add(checkin.declaracion.exporter_id)
        elif checkin.localJourney and checkin.localJourney.exporter_id:
            unique_exporter_ids.add(checkin.localJourney.exporter_id)
            
        # Active Stations
        # Checkin refers to a workstation?
        # The Checkin model usually has a workstation or user who checked it in.
        # Looking at original code: WorkStation.objects.filter(checkins__isnull=False)
        # That implies a Reverse relation `checkins` on WorkStation. 
        # So Checkin has a ForeignKey to WorkStation. Let's assume it's `workstation_id` or `created_by.station`?
        # Standard Orc Checkin usually has 'workstation' or 'created_by'.
        # Original code used `WorkStation.objects.filter(checkins__isnull=False).distinct().count()`
        # This implies Checkin has a FK to WorkStation named `workstation` (related_name='checkins').
        # If we have the checkin object, we can get `checkin.workstation_id`.
        if hasattr(checkin, 'workstation_id') and checkin.workstation_id:
            active_station_ids.add(checkin.workstation_id)

    unique_taxpayers = len(unique_exporter_ids)
    
    # For active stations, the customized logic in Python relies on the loop.
    # However, the original code did a separate query: `WorkStation.objects.filter(checkins__isnull=False)...`
    # This separate query MIGHT count stations that have checkins NOT in the `base_checkins_query` (which is filtered by status).
    # Original code: `base_checkins_query` (status filtered) was used for revenue.
    # BUT `active_stations` calculation (lines 61-63) used `WorkStation.objects.filter(checkins__isnull=False)`.
    # It did NOT filter by the status=["pass","paid","success"]. 
    # It just checked if *any* checkin exists for that station. 
    # Wait, `checkins__isnull=False` means "has any checkin". 
    # If the user intended "Active stations in this report", they usually imply "stations involved in these checkins".
    # BUT strictly reading the previous code: it was completely independent of `base_checkins_query`!
    # It counted ANY station that has ever had a checkin (or maybe `checkins` relates to the filtered set? No, that's not how reverse relations work unless filtered).
    # ACTUALLY, if `WorkStation` has `checkins` related name, `filter(checkins__isnull=False)` checks for existence of related objects.
    # This likely counts ALL stations with HISTORY.
    # To be safe and identical to original logic: I should Keep the original Active Stations Query as it does not involve the Window function error.
    # The Window function error comes from `checkins_with_revenue.aggregate(...)`.
    # The `active_stations` query is on `WorkStation` model. Safe.
    
    # 5. Calculate active stations (Original Logic - likely independent of date range/status?
    # If the intention was "Active stations *in this context*", the previous code might have been buggy or intended global usage.)
    # Let's keep the original query for active_stations to ensure behavior consistency, 
    # UNLESS `checkins` refers to `base_checkins_query`? No.
    active_stations = WorkStation.objects.filter(checkins__isnull=False).distinct().count()

    # 6. Calculate unique taxpayers (exporters)
    # The original code used `checkins_with_revenue.annotate(...)` then count.
    # Since `checkins_with_revenue` IS the filtered queryset, our Python loop sets `unique_exporter_ids` from THAT queryset.
    # So `unique_taxpayers` calculated in Python IS correct and matches the context.
    # AND it avoids the aggregation error.
    
    # So we use the Python calculated `unique_taxpayers`. (`active_stations` kept as DB query).

    # 6. Response (unchanged structure to maintain frontend compatibility)
    return Response(
        {
            "totalRevenue": float(total_revenue),
            "totalWeight": float(total_weight),
            "activeStations": active_stations,
            "uniqueTaxpayers": unique_taxpayers,
        }
    )
