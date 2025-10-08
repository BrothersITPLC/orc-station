from calendar import month_name
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, Q
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractWeekDay
from django.utils.timezone import make_aware
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import parse_and_validate_date_range
from drivers.models import Driver
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_registered_drivers_each_station_report(request):
    """
    Generates a trend report on the number of drivers registered at each workstation,
    aggregated over time based on the `selected_date_type` (weekly, monthly, or yearly).

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters drivers by their `created_at`
    date and their `register_place` (station). The number of registered drivers is then
    aggregated by day of the week, week of the month, or month of the year for each station.
    The `series` data in the response is formatted without an explicit 'type' property
    as the original output format didn't include it directly for the individual series,
    but implies it might be used on the frontend. I will ensure the `categories` are
    correctly generated and each station has data points for all categories.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering driver registrations. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering driver registrations. Required.

    Returns:
        Response: A dictionary containing 'series' (a list of data for each station,
        including 'name' and 'data') and 'categories' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Station A", "data": [5, 3, 7, 2, 0, 1, 0]},
                {"name": "Station B", "data": [2, 1, 4, 1, 0, 0, 0]},
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

    # Validate required parameters
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

    # 1. Date Validation and Parsing using the helper function with strict validation
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Fetch all stations and initialize categories
    all_stations = WorkStation.objects.all().order_by(
        "name"
    )  # Order for consistent series output
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

    # If no stations exist, return empty data
    if not all_stations.exists():
        return Response({"series": [], "categories": categories})

    # 3. Filter drivers within the date range and linked to a registration place
    drivers_query = Driver.objects.filter(
        register_place__isnull=False,  # Ensure drivers are linked to a station
        created_at__range=[start_date, inclusive_end_date],
    )

    # If no drivers registered, return empty series with correct categories
    if not drivers_query.exists():
        empty_series = []
        for station in all_stations:
            empty_series.append({"name": station.name, "data": [0] * len(categories)})
        return Response({"series": empty_series, "categories": categories})

    # 4. Perform database aggregation
    # station_data_map: { "Station Name": { "Category Label": count, ... } }
    station_data_map = {
        station.name: {label: 0 for label in categories} for station in all_stations
    }

    if selected_date_type == "weekly":
        # DB's ExtractWeekDay is 1=Sunday, 2=Monday, ..., 7=Saturday
        db_day_to_category_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }

        grouped_data = (
            drivers_query.annotate(time_unit=ExtractWeekDay("created_at"))
            .values("register_place__name", "time_unit")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "time_unit")
        )

        for entry in grouped_data:
            station_name = entry["register_place__name"]
            day_label = db_day_to_category_map.get(entry["time_unit"])
            if station_name in station_data_map and day_label:
                station_data_map[station_name][day_label] = entry["count"]

    elif selected_date_type == "monthly":
        # Group by week number within the month
        grouped_data = (
            drivers_query.annotate(
                week_of_month=((ExtractDay("created_at") - 1) // 7) + 1
            )
            .values("register_place__name", "week_of_month")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "week_of_month")
        )

        for entry in grouped_data:
            station_name = entry["register_place__name"]
            week_num = entry["week_of_month"]
            week_label = f"Week {week_num}"
            if station_name in station_data_map and week_label in categories:
                station_data_map[station_name][week_label] = entry["count"]

    elif selected_date_type == "yearly":
        # Group by month of the year
        grouped_data = (
            drivers_query.annotate(month_num=ExtractMonth("created_at"))
            .values("register_place__name", "month_num")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "month_num")
        )

        for entry in grouped_data:
            station_name = entry["register_place__name"]
            month_label = month_name[entry["month_num"]]
            if station_name in station_data_map and month_label:
                station_data_map[station_name][month_label] = entry["count"]

    else:
        # This case should ideally not be reached due to `parse_and_validate_date_range`
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 5. Build series data, ensuring all categories are present with 0 if no data
    series = []
    for station in all_stations:
        station_name = station.name
        # Get data for this station, ensuring it matches the order of 'categories'
        data_for_station = [
            station_data_map[station_name].get(category, 0) for category in categories
        ]

        series.append({"name": station_name, "data": data_for_station})

    return Response({"series": series, "categories": categories})

    return Response({"series": series, "categories": categories})
