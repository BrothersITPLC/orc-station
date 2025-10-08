from calendar import month_name
from collections import defaultdict
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Count, F, Q
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractWeekDay
from django.utils.timezone import make_aware
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import parse_and_validate_date_range
from exporters.models import Exporter


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cashier_taxpayers_registered_report(request):
    """
    Generates a report on the number of 'Regular' and 'Walk-in' exporters
    registered at a specific workstation (cashier station), aggregated by
    day of the week, week of the month, or month of the year.

    This endpoint filters exporter registrations by the provided date range
    and a specific `station_id` (where the registration occurred). It then
    aggregates the count of registered exporters for each category
    ('Regular'/'Walk-in') over the chosen time period ('weekly', 'monthly',
    or 'yearly'). Date range validation is strictly enforced by
    `parse_and_validate_date_range` for the selected `date_type`.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering registrations. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering registrations. Required.
    - station_id (int): The ID of the workstation (cashier station) for which to generate the report. Required.

    Returns:
        Response: A dictionary containing 'series' (list of data for 'Regular'
        and 'Walk-in' taxpayers) and 'categories' (labels for the time periods).
        Example (monthly for a full month):
        {
            "series": [
                {"name": "Regular", "data": [5, 3, 7, 2, 0]},
                {"name": "Walk-in", "data": [1, 0, 2, 4, 1]},
            ],
            "categories": ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
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

    # 2. Base filters for exporters registered at the specified station within the date range
    base_filters = Q(
        register_place_id=station_id,  # Filter by register_place_id for station
        created_at__range=[start_date, inclusive_end_date],
    )

    taxpayers_query = Exporter.objects.filter(base_filters)

    categories = []
    # Initialize dictionaries to hold aggregated data for each type, ensuring all periods are covered
    regular_counts_map = defaultdict(int)
    walkin_counts_map = defaultdict(int)

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

        # Mapping DB ExtractWeekDay (1=Sun, 2=Mon...7=Sat) to Python's weekday for categories.index
        db_day_to_category_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }

        # Query and aggregate at database level
        grouped_data = (
            taxpayers_query.annotate(
                time_unit=ExtractWeekDay("created_at")  # 1=Sun, 2=Mon...7=Sat
            )
            .values("time_unit", "type__name")
            .annotate(count=Count("id"))
            .order_by("time_unit", "type__name")
        )

        for entry in grouped_data:
            day_label = db_day_to_category_map.get(entry["time_unit"])
            if day_label:
                if entry["type__name"] == "regular":
                    regular_counts_map[day_label] = entry["count"]
                elif entry["type__name"] == "walk in":
                    walkin_counts_map[day_label] = entry["count"]

    elif selected_date_type == "monthly":
        # For 'monthly', parse_and_validate_date_range ensures a full calendar month.
        # So we can calculate weeks of the month.
        days_in_month = (inclusive_end_date.date() - start_date.date()).days + 1
        num_weeks = (days_in_month + 6) // 7  # Ceiling division
        categories = [f"Week {i}" for i in range(1, num_weeks + 1)]

        # Group by week number within the month
        grouped_data = (
            taxpayers_query.annotate(
                # Calculate week number relative to the start of the month (1-indexed)
                # For example, day 1-7 is week 1, day 8-14 is week 2, etc.
                week_of_month=((ExtractDay("created_at") - 1) // 7)
                + 1
            )
            .values("week_of_month", "type__name")
            .annotate(count=Count("id"))
            .order_by("week_of_month", "type__name")
        )

        for entry in grouped_data:
            week_num = entry["week_of_month"]
            week_label = f"Week {week_num}"
            if (
                week_label in categories
            ):  # Ensure the week label is valid for our defined categories
                if entry["type__name"] == "regular":
                    regular_counts_map[week_label] = entry["count"]
                elif entry["type__name"] == "walk in":
                    walkin_counts_map[week_label] = entry["count"]

    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]

        # Group by month of the year
        grouped_data = (
            taxpayers_query.annotate(month_num=ExtractMonth("created_at"))
            .values("month_num", "type__name")
            .annotate(count=Count("id"))
            .order_by("month_num", "type__name")
        )

        for entry in grouped_data:
            month_label = month_name[entry["month_num"]]
            if month_label:
                if entry["type__name"] == "regular":
                    regular_counts_map[month_label] = entry["count"]
                elif entry["type__name"] == "walk in":
                    walkin_counts_map[month_label] = entry["count"]

    else:
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Build series data, ensuring all categories are present with 0 if no data
    regular_series = [regular_counts_map.get(category, 0) for category in categories]
    walkin_series = [walkin_counts_map.get(category, 0) for category in categories]

    series = [
        {"name": "Regular", "data": regular_series},
        {"name": "Walk-in", "data": walkin_series},
    ]

    return Response({"series": series, "categories": categories})

    return Response({"series": series, "categories": categories})
