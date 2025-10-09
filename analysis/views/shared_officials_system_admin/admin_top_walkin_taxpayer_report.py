from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin
from exporters.models import Exporter
from localcheckings.models import JourneyWithoutTruck


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_top_walkin_taxpayer_report(request):
    """
    Generates a report of the top 10 "Walk-in" taxpayers (exporters associated
    with Local Journeys) based on their total number of unique local journeys
    within a specified date range.

    For each of these top taxpayers, the report provides their total revenue
    and total incremental weight (amount) derived from their check-ins during
    the period. This view leverages `parse_and_validate_date_range` for robust
    date handling and `annotate_revenue_on_checkins` for efficient database-level
    calculation of incremental revenue and weight, replacing manual Python loops.

    Query Parameters:
    - selected_date_type (str): Specifies the date range validation type ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins and journeys. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins and journeys. Required.

    Returns:
        Response: A list of dictionaries, where each dictionary represents a top
        "Walk-in" taxpayer with their details, total amount, total revenue, and
        total number of local journeys.
        Example:
        [
            {
                "uniqe_id": "WALKIN001",
                "type": "walk in",
                "exporter_name": "John Doe",
                "total_amount": 5000.75,
                "total_revenue": 1250.25,
                "total_path": 15
            },
            ... (up to 10 entries)
        ]

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              or the date range does not match the 'selected_date_type' rules.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Validate request parameters and parse dates using the helper function
    if not all([selected_date_type, start_date_str, end_date_str]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }.items()
            if not param_value
        ]
        return Response(
            {"error": f"Missing required parameters: {', '.join(missing_params)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Build the base queryset for relevant "walk-in" check-ins
    base_walkin_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
        localJourney__isnull=False,  # Filter for local journeys only (walk-in)
        localJourney__exporter__isnull=False,  # Ensure an exporter is linked
    )

    if not base_walkin_checkins_query.exists():
        return Response([])

    # 3. Annotate check-ins with incremental weight and revenue using the helper
    checkins_with_revenue_and_weight = annotate_revenue_on_checkins(
        base_walkin_checkins_query
    )

    # 4. Aggregate data for top "Walk-in" taxpayers
    top_walkin_taxpayers_data = (
        checkins_with_revenue_and_weight.annotate(
            # Coalesce to handle potential nulls in exporter details if necessary,
            # though localJourney__exporter__isnull=False should prevent most.
            exporter_id=F("localJourney__exporter__id"),
            first_name=Coalesce("localJourney__exporter__first_name", V("")),
            last_name=Coalesce("localJourney__exporter__last_name", V("")),
            unique_id=Coalesce("localJourney__exporter__unique_id", V("")),
            type_name=Coalesce("localJourney__exporter__type__name", V("Unknown")),
        )
        .values(
            "exporter_id",
            "first_name",
            "last_name",
            "unique_id",
            "type_name",
        )
        .annotate(
            total_revenue=Coalesce(Sum("revenue"), Decimal(0)),
            total_amount=Coalesce(Sum("incremental_weight"), Decimal(0)),
            total_path=Coalesce(
                Count("localJourney_id", distinct=True), 0
            ),  # Count unique local journeys
        )
        .filter(
            total_path__gt=0
        )  # Only include exporters with at least one local journey
        .order_by("-total_path", "-total_revenue")[
            :10
        ]  # Order by journey count, then revenue
    )

    # 5. Prepare the report data in the required format
    report_data = []
    for item in top_walkin_taxpayers_data:
        # The original code had category logic here, but it wasn't used in the final
        # output structure for 'admin_top_walkin_taxpayer_report'.
        # Keeping the format exactly as requested by the user.
        report_data.append(
            {
                "uniqe_id": item["unique_id"],
                "type": item["type_name"],
                "exporter_name": f"{item['first_name']} {item['last_name']}".strip(),
                "total_amount": float(round(item["total_amount"], 2)),
                "total_revenue": float(round(item["total_revenue"], 2)),
                "total_path": item["total_path"],
            }
        )

    return Response(report_data)
