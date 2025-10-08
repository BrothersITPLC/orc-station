from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin

from ..helpers import annotate_revenue_on_checkins, parse_and_validate_date_range


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def top_exporters_report(request):
    """
    Generates a report of the top 10 "merchant" (declaration-based) and top 10
    "local" (walk-in) exporters, ranked by their path/journey count.
    """
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    try:
        start_date, end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    base_filters = {
        "checkin_time__range": [start_date, end_date],
        "status__in": ["pass", "paid", "success"],
    }
    if station_id and station_id != "null":
        base_filters["station_id"] = station_id
    if controller_id and controller_id != "null":
        base_filters["employee_id"] = controller_id

    merchant_filters = {**base_filters, "declaracion__exporter__isnull": False}
    top_merchants = (
        annotate_revenue_on_checkins(Checkin.objects.filter(**merchant_filters))
        .values(
            "declaracion__exporter__tin_number",
            "declaracion__exporter__type__name",
            "declaracion__exporter__first_name",
            "declaracion__exporter__last_name",
        )
        .annotate(
            total_revenue=Sum("revenue"),
            total_amount=Sum("incremental_weight"),
            total_path=Count("declaracion_id", distinct=True),
        )
        .order_by("-total_path")[:10]
    )

    local_filters = {**base_filters, "localJourney__exporter__isnull": False}
    top_locals = (
        annotate_revenue_on_checkins(Checkin.objects.filter(**local_filters))
        .values(
            "localJourney__exporter__type__name",
            "localJourney__exporter__first_name",
            "localJourney__exporter__last_name",
        )
        .annotate(
            total_revenue=Sum("revenue"),
            total_amount=Sum("incremental_weight"),
            total_path=Count("localJourney_id", distinct=True),
        )
        .order_by("-total_path")[:10]
    )

    report_data = {"local": [], "merchant": []}
    for exporter in top_locals:
        report_data["local"].append(
            {
                "type": exporter["localJourney__exporter__type__name"],
                "exporter_name": f"{exporter['localJourney__exporter__first_name']} {exporter['localJourney__exporter__last_name']}",
                "total_amount": exporter["total_amount"] or 0,
                "total_revenue": round(exporter["total_revenue"] or Decimal(0), 2),
                "total_path": exporter["total_path"],
            }
        )

    for exporter in top_merchants:
        report_data["merchant"].append(
            {
                "tin_number": exporter["declaracion__exporter__tin_number"],
                "type": exporter["declaracion__exporter__type__name"],
                "exporter_name": f"{exporter['declaracion__exporter__first_name']} {exporter['declaracion__exporter__last_name']}",
                "total_amount": exporter["total_amount"] or 0,
                "total_revenue": round(exporter["total_revenue"] or Decimal(0), 2),
                "total_path": exporter["total_path"],
            }
        )

    return Response(report_data)
