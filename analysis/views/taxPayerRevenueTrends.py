from decimal import Decimal

from django.db.models import F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def tax_payer_revenue_trends(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))

    # Build filter criteria
    filter_criteria = {}
    if start_date:
        filter_criteria["checkin_time__gte"] = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        filter_criteria["checkin_time__lte"] = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
    filter_criteria["status__in"] = ["pass", "paid", "success"]

    # Fetch relevant checkins
    checkins = Checkin.objects.filter(**filter_criteria).select_related(
        "declaracion", "declaracion__exporter", "localJourney", "localJourney__exporter"
    )

    # Helper function for revenue calculation
    def calculate_revenue(checkins):
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
            revenue_data.append(
                {"checkin_time": checkin.checkin_time, "revenue": revenue}
            )
        return revenue_data

    # Calculate revenue data
    revenue_data = calculate_revenue(checkins)

    # Generate report based on selected_date_type
    labels = []
    datasets = []

    if selected_date_type == "weekly":
        # Group revenue by day of the week
        days_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        regular_taxpayer_data = [0] * 7
        walk_in_taxpayer_data = [0] * 7

        for entry in revenue_data:
            day_index = entry["checkin_time"].weekday()
            if entry["revenue"] > 1000:  # Example condition for "Regular Taxpayers"
                regular_taxpayer_data[day_index] += float(entry["revenue"])
            else:
                walk_in_taxpayer_data[day_index] += float(entry["revenue"])

        labels = days_labels
        datasets = [
            {"label": "Regular Taxpayers", "data": regular_taxpayer_data},
            {"label": "Walk-in Taxpayers", "data": walk_in_taxpayer_data},
        ]

    elif selected_date_type == "monthly":
        # Group revenue by day of the month
        daily_revenue = {}
        for entry in revenue_data:
            day = entry["checkin_time"].day
            if day not in daily_revenue:
                daily_revenue[day] = {"regular": 0, "walk_in": 0}
            if entry["revenue"] > 1000:  # Example condition for "Regular Taxpayers"
                daily_revenue[day]["regular"] += float(entry["revenue"])
            else:
                daily_revenue[day]["walk_in"] += float(entry["revenue"])

        labels = [f"{day:02}" for day in sorted(daily_revenue.keys())]
        datasets = [
            {
                "label": "Regular Taxpayers",
                "data": [
                    daily_revenue[day]["regular"]
                    for day in sorted(daily_revenue.keys())
                ],
            },
            {
                "label": "Walk-in Taxpayers",
                "data": [
                    daily_revenue[day]["walk_in"]
                    for day in sorted(daily_revenue.keys())
                ],
            },
        ]

    elif selected_date_type == "yearly":
        # Group revenue by month
        monthly_revenue = {}
        for entry in revenue_data:
            month = entry["checkin_time"].strftime("%b")
            if month not in monthly_revenue:
                monthly_revenue[month] = {"regular": 0, "walk_in": 0}
            if entry["revenue"] > 1000:  # Example condition for "Regular Taxpayers"
                monthly_revenue[month]["regular"] += float(entry["revenue"])
            else:
                monthly_revenue[month]["walk_in"] += float(entry["revenue"])

        labels = sorted(
            monthly_revenue.keys(),
            key=lambda x: timezone.datetime.strptime(x, "%b").month,
        )
        datasets = [
            {
                "label": "Regular Taxpayers",
                "data": [monthly_revenue[month]["regular"] for month in labels],
            },
            {
                "label": "Walk-in Taxpayers",
                "data": [monthly_revenue[month]["walk_in"] for month in labels],
            },
        ]

    return Response({"labels": labels, "datasets": datasets})
