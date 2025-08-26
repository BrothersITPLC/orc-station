from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Declaracion
from trucks.models import Truck

from ..serializers import TopTrucksSerializer
from .dateRangeValidator import validate_date_range


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
def admin_top_trucks_report(request):
    selected_date_type = request.query_params.get("selected_date_type")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    # Validate request parameters
    if not selected_date_type or not start_date or not end_date:
        return Response({"error": "Missing required parameters."}, status=400)

    validation_response = validate_date_range(start_date, end_date, selected_date_type)
    if validation_response:
        return validation_response

    try:
        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
        end_date = make_aware(
            datetime.strptime(end_date, "%Y-%m-%d")
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    filters = {"status": "success"}

    # Annotate top trucks and group data based on selected_date_type
    top_trucks = (
        Truck.objects.annotate(
            checkin_count=Count(
                "declaracions__checkins",
                filter=Q(
                    declaracions__checkins__status__in=["pass", "paid", "success"],
                    declaracions__created_at__gte=start_date,
                    declaracions__created_at__lte=end_date,
                ),
            ),
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
        owner = truck.owner
        owner_name = f"{owner.first_name} {owner.last_name}" if owner else "Unknown"
        total_weight, total_birr = calculate_total_weight(truck, start_date, end_date)

        # Use selected_date_type to categorize internally (e.g., weekly, monthly, yearly)
        if selected_date_type == "weekly":
            category = f"Week {((start_date.day - 1) // 7) + 1}"  # Example weekly logic
        elif selected_date_type == "monthly":
            category = start_date.strftime("%B")  # Example monthly logic
        elif selected_date_type == "yearly":
            category = start_date.year  # Example yearly logic
        else:
            return Response(
                {
                    "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
                },
                status=400,
            )

        # Collect report data (categorization logic is applied internally)
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
