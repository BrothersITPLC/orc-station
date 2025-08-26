from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from drivers.models import Driver
from exporters.models import Exporter
from helper.custom_pagination import CustomLimitOffsetPagination

from ..serializers import DriverSerializer, ExporterSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def model_report(request, model_name):
    start_date = parse_date(request.query_params.get("start_date"))
    end_date = parse_date(request.query_params.get("end_date"))
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    filters = {}
    if start_date:
        filters["created_at__gte"] = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
    if end_date:
        filters["created_at__lte"] = timezone.make_aware(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
    if station_id and station_id != "null":
        filters["register_place_id"] = station_id
    if controller_id and controller_id != "null":
        filters["register_by_id"] = controller_id

    if model_name == "drivers":
        model = Driver
        serializer_class = DriverSerializer
    elif model_name == "exporters":
        model = Exporter
        serializer_class = ExporterSerializer
    else:
        return Response(
            {"error": "Invalid model name"}, status=status.HTTP_400_BAD_REQUEST
        )

    queryset = model.objects.filter(**filters)

    paginator = CustomLimitOffsetPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)

    # Serialize the paginated data
    serializer = serializer_class(paginated_queryset, many=True)

    # Return the paginated response
    return paginator.get_paginated_response(serializer.data)

    # return Response(serializer.data)
