from calendar import month_name
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models import When
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
def controller_revenue_trends_report(request):
    """
    Generates a trend report of revenue contributed by a specific controller,
    categorized by taxpayer type ('Regular' or 'Walk-in'), over time.
    The aggregation period can be 'weekly', 'monthly', or 'yearly'.

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters check-ins by the
    provided date range and controller ID. Incremental revenue is calculated
    efficiently at the database level using `annotate_revenue_on_checkins`.
    The data is then aggregated by day of the week, week of the month, or
    month of the year to show revenue trends for both regular and walk-in taxpayers.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.
    - controller_id (int): The ID of the employee (controller) for whom to generate the report. Required.

    Returns:
        Response: A dictionary containing 'series' (list of revenue data for
        'Regular' and 'Walk-in' taxpayers) and 'categories' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Regular", "data": [1000.0, 1200.0, 0.0, 500.0, 800.0, 200.0, 0.0]},
                {"name": "Walk-in", "data": [50.0, 75.0, 0.0, 120.0, 30.0, 10.0, 0.0]},
            ],
            "categories": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        }

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              or the date range does not match the 'selected_date_type' rules.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    controller_id = request.query_params.get("controller_id")

    # Validate required parameters
    if not all([selected_date_type, start_date_str, end_date_str, controller_id]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "controller_id": controller_id,
            }.items()
            if not param_value
        ]
        return Response(
            {"error": f"Missing required parameters: {', '.join(missing_params)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Date Validation and Parsing using the helper function with strict validation
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Define the base filters for check-ins
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__range=[start_date, inclusive_end_date],
        employee_id=controller_id,
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    # Initialize categories and data maps for early return or if no data
    categories = []
    if selected_date_type == "weekly":
        categories = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    elif selected_date_type == "monthly":
        # Calculate max_weeks based on days in the filtered range
        days_in_range = (inclusive_end_date.date() - start_date.date()).days + 1
        num_weeks = (days_in_range + 6) // 7  # Ceiling division
        categories = [f"Week {i}" for i in range(1, num_weeks + 1)]
    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]

    if not checkins_query.exists():
        # Return empty data, but with correct categories for the frontend to render structure
        return Response(
            {
                "series": [
                    {"name": "Regular", "data": [0.0] * len(categories)},
                    {"name": "Walk-in", "data": [0.0] * len(categories)},
                ],
                "categories": categories,
            }
        )

    # 3. Annotate check-ins with incremental revenue and taxpayer type
    checkins_with_data = (
        annotate_revenue_on_checkins(checkins_query)
        .annotate(
            taxpayer_type=Case(
                When(declaracion__isnull=False, then=V("Regular")),
                When(localJourney__isnull=False, then=V("Walk-in")),
                default=V("Unknown"),
                output_field=CharField(),
            )
        )
        .filter(taxpayer_type__in=["Regular", "Walk-in"])
    )  # Ensure we only consider these types

    # Initialize maps to ensure all categories are present with 0 values
    regular_data_map = {category: Decimal(0) for category in categories}
    walkin_data_map = {category: Decimal(0) for category in categories}

    # 4. Perform aggregation in Python
    if selected_date_type == "weekly":
        checkins_with_data = checkins_with_data.annotate(
            weekday_num=ExtractWeekDay("checkin_time")
        )
        db_map = {
            2: "Monday", 3: "Tuesday", 4: "Wednesday",
            5: "Thursday", 6: "Friday", 7: "Saturday", 1: "Sunday"
        }
        for checkin in checkins_with_data:
            day_label = db_map.get(checkin.weekday_num)
            if day_label:
                rev = checkin.revenue or Decimal(0)
                if checkin.taxpayer_type == "Regular":
                    regular_data_map[day_label] += rev
                elif checkin.taxpayer_type == "Walk-in":
                    walkin_data_map[day_label] += rev

    elif selected_date_type == "monthly":
        checkins_with_data = checkins_with_data.annotate(
            day_of_month=ExtractDay("checkin_time")
        )
        for checkin in checkins_with_data:
            week_num = ((checkin.day_of_month - 1) // 7) + 1
            week_label = f"Week {week_num}"
            if week_label in categories:
                rev = checkin.revenue or Decimal(0)
                if checkin.taxpayer_type == "Regular":
                    regular_data_map[week_label] += rev
                elif checkin.taxpayer_type == "Walk-in":
                    walkin_data_map[week_label] += rev

    elif selected_date_type == "yearly":
        checkins_with_data = checkins_with_data.annotate(
            month_num=ExtractMonth("checkin_time")
        )
        for checkin in checkins_with_data:
            m_num = checkin.month_num
            if 1 <= m_num <= 12:
                month_label = month_name[m_num]
                if month_label:
                    rev = checkin.revenue or Decimal(0)
                    if checkin.taxpayer_type == "Regular":
                        regular_data_map[month_label] += rev
                    elif checkin.taxpayer_type == "Walk-in":
                        walkin_data_map[month_label] += rev

    # 5. Build series data, ensuring order matches categories and converting Decimals to floats
    regular_series = [
        float(regular_data_map.get(category, Decimal(0))) for category in categories
    ]
    walkin_series = [
        float(walkin_data_map.get(category, Decimal(0))) for category in categories
    ]

    series = [
        {"name": "Regular", "data": regular_series},
        {"name": "Walk-in", "data": walkin_series},
    ]

    return Response({"series": series, "categories": categories})

    return Response({"series": series, "categories": categories})
