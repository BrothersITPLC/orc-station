from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from declaracions.models import Checkin
from exporters.models import Exporter
from localcheckings.models import JourneyWithoutTruck

from .dateRangeValidator import validate_date_range


def calculate_local_revenue_and_amount(exporter=None, start_date=None, end_date=None):
    total_revenue = Decimal(0)
    total_amount = 0

    if exporter is not None:
        journeys = JourneyWithoutTruck.objects.filter(
            exporter=exporter,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).prefetch_related("checkins")

        for journey in journeys:
            checkins = journey.checkins.filter(
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
                unit_price = Decimal(checkin.unit_price)
                rate = Decimal(checkin.rate)
                total_revenue += weight * (unit_price / 100) * (rate / 100)
                total_amount += weight

    return total_revenue, total_amount


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_top_walkin_taxpayer_report(request):
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

    # Prepare report data
    report_data = []

    # Fetch top local exporters by journey count
    top_local_exporters = (
        Exporter.objects.annotate(
            local_journeys_count=Count(
                "localJourneys",
                filter=Q(
                    localJourneys__checkins__status__in=["pass", "paid", "success"],
                    localJourneys__created_at__gte=start_date,
                    localJourneys__created_at__lte=end_date,
                ),
                distinct=True,
            ),
        )
        .filter(local_journeys_count__gt=0)
        .order_by("-local_journeys_count")[:10]
    )

    for top_local_exporter in top_local_exporters:
        revenue, amount = calculate_local_revenue_and_amount(
            exporter=top_local_exporter,
            start_date=start_date,
            end_date=end_date,
        )

        # Categorize based on selected_date_type
        if selected_date_type == "weekly":
            category = f"Week {((start_date.day - 1) // 7) + 1}"
        elif selected_date_type == "monthly":
            category = start_date.strftime("%B")
        elif selected_date_type == "yearly":
            category = start_date.year
        else:
            return Response(
                {
                    "error": "Invalid selected_date_type. Must be 'weekly', 'monthly', or 'yearly'."
                },
                status=400,
            )

        # Add local exporter data to report
        report_data.append(
            {
                "uniqe_id": top_local_exporter.unique_id,
                "type": top_local_exporter.type.name,
                "exporter_name": f"{top_local_exporter.first_name} {top_local_exporter.last_name}",
                "total_amount": amount,
                "total_revenue": round(revenue, 2),
                "total_path": top_local_exporter.local_journeys_count,
            }
        )

    return Response(report_data)
