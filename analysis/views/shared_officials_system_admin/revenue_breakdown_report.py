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


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def revenue_breakdown_report(request):
    """
    Provides a breakdown of revenue and unique exporter counts, distinguishing
    between 'Regular Taxpayers' (associated with Declaracion) and
    'Walk-in Taxpayers' (associated with LocalJourneyWithoutTruck).

    This endpoint filters check-ins by a specified date range and status.
    It then calculates incremental weight and revenue for each check-in
    efficiently at the database level using `annotate_revenue_on_checkins`.
    Finally, it aggregates the total revenue and counts distinct exporters
    for each category.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing the revenue breakdown and exporter counts.
        Example:
        {
            "from_regular": 12345.67,
            "from_walkIn": 890.12,
            "total": 13235.79,
            "regular_exporters": 100,
            "walkin_exporters": 15,
        }

    Raises:
        HTTP 400 Bad Request: If 'start_date' or 'end_date' are missing or invalid.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Date Validation and Parsing using the helper function
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Common filter criteria for all relevant check-ins
    common_checkin_filters = Q(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
    )

    from_regular = Decimal(0)
    from_walkIn = Decimal(0)
    regular_exporters_count = 0
    walkin_exporters_count = 0

    # 2. Process Revenue and Exporters for 'Regular Taxpayers' (Declaracion-based)
    regular_checkins_query = Checkin.objects.filter(
        common_checkin_filters, declaracion__isnull=False
    )
    if regular_checkins_query.exists():
        # Annotate revenue on these specific check-ins
        regular_checkins_with_revenue = annotate_revenue_on_checkins(
            regular_checkins_query
        )

        # Aggregate total revenue and count distinct exporters
        regular_aggregates = regular_checkins_with_revenue.aggregate(
            total_revenue=Coalesce(Sum("revenue"), Decimal(0)),
            unique_exporters=Coalesce(Count("declaracion__exporter", distinct=True), 0),
        )
        from_regular = regular_aggregates["total_revenue"]
        regular_exporters_count = regular_aggregates["unique_exporters"]

    # 3. Process Revenue and Exporters for 'Walk-in Taxpayers' (LocalJourney-based)
    walkin_checkins_query = Checkin.objects.filter(
        common_checkin_filters, localJourney__isnull=False
    )
    if walkin_checkins_query.exists():
        # Annotate revenue on these specific check-ins
        walkin_checkins_with_revenue = annotate_revenue_on_checkins(
            walkin_checkins_query
        )

        # Aggregate total revenue and count distinct exporters
        walkin_aggregates = walkin_checkins_with_revenue.aggregate(
            total_revenue=Coalesce(Sum("revenue"), Decimal(0)),
            unique_exporters=Coalesce(
                Count("localJourney__exporter", distinct=True), 0
            ),
        )
        from_walkIn = walkin_aggregates["total_revenue"]
        walkin_exporters_count = walkin_aggregates["unique_exporters"]

    # 4. Final Calculation and Response (structure preserved for frontend)
    total = from_regular + from_walkIn
    result = {
        "from_regular": float(from_regular),
        "from_walkIn": float(from_walkIn),
        "total": float(total),
        "regular_exporters": regular_exporters_count,
        "walkin_exporters": walkin_exporters_count,
    }

    return Response(result)
