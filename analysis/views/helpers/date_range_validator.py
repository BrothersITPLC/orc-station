from calendar import monthrange
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware


def parse_and_validate_date_range(
    start_date_str, end_date_str, selected_date_type=None
):
    """
    Parses and validates a date range from string inputs.

    - Always validates format and logical order (start before end).
    - If `selected_date_type` is provided ('weekly', 'monthly', 'yearly'),
      it enforces strict rules on the date range duration.
    - If `selected_date_type` is None, it allows any flexible date range.

    Raises:
        ValidationError: If any validation check fails.

    Returns:
        tuple: A tuple of (start_date, end_date) as aware datetime objects.
    """
    if not start_date_str or not end_date_str:
        raise ValidationError("start_date and end_date are required parameters.")

    try:
        start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
        end_date = make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
    except (ValueError, TypeError):
        raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

    if end_date < start_date:
        raise ValidationError("End date cannot be earlier than start date.")

    # Convert end_date to be inclusive (the very end of the day)
    inclusive_end_date = end_date + timedelta(days=1) - timedelta(seconds=1)

    # --- Optional Strict Validation based on selected_date_type ---
    if selected_date_type:
        date_range_days = (end_date - start_date).days + 1

        if selected_date_type == "weekly" and date_range_days != 7:
            raise ValidationError(
                "For 'weekly', the date range must be exactly 7 days."
            )

        elif selected_date_type == "monthly":
            # Check if the provided range covers the exact calendar month of the start date
            _, days_in_month = monthrange(start_date.year, start_date.month)
            if not (start_date.day == 1 and date_range_days == days_in_month):
                raise ValidationError(
                    "For 'monthly', the date range must cover a full calendar month."
                )

        elif selected_date_type == "yearly":
            # Check if the provided range covers a full calendar year
            is_leap = (start_date.year % 4 == 0 and start_date.year % 100 != 0) or (
                start_date.year % 400 == 0
            )
            days_in_year = 366 if is_leap else 365
            if not (
                start_date.day == 1
                and start_date.month == 1
                and date_range_days == days_in_year
            ):
                raise ValidationError(
                    "For 'yearly', the date range must cover a full calendar year."
                )

    return start_date, inclusive_end_date
