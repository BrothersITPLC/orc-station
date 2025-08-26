from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([AllowAny])
def monthly_revenue_report(request):
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    filters = {"status": "success"}
    if start_date:
        filters["checkin_time__gte"] = start_date
    if end_date:
        filters["checkin_time__lte"] = end_date
    if station_id and station_id != "null":
        filters["station_id"] = station_id
    if controller_id and controller_id != "null":
        filters["employee_id"] = controller_id

    queryset = (
        Checkin.objects.filter(**filters)
        .annotate(amount=F("net_weight") * F("unit_price") * (1 + F("rate") / 100))
        .values("checkin_time", "amount")
    )

    revenue_by_day = {}
    for item in queryset:
        day = item["checkin_time"].strftime("%d")
        if day not in revenue_by_day:
            revenue_by_day[day] = 0
        revenue_by_day[day] += item["amount"]

    labels = sorted(revenue_by_day.keys())
    data = [revenue_by_day[label] for label in labels]

    response_data = {"labels": labels, "data": data}

    return Response(response_data)
