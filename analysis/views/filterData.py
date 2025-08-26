from decimal import Decimal

from django.utils import timezone

from declaracions.models import Checkin


def to_aware_datetime(date, is_start=True):
    """Convert a naive date to an aware datetime."""
    if not date:
        return None
    time = timezone.datetime.min.time() if is_start else timezone.datetime.max.time()
    naive_datetime = timezone.datetime.combine(date, time)
    return timezone.make_aware(naive_datetime)


def calculate_revenue_for_checkins(checkins, filter_field):
    """
    General function to calculate revenue for a given set of check-ins.
    The `filter_field` determines whether to filter by `declaracion` or `localJourney`.
    """
    revenue_data = []
    processed_checkins = set()  # Track processed check-ins to avoid duplicates

    for checkin in checkins:
        # Skip if this check-in has already been processed
        checkin_id = (
            checkin.id,
            (
                getattr(checkin, filter_field, None).id
                if getattr(checkin, filter_field, None)
                else None
            ),
        )
        if checkin_id in processed_checkins:
            continue

        # Determine the latest check-in based on the filter_field
        latest_checkin = (
            checkins.filter(
                checkin_time__lt=checkin.checkin_time,
                **{filter_field: getattr(checkin, filter_field, None)},
            )
            .order_by("-checkin_time")
            .first()
        )

        # Calculate weight difference (or use full weight if no previous check-in)
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

        # Append to revenue_data and mark check-in as processed
        revenue_data.append({"checkin_time": checkin.checkin_time, "revenue": revenue})
        processed_checkins.add(checkin_id)
    print(filter_field, revenue_data)
    return revenue_data


def filter_revenue_declaracion(start_date, end_date):
    """
    Filter check-ins related to 'declaracion' and calculate revenue.
    """
    filter_conditions = {}
    if start_date:
        filter_conditions["checkin_time__gte"] = to_aware_datetime(
            start_date, is_start=True
        )
    if end_date:
        filter_conditions["checkin_time__lte"] = to_aware_datetime(
            end_date, is_start=False
        )
    filter_conditions["status__in"] = ["pass", "paid", "success"]

    checkins = Checkin.objects.filter(**filter_conditions).select_related(
        "declaracion", "declaracion__exporter"
    )

    return calculate_revenue_for_checkins(checkins, filter_field="declaracion")


def filter_revenue_localJourney(start_date, end_date):
    """
    Filter check-ins related to 'localJourney' and calculate revenue.
    """
    filter_conditions = {}
    if start_date:
        filter_conditions["checkin_time__gte"] = to_aware_datetime(
            start_date, is_start=True
        )
    if end_date:
        filter_conditions["checkin_time__lte"] = to_aware_datetime(
            end_date, is_start=False
        )
    filter_conditions["status__in"] = ["pass", "paid", "success"]

    checkins = Checkin.objects.filter(**filter_conditions).select_related(
        "localJourney", "localJourney__exporter"
    )

    return calculate_revenue_for_checkins(checkins, filter_field="localJourney")
