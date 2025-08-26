from calendar import month_name, monthrange
from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractWeek, ExtractWeekDay
from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from drivers.models import Driver


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def cashier_drivers_registered_by_date_type(request):
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

    # Validate date range for selected_date_type
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
    elif selected_date_type == "yearly":
        if (end_date - start_date).days + 1 not in (365, 366):
            return Response(
                {"error": "For 'yearly', the date range must cover the entire year."},
                status=400,
            )

    # Filter drivers by station_id and date range
    drivers = Driver.objects.filter(
        register_place_id=station_id,
        created_at__range=[start_date, end_date],
    )

    # Initialize categories and data containers
    categories = []
    data = []

    # Group and aggregate data based on selected_date_type
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
        daily_counts = (
            drivers.annotate(day_of_week=ExtractWeekDay("created_at"))
            .values("day_of_week")
            .annotate(count=Count("id"))
        )
        day_to_name = {i: categories[i - 1] for i in range(1, 8)}
        data = [0] * 7
        for entry in daily_counts:
            day_name = day_to_name[entry["day_of_week"]]
            index = categories.index(day_name)
            data[index] = entry["count"]

    elif selected_date_type == "monthly":
        weeks = (
            drivers.annotate(week_number=ExtractWeek("created_at"))
            .values("week_number")
            .annotate(count=Count("id"))
        )
        total_weeks = (end_date.day - start_date.day) // 7 + 1
        categories = [f"Week {i}" for i in range(1, total_weeks + 1)]
        data = [0] * total_weeks
        for entry in weeks:
            week_label = (
                f"Week {entry['week_number'] - start_date.isocalendar()[1] + 1}"
            )
            if week_label in categories:
                index = categories.index(week_label)
                data[index] = entry["count"]

    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]
        monthly_counts = (
            drivers.annotate(month=ExtractMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
        )
        data = [0] * 12
        for entry in monthly_counts:
            index = entry["month"] - 1
            data[index] = entry["count"]

    else:
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=400,
        )

    # Build response data
    series = [{"name": "Drivers Registered", "data": data}]

    return Response({"series": series, "categories": categories})
