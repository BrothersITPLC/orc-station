from datetime import timedelta
from decimal import Decimal

from django.utils.timezone import now
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from users.models import CustomUser


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cashier_today_report(request):
    station_id = request.query_params.get("station_id")

    if not station_id or station_id == "null":
        return Response({"error": "station_id is required"}, status=400)

    controller_exists = CustomUser.objects.filter(id=station_id).exists()
    if not controller_exists:
        return Response({"error": "Controller not found"}, status=404)

    time_threshold = now() - timedelta(hours=24)

    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__gte": time_threshold,
        "station_id": station_id,
    }

    checkins = Checkin.objects.filter(**filters).select_related(
        "declaracion",
        "declaracion__exporter",
        "declaracion__commodity",
        "payment_method",
        "localJourney",
        "localJourney__exporter",
        "localJourney__commodity",
    )

    total_revenue = Decimal(0)
    revenue_walkin = Decimal(0)
    revenue_regular = Decimal(0)
    total_kg = Decimal(0)
    kg_walkin = Decimal(0)
    kg_regular = Decimal(0)
    checkedin_tax_payers = 0
    tax_payers_walkin = 0
    tax_payers_regular = 0

    for checkin in checkins:
        latest_checkin = (
            Checkin.objects.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        weight = (
            max(checkin.net_weight - latest_checkin.net_weight, 0)
            if latest_checkin
            else checkin.net_weight
        )
        weight = Decimal(weight)

        # Calculate revenue
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = weight * (unit_price / Decimal(100)) * (rate / Decimal(100))

        total_revenue += revenue
        total_kg += weight
        if checkin.localJourney:
            revenue_walkin += revenue
            kg_walkin += weight
            tax_payers_walkin += 1
        elif checkin.declaracion:
            revenue_regular += revenue
            kg_regular += weight
            tax_payers_regular += 1

    checkedin_tax_payers = tax_payers_walkin + tax_payers_regular

    response_data = [
        {
            "label": "Total Revenue",
            "amount": str(total_revenue.quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Walk-in",
            "amount": str(revenue_walkin.quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Regular",
            "amount": str(revenue_regular.quantize(Decimal("0.0"))),
        },
        {"label": "Total kg", "amount": str(total_kg.quantize(Decimal("0.0")))},
        {
            "label": "Total kg From Walk-in",
            "amount": str(kg_walkin.quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg From Regular",
            "amount": str(kg_regular.quantize(Decimal("0.0"))),
        },
        {"label": "Total Checked in Tax Payers", "amount": str(checkedin_tax_payers)},
        {
            "label": "Total Checked in Walk-in Tax Payers",
            "amount": str(tax_payers_walkin),
        },
        {
            "label": "Total Checked in Regular Tax Payers",
            "amount": str(tax_payers_regular),
        },
    ]

    return Response(response_data)
