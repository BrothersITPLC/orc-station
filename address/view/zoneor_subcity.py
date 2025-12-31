from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from address.serializers import ZoneOrSubcitySerializer
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import ZoneOrSubcity


class ZoneorSubcityViewset(viewsets.ModelViewSet):
    """
    A viewset for managing zones or sub-cities.

    Provides CRUD operations for ZoneOrSubcity entities and custom filtering by region.
    """

    queryset = ZoneOrSubcity.objects.all()
    serializer_class = ZoneOrSubcitySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_zoneorsubcity"

    @extend_schema(
        summary="List all zones or sub-cities",
        description="Retrieve a paginated list of all zones or sub-cities in the system.",
        tags=["Address - Zone/Subcity"],
        responses={
            200: ZoneOrSubcitySerializer(many=True),
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view zones/subcities"
            },
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "name": "Bole",
                        "region_id": 1,
                        "region": {"id": 1, "name": "Addis Ababa"},
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "created_by": 1,
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new zone or sub-city",
        description="Add a new zone or sub-city to the database. The name must be unique and must be associated with a region.",
        tags=["Address - Zone/Subcity"],
        request=ZoneOrSubcitySerializer,
        responses={
            201: ZoneOrSubcitySerializer,
            400: {
                "description": "Bad Request - Invalid data provided or missing region_id"
            },
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to create zones/subcities"
            },
        },
        examples=[
            OpenApiExample(
                "Create Zone Request",
                value={"name": "Bole", "region_id": 1},
                request_only=True,
            ),
            OpenApiExample(
                "Create Zone Response",
                value={
                    "id": 1,
                    "name": "Bole",
                    "region": {"id": 1, "name": "Addis Ababa"},
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "created_by": 1,
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific zone or sub-city",
        description="Get detailed information about a specific zone or sub-city by its ID, including its parent region.",
        tags=["Address - Zone/Subcity"],
        responses={
            200: ZoneOrSubcitySerializer,
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view this zone/subcity"
            },
            404: {
                "description": "Not Found - Zone/Subcity with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Bole",
                    "region": {"id": 1, "name": "Addis Ababa"},
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "created_by": 1,
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a zone or sub-city",
        description="Update all fields of an existing zone or sub-city. All fields are required.",
        tags=["Address - Zone/Subcity"],
        request=ZoneOrSubcitySerializer,
        responses={
            200: ZoneOrSubcitySerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this zone/subcity"
            },
            404: {
                "description": "Not Found - Zone/Subcity with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={"name": "Bole Subcity", "region_id": 1},
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a zone or sub-city",
        description="Update specific fields of an existing zone or sub-city. Only provided fields will be updated.",
        tags=["Address - Zone/Subcity"],
        request=ZoneOrSubcitySerializer,
        responses={
            200: ZoneOrSubcitySerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this zone/subcity"
            },
            404: {
                "description": "Not Found - Zone/Subcity with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Partial Update Request - Name Only",
                value={"name": "Bole"},
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update Request - Region Only",
                value={"region_id": 2},
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a zone or sub-city",
        description="Permanently delete a zone or sub-city from the database. This will fail if there are related woredas.",
        tags=["Address - Zone/Subcity"],
        responses={
            204: {"description": "No Content - Zone/Subcity successfully deleted"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to delete this zone/subcity"
            },
            404: {
                "description": "Not Found - Zone/Subcity with the specified ID does not exist"
            },
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve zones or sub-cities by region",
        description="Get all zones or sub-cities within a specific region.",
        tags=["Address - Zone/Subcity"],
        parameters=[
            OpenApiParameter(
                name="region_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the region to filter zones by",
                required=True,
            )
        ],
        responses={
            200: ZoneOrSubcitySerializer(many=True),
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view zones/subcities"
            },
        },
        examples=[
            OpenApiExample(
                "Filter by Region Response",
                value=[
                    {
                        "id": 1,
                        "name": "Bole",
                        "region": {"id": 1, "name": "Addis Ababa"},
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "created_by": 1,
                    },
                    {
                        "id": 2,
                        "name": "Kirkos",
                        "region": {"id": 1, "name": "Addis Ababa"},
                        "created_at": "2024-01-15T11:00:00Z",
                        "updated_at": "2024-01-15T11:00:00Z",
                        "created_by": 1,
                    },
                ],
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="by-region/(?P<region_id>[^/.]+)")
    def get_by_region(self, request, region_id=None):

        zones = self.queryset.filter(region_id=region_id)
        serializer = self.get_serializer(zones, many=True)
        return Response(serializer.data)

    def get_permissions(self):

        if self.action == "get_by_region":
            self.action = "list"

        if self.action in ["list", "retrieve"]:
            self.permission_required = None
            return []

        return has_custom_permission(self, "zoneorsubcity")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
