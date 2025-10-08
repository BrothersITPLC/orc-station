from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import (
    ExtractDay,
    ExtractMonth,
    ExtractWeekDay,
    TruncDate,
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
def tax_payer_revenue_trends(request):
    """
    Analyzes and returns revenue trends for taxpayers (categorized as 'Regular' or 'Walk-in')
    over a specified date range, grouped by week, month, or year.

    This view first filters check-ins by the provided date range and status.
    It then calculates incremental weight and revenue for each check-in at the
    database level using the `annotate_revenue_on_checkins` helper.
    Taxpayers are categorized based on a simplified revenue threshold (e.g., > 1000 for 'Regular').
    Finally, it aggregates the total revenue for these categories based on the
    `selected_date_type` (weekly, monthly, yearly trends).

    Query Parameters:
    - selected_date_type (str): Specifies the aggregation period ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing 'labels' (e.g., day names, month numbers)
        and 'datasets' (list of dictionaries for 'Regular Taxpayers' and
        'Walk-in Taxpayers' revenue data).
        Example:
        {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "datasets": [
                {"label": "Regular Taxpayers", "data": [1000.0, 1200.5, ...]},
                {"label": "Walk-in Taxpayers", "data": [50.0, 75.2, ...]},
            ]
        }

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

    # Build base filter criteria
    filter_criteria = {
        "checkin_time__range": [start_date, inclusive_end_date],
        "status__in": ["pass", "paid", "success"],
    }

    # Fetch relevant checkins
    base_checkins_query = Checkin.objects.filter(**filter_criteria)

    if not base_checkins_query.exists():
        return Response({"labels": [], "datasets": []})

    # 2. Annotate revenue on checkins using the helper function
    # This replaces the manual Python loop for calculating incremental_weight and revenue.
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # Annotate a field to categorize taxpayer type based on revenue threshold
    # This uses the same logic as the original example (revenue > 1000)
    checkins_categorized = checkins_with_revenue.annotate(
        is_regular_taxpayer=Case(
            When(revenue__gt=Decimal(1000), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    labels = []
    datasets = []

    if selected_date_type == "weekly":
        # Group revenue by day of the week
        # ExtractWeekDay returns 1 for Sunday, 2 for Monday, ..., 7 for Saturday.
        # Python's datetime.weekday() returns 0 for Monday, ..., 6 for Sunday.
        # We need to adjust to the desired output labels: ["Sun", "Mon", ..., "Sat"]
        days_labels_ordered = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

        # Aggregate data by day of week and taxpayer category
        aggregated_data = (
            checkins_categorized.annotate(day_of_week_db=ExtractWeekDay("checkin_time"))
            .values("day_of_week_db", "is_regular_taxpayer")
            .annotate(total_revenue=Sum("revenue", output_field=DecimalField()))
            .order_by("day_of_week_db", "is_regular_taxpayer")
        )

        regular_taxpayer_data = [Decimal(0)] * 7
        walk_in_taxpayer_data = [Decimal(0)] * 7

        for item in aggregated_data:
            # Adjust day_of_week_db (1-7, Sun-Sat) to 0-6 (Sun-Sat) for list indexing
            day_index = item["day_of_week_db"] - 1
            if item["is_regular_taxpayer"]:
                regular_taxpayer_data[day_index] += item["total_revenue"]
            else:
                walk_in_taxpayer_data[day_index] += item["total_revenue"]

        labels = days_labels_ordered
        datasets = [
            {
                "label": "Regular Taxpayers",
                "data": [float(r) for r in regular_taxpayer_data],
            },
            {
                "label": "Walk-in Taxpayers",
                "data": [float(w) for w in walk_in_taxpayer_data],
            },
        ]

    elif selected_date_type == "monthly":
        # Group revenue by day of the month
        aggregated_data = (
            checkins_categorized.annotate(day_of_month=ExtractDay("checkin_time"))
            .values("day_of_month", "is_regular_taxpayer")
            .annotate(total_revenue=Sum("revenue", output_field=DecimalField()))
            .order_by("day_of_month", "is_regular_taxpayer")
        )

        daily_revenue = {}  # {day_num: {'regular': Decimal, 'walk_in': Decimal}}
        for item in aggregated_data:
            day = item["day_of_month"]
            if day not in daily_revenue:
                daily_revenue[day] = {"regular": Decimal(0), "walk_in": Decimal(0)}

            if item["is_regular_taxpayer"]:
                daily_revenue[day]["regular"] += item["total_revenue"]
            else:
                daily_revenue[day]["walk_in"] += item["total_revenue"]

        # Sort by day number to get correct labels and data order
        sorted_days = sorted(daily_revenue.keys())
        labels = [f"{day:02}" for day in sorted_days]
        datasets = [
            {
                "label": "Regular Taxpayers",
                "data": [float(daily_revenue[day]["regular"]) for day in sorted_days],
            },
            {
                "label": "Walk-in Taxpayers",
                "data": [float(daily_revenue[day]["walk_in"]) for day in sorted_days],
            },
        ]

    elif selected_date_type == "yearly":
        # Group revenue by month of the year
        # ExtractMonth returns 1 for Jan, 2 for Feb, ..., 12 for Dec
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

        aggregated_data = (
            checkins_categorized.annotate(month_of_year=ExtractMonth("checkin_time"))
            .values("month_of_year", "is_regular_taxpayer")
            .annotate(total_revenue=Sum("revenue", output_field=DecimalField()))
            .order_by("month_of_year", "is_regular_taxpayer")
        )

        monthly_revenue_data = (
            {}
        )  # {month_num: {'regular': Decimal, 'walk_in': Decimal}}
        for item in aggregated_data:
            month = item["month_of_year"]
            if month not in monthly_revenue_data:
                monthly_revenue_data[month] = {
                    "regular": Decimal(0),
                    "walk_in": Decimal(0),
                }

            if item["is_regular_taxpayer"]:
                monthly_revenue_data[month]["regular"] += item["total_revenue"]
            else:
                monthly_revenue_data[month]["walk_in"] += item["total_revenue"]

        # Create labels and data ensuring all 12 months are represented, even if no data
        regular_data_for_year = [Decimal(0)] * 12
        walk_in_data_for_year = [Decimal(0)] * 12

        for month_num in range(1, 13):  # Loop through months 1 to 12
            if month_num in monthly_revenue_data:
                regular_data_for_year[month_num - 1] = monthly_revenue_data[month_num][
                    "regular"
                ]
                walk_in_data_for_year[month_num - 1] = monthly_revenue_data[month_num][
                    "walk_in"
                ]

        labels = month_names_ordered
        datasets = [
            {
                "label": "Regular Taxpayers",
                "data": [float(r) for r in regular_data_for_year],
            },
            {
                "label": "Walk-in Taxpayers",
                "data": [float(w) for w in walk_in_data_for_year],
            },
        ]

    return Response({"labels": labels, "datasets": datasets})
