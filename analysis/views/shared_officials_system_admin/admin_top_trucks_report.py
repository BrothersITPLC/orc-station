from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.serializers import (  # Assuming this serializer correctly maps the output structure
    TopTrucksSerializer,
)
from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import (  # We will primarily use Checkin, not Declaracion directly for aggregation
    Checkin,
)
from trucks.models import Truck  # Used for metadata like plate_number, make, owner


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_top_trucks_report(request):
    """
    Generates a report of the top 10 most active trucks based on check-in count
    and declarations (paths) within a specified date range.

    For each of these top trucks, the report includes total check-ins, total
    unique declarations (paths), total incremental weight (kg), and total revenue.
    This view uses `parse_and_validate_date_range` for robust date handling
    and `annotate_revenue_on_checkins` for efficient database-level calculations
    of incremental weight and revenue, replacing inefficient Python loops.

    Query Parameters:
    - selected_date_type (str): Specifies the date range validation type ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A serialized list of dictionaries, where each dictionary represents a top truck
        with its plate number, make, owner name, total check-ins, total paths, total kg,
        and total revenue.
        Example:
        [
            {
                "plate_number": "ABC123",
                "make": "Volvo",
                "owner_name": "Alice Smith",
                "total_checkins": 150,
                "path_count": 25,
                "total_kg": 150000.50,
                "total_revenue": 7500.25
            },
            ... (up to 10 entries)
        ]

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              or the date range does not match the 'selected_date_type' rules.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Validate request parameters and parse dates using the helper function
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

    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Build the base queryset for relevant check-ins
    # Filter for successful check-ins within the date range, linked to a declaration and a truck.
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__range=[start_date, inclusive_end_date],
        declaracion__isnull=False,  # Ensure it's a declaration-based checkin
        declaracion__truck__isnull=False,  # Ensure it's linked to a truck
    )

    base_checkins_query = Checkin.objects.filter(base_checkins_filters)

    if not base_checkins_query.exists():
        return Response([])

    # 3. Annotate check-ins with incremental weight and revenue using the helper
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 4. Aggregate data for top trucks directly at the database level
    # This replaces the entire manual 'calculate_total_weight' function and its loop.
    truck_stats = (
        checkins_with_revenue.values(
            "declaracion__truck__id",  # Group by truck ID
            "declaracion__truck__plate_number",
            "declaracion__truck__truck_brand",
            "declaracion__truck__owner__first_name",
            "declaracion__truck__owner__last_name",
        )
        .annotate(
            total_revenue=Coalesce(Sum("revenue"), Decimal(0)),
            total_kg=Coalesce(Sum("incremental_weight"), Decimal(0)),
            total_checkins=Coalesce(
                Count("id"), 0
            ),  # Count of all relevant check-ins for the truck
            path_count=Coalesce(
                Count("declaracion_id", distinct=True), 0
            ),  # Count of unique declarations (paths)
        )
        .order_by("-total_checkins", "-path_count")[
            :10
        ]  # Order by check-in count then path count, get top 10
    )

    # 5. Prepare the report data in the required format
    report_data = []
    for truck_entry in truck_stats:
        owner_first_name = truck_entry["declaracion__truck__owner__first_name"]
        owner_last_name = truck_entry["declaracion__truck__owner__last_name"]
        owner_name = (
            f"{owner_first_name} {owner_last_name}".strip()
            if owner_first_name or owner_last_name
            else "Unknown"
        )

        report_data.append(
            {
                "plate_number": truck_entry["declaracion__truck__plate_number"],
                "make": truck_entry["declaracion__truck__truck_brand"] or "Unknown",
                "owner_name": owner_name,
                "total_checkins": truck_entry["total_checkins"],
                "path_count": truck_entry["path_count"],
                "total_kg": float(round(truck_entry["total_kg"], 2)),
                "total_revenue": float(round(truck_entry["total_revenue"], 2)),
            }
        )

    # 6. Serialize and return the report data (frontend compatible)
    serializer = TopTrucksSerializer(data=report_data, many=True)
    serializer.is_valid(raise_exception=True)  # Will raise 400 if validation fails
    return Response(serializer.data)
