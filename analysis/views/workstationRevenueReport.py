from decimal import Decimal

from django.db.models import ExpressionWrapper, F, FloatField, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def workstation_revenue_report(request):
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))

    data = {}
    workstation = WorkStation.objects.all().prefetch_related("checkins")
    for station in workstation:
        data[station.name] = {
            "total_revenue": Decimal(0),
            "total_amount": 0,
        }
        total_revenue = Decimal(0)
        total_amount = 0
        checkins = station.checkins.filter(
            checkin_time__gte=start_date,
            checkin_time__lte=end_date,
            status__in=["pass", "paid", "success"],
        )

        for checkin in checkins:

            latest_checkin = None

            if checkin.declaracion:

                latest_checkin = (
                    Checkin.objects.filter(
                        checkin_time__lt=checkin.checkin_time,
                        declaracion=checkin.declaracion,
                    )
                    .order_by("-checkin_time")
                    .first()
                )

            else:
                latest_checkin = (
                    Checkin.objects.filter(
                        checkin_time__lt=checkin.checkin_time,
                        localJourney=checkin.localJourney,
                    )
                    .order_by("-checkin_time")
                    .first()
                )

            weight = max(
                checkin.net_weight
                - (latest_checkin.net_weight if latest_checkin else 0),
                0,
            )
            unit_price = Decimal(checkin.unit_price)
            rate = Decimal(checkin.rate)
            total_revenue += weight * (unit_price / 100) * (rate / 100)
            total_amount += weight

        data[station.name]["total_revenue"] = round(total_revenue, 2)
        data[station.name]["total_amount"] = round(total_amount, 2)

    # Prepare the report data
    labels = WorkStation.objects.all()
    labels = [station.name for station in labels]

    return Response({"labels": labels, "data": data})
