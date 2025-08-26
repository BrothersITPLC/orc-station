from calendar import monthrange
from datetime import datetime, timedelta

from django.utils.timezone import make_aware
from rest_framework.response import Response


def validate_date_range(start_date_str, end_date_str, selected_date_type):
    try:
        # Parse and make dates timezone-aware
        start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
        end_date = make_aware(
            datetime.strptime(end_date_str, "%Y-%m-%d")
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    # Ensure end date is not earlier than start date
    if end_date < start_date:
        return Response(
            {"error": "End date cannot be earlier than start date."}, status=400
        )

    # Validate date range against selected_date_type
    date_range_days = (end_date - start_date).days + 1
    if selected_date_type == "weekly" and date_range_days != 7:
        return Response(
            {"error": "For 'weekly', the date range must be exactly 7 days."},
            status=400,
        )
    elif selected_date_type == "monthly":
        days_in_month = monthrange(start_date.year, start_date.month)[1]
        if date_range_days != days_in_month:
            return Response(
                {"error": "For 'monthly', the date range must cover the entire month."},
                status=400,
            )
    elif selected_date_type == "yearly":
        if date_range_days not in (365, 366):
            return Response(
                {"error": "For 'yearly', the date range must cover the entire year."},
                status=400,
            )

    # Return None if validation passes
    return None
