from django.contrib.auth.models import AnonymousUser
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.response import Response

from declaracions.models import Declaracion
from helper.custom_pagination import CustomLimitOffsetPagination
from localcheckings.models import JourneyWithoutTruck
from path.serializers import PathSerializer

from ..models import Path


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


class PathViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing paths (routes between workstations).
    
    Provides CRUD operations for Path entities. Paths define routes that trucks
    and goods follow through multiple workstations. The queryset is automatically
    filtered to show only paths that include the current user's workstation.
    """
    
    queryset = Path.objects.all()
    serializer_class = PathSerializer
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all paths",
        description="""Retrieve a paginated list of paths. 
        
        **Filtering:**
        - For authenticated users with a current_station, only paths that include their station are shown
        - Anonymous users see all paths
        
        **Path Information:**
        - Each path has a name and a sequence of stations
        - Paths are used to track truck movements and declarations
        """,
        tags=["Paths"],
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
            200: PathSerializer(many=True),
            401: {"description": "Unauthorized"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value={
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "name": "Addis Ababa to Djibouti",
                            "created_by": 1,
                            "path_stations": [
                                {"id": 1, "station": 1, "order": 1},
                                {"id": 2, "station": 3, "order": 2},
                                {"id": 3, "station": 5, "order": 3}
                            ],
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
        summary="Create a new path",
        description="Create a new path. The creator will be automatically set to the current authenticated user. Note: Use the /add_path/ endpoint for creating paths with stations in one operation.",
        tags=["Paths"],
        request=PathSerializer,
        responses={
            201: PathSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized"},
        },
        examples=[
            OpenApiExample(
                "Create Path Request",
                value={
                    "name": "Addis Ababa to Djibouti"
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific path",
        description="Get detailed information about a specific path by its ID, including all stations in the path.",
        tags=["Paths"],
        responses={
            200: PathSerializer,
            404: {"description": "Not Found - Path with the specified ID does not exist"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a path",
        description="Update all fields of an existing path. Note: This only updates the path name, not the stations. Use path station endpoints to modify stations.",
        tags=["Paths"],
        request=PathSerializer,
        responses={
            200: PathSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a path",
        description="Update specific fields of an existing path.",
        tags=["Paths"],
        request=PathSerializer,
        responses={
            200: PathSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Name",
                value={
                    "name": "Updated Path Name"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a path",
        description="Permanently delete a path from the database. This will also delete all associated path stations.",
        tags=["Paths"],
        responses={
            204: {"description": "Path successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        queryset = Path.objects.all()

        if not isinstance(self.request.user, AnonymousUser):
            current_station = self.request.user.current_station
            if current_station:
                queryset = queryset.filter(
                    path_stations__station=current_station
                ).distinct()

        return queryset
