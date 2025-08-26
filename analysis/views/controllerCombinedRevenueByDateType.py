from calendar import month_name, monthrange
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def controller_combined_revenue_by_date_type(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")
    controller_id = request.query_params.get("controller_id")

    if not selected_date_type or not start_date or not end_date or not controller_id:
        return Response({"error": "Missing required parameters."}, status=400)

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
        if (end_date - start_date).days + 1 != days_in_month:
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

    # Define the time range and apply controller filter
    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__range": [start_date, end_date],
        "employee_id": controller_id,
    }

    # Query checkins
    checkins = Checkin.objects.filter(**filters).select_related(
        "declaracion", "localJourney"
    )

    # Initialize data containers
    revenue_data = {}

    # Generate categories and group data based on selected_date_type
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

            day_of_week = checkin.checkin_time.strftime("%A")
            revenue_data[day_of_week] = revenue_data.get(day_of_week, 0) + revenue

    elif selected_date_type == "monthly":
        categories = [
            f"Week {i}" for i in range(1, (end_date.day - start_date.day) // 7 + 2)
        ]
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

            week_number = (checkin.checkin_time.day - 1) // 7 + 1
            week_label = f"Week {week_number}"
            revenue_data[week_label] = revenue_data.get(week_label, 0) + revenue

    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]
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

            month_name_str = checkin.checkin_time.strftime("%B")
            revenue_data[month_name_str] = revenue_data.get(month_name_str, 0) + revenue

    else:
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=400,
        )

    # Build the series and categories in the desired format
    series_data = [
        {
            "name": "Revenue",
            "data": [revenue_data.get(category, 0) for category in categories],
        }
    ]

    return Response({"series": series_data, "labels": categories})
