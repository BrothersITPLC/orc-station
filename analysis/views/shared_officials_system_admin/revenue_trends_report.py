from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum
from django.db.models.functions import (
    Coalesce,
    ExtractDay,
    ExtractMonth,
    ExtractWeekDay,
)
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
def revenue_trends_report(request):
    """
    Generates a report on revenue trends, aggregated over time based on the
    `selected_date_type` (weekly, monthly, or yearly).

    This endpoint retrieves check-ins within a specified date range and calculates
    their incremental revenue using the `annotate_revenue_on_checkins` helper.
    It then groups these revenues by day of the week, day of the month, or month
    of the year, and returns the total revenue for each period. This significantly
    improves performance by performing aggregations at the database level.

    Query Parameters:
    - selected_date_type (str): Specifies the aggregation period ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A list of dictionaries, where each dictionary represents a time period
        (e.g., a day of the week, a day of the month, or a month) and its total revenue.
        Example (weekly):
        [
            {"label": "Sun", "amount": 123.45},
            {"label": "Mon", "amount": 678.90},
            ...
        ]

    Raises:
        HTTP 400 Bad Request: If 'selected_date_type', 'start_date', or 'end_date'
                              are missing or if date format is invalid.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    if not selected_date_type or not start_date_str or not end_date_str:
        return Response(
            {"error": "Missing required parameters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Date Validation and Parsing using the helper function
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Base filter criteria for all relevant check-ins
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
    )

    if not base_checkins_query.exists():
        return Response([])

    # 2. Annotate check-ins with incremental weight and revenue using the helper function
    # This replaces the manual Python loop for calculating these values.
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    report_data = []

    if selected_date_type == "weekly":
        # Group by day of the week (ExtractWeekDay returns 1 for Sunday, ..., 7 for Saturday)
        weekly_aggregates = (
            checkins_with_revenue.annotate(
                day_of_week_db=ExtractWeekDay("checkin_time")
            )
            .values("day_of_week_db")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("day_of_week_db")
        )

        days_labels_ordered = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        # Initialize results for all 7 days with 0 revenue
        revenue_by_day = [Decimal(0)] * 7

        for item in weekly_aggregates:
            # Adjust day_of_week_db (1-7, Sun-Sat) to 0-6 (Sun-Sat) for list indexing
            day_index = item["day_of_week_db"] - 1
            if 0 <= day_index < 7:  # Defensive check
                revenue_by_day[day_index] = item["total_revenue"]

        report_data = [
            {"label": days_labels_ordered[i], "amount": float(revenue_by_day[i])}
            for i in range(7)
        ]

    elif selected_date_type == "monthly":
        # Group by day of the month (1-31)
        monthly_aggregates = (
            checkins_with_revenue.annotate(day_of_month=ExtractDay("checkin_time"))
            .values("day_of_month")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("day_of_month")
        )

        # Collect all unique days within the date range for consistent labels
        all_days_in_range = set()
        current_date_iter = start_date.date()
        while current_date_iter <= inclusive_end_date.date():
            all_days_in_range.add(current_date_iter.day)
            current_date_iter += timezone.timedelta(days=1)

        sorted_days = sorted(list(all_days_in_range))
        revenue_by_day_dict = {day: Decimal(0) for day in sorted_days}

        for item in monthly_aggregates:
            if item["day_of_month"] in revenue_by_day_dict:  # Defensive check
                revenue_by_day_dict[item["day_of_month"]] = item["total_revenue"]

        report_data = [
            {"label": day, "amount": float(revenue_by_day_dict[day])}
            for day in sorted_days
        ]

    elif selected_date_type == "yearly":
        # Group by month of the year (ExtractMonth returns 1 for Jan, ..., 12 for Dec)
        yearly_aggregates = (
            checkins_with_revenue.annotate(month_of_year=ExtractMonth("checkin_time"))
            .values("month_of_year")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("month_of_year")
        )

        month_names_ordered = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        # Initialize results for all 12 months with 0 revenue
        revenue_by_month = [Decimal(0)] * 12

        for item in yearly_aggregates:
            # Adjust month_of_year (1-12) to 0-11 for list indexing
            month_index = item["month_of_year"] - 1
            if 0 <= month_index < 12:  # Defensive check
                revenue_by_month[month_index] = item["total_revenue"]

        report_data = [
            {"label": month_names_ordered[i], "amount": float(revenue_by_month[i])}
            for i in range(12)
        ]

    return Response(report_data)
