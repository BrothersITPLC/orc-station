from calendar import month_name
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import (
    Coalesce,
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractWeekDay,
)
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin
from users.models import CustomUser
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_station_ontroller_revenue_report(request):
    """
    Generates a trend report of revenue contributed by individual controllers
    within a specific workstation, aggregated over time based on the
    `selected_date_type` (weekly, monthly, or yearly).

    This endpoint filters check-ins by a given date range and a specific `station_name`.
    It uses `parse_and_validate_date_range` for strict date validation and
    `annotate_revenue_on_checkins` for efficient database-level calculation of
    incremental revenue. The revenue is then aggregated by time period (day of the week,
    week of the month, or month of the year) and by each controller working at that station.

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.
    - station_name (str): The name of the workstation for which to generate the report. Required.

    Returns:
        Response: A dictionary containing 'station_name', 'categories' (labels for
        the time periods), and 'series' (a list of revenue data, where each entry
        represents a controller).
        Example (weekly):
        {
            "station_name": "Main Station",
            "categories": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "series": [
                {"name": "Controller A", "data": [100.0, 150.0, 0.0, 80.0, 120.0, 30.0, 0.0]},
                {"name": "Controller B", "data": [50.0, 70.0, 0.0, 40.0, 60.0, 10.0, 0.0]},
            ]
        }

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              the date range does not match the 'selected_date_type' rules,
                              or multiple stations match the given name.
        HTTP 404 Not Found: If the specified 'station_name' does not exist.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    station_name_param = request.query_params.get("station_name")

    # Validate required parameters
    if not all([selected_date_type, start_date_str, end_date_str, station_name_param]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "station_name": station_name_param,
            }.items()
            if not param_value
        ]
        return Response(
            {"error": f"Missing required parameters: {', '.join(missing_params)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Date Validation and Parsing using the helper function with strict validation
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Get the station by name (case-insensitive)
    try:
        stations = WorkStation.objects.filter(name__iexact=station_name_param)
        if stations.count() == 0:
            return Response(
                {"error": "Station not found."}, status=status.HTTP_404_NOT_FOUND
            )
        elif stations.count() > 1:
            return Response(
                {"error": "Multiple stations match the given name. Be more specific."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        station = stations.first()
    except (
        WorkStation.DoesNotExist
    ):  # Redundant due to .count() check, but good for explicit error
        return Response(
            {"error": "Station not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # 3. Base filters for check-ins related to the station and date range
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__range=[start_date, inclusive_end_date],
        station=station,  # Filter by the found station object
        employee__isnull=False,  # Ensure check-ins are linked to an employee
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    # Initialize categories for output structure
    categories = []
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
    elif selected_date_type == "monthly":
        days_in_range = (inclusive_end_date.date() - start_date.date()).days + 1
        num_weeks = (days_in_range + 6) // 7
        categories = [f"Week {i}" for i in range(1, num_weeks + 1)]
    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]

    # If no check-ins, return empty data with correct categories structure
    if not checkins_query.exists():
        return Response(
            {
                "station_name": station.name,
                "categories": categories,
                "series": [],  # No series if no data
            }
        )

    # 4. Annotate check-ins with incremental revenue and employee full name
    checkins_with_revenue = annotate_revenue_on_checkins(checkins_query).annotate(
        employee_full_name=Coalesce(
            Concat(F("employee__first_name"), V(" "), F("employee__last_name")),
            F("employee__first_name"),
            F("employee__last_name"),
            V("Unknown Employee"),  # Fallback if no name parts
        )
    )

    # Get all relevant employees for the series names, even if no activity in this period
    # This ensures consistent series labels.
    all_employees_at_station_names = list(
        CustomUser.objects.filter(
            checkins_accepter__station=station,
            # Further filter employees to those who have checkins in the date range.
            # Otherwise, all employees ever assigned to station would show up.
            checkins_accepter__checkin_time__range=[start_date, inclusive_end_date],
        )
        .annotate(
            full_name=Coalesce(
                Concat(F("first_name"), V(" "), F("last_name")),
                F("first_name"),
                F("last_name"),
                V("Unknown Employee"),
            )
        )
        .values_list("full_name", flat=True)
        .distinct()
        .order_by("full_name")  # Ensure consistent order
    )

    # Initialize a dictionary to store aggregated revenue per employee and time category
    # { "Employee Name": { "Category1": Decimal(0), "Category2": Decimal(0), ... } }
    employee_revenue_by_category = {
        name: {cat: Decimal(0) for cat in categories}
        for name in all_employees_at_station_names
    }

    # 5. Perform database aggregation based on selected_date_type
    aggregated_query = None
    if selected_date_type == "weekly":
        db_day_to_category_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }
        aggregated_query = (
            checkins_with_revenue.annotate(time_unit=ExtractWeekDay("checkin_time"))
            .values("employee_full_name", "time_unit")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("employee_full_name", "time_unit")
        )
        for item in aggregated_query:
            employee_name = item["employee_full_name"]
            day_label = db_day_to_category_map.get(item["time_unit"])
            if employee_name in employee_revenue_by_category and day_label:
                employee_revenue_by_category[employee_name][day_label] += item[
                    "total_revenue"
                ]

    elif selected_date_type == "monthly":
        aggregated_query = (
            checkins_with_revenue.annotate(
                week_of_month=((ExtractDay("checkin_time") - 1) // 7) + 1
            )
            .values("employee_full_name", "week_of_month")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("employee_full_name", "week_of_month")
        )
        for item in aggregated_query:
            employee_name = item["employee_full_name"]
            week_label = f"Week {item['week_of_month']}"
            if (
                employee_name in employee_revenue_by_category
                and week_label in categories
            ):
                employee_revenue_by_category[employee_name][week_label] += item[
                    "total_revenue"
                ]

    elif selected_date_type == "yearly":
        aggregated_query = (
            checkins_with_revenue.annotate(time_unit=ExtractMonth("checkin_time"))
            .values("employee_full_name", "time_unit")
            .annotate(total_revenue=Coalesce(Sum("revenue"), Decimal(0)))
            .order_by("employee_full_name", "time_unit")
        )
        for item in aggregated_query:
            employee_name = item["employee_full_name"]
            month_label = month_name[item["time_unit"]]
            if employee_name in employee_revenue_by_category and month_label:
                employee_revenue_by_category[employee_name][month_label] += item[
                    "total_revenue"
                ]

    # 6. Format response `series`
    series = []
    for (
        employee_name
    ) in all_employees_at_station_names:  # Iterate through sorted employee names
        data_for_employee = [
            float(employee_revenue_by_category[employee_name].get(category, Decimal(0)))
            for category in categories
        ]
        series.append({"name": employee_name, "data": data_for_employee})

    return Response(
        {
            "station_name": station.name,
            "categories": categories,
            "series": series,
        }
    )
