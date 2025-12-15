from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.views.helpers import (
    annotate_revenue_on_checkins,
    parse_and_validate_date_range,
)
from declaracions.models import Checkin
from exporters.models import Exporter


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_top_regular_taxpayer_report(request):
    """
    Generates a report of the top 10 "Regular" taxpayers (exporters associated
    with Declaracions) based on their total number of unique declarations
    (merchant paths) within a specified date range.

    For each of these top taxpayers, the report provides their total revenue
    and total incremental weight (amount) derived from their check-ins during
    the period. This view leverages `parse_and_validate_date_range` for robust
    date handling and `annotate_revenue_on_checkins` for efficient database-level
    calculation of incremental revenue and weight, replacing manual Python loops.

    Query Parameters:
    - selected_date_type (str): Specifies the date range validation type ('weekly', 'monthly', 'yearly'). Required.
    - start_date (str, YYYY-MM-DD): The start date for filtering check-ins and declarations. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering check-ins and declarations. Required.

    Returns:
        Response: A list of dictionaries, where each dictionary represents a top
        "Regular" taxpayer with their details, total amount, total revenue, and
        total number of declarations.
        Example:
        [
            {
                "tin_number": "TAXID001",
                "type": "regular",
                "exporter_name": "Jane Doe",
                "total_amount": 10000.50,
                "total_revenue": 2500.75,
                "total_path": 20
            },
            ... (up to 10 entries)
        ]

    Raises:
        HTTP 400 Bad Request: If any required parameters are missing, date formats are invalid,
                              or the date range does not match the 'selected_date_type' rules.
    """
    selected_date_type = request.query_params.get("selected_date_type")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    # 1. Validate request parameters and parse dates using the helper function
    if not all([selected_date_type, start_date_str, end_date_str]):
        missing_params = [
            param_name
            for param_name, param_value in {
                "selected_date_type": selected_date_type,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }.items()
            if not param_value
        ]
        return Response(
            {"error": f"Missing required parameters: {', '.join(missing_params)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str, selected_date_type
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Build the base queryset for relevant "regular" check-ins
    base_regular_checkins_query = Checkin.objects.filter(
        checkin_time__range=[start_date, inclusive_end_date],
        status__in=["pass", "paid", "success"],
        declaracion__isnull=False,  # Filter for declaration-based check-ins only (regular)
        declaracion__exporter__isnull=False,  # Ensure an exporter is linked
    )

    if not base_regular_checkins_query.exists():
        return Response([])

    # 3. Annotate check-ins with incremental weight and revenue using the helper
    checkins_with_revenue_and_weight = annotate_revenue_on_checkins(
        base_regular_checkins_query
    )

    # 4. Aggregate data for top "Regular" taxpayers (Python)
    taxpayer_stats_map = {}

    for checkin in checkins_with_revenue_and_weight:
        # Access relationship fields.
        decl = checkin.declaracion
        exporter = decl.exporter
        
        if not exporter:
            continue
            
        e_id = exporter.id
        
        if e_id not in taxpayer_stats_map:
            # Safely get type name
            t_name = "Unknown"
            if exporter.type:
                t_name = exporter.type.name
                
            taxpayer_stats_map[e_id] = {
                "first_name": exporter.first_name,
                "last_name": exporter.last_name,
                "tin_number": exporter.tin_number,
                "type_name": t_name,
                "total_revenue": Decimal(0),
                "total_amount": Decimal(0),
                "path_set": set() # track unique declaracion_ids
            }
            
        rev = checkin.revenue or Decimal(0)
        weight = checkin.incremental_weight or Decimal(0)
        
        taxpayer_stats_map[e_id]["total_revenue"] += rev
        taxpayer_stats_map[e_id]["total_amount"] += weight
        taxpayer_stats_map[e_id]["path_set"].add(decl.id)

    # Convert to list
    stats_list = []
    for e_id, stats in taxpayer_stats_map.items():
        stats["total_path"] = len(stats["path_set"])
        if stats["total_path"] > 0:
            stats_list.append(stats)
            
    # Order by total_path (desc), then total_revenue (desc)
    stats_list.sort(key=lambda x: (x["total_path"], x["total_revenue"]), reverse=True)
    
    # Take top 10
    top_regular_taxpayers_data = stats_list[:10]

    # 5. Prepare the report data in the required format
    report_data = []
    for item in top_regular_taxpayers_data:
        # The original code had category logic here, but it wasn't used in the final
        # output structure for 'admin_top_regular_taxpayer_report'.
        # Keeping the format exactly as requested by the user.
        report_data.append(
            {
                "tin_number": item["tin_number"],
                "type": item["type_name"],
                "exporter_name": f"{item['first_name']} {item['last_name']}".strip(),
                "total_amount": float(round(item["total_amount"], 2)),
                "total_revenue": float(round(item["total_revenue"], 2)),
                "total_path": item["total_path"],
            }
        )

    return Response(report_data)
    return Response(report_data)
    return Response(report_data)
