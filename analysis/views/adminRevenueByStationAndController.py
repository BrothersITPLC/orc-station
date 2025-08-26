from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from users.models import CustomUser
from workstations.models import WorkStation

from .dateRangeValidator import validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_revenue_by_station_and_controller(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    station_name = request.query_params.get("station_name")  # Using station_name now

    # Validate request parameters
    if not selected_date_type or not start_date or not end_date or not station_name:
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

    # Get the station by name (case-insensitive)
    try:
        stations = WorkStation.objects.filter(name__iexact=station_name)
        if stations.count() == 0:
            return Response({"error": "Station not found."}, status=404)
        elif stations.count() > 1:
            return Response(
                {"error": "Multiple stations match the given name. Be more specific."},
                status=400,
            )
        station = stations.first()
    except WorkStation.DoesNotExist:
        return Response({"error": "Station not found."}, status=404)

    # Fetch all employees assigned to the station
    employees = CustomUser.objects.filter(checkins_accepter__station=station).distinct()
    # Filters for checkins
    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__range": [start_date, end_date],
        "station": station,
    }

    # Fetch checkins for the specified station
    checkins = Checkin.objects.filter(**filters).select_related("employee", "station")

    # Initialize data structures
    series_data = {employee.get_full_name(): {} for employee in employees}
    categories = []

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

        # Determine time category based on selected_date_type
        if selected_date_type == "weekly":
            time_category = checkin.checkin_time.strftime("%A")
        elif selected_date_type == "monthly":
            week_number = (checkin.checkin_time.day - 1) // 7 + 1
            time_category = f"Week {week_number}"
        elif selected_date_type == "yearly":
            time_category = checkin.checkin_time.strftime("%B")
        else:
            return Response(
                {
                    "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
                },
                status=400,
            )

        if time_category not in categories:
            categories.append(time_category)

        # Group revenue by controller (employee)
        employee_name = (
            checkin.employee.get_full_name() if checkin.employee else "Unknown"
        )
        if employee_name not in series_data:
            series_data[employee_name] = {}

        series_data[employee_name][time_category] = (
            series_data[employee_name].get(time_category, 0) + revenue
        )

    # Ensure all employees have entries for all categories
    for employee in series_data:
        for category in categories:
            if category not in series_data[employee]:
                series_data[employee][category] = 0

    # Format response
    series = [
        {
            "name": employee,
            "data": [series_data[employee].get(category, 0) for category in categories],
        }
        for employee in series_data
    ]

    return Response(
        {
            "station_name": station.name,
            "categories": categories,
            "series": series,
        }
    )
