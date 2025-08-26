from datetime import timedelta
from decimal import Decimal

from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from declaracions.models import Checkin
from workstations.models import WorkStation


@api_view(["GET"])
@permission_classes([AllowAny])
def admin_each_station_revenue_today_data(request):
    # Get the start and end time for the last 24 hours
    end_time = now()
    start_time = end_time - timedelta(hours=24)

    # Query all stations
    stations = WorkStation.objects.all()

    # Query checkins within the last 24 hours
    checkins = Checkin.objects.filter(
        checkin_time__range=[start_time, end_time],
        status__in=["pass", "paid", "success"],
    ).select_related("station")

    # Initialize station data with all stations having zeroed data
    station_data = {
        station.id: {
            "name": station.name,
            "total_revenue": 0,
            "transaction": 0,
            "total_weight": 0,
        }
        for station in stations
    }

    for checkin in checkins:
        # Find the latest previous checkin for the same declaracion/localJourney
        latest_checkin = (
            Checkin.objects.filter(
                checkin_time__lt=checkin.checkin_time,
                localJourney=checkin.localJourney if checkin.localJourney else None,
                declaracion=checkin.declaracion if checkin.declaracion else None,
            )
            .order_by("-checkin_time")
            .first()
        )

        # Calculate the incremental weight
        incremental_weight = max(
            checkin.net_weight - (latest_checkin.net_weight if latest_checkin else 0), 0
        )

        # Calculate revenue
        unit_price = Decimal(checkin.unit_price)
        rate = Decimal(checkin.rate)
        revenue = (
            incremental_weight * (unit_price / Decimal(100)) * (rate / Decimal(100))
        )

        station_id = checkin.station.id

        # Update station data
        station_data[station_id]["total_revenue"] += float(revenue)
        station_data[station_id]["transaction"] += 1
        station_data[station_id]["total_weight"] += float(incremental_weight)

    # Format response
    response_data = {"data": station_data}
    return Response(response_data)
