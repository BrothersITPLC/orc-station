from collections import defaultdict
from datetime import datetime, timedelta

#     return Response(response_data)
from django.db.models import F, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analysis.views.helpers import hourly_data as hour_data
from analysis.views.helpers import monthly_data as month_data
from analysis.views.helpers import weekly_data as week_data
from declaracions.models import Checkin
from exporters.models import Exporter


def calculate_amount_year(
    requested_year=timezone.now().year,
    current_station=None,
    user=None,
    new_Interval=None,
    date=None,
    week=None,
    month=None,
):

    # Filter Checkin objects for the requested year
    daily_data = week_data.copy()
    monthly_data = month_data.copy()
    hourly_data = hour_data.copy()
    all_checkins = []
    start_date = None
    end_date = None
    if new_Interval == "Weekly" and week is not None and month is not None:

        first_day_of_month = datetime(int(requested_year), int(month), 1)
        # Calculate the start of the specified week
        week_start_day = first_day_of_month + timedelta(weeks=int(week) - 1)

        # Adjust to the correct week day (Monday as start of the week)
        week_start_day = week_start_day - timedelta(
            days=week_start_day.weekday()
        )  # Get to Monday of that week

        # Determine the start and end dates for that week
        start_date = timezone.make_aware(
            week_start_day.replace(hour=0, minute=0, second=0)
        )
        end_date = timezone.make_aware(
            week_start_day.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        )
        print(start_date, end_date)

    if not requested_year:
        requested_year = timezone.now().year
    if new_Interval == "Daily":
        all_checkins = Checkin.objects.filter(checkin_time__date=date)
    elif new_Interval == "Weekly":
        all_checkins = Checkin.objects.filter(
            checkin_time__range=(start_date, end_date)
        )
    else:
        all_checkins = Checkin.objects.filter(checkin_time__year=requested_year)

    if current_station:
        print(current_station, "Current Staition")
        all_checkins = all_checkins.filter(station=current_station)
        if user.role.name == "controller":
            all_checkins = all_checkins.filter(employee=user)

    for check_in in all_checkins:
        amount = 0
        print(check_in.status, "")
        local = False
        if check_in.status not in ["paid", "pass", "success"]:
            continue
        # Determine the previous check-in based on declaracion or localJourney
        if check_in.declaracion:
            previous_checkin = (
                Checkin.objects.filter(
                    declaracion=check_in.declaracion,
                    checkin_time__lt=check_in.checkin_time,
                )
                .order_by("-checkin_time")
                .first()
            )
            local = False
        elif check_in.localJourney:
            previous_checkin = (
                Checkin.objects.filter(
                    localJourney=check_in.localJourney,
                    checkin_time__lt=check_in.checkin_time,
                )
                .order_by("-checkin_time")
                .first()
            )
            local = True
        else:
            previous_checkin = None

        # Calculate the amount based on the previous check-in
        if previous_checkin:
            weight_difference = check_in.net_weight - previous_checkin.net_weight
            if weight_difference > 0:
                amount = (
                    weight_difference * check_in.unit_price / 100 * check_in.rate / 100
                )
        else:
            amount = (
                check_in.net_weight * check_in.unit_price / 100 * check_in.rate / 100
            )

        # Get the month from the check-in time
        month = check_in.checkin_time.strftime("%b")  # Month in abbreviated format
        day = check_in.checkin_time.strftime("%a")
        hour = check_in.checkin_time.hour + 1
        if local:
            month += "_WalkIn"
            day += "_WalkIn"
            hour_key = f"{hour}h_WalkIn"

        else:
            month += "_Regular"
            day += "_Regular"
            hour_key = f"{hour}h_Regular"

        # Add the amount to the corresponding month
        monthly_data[month] += float(amount)
        daily_data[day] += float(amount)
        hourly_data[hour_key] += float(amount)

    # Sort months to ensure they are in the correct order
    if new_Interval == "Weekly":
        return daily_data
    elif new_Interval == "Daily":
        return hourly_data
    return monthly_data


