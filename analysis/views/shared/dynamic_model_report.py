from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from analysis.serializers import DriverSerializer, ExporterSerializer
from analysis.views.helpers import parse_and_validate_date_range
from drivers.models import Driver
from exporters.models import Exporter
from helper.custom_pagination import CustomLimitOffsetPagination


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def dynamic_model_report(request, model_name):
    """
    Generates a paginated report for either 'drivers' or 'exporters' models.

    This view dynamically fetches data based on the `model_name` provided in the URL.
    It applies date range filters based on the `created_at` field, and optional filters
    for `register_place_id` (station where registered) and `register_by_id` (controller who registered).
    Results are paginated using `CustomLimitOffsetPagination`.

    URL Parameters:
    - model_name (str): The name of the model to query ('drivers' or 'exporters').

    Query Parameters:
    - start_date (str, YYYY-MM-DD): The start date for filtering records by their 'created_at' field. Required.
    - end_date (str, YYYY-MM-DD): The end date for filtering records by their 'created_at' field. Required.
    - station_id (int, optional): Filters records by the ID of the registration station.
    - controller_id (int, optional): Filters records by the ID of the registering employee (controller).
    - limit (int, optional): Maximum number of items to return per page.
    - offset (int, optional): The starting point for the data.

    Returns:
        Response: A paginated JSON response containing serialized model instances.
        Example (for 'drivers'):
        {
            "count": 100,
            "next": "http://api.example.com/report/drivers/?limit=10&offset=20",
            "previous": "http://api.example.com/report/drivers/?limit=10&offset=0",
            "results": [
                {
                    "id": 1,
                    "first_name": "Driver",
                    "last_name": "One",
                    "created_at": "2023-01-15T10:00:00Z",
                    ...
                },
                ...
            ]
        }

    Raises:
        HTTP 400 Bad Request: If 'model_name' is invalid, or if 'start_date'/'end_date'
                              are missing or in an invalid format.
    """
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    station_id = request.query_params.get("station_id")
    controller_id = request.query_params.get("controller_id")

    # 1. Validate and parse the date range using the helper
    try:
        start_date, inclusive_end_date = parse_and_validate_date_range(
            start_date_str, end_date_str
        )
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Determine the model and serializer class based on model_name
    model = None
    serializer_class = None
    if model_name == "drivers":
        model = Driver
        serializer_class = DriverSerializer
    elif model_name == "exporters":
        model = Exporter
        serializer_class = ExporterSerializer
    else:
        return Response(
            {"error": "Invalid model name. Choose 'drivers' or 'exporters'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Build filter conditions for the queryset
    filters = {
        "created_at__range": [start_date, inclusive_end_date],
    }

    if station_id and station_id != "null":
        # Assuming 'register_place_id' is the field for station ID on Driver/Exporter
        filters["register_place_id"] = station_id
    if controller_id and controller_id != "null":
        # Assuming 'register_by_id' is the field for controller ID on Driver/Exporter
        filters["register_by_id"] = controller_id

    # 4. Filter the queryset
    queryset = model.objects.filter(**filters)

    # 5. Apply pagination
    paginator = CustomLimitOffsetPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)

    # 6. Serialize the paginated data
    serializer = serializer_class(paginated_queryset, many=True)

    # 7. Return the paginated response (frontend compatible)
    return paginator.get_paginated_response(serializer.data)
