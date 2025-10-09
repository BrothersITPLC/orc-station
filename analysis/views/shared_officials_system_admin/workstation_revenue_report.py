from django.core.exceptions import ValidationError
from django.db.models import Sum
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from workstations.models import WorkStation

from ..helpers import annotate_revenue_on_checkins, parse_and_validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def workstation_revenue_report(request):
    """
    Provides a revenue and total amount report aggregated by workstation
    for a given date range.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    try:
        start_date, end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    all_stations = WorkStation.objects.all()
    labels = [station.name for station in all_stations]
    data = {
        station.name: {"total_revenue": 0, "total_amount": 0}
        for station in all_stations
    }

    filters = {
        "checkin_time__range": [start_date, end_date],
        "status__in": ["pass", "paid", "success"],
    }

    revenue_data = (
        Checkin.objects.filter(**filters)
        .select_related("station")
        .annotate_revenue_on_checkins()
        .values("station__name")
        .annotate(
            total_revenue=Sum("revenue"),
            total_amount=Sum("incremental_weight"),
        )
        .order_by("station__name")
    )

    for item in revenue_data:
        station_name = item["station__name"]
        if station_name in data:
            data[station_name]["total_revenue"] = round(item["total_revenue"] or 0, 2)
            data[station_name]["total_amount"] = round(item["total_amount"] or 0, 2)

    return Response({"labels": labels, "data": data})
