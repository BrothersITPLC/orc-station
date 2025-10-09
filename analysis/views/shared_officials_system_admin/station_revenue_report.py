from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
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
def station_revenue_report(request):
    """
    Provides a revenue report aggregated by workstation within a specified date range.

    This endpoint calculates the total revenue, total incremental weight (referred to as 'total_amount'),
    and total number of transactions for each workstation. It leverages database-level
    calculations for efficiency, using `annotate_revenue_on_checkins` to compute
    incremental weight and revenue, and then aggregates these values per station.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A dictionary containing a list of workstation names as 'labels'
        and a dictionary 'data' where keys are workstation names and values are
        their aggregated statistics.
        Example:
        {
            "labels": ["Station A", "Station B"],
            "data": {
                "Station A": {"total_revenue": 1234.56, "total_amount": 7890.12, "transaction": 50},
                "Station B": {"total_revenue": 987.65, "total_amount": 4321.09, "transaction": 30},
            }
        }

    Raises:
        HTTP 400 Bad Request: If 'start_date' or 'end_date' are missing or invalid.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Date Validation and Parsing
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Filter initial check-ins for the specified date range and status.
    # Ensure check-ins are linked to a station to be included in the report.
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
        station__isnull=False,  # Exclude check-ins not linked to a workstation
    )

    # Get all workstation names to ensure consistent labels and default values
    # even for stations with no check-ins in the specified period.
    all_workstations = WorkStation.objects.all().order_by("name")
    labels = [station.name for station in all_workstations]

    # Initialize data dictionary with default values for all workstations
    data = {
        station.name: {
            "total_revenue": Decimal(0),
            "total_amount": Decimal(0),
            "transaction": 0,
        }
        for station in all_workstations
    }

    # If no check-ins exist for the period, return the initialized empty data
    if not base_checkins_query.exists():
        return Response({"labels": labels, "data": data})

    # 3. Annotate check-ins with incremental weight and revenue using the helper function.
    # This replaces the inefficient Python loop for calculating these values.
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 4. Aggregate total revenue, total incremental weight, and transaction count per workstation
    # directly in the database.
    station_aggregates = (
        checkins_with_revenue.values(
            "station__id", "station__name"  # Group by station ID and name
        )
        .annotate(
            total_revenue_sum=Coalesce(
                Sum("revenue"), Decimal(0)
            ),  # Sum of calculated revenue
            total_incremental_weight_sum=Coalesce(
                Sum("incremental_weight"), Decimal(0)
            ),  # Sum of incremental weight
            transaction_count=Coalesce(
                Count("id"), 0
            ),  # Count of check-ins (transactions)
        )
        .order_by("station__name")  # Order for consistent processing
    )

    # 5. Populate the 'data' dictionary with the aggregated results.
    for item in station_aggregates:
        station_name = item["station__name"]
        if (
            station_name in data
        ):  # Ensure the station name exists in our initialized data
            data[station_name]["total_revenue"] = round(item["total_revenue_sum"], 2)
            data[station_name]["total_amount"] = round(
                item["total_incremental_weight_sum"], 2
            )
            data[station_name]["transaction"] = item["transaction_count"]

    # 6. Return the response in the required format.
    # The `labels` list is already prepared from all_workstations.
    # The `data` dictionary is populated with aggregates, defaulting to zero for stations
    # with no activity in the period.
    return Response({"labels": labels, "data": data})
