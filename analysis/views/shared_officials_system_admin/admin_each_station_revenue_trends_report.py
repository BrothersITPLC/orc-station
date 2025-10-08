from calendar import month_name
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models.functions import (
    Coalesce,
    ExtractDay,
    ExtractMonth,
    ExtractWeekDay,
)
from django.utils.timezone import (  # parse_and_validate_date_range already handles this
    make_aware,
)
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_each_station_revenue_trends_report(request):
    """
    Generates a trend report of the total revenue processed at each workstation,
    aggregated over time based on the `selected_date_type` (weekly, monthly, or yearly).

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters successful check-ins by
    the provided date range and `station`. Incremental revenue is calculated efficiently
    at the database level using `annotate_revenue_on_checkins`. The total revenue for
    each station is then aggregated by day of the week, week of the month, or month of the year.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing 'series' (a list of revenue data for each station,
        including 'name' and 'data') and 'categories' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Station A", "data": [1000.0, 1200.0, 0.0, 500.0, 800.0, 200.0, 0.0]},
                {"name": "Station B", "data": [50.0, 75.0, 0.0, 120.0, 30.0, 10.0, 0.0]},
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

    # 2. Base filters for check-ins
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__range=[start_date, inclusive_end_date],
        station__isnull=False,  # Ensure check-ins are linked to a station
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    # Get all workstation names for consistent `labels` output
    all_stations = WorkStation.objects.all().order_by("name")

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
        empty_series = []
        for station in all_stations:
            empty_series.append({"name": station.name, "data": [0.0] * len(categories)})
        return Response({"series": empty_series, "categories": categories})

    # 3. Annotate check-ins with incremental revenue using the helper
    checkins_with_revenue = annotate_revenue_on_checkins(checkins_query)

    # Initialize a nested dictionary to hold revenue per station per category
    # station_revenue_map: { "Station Name": { "Category Label": Decimal(0), ... } }
    station_revenue_map = {
        station.name: {category: Decimal(0) for category in categories}
        for station in all_stations
    }

    # 4. Perform database aggregation based on selected_date_type
    if selected_date_type == "weekly":
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
            checkins_with_revenue.annotate(time_unit=ExtractWeekDay("checkin_time"))
            .values("station__name", "time_unit")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("station__name", "time_unit")
        )

        for item in aggregated_query:
            station_name = item["station__name"]
            day_label = db_day_to_category_map.get(item["time_unit"])
            if station_name in station_revenue_map and day_label:
                station_revenue_map[station_name][day_label] += item["total_revenue"]

    elif selected_date_type == "monthly":
        # Group by week number within the month
        aggregated_query = (
            checkins_with_revenue.annotate(
                week_of_month=((ExtractDay("checkin_time") - 1) // 7) + 1
            )
            .values("station__name", "week_of_month")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("station__name", "week_of_month")
        )

        for item in aggregated_query:
            station_name = item["station__name"]
            week_num = item["week_of_month"]
            week_label = f"Week {week_num}"
            if station_name in station_revenue_map and week_label in categories:
                station_revenue_map[station_name][week_label] += item["total_revenue"]

    elif selected_date_type == "yearly":
        aggregated_query = (
            checkins_with_revenue.annotate(time_unit=ExtractMonth("checkin_time"))
            .values("station__name", "time_unit")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("station__name", "time_unit")
        )

        for item in aggregated_query:
            station_name = item["station__name"]
            month_label = month_name[item["time_unit"]]
            if station_name in station_revenue_map and month_label:
                station_revenue_map[station_name][month_label] += item["total_revenue"]

    # 5. Build series data, ensuring all categories are present with 0 if no data
    series = []
    for station in all_stations:
        station_name = station.name
        # Get data for this station, ensuring it matches the order of 'categories'
        data_for_station = [
            float(station_revenue_map[station_name].get(category, Decimal(0)))
            for category in categories
        ]
        series.append({"name": station_name, "data": data_for_station})

    return Response({"series": series, "categories": categories})
