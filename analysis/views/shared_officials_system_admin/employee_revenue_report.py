from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum
from django.db.models import (
    Value as V,  # Renaming Value to V to avoid conflict with `Value` in annotate_revenue_on_checkins
)
from django.db.models.functions import Coalesce, Concat
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def employee_revenue_report(request):
    """
    Generates a report detailing the total revenue contributed by each employee
    (controller) within a specified date range.

    This endpoint filters check-ins by the provided date range and successful status.
    It then efficiently calculates incremental weight and revenue for each check-in
    at the database level using `annotate_revenue_on_checkins`. Finally, it aggregates
    the total revenue for each employee who processed a check-in during the period.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A list of dictionaries, where each dictionary represents an employee
        with their combined first and last name, and their total aggregated revenue.
        Example:
        [
            {"name": "John Doe", "value": 12345.67},
            {"name": "Jane Smith", "value": 8901.23},
            ...
        ]

    Raises:
        HTTP 400 Bad Request: If 'start_date' or 'end_date' are missing or invalid.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Date Validation and Parsing using the helper function
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Build filter criteria for the base queryset
    # Ensure check-ins are linked to an employee to be included in this report
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
        employee__isnull=False,  # Only include check-ins processed by an employee
    )

    if not base_checkins_query.exists():
        return Response([])

    # 3. Annotate check-ins with incremental weight and revenue using the helper function
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 4. Aggregate total revenue per employee directly in the database
    employee_revenue_aggregates = (
        checkins_with_revenue.annotate(
            # Concatenate first_name and last_name to get the full employee name
            full_employee_name=Coalesce(
                Concat(F("employee__first_name"), V(" "), F("employee__last_name")),
                F("employee__first_name"),  # Fallback if only first name exists
                F("employee__last_name"),  # Fallback if only last name exists
                V("Unknown Employee"),  # Default if no name parts exist
            )
        )
        .values(
            "employee__id", "full_employee_name"
        )  # Group by employee ID and their derived full name
        .annotate(
            total_employee_revenue=Coalesce(
                Sum("revenue"), Decimal(0)
            )  # Sum of calculated revenue
        )
        .order_by("full_employee_name")  # Order for consistent output
    )

    # 5. Format the response data (structure preserved for frontend)
    response_data = [
        {
            "name": item["full_employee_name"],
            "value": round(item["total_employee_revenue"], 2),
        }
        for item in employee_revenue_aggregates
    ]

    return Response(response_data)
