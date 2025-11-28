from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status, viewsets

from address.serializers import RegionOrCitySerializer
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import RegionOrCity


class RegionorCityViewset(viewsets.ModelViewSet):
    """
    A viewset for managing regions or cities.
    
    Provides CRUD operations for RegionOrCity entities.
    """

    queryset = RegionOrCity.objects.all()
    serializer_class = RegionOrCitySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_regionorcity"

    @extend_schema(
        summary="List all regions or cities",
        description="Retrieve a paginated list of all regions or cities in the system.",
        tags=["Address - Region/City"],
        responses={
            200: RegionOrCitySerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view regions/cities"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "name": "Addis Ababa",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "created_by": 1
                    },
                    {
                        "id": 2,
                        "name": "Oromia",
                        "created_at": "2024-01-15T11:00:00Z",
                        "updated_at": "2024-01-15T11:00:00Z",
                        "created_by": 1
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new region or city",
        description="Add a new region or city to the database. The name must be unique.",
        tags=["Address - Region/City"],
        request=RegionOrCitySerializer,
        responses={
            201: RegionOrCitySerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create regions/cities"},
        },
        examples=[
            OpenApiExample(
                "Create Region Request",
                value={
                    "name": "Addis Ababa"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Region Response",
                value={
                    "id": 1,
                    "name": "Addis Ababa",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "created_by": 1
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific region or city",
        description="Get detailed information about a specific region or city by its ID.",
        tags=["Address - Region/City"],
        responses={
            200: RegionOrCitySerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this region/city"},
            404: {"description": "Not Found - Region/City with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Addis Ababa",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "created_by": 1
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a region or city",
        description="Update all fields of an existing region or city. All fields are required.",
        tags=["Address - Region/City"],
        request=RegionOrCitySerializer,
        responses={
            200: RegionOrCitySerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this region/city"},
            404: {"description": "Not Found - Region/City with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "name": "Addis Ababa City"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a region or city",
        description="Update specific fields of an existing region or city. Only provided fields will be updated.",
        tags=["Address - Region/City"],
        request=RegionOrCitySerializer,
        responses={
            200: RegionOrCitySerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this region/city"},
            404: {"description": "Not Found - Region/City with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update Request",
                value={
                    "name": "Addis Ababa"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a region or city",
        description="Permanently delete a region or city from the database. This will fail if there are related zones/subcities.",
        tags=["Address - Region/City"],
        responses={
            204: {"description": "No Content - Region/City successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this region/city"},
            404: {"description": "Not Found - Region/City with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        return has_custom_permission(self, "regionorcity")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

