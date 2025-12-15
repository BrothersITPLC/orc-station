from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analysis.views.helpers import annotate_revenue_on_checkins
from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([AllowAny])
def admin_each_station_revenue_today_report(request):
    """
    Generates a daily summary report for each workstation, covering the last 24 hours.

    This report provides the total revenue, total number of transactions (check-ins),
    and total incremental weight processed at each station. It efficiently calculates
    incremental weight and revenue at the database level using `annotate_revenue_on_checkins`
    and performs all aggregations in a single database query.

    Returns:
        Response: A dictionary where the 'data' key holds another dictionary.
        Keys of the inner dictionary are workstation IDs, and values are dictionaries
        containing 'name', 'total_revenue', 'transaction' (count), and 'total_weight'
        for that workstation over the last 24 hours. Stations with no activity
        will be included with zero values.
        Example:
        {
            "data": {
                "1": {"name": "Station A", "total_revenue": 12345.67, "transaction": 50, "total_weight": 98765.43},
                "2": {"name": "Station B", "total_revenue": 0.0, "transaction": 0, "total_weight": 0.0},
                ...
            }
        }
    """
    # Get the start and end time for the last 24 hours
    end_time = now()
    start_time = end_time - timedelta(hours=24)

    # 1. Query all stations to ensure all are represented in the output, even if no check-ins
    all_stations = WorkStation.objects.all()

    # Initialize station data with all stations having zeroed data
    station_data = {
        str(station.id): {  # Convert ID to string as it might be used as dictionary key
            "name": station.name,
            "total_revenue": 0.0,
            "transaction": 0,
            "total_weight": 0.0,
        }
        for station in all_stations
    }

    # 2. Filter check-ins within the last 24 hours for successful statuses
    base_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_time, end_time],
        status__in=["pass", "paid", "success"],
        station__isnull=False,  # Ensure check-ins are linked to a station
    )

    if not base_checkins_query.exists():
        # If no check-ins found, return the initialized data
        return Response({"data": station_data})

    # 3. Annotate check-ins with incremental weight and revenue using the helper
    checkins_with_revenue = annotate_revenue_on_checkins(base_checkins_query)

    # 4. Perform a single database aggregation for all required metrics per station
    # 4. Perform aggregation in Python
    # Checkin query is already executed when iterating
    for checkin in checkins_with_revenue:
        # annotations: revenue, incremental_weight
        # station is fetched via filter
        if checkin.station_id:
            sid_str = str(checkin.station_id)
            if sid_str in station_data:
                rev = checkin.revenue or Decimal(0)
                weight = checkin.incremental_weight or Decimal(0)
                
                station_data[sid_str]["total_revenue"] += float(rev)
                station_data[sid_str]["total_weight"] += float(weight)
                station_data[sid_str]["transaction"] += 1

    # 5. Format response (frontend compatible)
    response_data = {"data": station_data}
    return Response(response_data)
