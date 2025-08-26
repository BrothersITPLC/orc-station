from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin, Declaracion
from exporters.models import Exporter
from localcheckings.models import JourneyWithoutTruck

from ..serializers import TopExportersSerializer


def calculate_local_revenue_and_amount(exporter=None, start_date=None, end_date=None):
    total_revenue = Decimal(0)
    total_amount = 0
    if exporter is not None:
        journeys = JourneyWithoutTruck.objects.filter(
            exporter=exporter,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).prefetch_related("checkins")

        for journey in journeys:
            checkins = journey.checkins.filter(
                checkin_time__lte=end_date,
                checkin_time__gte=start_date,
                status__in=["pass", "paid", "success"],
            )
            for checkin in checkins:
                latest_checkin = (
                    checkins.filter(checkin_time__lt=checkin.checkin_time)
                    .order_by("-checkin_time")
                    .first()
                )
                weight = (
                    max(checkin.net_weight - latest_checkin.net_weight, 0)
                    if latest_checkin
                    else checkin.net_weight
                )
                unit_price = Decimal(checkin.unit_price)
                rate = Decimal(checkin.rate)
                total_revenue += weight * (unit_price / 100) * (rate / 100)
                total_amount += weight

    return total_revenue, total_amount


def calculate_merchant_revenue_and_amount(
    exporter=None, start_date=None, end_date=None
):
    total_revenue = Decimal(0)
    total_amount = 0
    if exporter is not None:
        declaracions = Declaracion.objects.filter(
            exporter=exporter, created_at__gte=start_date, created_at__lte=end_date
        ).prefetch_related("checkins")

        for declaracion in declaracions:
            checkins = declaracion.checkins.filter(
                checkin_time__lte=end_date,
                checkin_time__gte=start_date,
                status__in=["pass", "paid", "success"],
            )
            for checkin in checkins:
                latest_checkin = (
                    checkins.filter(checkin_time__lt=checkin.checkin_time)
                    .order_by("-checkin_time")
                    .first()
                )
                weight = (
                    max(checkin.net_weight - latest_checkin.net_weight, 0)
                    if latest_checkin
                    else checkin.net_weight
                )
                unit_price = Decimal(checkin.unit_price)
                rate = Decimal(checkin.rate)
                total_revenue += weight * (unit_price / 100) * (rate / 100)
                total_amount += weight

    return total_revenue, total_amount


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def top_exporters_report(request):
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    print(start_date_str, " start_date")
    print(end_date_str, " end_date")
    # 2. Parse the dates using parse_date
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    today = timezone.now().date()
    if not end_date:
        end_date = today
    if not start_date:
        start_date = today - timedelta(days=365)  # Approx. one year

    # Calculate total revenue and other metrics
    top_exporter_merchant = (
        Exporter.objects.annotate(
            declaracions_count=Count(
                "declaracions",
                filter=Q(
                    declaracions__checkins__status__in=["pass", "paid", "success"],
                    declaracions__created_at__gte=start_date,
                    declaracions__created_at__lte=end_date,
                ),
                distinct=True,
            )
        )
        .filter(declaracions_count__gt=0)
        .order_by("-declaracions_count")[:10]
    )

    top_exporter_local = (
        Exporter.objects.annotate(
            localJourneys_count=Count(
                "localJourneys",
                filter=Q(
                    localJourneys__checkins__status__in=["pass", "paid", "success"],
                    localJourneys__created_at__gte=start_date,
                    localJourneys__created_at__lte=end_date,
                ),
                distinct=True,
            ),
        )
        .filter(localJourneys_count__gt=0)
        .order_by("-localJourneys_count")[:10]
    )

    report_data = {"local": [], "merchant": []}

    for top_local_exporter in top_exporter_local:
        revenue, amount = calculate_local_revenue_and_amount(
            exporter=top_local_exporter,
            start_date=start_date,
            end_date=end_date,
        )

        if top_local_exporter:
            report_data["local"].append(
                {
                    # "tin_number": exporter.tin_number,
                    "type": top_local_exporter.type.name,
                    "exporter_name": top_local_exporter.first_name
                    + " "
                    + top_local_exporter.last_name,
                    "total_amount": amount,
                    "total_revenue": round(revenue, 2),
                    "total_path": top_local_exporter.localJourneys_count,
                }
            )

    for top_merchant_exporter in top_exporter_merchant:
        revenue, amount = calculate_merchant_revenue_and_amount(
            exporter=top_merchant_exporter,
            start_date=start_date,
            end_date=end_date,
        )

        if top_merchant_exporter:
            report_data["merchant"].append(
                {
                    "tin_number": top_merchant_exporter.tin_number,
                    "type": top_merchant_exporter.type.name,
                    "exporter_name": top_merchant_exporter.first_name
                    + " "
                    + top_merchant_exporter.last_name,
                    "total_amount": amount,
                    "total_revenue": round(revenue, 2),
                    "total_path": top_merchant_exporter.declaracions_count,
                }
            )

    # Prepare the report data

    return Response(report_data)
