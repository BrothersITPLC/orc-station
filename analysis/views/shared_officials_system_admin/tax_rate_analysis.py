from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Case, DecimalField, F, Max, Min, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def tax_rate_analysis(request):
    """
    Analyzes revenue distribution across dynamically determined weight ranges for check-ins.

    This endpoint calculates the total revenue for different net weight categories
    (e.g., 0-1000kg, 1000-2000kg, etc.) and expresses each category's revenue
    as a percentage of the overall total revenue within the specified date range.
    The weight ranges are determined dynamically based on the minimum and maximum
    net weights found in the filtered check-ins, divided into 5 equal steps.

    It leverages `annotate_revenue_on_checkins` for efficient database-level
    calculation of incremental weight and revenue, and `parse_and_validate_date_range`
    for robust date handling.

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins. Required.

    Returns:
        Response: A list of dictionaries, where each dictionary represents a weight range
        with its calculated revenue and its percentage 'rate' of the total revenue.
        Example:
        [
            {"weight": "0-1000kg", "rate": 25.50, "revenue": 12500.00},
            {"weight": "1001-2000kg", "rate": 40.00, "revenue": 20000.00},
            ...
            {"weight": "4001kg+", "rate": 10.00, "revenue": 5000.00},
        ]

    Raises:
        HTTP 400 Bad Request: If 'start_date' or 'end_date' are missing or invalid.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Date Validation and Parsing using the helper function
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Initial filtering for relevant checkins (e.g., successful transactions)
    # The status filter is added for consistency with other reports, assuming
    # only successful check-ins contribute to revenue analysis.
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
    )

    if not base_checkins_query.exists():
        return Response([])

    # 2. Annotate revenue on checkins using the helper function
    # This replaces the manual Python loop for calculating incremental_weight and revenue.
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 3. Get min and max net_weight for dynamic range definition
    # Use Coalesce with Decimal(0) to handle cases where Min/Max might return None for empty results,
    # though base_checkins_query.exists() check should prevent this.
    weight_stats = base_checkins_query.aggregate(
        min_w=Coalesce(Min("net_weight"), Decimal(0)),
        max_w=Coalesce(Max("net_weight"), Decimal(0)),
    )
    min_weight = int(weight_stats["min_w"])
    max_weight = int(weight_stats["max_w"])

    # Define 5 dynamic ranges based on min/max weight
    ranges = []
    if max_weight == min_weight and base_checkins_query.exists():
        # If all checkins have the same weight, create a single unbounded range
        ranges.append({"min": min_weight, "max": None})
    elif max_weight > min_weight:
        diff = max_weight - min_weight
        # Calculate step, ensuring it's at least 1 if there's any difference
        # This addresses the original problem where step could be 0, creating empty ranges.
        step = max(1, diff // 5)

        for i in range(5):
            start = min_weight + (i * step)
            # For intermediate ranges, the upper bound is exclusive (`net_weight__lt=max_w`)
            # For the last range (i=4), it's unbounded (None).
            end = start + step if i < 4 else None

            # Ensure the 'end' of an intermediate range doesn't exceed the overall max_weight
            # for `lt` comparisons if the step is large.
            if end is not None and end > max_weight + 1:  # +1 for exclusive upper bound
                end = max_weight + 1

            # If the last range's calculated end is still less than or equal to the overall max_weight,
            # make it truly unbounded to capture all remaining values.
            if i == 4 and (end is None or (end is not None and end <= max_weight)):
                end = None

            ranges.append({"min": start, "max": end})
    else:  # max_weight < min_weight implies an issue, or empty data
        pass  # The base_checkins_query.exists() handles the truly empty case

    # If no ranges are generated (e.g., after empty queryset or edge case), return empty response
    if not ranges:
        return Response([])

    # 4. Aggregate revenue per range using Python
    # Initialize buckets for the 5 ranges
    # ranges looks like: [{'min': 0, 'max': 200}, {'min': 201, 'max': 400}, ...]
    # We need to sum revenue for checkins falling into each bucket.
    
    range_revenues_ordered = [Decimal(0)] * len(ranges)
    total_revenue = Decimal(0)
    
    for checkin in checkins_with_revenue:
        w_val = checkin.net_weight
        if w_val is None: 
            continue
            
        rev = checkin.revenue or Decimal(0)
        
        # Determine which range this checkin belongs to
        assigned_idx = -1
        for i, r in enumerate(ranges):
            min_w = r["min"]
            max_w = r["max"]
            
            # Check range conditions matching the Original Query Logic:
            # Q(net_weight__gte=min_w) & Q(net_weight__lt=max_w)
            
            if w_val >= min_w:
                if max_w is None: 
                    # Unbounded upper limit
                    assigned_idx = i
                    break
                elif w_val < max_w:
                    # Within bounds (exclusive top)
                    assigned_idx = i
                    break
        
        if assigned_idx != -1:
            range_revenues_ordered[assigned_idx] += rev
            total_revenue += rev

    # Reconstitute labels for the response
    range_labels = []
    for weight_range in ranges:
        min_w = weight_range["min"]
        max_w = weight_range["max"]
        if max_w is not None:
            weight_label = f"{min_w}-{max_w}kg"
        else:
            weight_label = f"{min_w}kg+"
        range_labels.append(weight_label)

    # 6. Calculate percentage rates and format for the final response (unchanged structure)
    final_results = []
    for idx, revenue_for_range in enumerate(range_revenues_ordered):
        current_weight_label = range_labels[idx]
        rate_percentage = (
            (revenue_for_range / total_revenue * 100)
            if total_revenue > 0
            else Decimal(0)
        )

        final_results.append(
            {
                "weight": current_weight_label,
                "rate": float(rate_percentage),
                "revenue": float(revenue_for_range),
            }
        )

    return Response(final_results)
