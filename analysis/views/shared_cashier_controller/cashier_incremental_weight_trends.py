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
def cashier_incremental_weight_trends(request):
    """
    Analyzes the incremental weight contributed at a specific workstation (cashier station),
    broken down by time periods (weekly, monthly, or yearly) and categorized
    by taxpayer type ('Regular' or 'Walk-in').

    This endpoint filters check-ins by a given date range and a specific `station_id`.
    It leverages `parse_and_validate_date_range` for strict date validation
    and `annotate_revenue_on_checkins` to efficiently calculate the incremental
    weight (total_amount) at the database level. Data is then aggregated by
    day of the week, week of the month, or month of the year, providing trends
    for both regular and walk-in taxpayer categories at that station.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.
    - station_id (int): The ID of the workstation (cashier station) for which to generate the report. Required.

    Returns:
        Response: A dictionary containing 'series' (list of data for 'Regular' and 'Walk-in'
        taxpayers) and 'categories' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Regular", "data": [1000.0, 1200.0, 0.0, ...]},
                {"name": "Walk-in", "data": [50.0, 75.0, 0.0, ...]},
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
    station_id = request.query_params.get("station_id")

    # Validate required parameters
    if not all([selected_date_type, start_date_str, end_date_str, station_id]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "station_id": station_id,
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
        station_id=station_id,
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

    # 3. Annotate check-ins with incremental weight and taxpayer type
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

    # 4. Perform database aggregation based on selected_date_type
    if selected_date_type == "weekly":
        # DB's ExtractWeekDay is 1=Sunday, 2=Monday, ..., 7=Saturday
        # We need to map it to our 'categories' list which starts with Monday (index 0)
        db_day_to_category_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }

        aggregated_query = (
            checkins_with_data.annotate(time_unit=ExtractWeekDay("checkin_time"))
            .values("time_unit", "taxpayer_type")
            .annotate(total_weight=Coalesce(Sum("incremental_weight"), Decimal(0)))
            .order_by("time_unit", "taxpayer_type")
        )

        for item in aggregated_query:
            day_label = db_day_to_category_map.get(item["time_unit"])
            if day_label:
                if item["taxpayer_type"] == "Regular":
                    regular_data_map[day_label] += item["total_weight"]
                elif item["taxpayer_type"] == "Walk-in":
                    walkin_data_map[day_label] += item["total_weight"]

    elif selected_date_type == "monthly":
        # The `parse_and_validate_date_range` helper for 'monthly' ensures a full calendar month.
        # We'll calculate week number within the month.

        aggregated_query = (
            checkins_with_data.annotate(
                # Calculate week number relative to the start of the month (1-indexed)
                week_of_month=((ExtractDay("checkin_time") - 1) // 7)
                + 1
            )
            .values("week_of_month", "taxpayer_type")
            .annotate(total_weight=Coalesce(Sum("incremental_weight"), Decimal(0)))
            .order_by("week_of_month", "taxpayer_type")
        )

        for item in aggregated_query:
            week_num = item["week_of_month"]
            week_label = f"Week {week_num}"
            if (
                week_label in categories
            ):  # Ensure the week label is valid for our defined categories
                if item["taxpayer_type"] == "Regular":
                    regular_data_map[week_label] += item["total_weight"]
                elif item["taxpayer_type"] == "Walk-in":
                    walkin_data_map[week_label] += item["total_weight"]

    elif selected_date_type == "yearly":
        aggregated_query = (
            checkins_with_data.annotate(
                time_unit=ExtractMonth("checkin_time")  # 1=Jan, 12=Dec
            )
            .values("time_unit", "taxpayer_type")
            .annotate(total_weight=Coalesce(Sum("incremental_weight"), Decimal(0)))
            .order_by("time_unit", "taxpayer_type")
        )

        for item in aggregated_query:
            month_label = month_name[
                item["time_unit"]
            ]  # Map month number to full month name
            if month_label:
                if item["taxpayer_type"] == "Regular":
                    regular_data_map[month_label] += item["total_weight"]
                elif item["taxpayer_type"] == "Walk-in":
                    walkin_data_map[month_label] += item["total_weight"]

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
