from calendar import month_name
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, Q
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractWeekDay
from django.utils.timezone import (  # parse_and_validate_date_range already handles this
    make_aware,
)
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import parse_and_validate_date_range
from exporters.models import Exporter
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_registered_exporters_each_station_by_date_type(request):
    """
    Generates a trend report on the number of exporters registered at each workstation,
    aggregated over time based on the `selected_date_type` (weekly, monthly, or yearly).

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters exporters by their `created_at`
    date and the `register_place` (station). The number of registered exporters is then
    aggregated by day of the week, week of the month, or month of the year for each station.
    The `series` data is formatted with a 'type' property ('line' or 'column') based on
    the station's index, as per the original logic.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering exporter registrations. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering exporter registrations. Required.

    Returns:
        Response: A dictionary containing 'series' (a list of data for each station,
        including 'name', 'type', and 'data') and 'labels' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Station A", "type": "column", "data": [5, 3, 7, 2, 0, 1, 0]},
                {"name": "Station B", "type": "line", "data": [2, 1, 4, 1, 0, 0, 0]},
            ],
            "labels": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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

    # 2. Fetch all stations and initialize labels
    all_stations = WorkStation.objects.all().order_by(
        "name"
    )  # Order for consistent series type assignment
    labels = []
    if selected_date_type == "weekly":
        labels = [
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
        labels = [f"Week {i}" for i in range(1, num_weeks + 1)]
    elif selected_date_type == "yearly":
        labels = [month_name[i] for i in range(1, 13)]

    # If no stations exist, return empty data
    if not all_stations.exists():
        return Response({"series": [], "labels": labels})

    # 3. Base filters for exporters registered within the date range and linked to a place
    exporters_query = Exporter.objects.filter(
        register_place__isnull=False, created_at__range=[start_date, inclusive_end_date]
    )

    # If no exporters registered, return empty data (but with correct labels)
    if not exporters_query.exists():
        empty_series = []
        for index, station in enumerate(all_stations):
            series_type = "line" if index % 2 != 0 else "column"
            empty_series.append(
                {"name": station.name, "type": series_type, "data": [0] * len(labels)}
            )
        return Response({"series": empty_series, "labels": labels})

    # 4. Perform database aggregation
    aggregated_data = None
    if selected_date_type == "weekly":
        # DB's ExtractWeekDay is 1=Sunday, 2=Monday, ..., 7=Saturday
        # Map it to our 'labels' list which starts with Monday (index 0)
        db_day_to_label_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }
        aggregated_query = (
            exporters_query.annotate(time_unit=ExtractWeekDay("created_at"))
            .values("register_place__name", "time_unit")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "time_unit")
        )
        # Convert DB's time_unit to a string label for mapping
        processed_data = []
        for item in aggregated_query:
            label = db_day_to_label_map.get(item["time_unit"])
            if label:
                processed_data.append(
                    {
                        "station_name": item["register_place__name"],
                        "label": label,
                        "count": item["count"],
                    }
                )
        aggregated_data = processed_data

    elif selected_date_type == "monthly":
        # Group by week number within the month
        aggregated_query = (
            exporters_query.annotate(
                # Calculate week number relative to the start of the month (1-indexed)
                week_of_month=((ExtractDay("created_at") - 1) // 7)
                + 1
            )
            .values("register_place__name", "week_of_month")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "week_of_month")
        )
        # Convert week_of_month to a string label for mapping
        processed_data = []
        for item in aggregated_query:
            label = f"Week {item['week_of_month']}"
            if (
                label in labels
            ):  # Ensure it's a valid week within our defined categories
                processed_data.append(
                    {
                        "station_name": item["register_place__name"],
                        "label": label,
                        "count": item["count"],
                    }
                )
        aggregated_data = processed_data

    elif selected_date_type == "yearly":
        aggregated_query = (
            exporters_query.annotate(
                time_unit=ExtractMonth("created_at")  # 1=Jan, ..., 12=Dec
            )
            .values("register_place__name", "time_unit")
            .annotate(count=Count("id"))
            .order_by("register_place__name", "time_unit")
        )
        # Convert month_num to a string label for mapping
        processed_data = []
        for item in aggregated_query:
            label = month_name[item["time_unit"]]
            if label:
                processed_data.append(
                    {
                        "station_name": item["register_place__name"],
                        "label": label,
                        "count": item["count"],
                    }
                )
        aggregated_data = processed_data

    else:
        # This case should ideally not be reached due to `parse_and_validate_date_range`
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 5. Restructure data into the final `series` format
    # station_data_map: { "Station Name": { "Category Label": count, ... } }
    station_data_map = {
        station.name: {label: 0 for label in labels} for station in all_stations
    }

    for item in aggregated_data:
        station_name = item["station_name"]
        category_label = item["label"]
        count = item["count"]

        if (
            station_name in station_data_map
            and category_label in station_data_map[station_name]
        ):
            station_data_map[station_name][category_label] = count

    series = []
    for index, station in enumerate(all_stations):
        station_name = station.name
        # Get data for this station, ensuring it matches the order of 'labels'
        data_for_station = [
            station_data_map[station_name].get(label, 0) for label in labels
        ]

        # Set type to "line" for odd indices and "column" for even indices
        series_type = "line" if index % 2 != 0 else "column"

        series.append(
            {"name": station_name, "type": series_type, "data": data_for_station}
        )

    return Response({"series": series, "labels": labels})
