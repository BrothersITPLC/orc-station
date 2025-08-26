from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def employee_revenue_report(request):
    # Extract date filters from query parameters
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))

    # Build the filtering conditions
    filter_conditions = {"status__in": ["pass", "paid", "success"]}
    if start_date:
        filter_conditions["checkin_time__gte"] = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        filter_conditions["checkin_time__lte"] = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )

    # Fetch all relevant check-ins
    checkins = Checkin.objects.filter(**filter_conditions).select_related("employee")

    # Calculate revenue for each employee
    employee_revenue = {}
    for checkin in checkins:
        # Find the latest check-in for the same context (declaracion or localJourney)
        latest_checkin = (
            checkins.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        # Calculate weight difference
        weight_difference = (
            max(checkin.net_weight - latest_checkin.net_weight, 0)
            if latest_checkin
            else checkin.net_weight
        )

        # Compute revenue
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = (
            weight_difference * (unit_price / Decimal(100)) * (rate / Decimal(100))
        )

        # Add revenue to the employee's total
        employee_name = (
            checkin.employee.first_name
        )  # Replace with the correct field for employee's name
        if employee_name not in employee_revenue:
            employee_revenue[employee_name] = Decimal(0)
        employee_revenue[employee_name] += revenue

    # Format the response data
    response_data = [
        {"name": name, "value": round(revenue, 2)}
        for name, revenue in employee_revenue.items()
    ]

    return Response(response_data)
