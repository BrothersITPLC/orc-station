from calendar import Calendar, month_name, monthrange
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cashier_revenue_by_date_type(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")

    # Validate required parameters
    missing_params = [
        param
        for param in ["selected_date_type", "start_date", "end_date", "station_id"]
        if not request.query_params.get(param)
    ]
    if missing_params:
        return Response(
            {"error": f"Missing required parameters: {', '.join(missing_params)}."},
            status=400,
        )

    # Parse and validate dates
    try:
        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
        end_date = make_aware(
            datetime.strptime(end_date, "%Y-%m-%d")
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    if end_date < start_date:
        return Response(
            {"error": "End date cannot be earlier than start date."}, status=400
        )

    # Validate date range against selected_date_type
    if selected_date_type == "weekly":
        if (end_date - start_date).days + 1 != 7:
            return Response(
                {"error": "For 'weekly', the date range must be exactly 7 days."},
                status=400,
            )
    elif selected_date_type == "monthly":
        days_in_month = monthrange(start_date.year, start_date.month)[1]
        if start_date.day != 1 or end_date.day != days_in_month:
            return Response(
                {"error": "For 'monthly', the date range must cover the entire month."},
                status=400,
            )
        # Adjust end_date to the last second of the month
        end_date = make_aware(
            datetime(start_date.year, start_date.month, days_in_month, 23, 59, 59)
        )
    elif selected_date_type == "yearly":
        if (end_date - start_date).days + 1 not in (365, 366):
            return Response(
                {"error": "For 'yearly', the date range must cover the entire year."},
                status=400,
            )

    # Query filters
    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__range": [start_date, end_date],
        "station_id": station_id,
    }

    # Query Checkin records
    checkins = (
        Checkin.objects.filter(**filters)
        .select_related("declaracion", "localJourney")
        .order_by("checkin_time")
    )

    # Data containers
    regular_data = {}
    walkin_data = {}

    # Generate categories and process data
    if selected_date_type == "weekly":
        categories = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        for checkin in checkins:
            day_of_week = checkin.checkin_time.strftime("%A")
            revenue = calculate_revenue(checkin)
            if checkin.localJourney:
                walkin_data[day_of_week] = walkin_data.get(day_of_week, 0) + revenue
            else:
                regular_data[day_of_week] = regular_data.get(day_of_week, 0) + revenue

    elif selected_date_type == "monthly":
        calendar = Calendar()
        weeks = calendar.monthdayscalendar(start_date.year, start_date.month)
        categories = [f"Week {i + 1}" for i in range(len(weeks))]
        for checkin in checkins:
            week_number = next(
                (
                    i + 1
                    for i, week in enumerate(weeks)
                    if checkin.checkin_time.day in week
                ),
                0,
            )
            week_label = f"Week {week_number}"
            revenue = calculate_revenue(checkin)
            if checkin.localJourney:
                walkin_data[week_label] = walkin_data.get(week_label, 0) + revenue
            else:
                regular_data[week_label] = regular_data.get(week_label, 0) + revenue

    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]
        for checkin in checkins:
            month_label = checkin.checkin_time.strftime("%B")
            revenue = calculate_revenue(checkin)
            if checkin.localJourney:
                walkin_data[month_label] = walkin_data.get(month_label, 0) + revenue
            else:
                regular_data[month_label] = regular_data.get(month_label, 0) + revenue

    else:
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=400,
        )

    # Build response data
    regular_series = [regular_data.get(category, 0) for category in categories]
    walkin_series = [walkin_data.get(category, 0) for category in categories]
    series = [
        {"name": "Regular", "data": regular_series},
        {"name": "Walk-in", "data": walkin_series},
    ]

    return Response({"series": series, "categories": categories})


def calculate_revenue(checkin):
    """Calculate revenue for a given checkin."""
    latest_checkin = (
        Checkin.objects.filter(
            checkin_time__lt=checkin.checkin_time,
            localJourney=checkin.localJourney if checkin.localJourney else None,
            declaracion=checkin.declaracion if checkin.declaracion else None,
        )
        .order_by("-checkin_time")
        .first()
    )
    if latest_checkin and latest_checkin.net_weight is not None:
        current_weight = max(checkin.net_weight - latest_checkin.net_weight, 0)
    else:
        current_weight = checkin.net_weight or Decimal(0)

    unit_price = Decimal(checkin.unit_price or 0)
    rate = Decimal(checkin.rate or 0)
    return current_weight * (unit_price / Decimal(100)) * (rate / Decimal(100))
