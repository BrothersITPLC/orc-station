from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, CharField, Count, DecimalField, F, Q, Sum
from django.db.models import Value as V
from django.db.models import When
from django.db.models.functions import Coalesce
from django.utils.timezone import now
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import annotate_revenue_on_checkins
from declaracions.models import Checkin
from users.models import CustomUser


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def controller_daily_summary_report(request):
    """
    Generates a daily summary report of a specific controller's activity over the last 24 hours.

    This report includes total revenue, total incremental weight (kg), and the count
    of checked-in taxpayers, broken down into 'Regular' (Declaracion-based) and
    'Walk-in' (LocalJourney-based) categories. It efficiently calculates incremental
    weight and revenue using `annotate_revenue_on_checkins` and performs all
    aggregations at the database level.

    Query Parameters:
    - controller_id (int): The ID of the employee (controller) for whom to generate the report. Required.

    Returns:
        Response: A list of dictionaries, each representing a key metric with its label and calculated amount.
        Example:
        [
            {"label": "Total Revenue", "amount": "12345.67"},
            {"label": "Revenue From Walk-in", "amount": "890.12"},
            ...
        ]

    Raises:
        HTTP 400 Bad Request: If 'controller_id' is missing.
        HTTP 404 Not Found: If the specified 'controller_id' does not exist.
    """
    controller_id = request.query_params.get("controller_id")

    if not controller_id or controller_id == "null":
        return Response(
            {"error": "controller_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate if controller exists
    controller_exists = CustomUser.objects.filter(id=controller_id).exists()
    if not controller_exists:
        return Response(
            {"error": "Controller not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # Define the time range (last 24 hours)
    time_threshold = now() - timedelta(hours=24)

    # 1. Build base filter criteria for check-ins
    base_checkins_filters = Q(
        status__in=["pass", "paid", "success"],
        checkin_time__gte=time_threshold,
        employee_id=controller_id,
    )

    checkins_query = Checkin.objects.filter(base_checkins_filters)

    if not checkins_query.exists():
        # Return all zero values if no check-ins found
        response_data = [
            {"label": "Total Revenue", "amount": "0.0"},
            {"label": "Revenue From Walk-in", "amount": "0.0"},
            {"label": "Revenue From Regular", "amount": "0.0"},
            {"label": "Total kg", "amount": "0.0"},
            {"label": "Total kg From Walk-in", "amount": "0.0"},
            {"label": "Total kg From Regular", "amount": "0.0"},
            {"label": "Total Checked in Tax Payers", "amount": "0"},
            {"label": "Total Checked in Walk-in Tax Payers", "amount": "0"},
            {"label": "Total Checked in Regular Tax Payers", "amount": "0"},
        ]
        return Response(response_data)

    # 2. Annotate check-ins with incremental weight, revenue, and taxpayer type
    checkins_with_data = (
        annotate_revenue_on_checkins(checkins_query)
        .annotate(
            taxpayer_type=Case(
                When(declaracion__isnull=False, then=V("Regular")),
                When(localJourney__isnull=False, then=V("Walk-in")),
                default=V("Unknown"),  # Should be rare if data is clean
                output_field=CharField(),
            )
        )
        .filter(taxpayer_type__in=["Regular", "Walk-in"])
    )  # Only consider valid taxpayer types

    # 3. Perform a single database aggregation for all revenue and weight sums
    aggregates = checkins_with_data.aggregate(
        total_revenue_overall=Coalesce(Sum("revenue"), Decimal(0)),
        total_weight_overall=Coalesce(Sum("incremental_weight"), Decimal(0)),
        revenue_regular_sum=Coalesce(
            Sum("revenue", filter=Q(taxpayer_type="Regular")), Decimal(0)
        ),
        revenue_walkin_sum=Coalesce(
            Sum("revenue", filter=Q(taxpayer_type="Walk-in")), Decimal(0)
        ),
        weight_regular_sum=Coalesce(
            Sum("incremental_weight", filter=Q(taxpayer_type="Regular")), Decimal(0)
        ),
        weight_walkin_sum=Coalesce(
            Sum("incremental_weight", filter=Q(taxpayer_type="Walk-in")), Decimal(0)
        ),
    )

    # 4. Count distinct taxpayers (exporters)
    # We need to coalesce the exporter ID first, then count distinct.
    annotated_exporters = checkins_with_data.annotate(
        exporter_id=Coalesce(
            F("declaracion__exporter__id"), F("localJourney__exporter__id")
        )
    ).filter(
        exporter_id__isnull=False
    )  # Ensure an exporter is linked

    # Count overall distinct taxpayers
    checkedin_tax_payers = annotated_exporters.aggregate(
        count=Coalesce(Count("exporter_id", distinct=True), 0)
    )["count"]

    # Count distinct regular taxpayers
    tax_payers_regular = annotated_exporters.filter(taxpayer_type="Regular").aggregate(
        count=Coalesce(Count("exporter_id", distinct=True), 0)
    )["count"]

    # Count distinct walk-in taxpayers
    tax_payers_walkin = annotated_exporters.filter(taxpayer_type="Walk-in").aggregate(
        count=Coalesce(Count("exporter_id", distinct=True), 0)
    )["count"]

    # 5. Prepare the response data (structure preserved for frontend)
    response_data = [
        {
            "label": "Total Revenue",
            "amount": str(aggregates["total_revenue_overall"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Walk-in",
            "amount": str(aggregates["revenue_walkin_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Revenue From Regular",
            "amount": str(aggregates["revenue_regular_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg",
            "amount": str(aggregates["total_weight_overall"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg From Walk-in",
            "amount": str(aggregates["weight_walkin_sum"].quantize(Decimal("0.0"))),
        },
        {
            "label": "Total kg From Regular",
            "amount": str(aggregates["weight_regular_sum"].quantize(Decimal("0.0"))),
        },
        {"label": "Total Checked in Tax Payers", "amount": str(checkedin_tax_payers)},
        {
            "label": "Total Checked in Walk-in Tax Payers",
            "amount": str(tax_payers_walkin),
        },
        {
            "label": "Total Checked in Regular Tax Payers",
            "amount": str(tax_payers_regular),
        },
    ]

    return Response(response_data)
