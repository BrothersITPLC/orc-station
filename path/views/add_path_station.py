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


class AddPathStation(APIView):
    """
    API view to add a new station to an existing path.
    
    Validates that adding the station won't create duplicate sequences
    and checks for unfinished journeys before allowing modifications.
    """

    @extend_schema(
        summary="Add a station to an existing path",
        description="""Add a new station to the end of an existing path's sequence.
        
        **Validation:**
        - Checks if the path has any unfinished journeys (PENDING or ON_GOING)
        - Validates that adding this station won't create a duplicate station sequence
        - Automatically assigns the next order number
        
        **Request Body:**
        - `path_id`: ID of the path to add the station to
        - `station_id`: ID of the station to add
        
        **Error Responses:**
        - 400: Invalid data, unfinished journey, or duplicate sequence
        - 500: Internal server error
        """,
        tags=["Paths - Management"],
        request={
            "type": "object",
            "properties": {
                "path_id": {"type": "integer", "description": "ID of the path"},
                "station_id": {"type": "integer", "description": "ID of the station to add"}
            },
            "required": ["path_id", "station_id"]
        },
        responses={
            201: {"description": "Path station added successfully", "type": "object", "properties": {"message": {"type": "string"}}},
            400: {"description": "Invalid data, unfinished journey, or duplicate sequence"},
            500: {"description": "Internal server error"},
        },
        examples=[
            OpenApiExample(
                "Add Station Request",
                value={
                    "path_id": 1,
                    "station_id": 8
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "path Station  added successfully"
                },
                response_only=True,
                status_codes=["201"],
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
    def post(self, request):
        try:
            data = request.data

            path_id = data.get("path_id")
            station_id = data.get("station_id")

            if not path_id or not station_id:
                return Response({"error": "Invalid data"}, status=400)

            response = pathHasUnfinishedJourney(path_id=path_id)
            if response:
                return response
            station_ids = PathStation.objects.filter(path_id=path_id).order_by("order")

            new_station_sequence = "-".join(
                str(path_station.station_id) for path_station in station_ids
            )

            new_station_sequence = new_station_sequence + "-" + str(station_id)

            print(new_station_sequence, " like Error")

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

                if existing_station_sequence.startswith(new_station_sequence):
                    continue

                if new_station_sequence.startswith(existing_station_sequence):
                    continue

            last_path_station = (
                PathStation.objects.filter(path_id=path_id).order_by("-order").first()
            )
            order = last_path_station.order + 1 if last_path_station else 1
            PathStation.objects.create(
                path_id=path_id, station_id=station_id, order=order
            )
            return Response({"message": "path Station  added successfully"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
