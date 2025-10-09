from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, DecimalField, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin
from exporters.models import Exporter


@api_view(["GET"])
@permission_classes([AllowAny])
def overall_revenue_and_taxpayer_summary(request):
    """
    Provides a summary of total revenue split between 'Regular' and 'Walk-in' taxpayers,
    along with their respective counts, for a given date range.

    This endpoint filters check-ins by the provided 'start_date' and 'end_date',
    and optional workstation/controller filters. It efficiently calculates total
    revenue for each taxpayer category using `annotate_revenue_on_checkins` and
    aggregates these at the database level. It also counts exporters created
    within the same date range.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins and exporter creation. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins and exporter creation. Required.
    - station_id (str, optional): Filters check-ins by workstation ID.
    - controller_id (str, optional): Filters check-ins by employee (controller) ID.

    Returns:
        Response: A dictionary containing total revenue for walk-ins and regulars,
        and counts of regular and walk-in exporters created within the period.
        Example:
        {
            "walk_in_amount": 890.12,
            "regular_amount": 12345.67,
            "regular": 100,
            "walk_in": 15,
        }

    Raises:
        HTTP 400 Bad Request: If 'start_date' or 'end_date' are missing or invalid.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    # 1. Date Validation and Parsing using the helper function
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Build base filter criteria for check-ins
    base_checkin_filters = Q(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
    )

    if station_id and station_id != "null":
        base_checkin_filters &= Q(station_id=station_id)

    # Apply user-specific filtering for controllers, or general controller_id filter
    # The original view used request.user.current_station and request.user.role.name
    # Assuming request.user is authenticated if these are expected.
    if request.user.is_authenticated:
        if request.user.role.name == "controller":
            # If the logged-in user is a controller, filter by their employee ID
            base_checkin_filters &= Q(employee=request.user)
        # If user is not a controller, but a controller_id is provided, filter by that.
        elif controller_id and controller_id != "null":
            base_checkin_filters &= Q(employee_id=controller_id)
    elif (
        controller_id and controller_id != "null"
    ):  # If user is anonymous, but controller_id is provided
        base_checkin_filters &= Q(employee_id=controller_id)

    checkins_query = Checkin.objects.filter(base_checkin_filters)

    walk_in_amount = Decimal(0)
    regular_amount = Decimal(0)

    if checkins_query.exists():
        # 3. Annotate check-ins with incremental revenue and taxpayer type
        checkins_with_revenue = (
            annotate_revenue_on_checkins(checkins_query)
            .annotate(
                taxpayer_type=Case(
                    When(declaracion__isnull=False, then=V("Regular")),
                    When(localJourney__isnull=False, then=V("WalkIn")),
                    default=V("Unknown"),
                    output_field=CharField(),
                )
            )
            .filter(taxpayer_type__in=["Regular", "WalkIn"])
        )  # Only consider valid taxpayer types

        # 4. Aggregate total revenue by taxpayer type
        aggregated_revenue = checkins_with_revenue.values("taxpayer_type").annotate(
            total_revenue=Coalesce(Sum("revenue"), Decimal(0))
        )

        for item in aggregated_revenue:
            if item["taxpayer_type"] == "WalkIn":
                walk_in_amount = item["total_revenue"]
            elif item["taxpayer_type"] == "Regular":
                regular_amount = item["total_revenue"]

    # 5. Count regular and walk-in exporters within the specified date range (based on created_at)
    regular_exporters_count = Exporter.objects.filter(
        type__name="regular", created_at__range=[start_date, inclusive_end_date]
    ).count()
    walk_in_exporters_count = Exporter.objects.filter(
        type__name="walk in", created_at__range=[start_date, inclusive_end_date]
    ).count()

    # 6. Format the response data (structure preserved for frontend)
    response_data = {
        "walk_in_amount": float(walk_in_amount),
        "regular_amount": float(regular_amount),
        "regular": regular_exporters_count,
        "walk_in": walk_in_exporters_count,
    }

    return Response(response_data)

    return Response(response_data)
