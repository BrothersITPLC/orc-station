from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from address.serializers import WoredaSerializer
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Woreda


class WoredaViewset(viewsets.ModelViewSet):
    """
    A viewset for managing woredas.

    Provides CRUD operations for Woreda entities and custom filtering by zone/subcity.
    """

    queryset = Woreda.objects.all()
    serializer_class = WoredaSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_woreda"

    @extend_schema(
        summary="List all woredas",
        description="Retrieve a paginated list of all woredas in the system.",
        tags=["Address - Woreda"],
        responses={
            200: WoredaSerializer(many=True),
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view woredas"
            },
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "name": "Woreda 01",
                        "zone_id": 1,
                        "zone": {
                            "id": 1,
                            "name": "Bole",
                            "region": {"id": 1, "name": "Addis Ababa"},
                        },
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
        summary="Create a new woreda",
        description="Add a new woreda to the database. The name must be unique and must be associated with a zone/subcity.",
        tags=["Address - Woreda"],
        request=WoredaSerializer,
        responses={
            201: WoredaSerializer,
            400: {
                "description": "Bad Request - Invalid data provided or missing zone_id"
            },
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to create woredas"
            },
        },
        examples=[
            OpenApiExample(
                "Create Woreda Request",
                value={"name": "Woreda 01", "zone_id": 1},
                request_only=True,
            ),
            OpenApiExample(
                "Create Woreda Response",
                value={
                    "id": 1,
                    "name": "Woreda 01",
                    "zone": {
                        "id": 1,
                        "name": "Bole",
                        "region": {"id": 1, "name": "Addis Ababa"},
                    },
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
        summary="Retrieve a specific woreda",
        description="Get detailed information about a specific woreda by its ID, including its parent zone/subcity.",
        tags=["Address - Woreda"],
        responses={
            200: WoredaSerializer,
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view this woreda"
            },
            404: {
                "description": "Not Found - Woreda with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Woreda 01",
                    "zone": {
                        "id": 1,
                        "name": "Bole",
                        "region": {"id": 1, "name": "Addis Ababa"},
                    },
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
        summary="Update a woreda",
        description="Update all fields of an existing woreda. All fields are required.",
        tags=["Address - Woreda"],
        request=WoredaSerializer,
        responses={
            200: WoredaSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this woreda"
            },
            404: {
                "description": "Not Found - Woreda with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={"name": "Woreda 01", "zone_id": 1},
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a woreda",
        description="Update specific fields of an existing woreda. Only provided fields will be updated.",
        tags=["Address - Woreda"],
        request=WoredaSerializer,
        responses={
            200: WoredaSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this woreda"
            },
            404: {
                "description": "Not Found - Woreda with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Partial Update Request - Name Only",
                value={"name": "Woreda 01"},
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update Request - Zone Only",
                value={"zone_id": 2},
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a woreda",
        description="Permanently delete a woreda from the database.",
        tags=["Address - Woreda"],
        responses={
            204: {"description": "No Content - Woreda successfully deleted"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to delete this woreda"
            },
            404: {
                "description": "Not Found - Woreda with the specified ID does not exist"
            },
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve woredas by zone or sub-city",
        description="Get all woredas within a specific zone or sub-city.",
        tags=["Address - Woreda"],
        parameters=[
            OpenApiParameter(
                name="zone_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the zone or sub-city to filter woredas by",
                required=True,
            )
        ],
        responses={
            200: WoredaSerializer(many=True),
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view woredas"
            },
        },
        examples=[
            OpenApiExample(
                "Filter by Zone Response",
                value=[
                    {
                        "id": 1,
                        "name": "Woreda 01",
                        "zone": {
                            "id": 1,
                            "name": "Bole",
                            "region": {"id": 1, "name": "Addis Ababa"},
                        },
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "created_by": 1,
                    },
                    {
                        "id": 2,
                        "name": "Woreda 02",
                        "zone": {
                            "id": 1,
                            "name": "Bole",
                            "region": {"id": 1, "name": "Addis Ababa"},
                        },
                        "created_at": "2024-01-15T11:00:00Z",
                        "updated_at": "2024-01-15T11:00:00Z",
                        "created_by": 1,
                    },
                ],
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="by-zone/(?P<zone_id>[^/.]+)")
    def get_by_ZoneSubcity(self, request, zone_id=None):
        woredas = self.queryset.filter(zone_id=zone_id)
        serializer = self.get_serializer(woredas, many=True)
        return Response(serializer.data)

    def get_permissions(self):

        if self.action == "get_by_ZoneSubcity":
            self.action = "list"

        if self.action in ["list", "retrieve"]:
            self.permission_required = None
            return [permission() for permission in self.permission_classes]

        return has_custom_permission(self, "woreda")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
