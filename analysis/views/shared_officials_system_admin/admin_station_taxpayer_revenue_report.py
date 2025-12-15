from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Count, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import Coalesce
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
def admin_station_taxpayer_revenue_report(request):
    """
    Generates a detailed revenue report for each workstation, breaking down
    total revenue and incremental weight (total amount) by 'Regular' and
    'Walk-in' taxpayer categories within a specified date range.

    This endpoint iterates through all workstations and, for each, aggregates
    the revenue and incremental weight from associated successful check-ins.
    It utilizes `parse_and_validate_date_range` for robust date handling and
    `annotate_revenue_on_checkins` for efficient database-level calculation of
    incremental weight and revenue. Taxpayer type is determined by the presence
    of a `declaracion` or `localJourney` link on the check-in.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing 'labels' (names of all workstations)
        and 'data' (a dictionary where keys are workstation names, and values
        are nested dictionaries for 'regular' and 'walkin' taxpayer data,
        including total_revenue, total_amount, and transaction count).
        Example:
        {
            "labels": ["Station A", "Station B"],
            "data": {
                "Station A": {
                    "regular": {"total_revenue": 1234.56, "total_amount": 7890.12, "transaction": 0},
                    "walkin": {"total_revenue": 987.65, "total_amount": 4321.09, "transaction": 0}
                },
                "Station B": { ... }
            }
        }

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

    # 2. Get all workstation names for `labels` and initialize the `data` structure
    all_workstations = WorkStation.objects.all().order_by("name")
    labels = [station.name for station in all_workstations]

    data = {}
    for station in all_workstations:
        data[station.name] = {
            "regular": {
                "total_revenue": Decimal(0),
                "total_amount": Decimal(0),
                "transaction": 0,  # As per original output logic, this remains 0
            },
            "walkin": {
                "total_revenue": Decimal(0),
                "total_amount": Decimal(0),
                "transaction": 0,  # As per original output logic, this remains 0
            },
        }

    # 3. Filter base check-ins for the date range and successful status
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
        station__isnull=False,  # Ensure check-ins are linked to a station
    )

    if not base_checkins_query.exists():
        # If no check-ins, return the initialized data with all zeros
        return Response({"labels": labels, "data": data})

    # 4. Annotate check-ins with incremental weight, revenue, and taxpayer type
    checkins_with_data = (
        annotate_revenue_on_checkins(base_checkins_query)
        .annotate(
            taxpayer_type=Case(
                When(declaracion__isnull=False, then=V("regular")),
                When(localJourney__isnull=False, then=V("walkin")),
                default=V("unknown"),  # Should ideally not hit 'unknown'
                output_field=CharField(),
            )
        )
        .filter(taxpayer_type__in=["regular", "walkin"])
    )  # Only consider valid taxpayer types

    # 5. Aggregate revenue and incremental weight per station and taxpayer type (Python)
    for checkin in checkins_with_data:
        # Checkin has annotated fields from steps above
        s_name = checkin.station.name if checkin.station else None
        t_type = checkin.taxpayer_type
        
        if s_name and t_type in ["regular", "walkin"]:
            rev = checkin.revenue or Decimal(0)
            weight = checkin.incremental_weight or Decimal(0)
            
            if s_name in data:
                 data[s_name][t_type]["total_revenue"] += rev
                 data[s_name][t_type]["total_amount"] += weight

    # 6. Populate the `data` dictionary with the aggregated results
    for item in station_taxpayer_aggregates:
        station_name = item["station__name"]
        taxpayer_type = item["taxpayer_type"]

        if station_name in data and taxpayer_type in data[station_name]:
            data[station_name][taxpayer_type]["total_revenue"] = round(
                item["total_revenue_sum"], 2
            )
            data[station_name][taxpayer_type]["total_amount"] = round(
                item["total_amount_sum"], 2
            )
            # data[station_name][taxpayer_type]["transaction"] = item["transaction_count"] # If needed

    # 7. Return the response (frontend compatible)
    return Response({"labels": labels, "data": data})
