from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, CharField, Count, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import annotate_revenue_on_checkins
from declaracions.models import Checkin
from workstations.models import (  # Assuming WorkStation model exists and is importable
    WorkStation,
)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cashier_daily_summary_report(request):
    """
    Generates a daily summary report of a specific workstation's (cashier's) activity
    over the last 24 hours.

    This report includes total revenue, total incremental weight (kg), and the count
    of checked-in taxpayers, broken down into 'Regular' (Declaracion-based) and
    'Walk-in' (LocalJourney-based) categories. It efficiently calculates incremental
    weight and revenue using `annotate_revenue_on_checkins` and performs all
    aggregations at the database level.

    Query Parameters:
    - station_id (int): The ID of the workstation (cashier station) for which to generate the report. Required.

    Returns:
        Response: A list of dictionaries, each representing a key metric with its label and calculated amount.
        Example:
        [
            {"label": "Total Revenue", "amount": "12345.67"},
            {"label": "Revenue From Walk-in", "amount": "890.12"},
            ...
        ]

    Raises:
        HTTP 400 Bad Request: If 'station_id' is missing.
        HTTP 404 Not Found: If the specified 'station_id' does not exist.
    """
    station_id = request.query_params.get("station_id")

    if not station_id or station_id == "null":
        return Response(
            {"error": "station_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate if station exists (correctly checking against WorkStation model)
    station_exists = WorkStation.objects.filter(id=station_id).exists()
    if not station_exists:
        return Response(
            {"error": "Workstation not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Define the time range (last 24 hours)
    time_threshold = now() - timedelta(hours=24)

    # 1. Build base filter criteria for check-ins
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__gte=time_threshold,
        station_id=station_id,  # Filter by station_id
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    if not checkins_query.exists():
        # Return all zero values if no check-ins found
        response_data = [
            {"label": "Total Revenue", "amount": "0.0"},
            {"label": "Revenue From Walk-in", "amount": "0.0"},
            {"label": "Revenue From Regular", "amount": "0.0"},
            {"label": "Total kg", "amount": "0.0"},
            {"label": "Total kg From Walk-in", "amount": "0.0"},
            {"label": "Total kg From Regular", "amount": "0.0"},
            {"label": "Total Checked in Tax Payers", "amount": "0"},
            {"label": "Total Checked in Walk-in Tax Payers", "amount": "0"},
            {"label": "Total Checked in Regular Tax Payers", "amount": "0"},
        ]
        return Response(response_data)

    # 2. Annotate check-ins with incremental weight, revenue, and taxpayer type
    checkins_with_data = (
        annotate_revenue_on_checkins(checkins_query)
        .annotate(
            taxpayer_type=Case(
                When(declaracion__isnull=False, then=V("Regular")),
                When(localJourney__isnull=False, then=V("Walk-in")),
                default=V("Unknown"),  # Should be rare if data is clean
                output_field=CharField(),
            )
        )
        .filter(taxpayer_type__in=["Regular", "Walk-in"])
    )  # Only consider valid taxpayer types

    # 3. Perform aggregation in Python
    # Initialize accumulators
    total_rev = Decimal(0)
    total_weight = Decimal(0)
    rev_reg = Decimal(0)
    rev_walk = Decimal(0)
    weight_reg = Decimal(0)
    weight_walk = Decimal(0)
    
    unique_exporters_all = set()
    unique_exporters_regular = set()
    unique_exporters_walkin = set()

    for checkin in checkins_with_data:
        rev = checkin.revenue or Decimal(0)
        weight = checkin.incremental_weight or Decimal(0)
        t_type = checkin.taxpayer_type
        
        # Collect explicit exporter ID if available (either from declaracion or localJourney)
        # Note: checkin.taxpayer_type is set by the annotation, so we know which relation to check
        # BUT getting the ID directly via relation traversal in loop is fine.
        # Ideally checkin.declaracion_id or checkin.localJourney_id is faster if we only needed checkin ID,
        # but we need Exporter ID.
        # We can also check both since one will be null.
        exporter_id = None
        if checkin.declaracion_id and checkin.declaracion.exporter_id:
            exporter_id = checkin.declaracion.exporter_id
        elif checkin.localJourney_id and checkin.localJourney.exporter_id:
            exporter_id = checkin.localJourney.exporter_id
            
        if exporter_id:
            unique_exporters_all.add(exporter_id)
            if t_type == "Regular":
                unique_exporters_regular.add(exporter_id)
            elif t_type == "Walk-in":
                unique_exporters_walkin.add(exporter_id)

        total_rev += rev
        total_weight += weight
        
        if t_type == "Regular":
            rev_reg += rev
            weight_reg += weight
        elif t_type == "Walk-in":
            rev_walk += rev
            weight_walk += weight

    aggregates = {
        "total_revenue_overall": total_rev,
        "total_weight_overall": total_weight,
        "revenue_regular_sum": rev_reg,
        "revenue_walkin_sum": rev_walk,
        "weight_regular_sum": weight_reg,
        "weight_walkin_sum": weight_walk,
    }

    # 4. Count distinct taxpayers (exporters) - Python
    checkedin_tax_payers = len(unique_exporters_all)
    tax_payers_regular = len(unique_exporters_regular)
    tax_payers_walkin = len(unique_exporters_walkin)

    # 5. Prepare the response data (structure preserved for frontend)
    response_data = [
        {
            "label": "Total Revenue",
            "amount": str(aggregates["total_revenue_overall"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Walk-in",
            "amount": str(aggregates["revenue_walkin_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Regular",
            "amount": str(aggregates["revenue_regular_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg",
            "amount": str(aggregates["total_weight_overall"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg From Walk-in",
            "amount": str(aggregates["weight_walkin_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg From Regular",
            "amount": str(aggregates["weight_regular_sum"].quantize(Decimal("0.0"))),
        },
        {"label": "Total Checked in Tax Payers", "amount": str(checkedin_tax_payers)},
        {
            "label": "Total Checked in Walk-in Tax Payers",
            "amount": str(tax_payers_walkin),
        },
        {
            "label": "Total Checked in Regular Tax Payers",
            "amount": str(tax_payers_regular),
        },
    ]

    return Response(response_data)
