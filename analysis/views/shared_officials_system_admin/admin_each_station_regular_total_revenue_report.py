from calendar import month_name
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum
from django.db.models import Value as V
from django.db.models.functions import Coalesce
from django.utils.timezone import make_aware
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
def admin_each_station_regular_total_revenue_report(request):
    """
    Generates a report summarizing the total "Regular" revenue generated at each workstation
    within a specified date range, aggregated by the chosen `selected_date_type`.

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters successful "Regular" check-ins
    (those associated with a `declaracion`) by the provided date range and `station`.
    Incremental revenue is calculated efficiently at the database level using
    `annotate_revenue_on_checkins`. The total "Regular" revenue for each station is then
    summed up to provide a single total revenue per station for the entire period.

    Query Parameters:
    - selected_date_type (str): The type of date range validation ('weekly', 'monthly', 'yearly'). Required.
                                 Note: While required for validation, the specific grouping
                                 (day of week, week of month, etc.) is *not* reflected in
                                 the final output's `data` list, which is a single sum
                                 per station for the entire period.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing 'data' (a list of total "Regular" revenues for each station)
        and 'labels' (names of the workstations).
        Example:
        {
            "data": [12345.67, 8901.23, 0.0, ...],
            "labels": ["Station A", "Station B", "Station C", ...]
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

    # 2. Base filters for "Regular" check-ins
    # Filters for successful check-ins within the date range, linked to a station,
    # and specifically those with an associated 'declaracion' (indicating regular taxpayer).
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__range=[start_date, inclusive_end_date],
        station__isnull=False,  # Ensure check-ins are linked to a station
        declaracion__isnull=False,  # This is the key for "Regular" revenue
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    # Get all workstation names for consistent `labels` output
    all_stations = WorkStation.objects.all().order_by("name")
    labels = [station.name for station in all_stations]

    if not checkins_query.exists():
        # If no check-ins, return empty data list with all zeros
        return Response({"data": [0.0] * len(labels), "labels": labels})

    # 3. Annotate check-ins with incremental revenue using the helper
    checkins_with_revenue = annotate_revenue_on_checkins(checkins_query)

    # Initialize a dictionary to hold total "Regular" revenue for each station, initialized to 0
    # station_revenues_map: { "Station Name": Decimal(0) }
    station_revenues_map = {station.name: Decimal(0) for station in all_stations}

    # 4. Perform aggregation in Python
    # We iterate over the queryset and sum up the revenue for each station manually.
    for checkin in checkins_with_revenue:
        # annotations from annotate_revenue_on_checkins
        revenue = checkin.revenue or Decimal(0)
        # Ensure we have a station (robustness)
        if checkin.station:
            s_name = checkin.station.name
            if s_name in station_revenues_map:
                station_revenues_map[s_name] += revenue

    # 5. Build the final `data` list, ensuring it matches the order of `labels`
    # Convert Decimal to float and round for output consistency with previous code.
    data_list = [
        float(round(station_revenues_map.get(label, Decimal(0)), 2)) for label in labels
    ]

    return Response({"data": data_list, "labels": labels})
