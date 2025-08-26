from calendar import month_name
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from workstations.models import WorkStation

from .dateRangeValidator import validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_each_station_revenue_by_date_type_no_sum(request):
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

    # Filters for checkins
    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__range": [start_date, end_date],
    }

    # Fetch all stations and checkins
    stations = WorkStation.objects.all()
    checkins = Checkin.objects.filter(**filters).select_related(
        "station", "declaracion", "localJourney"
    )

    # Initialize data structure for station revenues
    station_revenues = {station.id: {} for station in stations}

    # Generate revenue data
    for checkin in checkins:
        # Get latest checkin to calculate incremental weight
        latest_checkin = (
            Checkin.objects.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        weight = (
            max(checkin.net_weight - latest_checkin.net_weight, 0)
            if latest_checkin
            else checkin.net_weight
        )
        weight = Decimal(weight)

        # Calculate revenue
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = weight * (unit_price / Decimal(100)) * (rate / Decimal(100))

        station_id = checkin.station.id

        # Categorize revenue based on selected_date_type
        if selected_date_type == "weekly":
            day_of_week = checkin.checkin_time.strftime("%A")
            station_revenues[station_id][day_of_week] = (
                station_revenues[station_id].get(day_of_week, 0) + revenue
            )
        elif selected_date_type == "monthly":
            week_number = (checkin.checkin_time.day - 1) // 7 + 1
            week_label = f"Week {week_number}"
            station_revenues[station_id][week_label] = (
                station_revenues[station_id].get(week_label, 0) + revenue
            )
        elif selected_date_type == "yearly":
            month_name_str = checkin.checkin_time.strftime("%B")
            station_revenues[station_id][month_name_str] = (
                station_revenues[station_id].get(month_name_str, 0) + revenue
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
        categories = [
            f"Week {i}" for i in range(1, (end_date.day - start_date.day) // 7 + 2)
        ]
    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]

    for station in stations:
        revenue_data = [
            float(station_revenues[station.id].get(category, 0))
            for category in categories
        ]
        series.append({"name": station.name, "data": revenue_data})

    return Response({"series": series, "categories": categories})
