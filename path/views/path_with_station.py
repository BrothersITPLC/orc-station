from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from helper.custom_pagination import CustomLimitOffsetPagination
from path.serializers import PathSerializer

from ..models import Path


class PathViewSetWithStation(viewsets.ModelViewSet):
    """
    A viewset for managing paths with station filtering.
    
    Similar to PathViewSet but filters paths based on the current user's station.
    This viewset is used when you need to see only paths that include the user's
    current workstation.
    """
    
    queryset = Path.objects.all()
    serializer_class = PathSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List paths for current user's station",
        description="""Retrieve a paginated list of paths that include the current user's workstation.
        
        **Filtering:**
        - Automatically filters to show only paths where the user's current_station is one of the path stations
        - Returns distinct paths (no duplicates)
        
        **Use Case:**
        - Used to show relevant paths to users at specific workstations
        - Helps users see only the routes they are involved with
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
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "name": "Addis Ababa to Djibouti",
                            "created_by": 1,
                            "path_stations": [
                                {"id": 1, "station": 1, "order": 1},
                                {"id": 2, "station": 3, "order": 2}
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
        description="Create a new path. The creator will be automatically set to the current authenticated user.",
        tags=["Paths"],
        request=PathSerializer,
        responses={
            201: PathSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific path",
        description="Get detailed information about a specific path by its ID.",
        tags=["Paths"],
        responses={
            200: PathSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a path",
        description="Update all fields of an existing path.",
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
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a path",
        description="Permanently delete a path from the database.",
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
        current_station = self.request.user.current_station

        if current_station:
            queryset = queryset.filter(
                pathstation__station__name=current_station
            ).distinct()

        return queryset
