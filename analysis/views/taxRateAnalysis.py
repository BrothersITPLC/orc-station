from decimal import Decimal

from django.db.models import DecimalField, F, Q, Sum
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def tax_rate_analysis(request):
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    # Filter checkins by date range if provided
    checkins = Checkin.objects.all()
    if start_date and end_date:
        checkins = checkins.filter(
            Q(checkin_time__gte=start_date) & Q(checkin_time__lte=end_date)
        )

    if not checkins.exists():
        return Response([])  # Return empty list if no checkins found

    # Get min and max weight
    weights = checkins.values_list("net_weight", flat=True)
    min_weight = int(min(weights, default=0))
    max_weight = int(max(weights, default=0))

    # Define 5 dynamic ranges
    step = (max_weight - min_weight) // 5
    ranges = []
    for i in range(5):
        start = min_weight + (i * step)
        end = start + step if i < 4 else None  # Last range is open-ended
        ranges.append({"min": start, "max": end})

    # Initialize result and total revenue
    results = []
    total_revenue = Decimal(0)

    # Revenue per range
    range_revenues = []

    for weight_range in ranges:
        min_weight = weight_range["min"]
        max_weight = weight_range["max"]

        range_checkins = checkins.filter(
            net_weight__gte=min_weight,
            net_weight__lt=max_weight if max_weight else Decimal("Infinity"),
        )

        range_revenue = Decimal(0)

        for checkin in range_checkins:
            # Find the latest check-in for the same context
            latest_checkin = (
                checkins.filter(
                    checkin_time__lt=checkin.checkin_time,
                    localJourney=checkin.localJourney if checkin.localJourney else None,
                    declaracion=checkin.declaracion if checkin.declaracion else None,
                )
                .order_by("-checkin_time")
                .first()
            )

            # Calculate weight difference
            weight = (
                max(checkin.net_weight - latest_checkin.net_weight, 0)
                if latest_checkin
                else checkin.net_weight
            )
            weight = Decimal(weight)

            # Calculate revenue for the check-in
            unit_price = Decimal(checkin.unit_price)
            rate = Decimal(checkin.rate)
            revenue = weight * (unit_price / Decimal(100)) * (1 + rate / Decimal(100))

            range_revenue += revenue

        # Append to range revenues and update total revenue
        range_revenues.append(range_revenue)
        total_revenue += range_revenue

    # Calculate percentage rates for each range
    for idx, weight_range in enumerate(ranges):
        min_weight = weight_range["min"]
        max_weight = weight_range["max"]
        range_revenue = range_revenues[idx]

        # Calculate rate as percentage of total revenue
        rate = (
            (range_revenue / total_revenue * 100) if total_revenue > 0 else Decimal(0)
        )

        weight_label = (
            f"{min_weight}-{max_weight}kg"
            if max_weight is not None
            else f"{min_weight}kg+"
        )
        results.append(
            {
                "weight": weight_label,
                "rate": float(rate),
                "revenue": float(range_revenue),
            }
        )

    return Response(results)
