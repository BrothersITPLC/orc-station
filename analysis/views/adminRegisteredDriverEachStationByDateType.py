from calendar import month_name
from datetime import datetime, timedelta

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from drivers.models import Driver
from workstations.models import WorkStation

from .dateRangeValidator import validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_registered_driver_each_station_by_date_type(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    # Validate request parameters
    if not selected_date_type or not start_date or not end_date:
        return Response({"error": "Missing required parameters."}, status=400)

    validation_response = validate_date_range(start_date, end_date, selected_date_type)
    if validation_response:
        return validation_response

    # Parse and convert dates
    try:
        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
        end_date = make_aware(
            datetime.strptime(end_date, "%Y-%m-%d")
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    # Fetch all workstations
    stations = WorkStation.objects.all()

    # Initialize structure for storing driver counts
    station_counts = {station.id: {} for station in stations}

    # Fetch drivers within the date range
    drivers = Driver.objects.filter(created_at__range=(start_date, end_date))

    for driver in drivers:
        station_id = driver.register_place.id if driver.register_place else None
        if not station_id:
            continue  # Skip drivers without a register place

        if selected_date_type == "weekly":
            day_of_week = driver.created_at.strftime("%A")
            station_counts[station_id][day_of_week] = (
                station_counts[station_id].get(day_of_week, 0) + 1
            )
        elif selected_date_type == "monthly":
            week_number = (driver.created_at.day - 1) // 7 + 1
            week_label = f"Week {week_number}"
            station_counts[station_id][week_label] = (
                station_counts[station_id].get(week_label, 0) + 1
            )
        elif selected_date_type == "yearly":
            month_name_str = driver.created_at.strftime("%B")
            station_counts[station_id][month_name_str] = (
                station_counts[station_id].get(month_name_str, 0) + 1
            )
        else:
            return Response(
                {
                    "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
                },
                status=400,
            )

    # Build response data
    series = []
    for index, station in enumerate(stations):
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
            categories = [
                f"Week {i}" for i in range(1, 6)
            ]  # Assuming up to 5 weeks in a month
        elif selected_date_type == "yearly":
            categories = [month_name[i] for i in range(1, 13)]
        else:
            categories = []

        driver_counts = [
            station_counts[station.id].get(category, 0) for category in categories
        ]

        # Determine type based on index
        series_type = "line" if index % 2 != 0 else "column"

        series.append(
            {
                "name": station.name,
                "data": driver_counts,
            }
        )

    return Response({"series": series, "categories": categories})
