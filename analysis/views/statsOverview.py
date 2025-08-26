from decimal import Decimal

from django.db.models import F, Sum
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def stats_overview(request):
    checkins = Checkin.objects.all()

    total_revenue = Decimal(0)
    total_weight = Decimal(0)

    for checkin in checkins:
        latest_checkin = (
            checkins.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        # Correct weight calculation
        weight = (
            max(Decimal(checkin.net_weight) - Decimal(latest_checkin.net_weight), 0)
            if latest_checkin
            else Decimal(checkin.net_weight)
        )

        # Accumulate weight and revenue
        total_weight += weight  # Now total_weight reflects incremental changes
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = weight * (unit_price / Decimal(100)) * (rate / Decimal(100))
        total_revenue += revenue

    # Calculate active stations and unique taxpayers
    total = Checkin.objects.aggregate(total=Sum("net_weight"))["total"] or 0

    active_stations = (
        WorkStation.objects.filter(checkins__isnull=False).distinct().count()
    )
    unique_taxpayers = checkins.values("declaracion__exporter").distinct().count()

    # Response
    return Response(
        {
            "totalRevenue": float(total_revenue),
            "totalWeight": float(total_weight),
            "activeStations": active_stations,
            "uniqueTaxpayers": unique_taxpayers,
        }
    )