def calculate_amount(
    current_station=None, user=None, requested_year=None, start_date=None, end_date=None
):
    all_checkins = None
    if start_date is None or end_date is None:
        requested_year = timezone.now().year
        all_checkins = Checkin.objects.filter(checkin_time__year=requested_year)
    else:
        all_checkins = Checkin.objects.filter(
            checkin_time__gte=start_date, checkin_time__lte=end_date
        )
    if current_station:
        all_checkins = all_checkins.filter(station=current_station)
        if user.role.name == "controller":
            all_checkins = all_checkins.filter(employee=user)
    walk_in_amount = 0
    regular_amount = 0
    is_local = False

    for check_in in all_checkins:
        amount = 0
        if not check_in.status in ["paid", "pass", "success"]:
            continue
        # Determine the previous check-in based on declaracion or localJourney
        if check_in.declaracion:
            previous_checkin = (
                Checkin.objects.filter(
                    declaracion=check_in.declaracion,
                    checkin_time__lt=check_in.checkin_time,
                )
                .order_by("-checkin_time")
                .first()
            )
            is_local = False
        elif check_in.localJourney:
            previous_checkin = (
                Checkin.objects.filter(
                    localJourney=check_in.localJourney,
                    checkin_time__lt=check_in.checkin_time,
                )
                .order_by("-checkin_time")
                .first()
            )
            is_local = True
        else:
            previous_checkin = None

        # Calculate the amount based on the previous check-in
        if previous_checkin:
            weight_difference = check_in.net_weight - previous_checkin.net_weight
            if weight_difference > 0:
                amount = (
                    weight_difference * check_in.unit_price / 100 * check_in.rate / 100
                )
            previous_checkin = None

        else:
            amount = (
                check_in.net_weight * check_in.unit_price / 100 * check_in.rate / 100
            )

        if not is_local:
            regular_amount += amount
        else:
            walk_in_amount += amount

        # Get the month from the check-in time
    return walk_in_amount, regular_amount


@api_view(["GET"])
def daily_revenue_report(request):
    year = request.query_params.get("year")
    month = request.query_params.get("month")
    date = request.query_params.get("date")
    week = request.query_params.get("week")
    newInterval = request.query_params.get("newInterval")

    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    end_date = parse_date(end_date_str) if end_date_str else datetime.now().date()

    # If no start_date is provided, set it to one year before the end_date
    start_date = (
        parse_date(start_date_str)
        if start_date_str
        else (end_date - timedelta(days=365))
    )

    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")
    regular = Exporter.objects.filter(type__name="regular").count()
    walk_in = Exporter.objects.filter(type__name="walk in").count()
    current_station = request.user.current_station

    data = calculate_amount_year(
        year, current_station, request.user, newInterval, date, week, month
    )

    return Response(
        {
            "data": data,
            "regular": regular,
            "walk_in": walk_in,
        }
    )


@api_view(["GET"])
def revenue_and_number(request):

    start_date = request.query_params.get("start_date")
    start_date = parse_date(start_date)
    end_date = request.query_params.get("end_date")
    end_date = parse_date(end_date)
    start_datetime = datetime.combine(start_date, datetime.min.time())

    # Convert end_date to the end of the day (23:59:59)
    end_datetime = datetime.combine(end_date, datetime.max.time())
    start_date = start_datetime
    end_date = end_datetime
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")
    regular = Exporter.objects.filter(
        type__name="regular", created_at__gte=start_date, created_at__lte=end_date
    ).count()
    walk_in = Exporter.objects.filter(
        type__name="walk in", created_at__gte=start_date, created_at__lte=end_date
    ).count()
    current_station = request.user.current_station

    walk_in_amount, regular_amount = calculate_amount(
        current_station, request.user, start_date=start_date, end_date=end_date
    )

    return Response(
        {
            "walk_in_amount": walk_in_amount,
            "regular_amount": regular_amount,
            "regular": regular,
            "walk_in": walk_in,
        }
    )
