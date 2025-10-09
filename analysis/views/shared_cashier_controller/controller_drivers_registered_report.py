from calendar import month_name
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Count, F, Q
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractWeekDay
from django.utils.timezone import make_aware
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import parse_and_validate_date_range
from drivers.models import Driver


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def controller_drivers_registered_report(request):
    """
    Generates a trend report on the number of drivers registered by a specific controller,
    aggregated by day of the week, week of the month, or month of the year.

    This endpoint first validates the date range strictly against the `selected_date_type`
    using `parse_and_validate_date_range`. It then filters drivers by their `created_at`
    date, and the `register_by_id` (controller ID). The number of registered drivers
    is then aggregated over the chosen time period ('weekly', 'monthly', or 'yearly').

    Query Parameters:
    - selected_date_type (str): The type of aggregation ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering driver registrations. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering driver registrations. Required.
    - controller_id (int): The ID of the employee (controller) for whom to generate the report. Required.

    Returns:
        Response: A dictionary containing 'series' (list with one entry for 'Drivers Registered')
        and 'categories' (labels for the time periods).
        Example (weekly):
        {
            "series": [
                {"name": "Drivers Registered", "data": [5, 3, 7, 2, 0, 1, 0]}
            ],
            "categories": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        }

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              or the date range does not match the 'selected_date_type' rules.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    controller_id = request.query_params.get("controller_id")

    # Validate required parameters
    if not all([selected_date_type, start_date_str, end_date_str, controller_id]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "controller_id": controller_id,
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

    # 2. Filter drivers by controller_id and date range
    drivers_query = Driver.objects.filter(
        register_by_id=controller_id,
        created_at__range=[start_date, inclusive_end_date],
    )

    categories = []
    # Initialize a dictionary to hold aggregated counts, ensuring all periods are covered
    # This will map a category label (e.g., "Monday", "Week 1", "January") to its count.
    counts_map = {}

    # 3. Group and aggregate data based on selected_date_type
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
        # Initialize counts_map to 0 for all categories
        for cat in categories:
            counts_map[cat] = 0

        # DB's ExtractWeekDay is 1=Sunday, 2=Monday, ..., 7=Saturday
        # We need to map it to our 'categories' list which starts with Monday (index 0)
        db_day_to_category_map = {
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
            1: "Sunday",
        }

        grouped_data = (
            drivers_query.annotate(
                time_unit=ExtractWeekDay("created_at")  # 1=Sun, 2=Mon...7=Sat
            )
            .values("time_unit")
            .annotate(count=Count("id"))
            .order_by("time_unit")
        )

        for entry in grouped_data:
            day_label = db_day_to_category_map.get(entry["time_unit"])
            if day_label:
                counts_map[day_label] = entry["count"]

    elif selected_date_type == "monthly":
        # For 'monthly', parse_and_validate_date_range ensures a full calendar month.
        # We need to calculate the number of weeks in that month.
        days_in_month = (inclusive_end_date.date() - start_date.date()).days + 1
        num_weeks = (days_in_month + 6) // 7  # Ceiling division
        categories = [f"Week {i}" for i in range(1, num_weeks + 1)]
        # Initialize counts_map to 0 for all categories
        for cat in categories:
            counts_map[cat] = 0

        # Group by week number within the month
        grouped_data = (
            drivers_query.annotate(
                # Calculate week number relative to the start of the month (1-indexed)
                week_of_month=((ExtractDay("created_at") - 1) // 7)
                + 1
            )
            .values("week_of_month")
            .annotate(count=Count("id"))
            .order_by("week_of_month")
        )

        for entry in grouped_data:
            week_num = entry["week_of_month"]
            week_label = f"Week {week_num}"
            if (
                week_label in categories
            ):  # Ensure the week label is valid for our defined categories
                counts_map[week_label] = entry["count"]

    elif selected_date_type == "yearly":
        categories = [month_name[i] for i in range(1, 13)]
        # Initialize counts_map to 0 for all categories
        for cat in categories:
            counts_map[cat] = 0

        # Group by month of the year
        grouped_data = (
            drivers_query.annotate(month_num=ExtractMonth("created_at"))
            .values("month_num")
            .annotate(count=Count("id"))
            .order_by("month_num")
        )

        for entry in grouped_data:
            month_label = month_name[entry["month_num"]]
            if month_label:
                counts_map[month_label] = entry["count"]

    else:
        return Response(
            {
                "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Build series data, ensuring all categories are present with 0 if no data
    # The 'data' list must follow the order of 'categories'.
    series_data_list = [counts_map.get(category, 0) for category in categories]

    series = [{"name": "Drivers Registered", "data": series_data_list}]

    return Response({"series": series, "categories": categories})
