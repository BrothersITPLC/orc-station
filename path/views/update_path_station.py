from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.models import Declaracion
from localcheckings.models import JourneyWithoutTruck

from ..models import PathStation


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


class UpdatePathStationOrder(APIView):
    """
    API view to reorder stations within a path.
    
    Allows changing the sequence of stations in a path while validating
    against duplicate sequences and checking for unfinished journeys.
    """

    @extend_schema(
        summary="Update the order of stations in a path",
        description="""Reorder the stations within an existing path.
        
        **Validation:**
        - Checks if the path has any unfinished journeys (PENDING or ON_GOING)
        - Validates that the new order won't create a duplicate station sequence
        - All updates are wrapped in a transaction for data consistency
        
        **Request Body:**
        - `path_id`: ID of the path to update
        - `stations_order`: Array of path station IDs in the new desired order
        
        **Important:**
        - The `stations_order` array should contain path station IDs (not station IDs)
        - The order will be recalculated starting from the last existing order + 1
        
        **Error Responses:**
        - 400: Invalid data, unfinished journey, or duplicate sequence
        - 500: Internal server error
        """,
        tags=["Paths - Management"],
        request={
            "type": "object",
            "properties": {
                "path_id": {"type": "integer", "description": "ID of the path"},
                "stations_order": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Array of path station IDs in the new order"
                }
            },
            "required": ["path_id", "stations_order"]
        },
        responses={
            200: {"description": "Order updated successfully", "type": "object", "properties": {"status": {"type": "string"}}},
            400: {"description": "Invalid data, unfinished journey, or duplicate sequence"},
            500: {"description": "Internal server error"},
        },
        examples=[
            OpenApiExample(
                "Update Order Request",
                value={
                    "path_id": 1,
                    "stations_order": [3, 1, 2]
                },
                request_only=True,
                description="Reorder path stations with IDs 3, 1, 2 to be in that sequence"
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "status": "Order updated"
                },
                response_only=True,
            ),
            OpenApiExample(
                "Unfinished Journey Error",
                value={
                    "error": "this path has unfinished Journey So you can not change this path"
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Duplicate Sequence Error",
                value={
                    "error": "A path with the same station sequence already exists."
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def put(self, request):
        data = request.data
        path_id = data.get("path_id")
        stations_order = data.get("stations_order")
        response = pathHasUnfinishedJourney(path_id=path_id)
        if response:
            return response
        if not path_id or not stations_order:
            return Response(
                {"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST
            )

        last_order = (
            PathStation.objects.filter(path_id=path_id).order_by("-order").first().order
        )

        station_ids = []
        for station in stations_order:
            station_ids.append(
                PathStation.objects.filter(id=station).first().station.id
            )

        new_station_sequence = "-".join(str(station) for station in station_ids)
        existing_paths = PathStation.objects.values("path_id").distinct()
        for path_info in existing_paths:
            existing_path_stations = PathStation.objects.filter(
                path_id=path_info["path_id"]
            ).order_by("order")
            existing_station_sequence = "-".join(
                str(station.station_id) for station in existing_path_stations
            )
            print(existing_station_sequence, "existing station")
            if new_station_sequence == existing_station_sequence:
                return Response(
                    {"error": "A path with the same station sequence already exists."},
                    status=400,
                )

            if new_station_sequence.startswith(existing_station_sequence):
                continue

            if existing_station_sequence.startswith(new_station_sequence):
                continue

        try:
            with transaction.atomic():
                for order, station_id in enumerate(
                    stations_order, start=last_order + 1
                ):
                    print(order, " :Order: ", station_id)
                    PathStation.objects.filter(path_id=path_id, id=station_id).update(
                        order=order
                    )
            return Response({"status": "Order updated"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
