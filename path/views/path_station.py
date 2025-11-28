from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from declaracions.models import Declaracion
from helper.custom_pagination import CustomLimitOffsetPagination
from localcheckings.models import JourneyWithoutTruck
from path.serializers import PathStationSerializer

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


class PathStationViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing path stations (individual stations within a path).
    
    Provides CRUD operations for PathStation entities. Each path station represents
    one workstation in a path's sequence. The order field determines the sequence.
    Includes validation to prevent duplicate station sequences and checks for unfinished journeys.
    """
    
    queryset = PathStation.objects.all()
    serializer_class = PathStationSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all path stations",
        description="Retrieve a paginated list of all path stations in the system.",
        tags=["Paths - Stations"],
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of results to return per page",
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="The initial index from which to return the results",
                required=False,
            ),
        ],
        responses={
            200: PathStationSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value={
                    "count": 3,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "path": 1,
                            "station": 1,
                            "order": 1,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        },
                        {
                            "id": 2,
                            "path": 1,
                            "station": 3,
                            "order": 2,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        }
                    ]
                },
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new path station",
        description="Add a new station to a path. The order will be automatically set if not provided. Note: Use /add_path_station/ endpoint for better validation.",
        tags=["Paths - Stations"],
        request=PathStationSerializer,
        responses={
            201: PathStationSerializer,
            400: {"description": "Bad Request - Invalid data or duplicate station sequence"},
        },
        examples=[
            OpenApiExample(
                "Create Path Station Request",
                value={
                    "path": 1,
                    "station": 5
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific path station",
        description="Get detailed information about a specific path station by its ID.",
        tags=["Paths - Stations"],
        responses={
            200: PathStationSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a path station",
        description="Update all fields of an existing path station.",
        tags=["Paths - Stations"],
        request=PathStationSerializer,
        responses={
            200: PathStationSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a path station",
        description="Update specific fields of an existing path station.",
        tags=["Paths - Stations"],
        request=PathStationSerializer,
        responses={
            200: PathStationSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a path station",
        description="""Delete a path station from a path.
        
        **Validation:**
        - Checks if the path has any unfinished journeys (PENDING or ON_GOING)
        - Validates that removing this station won't create a duplicate station sequence
        - Prevents deletion if it would conflict with existing paths
        
        **Error Responses:**
        - 400: Path has unfinished journeys or would create duplicate sequence
        """,
        tags=["Paths - Stations"],
        responses={
            200: {"description": "Path station deleted successfully", "type": "object", "properties": {"message": {"type": "string"}, "id": {"type": "integer"}}},
            400: {"description": "Bad Request - Unfinished journey or duplicate sequence"},
            404: {"description": "Not Found"},
        },
        examples=[
            OpenApiExample(
                "Delete Success Response",
                value={
                    "message": "Path station deleted successfully.",
                    "id": 5
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
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            instance_id = instance.id
            path_id = instance.path_id

            response = pathHasUnfinishedJourney(path_id=path_id)
            if response:
                return response
            data = PathStation.objects.filter(path_id=path_id).order_by("order")
            data_order = [x for x in data if x.id != instance_id]
            new_station_sequence = "-".join(
                str(station.station.id) for station in data_order
            )
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
                        {
                            "error": "A path with the same station sequence already exists."
                        },
                        status=400,
                    )

                if new_station_sequence.startswith(existing_station_sequence):
                    continue

                if existing_station_sequence.startswith(new_station_sequence):
                    continue

            self.perform_destroy(instance)

            return Response(
                {"message": "Path station deleted successfully.", "id": instance_id},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        instance.delete()
