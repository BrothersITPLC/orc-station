from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from declaracions.models import Checkin

from ..helpers import annotate_revenue_on_checkins, parse_and_validate_date_range


@api_view(["GET"])
@permission_classes([AllowAny])
def yearly_revenue_report(request):
    """
    Provides a monthly revenue report for a given period.
    This report correctly calculates revenue based on incremental weight.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    try:
        start_date, end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    filters = {
        "status__in": ["pass", "paid", "success"],
        "checkin_time__range": [start_date, end_date],
    }
    if station_id and station_id != "null":
        filters["station_id"] = station_id
    if controller_id and controller_id != "null":
        filters["employee_id"] = controller_id

    base_queryset = Checkin.objects.filter(**filters)
    checkins_with_revenue = annotate_revenue_on_checkins(base_queryset)

    # Aggregate in Python
    # Use a dictionary to sum revenue by month string e.g. "2023-11"
    monthly_map = defaultdict(Decimal)

    # We need to extract month from checkin_time in python or annotation
    # TruncMonth in annotation is fine as it doesn't aggregate.
    checkins_with_revenue = checkins_with_revenue.annotate(month=TruncMonth("checkin_time"))

    for checkin in checkins_with_revenue:
        # TruncMonth returns a datetime/date object
        m_str = checkin.month.strftime("%Y-%m")
        rev = checkin.revenue or Decimal(0)
        monthly_map[m_str] += rev
    
    # Sort keys to ensure chronological order
    sorted_months = sorted(monthly_map.keys())

    labels = []
    data = []
    for m_str in sorted_months:
        labels.append(m_str)
        data.append(monthly_map[m_str])

    response_data = {"labels": labels, "data": data}

    return Response(response_data)
