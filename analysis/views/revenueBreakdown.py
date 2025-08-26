from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin, Declaracion
from exporters.models import Exporter
from localcheckings.models import JourneyWithoutTruck


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def revenue_breakdown_report(request):
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))

    if start_date:
        start_date = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        end_date = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )

    from_regular = Decimal(0)
    from_walkIn = Decimal(0)
    regular_exporters = set()
    walkin_exporters = set()

    # Revenue from declaracions
    declaracions = Declaracion.objects.filter(
        created_at__gte=start_date, created_at__lte=end_date
    ).prefetch_related("checkins", "exporter")

    for declaracion in declaracions:
        checkins = declaracion.checkins.filter(
            checkin_time__lte=end_date,
            checkin_time__gte=start_date,
            status__in=["pass", "paid", "success"],
        )
        if checkins.exists():
            regular_exporters.add(declaracion.exporter_id)
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
            from_regular += weight * (unit_price / 100) * (rate / 100)

    # Revenue from local journeys
    journeys = JourneyWithoutTruck.objects.filter(
        created_at__gte=start_date, created_at__lte=end_date
    ).prefetch_related("checkins", "exporter")

    for journey in journeys:
        checkins = journey.checkins.filter(
            checkin_time__lte=end_date,
            checkin_time__gte=start_date,
            status__in=["pass", "paid", "success"],
        )
        if checkins.exists():
            walkin_exporters.add(journey.exporter_id)
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
            from_walkIn += weight * (unit_price / 100) * (rate / 100)

    total = from_regular + from_walkIn
    result = {
        "from_regular": float(from_regular),
        "from_walkIn": float(from_walkIn),
        "total": float(total),
        "regular_exporters": len(regular_exporters),
        "walkin_exporters": len(walkin_exporters),
    }

    return Response(result)
