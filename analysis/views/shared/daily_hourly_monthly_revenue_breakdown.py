from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import (
    Coalesce,
    ExtractHour,
    ExtractMonth,
    ExtractWeekDay,
)
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from analysis.views.helpers.date_info import hourly_data, monthly_data, weekly_data
from declaracions.models import Checkin
from exporters.models import Exporter


@api_view(["GET"])
@permission_classes([AllowAny])
def daily_hourly_monthly_revenue_breakdown(request):
    """
    Provides a breakdown of revenue for 'Regular' and 'Walk-in' taxpayers,
    aggregated by day of the week, hour of the day, or month of the year,
    based on the 'newInterval' query parameter.

    This endpoint dynamically determines the date range based on 'year', 'month',
    'week', 'date', or the explicit 'start_date' and 'end_date'. It uses
    `annotate_revenue_on_checkins` for efficient database-level revenue calculations
    and categorizes taxpayers based on `declaracion` or `localJourney` links.
    The output format matches predefined templates (`weekly_data`, `monthly_data`,
    `hourly_data`) from the `date_info` helper.

    Query Parameters:
    - newInterval (str): Specifies the aggregation type ('Weekly', 'Daily', or 'Yearly' (default)). Required.
    - year (str, optional): The year for data filtering (e.g., "2023"). Used with 'Weekly' and default.
    - month (str, optional): The month (1-12) for 'Weekly' interval.
    - week (str, optional): The week number for 'Weekly' interval.
    - date (str, YYYY-MM-DD, optional): Specific date for 'Daily' interval.
    - start_date (str, YYYY-MM-DD, optional): Overall start date if other interval params are not used.
    - end_date (str, YYYY-MM-DD, optional): Overall end date if other interval params are not used.
    - station_id (str, optional): Filters check-ins by workstation ID.
    - controller_id (str, optional): Filters check-ins by employee (controller) ID.

    Returns:
        Response: A dictionary containing 'data' (aggregated revenue by interval and taxpayer type),
        'regular' (count of regular exporters created in the period), and 'walk_in' (count of walk-in
        exporters created in the period).

    Raises:
        HTTP 400 Bad Request: If date parameters are invalid or missing for the chosen interval.
    """
    year_str = request.query_params.get("year")
    month_str = request.query_params.get("month")
    date_str = request.query_params.get("date")
    week_str = request.query_params.get("week")
    new_interval = request.query_params.get(
        "newInterval"
    )  # Renamed to avoid conflict with `newInterval` in docstring

    start_date_param = request.query_params.get("start_date")
    end_date_param = request.query_params.get("end_date")

    # 1. Determine the effective date range for filtering check-ins
    actual_start_date = None
    actual_end_date = None

    try:
        if new_interval == "Daily" and date_str:
            # For a single day, uses the 'date' parameter
            parsed_date = parse_date(date_str)
            if not parsed_date:
                raise ValidationError("Invalid 'date' format. Use YYYY-MM-DD.")
            actual_start_date = timezone.make_aware(
                datetime.combine(parsed_date, datetime.min.time())
            )
            actual_end_date = timezone.make_aware(
                datetime.combine(parsed_date, datetime.max.time())
            )
        elif new_interval == "Weekly" and year_str and month_str and week_str:
            # For a specific week within a month/year
            requested_year_int = int(year_str)
            month_int = int(month_str)
            week_int = int(week_str)

            first_day_of_month = datetime(requested_year_int, month_int, 1)
            week_start_day = first_day_of_month + timedelta(weeks=week_int - 1)
            week_start_day = week_start_day - timedelta(
                days=week_start_day.weekday()
            )  # Adjust to Monday of that week

            actual_start_date = timezone.make_aware(
                week_start_day.replace(hour=0, minute=0, second=0)
            )
            actual_end_date = timezone.make_aware(
                week_start_day.replace(hour=23, minute=59, second=59)
                + timedelta(days=6)
            )
        else:
            # Default to using start_date/end_date query parameters.
            # If not provided, fallback to current year (matching original calculate_amount_year's default)
            if not start_date_param and not end_date_param:
                current_year = timezone.now().year
                start_date_param = f"{current_year}-01-01"
                end_date_param = f"{current_year}-12-31"
            elif not start_date_param and end_date_param:
                # If only end_date is provided, assume 1 year before it (matching original logic)
                parsed_end_date = parse_date(end_date_param)
                if not parsed_end_date:
                    raise ValidationError("Invalid 'end_date' format. Use YYYY-MM-DD.")
                start_date_param = (parsed_end_date - timedelta(days=365)).strftime(
                    "%Y-%m-%d"
                )

            # Now, use the helper to parse and validate the determined date range
            actual_start_date, actual_end_date = parse_and_validate_date_range(
                start_date_param, end_date_param
            )

    except (ValueError, TypeError, ValidationError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    # 2. Build base filter criteria for check-ins
    base_checkin_filters = Q(
        checkin_time__range=[actual_start_date, actual_end_date],
        status__in=["pass", "paid", "success"],
    )

    if station_id and station_id != "null":
        base_checkin_filters &= Q(station_id=station_id)

    # Apply user-specific filtering for controllers, or general controller_id filter
    if request.user.is_authenticated and request.user.role.name == "controller":
        base_checkin_filters &= Q(employee=request.user)
    elif controller_id and controller_id != "null":
        base_checkin_filters &= Q(employee_id=controller_id)

    checkins_query = Checkin.objects.filter(base_checkin_filters)

    if not checkins_query.exists():
        return Response({"data": {}, "regular": 0, "walk_in": 0})

    # 3. Annotate check-ins with incremental revenue and taxpayer type
    checkins_with_revenue = (
        annotate_revenue_on_checkins(checkins_query)
        .annotate(
            taxpayer_type=Case(
                When(declaracion__isnull=False, then=V("Regular")),
                When(localJourney__isnull=False, then=V("WalkIn")),
                default=V(
                    "Unknown"
                ),  # Should ideally not hit 'Unknown' if data is clean
                output_field=CharField(),
            )
        )
        .filter(taxpayer_type__in=["Regular", "WalkIn"])
    )  # Filter out 'Unknown' types if any

    aggregated_data_result = {}

    if new_interval == "Weekly":
        # Group by day of the week (DB: 1=Sun, ..., 7=Sat) and taxpayer type
        aggregated_query = (
            checkins_with_revenue.annotate(
                db_day_of_week=ExtractWeekDay("checkin_time")
            )
            .values("db_day_of_week", "taxpayer_type")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("db_day_of_week", "taxpayer_type")
        )

        # Initialize from template
        aggregated_data_result = weekly_data.copy()

        # Map DB weekday (1-7) to Python weekday (0-6) and then to label
        # DB: 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri, 7=Sat
        # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        db_day_to_label_map = {
            1: "Sun",
            2: "Mon",
            3: "Tue",
            4: "Wed",
            5: "Thu",
            6: "Fri",
            7: "Sat",
        }

        for item in aggregated_query:
            day_label = db_day_to_label_map.get(item["db_day_of_week"])
            taxpayer_cat = item["taxpayer_type"]
            total_rev = item["total_revenue"]

            if day_label:
                key = f"{day_label}_{taxpayer_cat}"
                aggregated_data_result[key] += float(
                    total_rev
                )  # Use += for cases where multiple entries might aggregate to same key

    elif new_interval == "Daily":  # This originally meant hourly data for a single day
        # Group by hour (DB: 0-23) and taxpayer type
        aggregated_query = (
            checkins_with_revenue.annotate(hour_of_day=ExtractHour("checkin_time"))
            .values("hour_of_day", "taxpayer_type")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("hour_of_day", "taxpayer_type")
        )

        # Initialize from template
        aggregated_data_result = hourly_data.copy()

        for item in aggregated_query:
            db_hour = item["hour_of_day"]
            taxpayer_cat = item["taxpayer_type"]
            total_rev = item["total_revenue"]

            display_hour = db_hour + 1  # Convert 0-23 to 1-24
            key = f"{display_hour}h_{taxpayer_cat}"
            if key in aggregated_data_result:  # Defensive check
                aggregated_data_result[key] += float(total_rev)

    else:  # Default is monthly data (originally yearly)
        # Group by month (DB: 1=Jan, ..., 12=Dec) and taxpayer type
        aggregated_query = (
            checkins_with_revenue.annotate(month_of_year=ExtractMonth("checkin_time"))
            .values("month_of_year", "taxpayer_type")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("month_of_year", "taxpayer_type")
        )

        # Initialize from template
        aggregated_data_result = monthly_data.copy()
        month_num_to_label_map = {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dec",
        }

        for item in aggregated_query:
            db_month = item["month_of_year"]
            taxpayer_cat = item["taxpayer_type"]
            total_rev = item["total_revenue"]

            month_label = month_num_to_label_map.get(db_month)
            if month_label:
                key = f"{month_label}_{taxpayer_cat}"
                aggregated_data_result[key] += float(total_rev)

    # 4. Count regular and walk-in exporters within the determined date range
    # These counts are based on the 'created_at' field of Exporter, not check-ins.
    regular_exporters_count = Exporter.objects.filter(
        type__name="regular", created_at__range=[actual_start_date, actual_end_date]
    ).count()
    walk_in_exporters_count = Exporter.objects.filter(
        type__name="walk in", created_at__range=[actual_start_date, actual_end_date]
    ).count()

    response_data = {
        "data": aggregated_data_result,
        "regular": regular_exporters_count,
        "walk_in": walk_in_exporters_count,
    }

    return Response(response_data)
