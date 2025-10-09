from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce, ExtractDay
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([AllowAny])
def monthly_revenue_report(request):
    """
    Generates a daily revenue report for a specified date range, with optional
    filtering by station and controller. This report is intended to show
    revenue trends day-by-day within a month-like period.

    This view uses `parse_and_validate_date_range` to handle date inputs and
    `annotate_revenue_on_checkins` to efficiently calculate incremental revenue
    at the database level. It then aggregates this revenue by each day within
    the selected period.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.
    - station_id (int, optional): Filters check-ins by a specific workstation ID.
    - controller_id (int, optional): Filters check-ins by a specific employee (controller) ID.

    Returns:
        Response: A dictionary containing 'labels' (days of the month, formatted as "DD")
        and 'data' (corresponding total daily revenue).
        Example:
        {
            "labels": ["01", "02", "03", ...],
            "data": [123.45, 678.90, 0.0, ...]
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

    # 2. Build filter criteria for the base queryset
    filters = Q(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
    )
    if station_id and station_id != "null":
        filters &= Q(station_id=station_id)
    if controller_id and controller_id != "null":
        filters &= Q(employee_id=controller_id)

    base_checkins_query = Checkin.objects.filter(filters)

    if not base_checkins_query.exists():
        return Response({"labels": [], "data": []})

    # 3. Annotate check-ins with incremental weight and revenue using the helper function
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 4. Aggregate revenue by day of the month directly in the database
    daily_revenue_aggregates = (
        checkins_with_revenue.annotate(day_of_month=ExtractDay("checkin_time"))
        .values("day_of_month")
        .annotate(total_daily_revenue=Coalesce(Sum("revenue"), Decimal(0)))
        .order_by("day_of_month")
    )

    # Prepare labels and data, ensuring all days in the range are represented
    # even if they have no revenue.
    all_days_in_range = []
    current_date = start_date.date()
    while current_date <= inclusive_end_date.date():
        all_days_in_range.append(current_date.day)
        current_date += F(
            "timedelta(days=1)"
        )  # Using F for database calculation might be faster

    # Create a dictionary to hold revenue for each day, initialized to 0
    revenue_by_day_dict = {
        day: Decimal(0) for day in sorted(list(set(all_days_in_range)))
    }

    for item in daily_revenue_aggregates:
        day = item["day_of_month"]
        if day in revenue_by_day_dict:  # Defensive check
            revenue_by_day_dict[day] = item["total_daily_revenue"]

    labels = [f"{day:02}" for day in sorted(revenue_by_day_dict.keys())]
    data = [
        float(revenue_by_day_dict[day]) for day in sorted(revenue_by_day_dict.keys())
    ]

    response_data = {"labels": labels, "data": data}

    return Response(response_data)
