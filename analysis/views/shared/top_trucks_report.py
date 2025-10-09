from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.serializers import TopTrucksSerializer
from declaracions.models import Checkin

from ..helpers import annotate_revenue_on_checkins, parse_and_validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def top_trucks_report(request):
    """
    Generates a report of the top 10 most active trucks based on check-in count
    within a given date range. It can be filtered by station and controller.
    This view efficiently calculates all metrics using a single, optimized database query.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    try:
        start_date, end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    filters = {
        "checkin_time__range": [start_date, end_date],
        "status__in": ["pass", "paid", "success"],
        "declaracion__truck__isnull": False,
    }
    if station_id and station_id != "null":
        filters["station_id"] = station_id
    if controller_id and controller_id != "null":
        filters["employee_id"] = controller_id

    base_checkins = Checkin.objects.filter(**filters)
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins)

    truck_stats = (
        checkins_with_revenue.values(
            "declaracion__truck__id",
            "declaracion__truck__plate_number",
            "declaracion__truck__truck_brand",
            "declaracion__truck__owner__first_name",
            "declaracion__truck__owner__last_name",
        )
        .annotate(
            total_revenue=Sum("revenue"),
            total_kg=Sum("incremental_weight"),
            total_checkins=Count("id"),
            path_count=Count("declaracion_id", distinct=True),
        )
        .order_by("-total_checkins", "-path_count")[:10]
    )

    report_data = []
    for truck in truck_stats:
        owner_first_name = truck["declaracion__truck__owner__first_name"]
        owner_last_name = truck["declaracion__truck__owner__last_name"]
        owner_name = (
            f"{owner_first_name} {owner_last_name}"
            if owner_first_name and owner_last_name
            else "Unknown"
        )

        report_data.append(
            {
                "plate_number": truck["declaracion__truck__plate_number"],
                "make": truck["declaracion__truck__truck_brand"] or "Unknown",
                "owner_name": owner_name,
                "total_checkins": truck["total_checkins"],
                "path_count": truck["path_count"],
                "total_kg": round(truck["total_kg"] or 0, 2),
                "total_revenue": round(truck["total_revenue"] or Decimal(0), 2),
            }
        )

    serializer = TopTrucksSerializer(data=report_data, many=True)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)
