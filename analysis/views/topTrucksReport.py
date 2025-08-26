from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin, Declaracion
from trucks.models import Truck, TruckOwner

from ..serializers import TopTrucksSerializer


def calculate_total_weight(truck=None, start_date=None, end_date=None):
    total_weight = 0
    total_birr = Decimal(0)
    # Filter declarations related to the truck and prefetch related checkins to optimize queries
    declaracions = Declaracion.objects.filter(
        truck=truck, created_at__gte=start_date, created_at__lte=end_date
    ).prefetch_related("checkins")

    for declaracion in declaracions:
        checkins = declaracion.checkins.filter(
            checkin_time__lte=end_date,
            checkin_time__gte=start_date,
            status__in=["pass", "paid", "success"],
        )
        for checkin in checkins:
            latest_checkin = (
                checkins.filter(checkin_time__lt=checkin.checkin_time)
                .order_by("-checkin_time")
                .first()
            )
            weight = (
                max(checkin.net_weight - latest_checkin.net_weight, 0)
                if latest_checkin
                else checkin.net_weight
            )
            print("total Weight", checkin.net_weight)
            total_weight += weight
            unit_price = Decimal(checkin.unit_price)
            rate = Decimal(checkin.rate)
            total_birr += weight * (unit_price / 100) * (rate / 100)

    return total_weight, total_birr


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def top_trucks_report(request):
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    print(start_date_str, " start_date")
    print(end_date_str, " end_date")
    # 2. Parse the dates using parse_date
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    # 3. Set default dates if not provided
    today = timezone.now().date()
    if not end_date:
        end_date = today
    if not start_date:
        start_date = today - timedelta(days=365)  # Approx. one year

    filters = {}
    if station_id:
        filters["station_id"] = station_id
    if controller_id:
        filters["employee_id"] = controller_id
    filters["status"] = "success"

    top_trucks = (
        Truck.objects.annotate(
            # Count check-ins with the status filter
            checkin_count=Count(
                "declaracions__checkins",
                filter=Q(
                    declaracions__checkins__status__in=["pass", "paid", "success"],
                    declaracions__created_at__gte=start_date,
                    declaracions__created_at__lte=end_date,
                ),
            ),
            # Count declarations that fall within the date range
            declaracion_count=Count(
                "declaracions",
                filter=Q(
                    declaracions__created_at__gte=start_date,
                    declaracions__created_at__lte=end_date,
                ),
                distinct=True,
            ),
        )
        .filter(checkin_count__gt=0)
        .order_by("-checkin_count", "-declaracion_count")
    )[:10]
    report_data = []

    for truck in top_trucks:
        owner = truck.owner  # Directly access owner from truck instance
        owner_name = f"{owner.first_name} {owner.last_name}" if owner else "Unknown"
        total_weight, total_birr = calculate_total_weight(truck, start_date, end_date)
        # Collect report data
        report_data.append(
            {
                "plate_number": truck.plate_number,
                "make": truck.truck_brand if truck.truck_brand else "Unknown",
                "owner_name": owner_name,
                "total_checkins": truck.checkin_count,
                "path_count": truck.declaracion_count,
                "total_kg": round(total_weight, 2),
                "total_revenue": round(total_birr, 2),
            }
        )

    # Serialize and return the report data
    serializer = TopTrucksSerializer(data=report_data, many=True)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)
