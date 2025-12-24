from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.models import Declaracion
from localcheckings.models import JourneyWithoutTruck

from ..models import Path, PathStation


def pathHasUnfinishedJourney(path_id):
    try:
        has_without_truck_journey = (
            JourneyWithoutTruck.objects.filter(status__in=["PENDING", "ON_GOING"])
            .filter(path_id=path_id)
            .exists()
        )
        has_with_truck_journey = (
            Declaracion.objects.filter(status__in=["PENDING", "ON_GOING"])
            .filter(path_id=path_id)
            .exists()
        )
        if has_without_truck_journey or has_with_truck_journey:
            return Response(
                {
                    "error": "this path has unfinished Journey So you can not change this path"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AddPath(APIView):
    """
    API view to create a complete path with all its stations in one operation.
    
    This endpoint creates a path and all its stations atomically, ensuring
    data consistency and validating against duplicate station sequences.
    """

    @extend_schema(
        summary="Create a path with stations",
        description="""Create a new path along with all its stations in a single atomic operation.
        
        **Validation:**
        - Checks for duplicate station sequences across all paths
        - Prevents creating paths that are subsets or supersets of existing paths
        - All operations are wrapped in a transaction for data consistency
        
        **Request Body:**
        - `path_name`: Name of the path
        - `path_stations`: Array of station IDs in order
        
        **Example:**
        ```json
        {
            "path_name": "Addis Ababa to Djibouti",
            "path_stations": [1, 3, 5, 7]
        }
        ```
        
        **Station Sequence Validation:**
        - Each unique sequence of stations can only exist once
        - Sequences like "1-3-5" and "1-3-5-7" can coexist (one is not a subset)
        - Sequences like "1-3-5" and "1-3-5" cannot coexist (exact duplicates)
        """,
        tags=["Paths - Management"],
        request={
            "type": "object",
            "properties": {
                "path_name": {"type": "string", "description": "Name of the path"},
                "path_stations": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Array of station IDs in sequence order"
                }
            },
            "required": ["path_name", "path_stations"]
        },
        responses={
            201: {"description": "Path added successfully", "type": "object", "properties": {"message": {"type": "string"}}},
            400: {"description": "Invalid data or duplicate station sequence"},
            500: {"description": "Internal server error"},
        },
        examples=[
            OpenApiExample(
                "Create Path with Stations Request",
                value={
                    "path_name": "Addis Ababa to Djibouti",
                    "path_stations": [1, 3, 5, 7]
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "Path added successfully"
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Duplicate Sequence Error",
                value={
                    "error": "A path with the same station sequence already exists."
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Invalid Data Error",
                value={
                    "error": "Invalid data"
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        try:
            data = request.data

            path_name = data.get("path_name")
            path_stations = data.get("path_stations")
            if not path_name or not path_stations:
                return Response({"error": "Invalid data"}, status=400)

            new_station_sequence = "-".join(
                str(station_id) for station_id in path_stations
            )

            existing_paths = PathStation.objects.values("path_id").distinct()
            for path_info in existing_paths:
                existing_path_stations = PathStation.objects.filter(
                    path_id=path_info["path_id"]
                ).order_by("order")
                existing_station_sequence = "-".join(
                    str(station.station_id) for station in existing_path_stations
                )

                if new_station_sequence == existing_station_sequence:
                    return Response(
                        {
                            "error": "A path with the same station sequence already exists."
                        },
                        status=400,
                    )

                if new_station_sequence.startswith(
                    existing_station_sequence
                ) or existing_station_sequence.startswith(new_station_sequence):
                    continue

            with transaction.atomic():

                path = Path.objects.create(name=path_name, created_by=request.user)
                for station in path_stations:

                    PathStation.objects.create(path=path, station_id=station)
            return Response({"message": "Path added successfully"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
