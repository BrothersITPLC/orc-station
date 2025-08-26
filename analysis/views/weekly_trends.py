from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, now
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def weekly_revenue_report(request):
    today = now().date()

    # Calculate the start date (4 weeks ago)
    four_weeks_ago = today - timedelta(weeks=4)

    # Define week ranges (4 weeks)
    week_ranges = [
        (
            make_aware(
                datetime.combine(
                    four_weeks_ago + timedelta(days=i * 7), datetime.min.time()
                )
            ),
            make_aware(
                datetime.combine(
                    four_weeks_ago + timedelta(days=(i + 1) * 7 - 1),
                    datetime.max.time(),
                )
            ),
        )
        for i in range(4)
    ]
    # Initialize response data
    weekly_data = {
        "week1": {"total_revenue": Decimal(0), "total_amount": 0, "transaction": 0},
        "week2": {"total_revenue": Decimal(0), "total_amount": 0, "transaction": 0},
        "week3": {"total_revenue": Decimal(0), "total_amount": 0, "transaction": 0},
        "week4": {"total_revenue": Decimal(0), "total_amount": 0, "transaction": 0},
    }

    # Process data for each week
    for week_idx, (week_start, week_end) in enumerate(week_ranges):
        week_key = f"week{week_idx + 1}"
        total_revenue = Decimal(0)
        total_amount = 0
        week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)

        print("start_date ", week_start, "         end_date:", week_end)
        # Fetch checkins for the current week
        checkins = Checkin.objects.filter(
            checkin_time__gte=week_start,
            checkin_time__lte=week_end,
            status__in=["pass", "paid", "success"],
        )
        weekly_data[week_key]["transaction"] = len(checkins)
        print(checkins)
        for checkin in checkins:

            print(checkin.checkin_time, "this is checkin Time")
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

        weekly_data[week_key]["total_revenue"] = round(total_revenue, 2)
        weekly_data[week_key]["total_amount"] = round(total_amount, 2)

    return Response(weekly_data)
