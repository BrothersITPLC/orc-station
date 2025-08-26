from decimal import Decimal

from django.db.models import F, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def revenue_trends_report(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))

    filter = {}
    if start_date:
        filter["checkin_time__gte"] = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        filter["checkin_time__lte"] = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
    filter["status__in"] = ["pass", "paid", "success"]

    checkins = Checkin.objects.filter(**filter).select_related(
        "declaracion", "declaracion__exporter", "localJourney", "localJourney__exporter"
    )

    revenue_data = []
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
    print(revenue_data)
    report_data = []

    if selected_date_type == "weekly":
        # Group by day of the week
        days_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for i in range(1, 8):
            day_revenue = sum(
                entry["revenue"]
                for entry in revenue_data
                if entry["checkin_time"].weekday() + 1 == i
            )
            report_data.append(
                {
                    "label": days_labels[i % 7],
                    "amount": float(day_revenue),
                }
            )

    elif selected_date_type == "monthly":
        # Group by day of the month
        monthly_revenue = {}
        for entry in revenue_data:
            day = entry["checkin_time"].day
            monthly_revenue[day] = (
                monthly_revenue.get(day, Decimal(0)) + entry["revenue"]
            )
        for day, total_revenue in sorted(monthly_revenue.items()):
            report_data.append(
                {
                    "label": day,
                    "amount": float(total_revenue),
                }
            )

    elif selected_date_type == "yearly":
        # Group by month
        yearly_revenue = {}
        for entry in revenue_data:
            month = entry["checkin_time"].strftime("%b")
            yearly_revenue[month] = (
                yearly_revenue.get(month, Decimal(0)) + entry["revenue"]
            )
        for month, total_revenue in sorted(yearly_revenue.items()):
            report_data.append(
                {
                    "label": month,
                    "amount": float(total_revenue),
                }
            )

    return Response(report_data)
