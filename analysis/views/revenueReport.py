from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin

from ..serializers import RevenueSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def revenue_report(request):
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    filters = {}
    if start_date:
        filters["checkin_time__gte"] = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        filters["checkin_time__lte"] = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
    if station_id and station_id != "null":
        filters["station_id"] = station_id
    if controller_id and controller_id != "null":
        filters["employee_id"] = controller_id
    filters["status"] = "success"

    checkins = Checkin.objects.filter(**filters).select_related(
        "declaracion",
        "declaracion__exporter",
        "declaracion__commodity",
        "payment_method",
        "localJourney",
        "localJourney__exporter",
        "localJourney__commodity",
    )

    revenue_data = []
    for checkin in checkins:
        # Find the latest checkin for the same declaracion or localJourney
        latest_checkin = (
            checkins.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        # Calculate weight based on the difference from the latest checkin
        weight = (
            max(checkin.net_weight - latest_checkin.net_weight, 0)
            if latest_checkin
            else checkin.net_weight
        )
        weight = Decimal(weight)
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = weight * (unit_price / Decimal(100)) * (rate / Decimal(100))

        revenue_data.append({"checkin_time": checkin.checkin_time, "revenue": revenue})

    # Prepare data for serialization
    report_data = []
    for revenue_entry in revenue_data:
        checkin_time = revenue_entry["checkin_time"]
        revenue = revenue_entry["revenue"]
        checkin = checkins.get(checkin_time=checkin_time)

        if checkin.declaracion:
            declaracion = checkin.declaracion
            report_data.append(
                {
                    "tin_number": (
                        declaracion.exporter.tin_number
                        if declaracion.exporter
                        else None
                    ),
                    "exporter_first_name": (
                        declaracion.exporter.first_name
                        if declaracion.exporter
                        else None
                    ),
                    "exporter_last_name": (
                        declaracion.exporter.last_name if declaracion.exporter else None
                    ),
                    "commodity_name": (
                        declaracion.commodity.name if declaracion.commodity else None
                    ),
                    "payment_method": (
                        checkin.payment_method.name if checkin.payment_method else None
                    ),
                    "amount": round(float(revenue), 2),
                }
            )
        elif checkin.localJourney:
            local_journey = checkin.localJourney
            report_data.append(
                {
                    "tin_number": (
                        local_journey.exporter.unique_id
                        if local_journey.exporter
                        else None
                    ),
                    "exporter_first_name": (
                        local_journey.exporter.first_name
                        if local_journey.exporter
                        else None
                    ),
                    "exporter_last_name": (
                        local_journey.exporter.last_name
                        if local_journey.exporter
                        else None
                    ),
                    "commodity_name": (
                        local_journey.commodity.name
                        if local_journey.commodity
                        else None
                    ),
                    "payment_method": (
                        checkin.payment_method.name if checkin.payment_method else None
                    ),
                    "amount": round(float(revenue), 2),
                }
            )

    serializer = RevenueSerializer(data=report_data, many=True)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)
