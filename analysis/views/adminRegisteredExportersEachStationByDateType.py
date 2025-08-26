from calendar import month_name
from datetime import datetime, timedelta

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from exporters.models import Exporter
from workstations.models import WorkStation

from .dateRangeValidator import validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_registered_exporters_each_station_by_date_type(request):
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

    # Fetch all stations and exporters
    stations = WorkStation.objects.all()
    exporters = Exporter.objects.filter(
        register_place__isnull=False, created_at__range=[start_date, end_date]
    ).select_related("register_place")

    # Initialize data structure for station exporter counts
    station_data = {}

    # Categorize exporter counts by station and selected_date_type
    for exporter in exporters:
        station_name = exporter.register_place.name
        category = None

        if selected_date_type == "weekly":
            category = exporter.created_at.strftime("%A")
        elif selected_date_type == "monthly":
            week_number = (exporter.created_at.day - 1) // 7 + 1
            category = f"Week {week_number}"
        elif selected_date_type == "yearly":
            category = exporter.created_at.strftime("%B")
        else:
            return Response(
                {
                    "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
                },
                status=400,
            )

        if station_name not in station_data:
            station_data[station_name] = {}

        station_data[station_name][category] = (
            station_data[station_name].get(category, 0) + 1
        )

    # Build response data
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
        labels = [f"Week {i}" for i in range(1, 6)]  # Assume up to 5 weeks in a month
    elif selected_date_type == "yearly":
        labels = [month_name[i] for i in range(1, 13)]

    series = []

    # Include all stations in the series, even if they have no registered exporters

    for index, station in enumerate(stations):
        station_name = station.name
        category_data = station_data.get(
            station_name, {}
        )  # Get existing data or empty dict
        data = [
            category_data.get(label, 0) for label in labels
        ]  # Ensure all labels are present

        # Set type to "line" for odd indices and "column" for even indices
        series_type = "line" if index % 2 != 0 else "column"

        series.append({"name": station_name, "type": series_type, "data": data})

    return Response({"series": series, "labels": labels})
