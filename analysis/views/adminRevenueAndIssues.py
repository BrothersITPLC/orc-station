from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from users.models import Report  # Assuming the Report model is in reports.models
from users.models import CustomUser
from workstations.models import WorkStation

from .dateRangeValidator import validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_revenue_and_issues(request):
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

    # Fetch all stations
    stations = WorkStation.objects.all()

    # Initialize result list
    result = []

    for station in stations:
        # Fetch all employees assigned to the station
        employees = CustomUser.objects.filter(
            checkins_accepter__station=station
        ).distinct()

        # Filters for checkins
        filters = {
            "status__in": ["pass", "paid", "success"],
            "checkin_time__range": [start_date, end_date],
            "station": station,
        }

        # Fetch checkins for the station
        checkins = Checkin.objects.filter(**filters).select_related(
            "employee", "station"
        )

        # Calculate revenue and count issues
        for employee in employees:
            employee_name = employee.get_full_name()

            # Calculate total revenue
            total_revenue = Decimal(0)
            employee_checkins = checkins.filter(employee=employee)

            for checkin in employee_checkins:
                latest_checkin = (
                    Checkin.objects.filter(
                        checkin_time__lt=checkin.checkin_time,
                        localJourney=(
                            checkin.localJourney if checkin.localJourney else None
                        ),
                        declaracion=(
                            checkin.declaracion if checkin.declaracion else None
                        ),
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

                unit_price = Decimal(checkin.unit_price)
                rate = Decimal(checkin.rate)
                revenue = weight * (unit_price / Decimal(100)) * (rate / Decimal(100))
                total_revenue += revenue

            # Count reports/issues
            issue_count = Report.objects.filter(
                employee=employee,
                station=station,
                created_at__range=[start_date, end_date],
            ).count()

            # Append data to result
            result.append(
                {
                    "Name": employee_name,
                    "Station": station.name,
                    "Collected Revenue": float(
                        total_revenue
                    ),  # Convert to float for JSON serialization
                    "Issue Count": issue_count,
                }
            )

    # Sort result by revenue in descending order
    result.sort(key=lambda x: x["Collected Revenue"], reverse=True)

    return Response(result)
