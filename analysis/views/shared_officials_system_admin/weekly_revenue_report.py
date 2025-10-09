from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.utils.timezone import now
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin

from ..helpers import annotate_revenue_on_checkins


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def weekly_revenue_report(request):
    """
    Provides a report of total revenue, total amount (weight), and transaction
    count aggregated over the last four complete weeks, ending on the most
    recent Sunday. This report is generated with a single, optimized
    database query.
    """
    today = now().date()
    start_of_this_week = today - timedelta(days=today.weekday())
    four_weeks_ago = start_of_this_week - timedelta(weeks=4)
    end_of_last_week = start_of_this_week - timedelta(seconds=1)

    filters = {
        "checkin_time__range": [four_weeks_ago, end_of_last_week],
        "status__in": ["pass", "paid", "success"],
    }

    weekly_totals = (
        Checkin.objects.filter(**filters)
        .annotate_revenue_on_checkins()
        .annotate(week_start=TruncWeek("checkin_time"))
        .values("week_start")
        .annotate(
            total_revenue=Sum("revenue"),
            total_amount=Sum("incremental_weight"),
            transaction=Count("id"),
        )
        .order_by("week_start")
    )

    week_starts = [four_weeks_ago + timedelta(weeks=i) for i in range(4)]
    week_keys = ["week1", "week2", "week3", "week4"]
    date_to_key_map = {
        week_starts[i].date(): week_keys[i] for i in range(len(week_starts))
    }

    response_data = {
        key: {"total_revenue": Decimal(0), "total_amount": 0, "transaction": 0}
        for key in week_keys
    }

    for item in weekly_totals:
        week_key = date_to_key_map.get(item["week_start"].date())
        if week_key:
            response_data[week_key] = {
                "total_revenue": round(item["total_revenue"] or Decimal(0), 2),
                "total_amount": round(item["total_amount"] or 0, 2),
                "transaction": item["transaction"],
            }

    return Response(response_data)
