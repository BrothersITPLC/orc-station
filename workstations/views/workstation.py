from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission
from workstations.serializers import WorkStationSerializer

from ..models import WorkStation


class WorkStationViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing workstations.
    
    Provides CRUD operations for WorkStation entities with search functionality
    and custom actions for position management.
    """
    
    queryset = WorkStation.objects.all()
    serializer_class = WorkStationSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_workstation"
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "machine_number"]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all workstations",
        description="Retrieve a paginated list of all workstations in the system. Supports search by name and machine number.",
        tags=["Workstations"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter workstations by name or machine number",
                required=False,
            ),
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
            200: WorkStationSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view workstations"},
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
                            "name": "Main Office",
                            "machine_number": "WS001",
                            "woreda": 1,
                            "kebele": "01",
                            "managed_by": 1,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        },
                        {
                            "id": 2,
                            "name": "Border Station",
                            "machine_number": "WS002",
                            "woreda": 2,
                            "kebele": "03",
                            "managed_by": 2,
                            "created_at": "2024-01-15T11:00:00Z",
                            "updated_at": "2024-01-15T11:00:00Z"
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
        summary="Create a new workstation",
        description="Add a new workstation to the database. The name and machine number must be unique. The workstation will be automatically assigned to the current user as manager.",
        tags=["Workstations"],
        request=WorkStationSerializer,
        responses={
            201: WorkStationSerializer,
            400: {"description": "Bad Request - Invalid data provided or duplicate name/machine number"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create workstations"},
        },
        examples=[
            OpenApiExample(
                "Create Workstation Request",
                value={
                    "name": "Main Office",
                    "machine_number": "WS001",
                    "woreda": 1,
                    "kebele": "01"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Workstation Response",
                value={
                    "id": 1,
                    "name": "Main Office",
                    "machine_number": "WS001",
                    "woreda": 1,
                    "kebele": "01",
                    "managed_by": 1,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific workstation",
        description="Get detailed information about a specific workstation by its ID.",
        tags=["Workstations"],
        responses={
            200: WorkStationSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this workstation"},
            404: {"description": "Not Found - Workstation with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Main Office",
                    "machine_number": "WS001",
                    "woreda": 1,
                    "kebele": "01",
                    "managed_by": 1,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a workstation",
        description="Update all fields of an existing workstation. All fields are required.",
        tags=["Workstations"],
        request=WorkStationSerializer,
        responses={
            200: WorkStationSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this workstation"},
            404: {"description": "Not Found - Workstation with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "name": "Main Office - Updated",
                    "machine_number": "WS001",
                    "woreda": 1,
                    "kebele": "01"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a workstation",
        description="Update specific fields of an existing workstation. Only provided fields will be updated.",
        tags=["Workstations"],
        request=WorkStationSerializer,
        responses={
            200: WorkStationSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this workstation"},
            404: {"description": "Not Found - Workstation with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Name Only",
                value={
                    "name": "Updated Office Name"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Kebele Only",
                value={
                    "kebele": "05"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a workstation",
        description="Permanently delete a workstation from the database.",
        tags=["Workstations"],
        responses={
            204: {"description": "No Content - Workstation successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this workstation"},
            404: {"description": "Not Found - Workstation with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Add workstation with position",
        description="Create a new workstation with a specific position in the ordering.",
        tags=["Workstations"],
        request={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "machine_id": {"type": "string"},
                "location": {"type": "string"},
                "position": {"type": "integer"}
            },
            "required": ["name", "location", "position"]
        },
        responses={
            201: WorkStationSerializer,
            400: {"description": "Bad Request - Name, location, and position are required"},
        },
        examples=[
            OpenApiExample(
                "Add with Position Request",
                value={
                    "name": "Border Station",
                    "machine_id": "WS003",
                    "location": "North Border",
                    "position": 1
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"])
    def add_with_position(self, request):
        name = request.data.get("name")
        machine_id = request.data.get("machine_id")
        location = request.data.get("location")
        position = request.data.get("position")

        if not name or not location or position is None:
            return Response(
                {"error": "Name, location, and position are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_station = WorkStation.add_with_position(
            name, machine_id, location, position
        )
        serializer = self.get_serializer(new_station)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Swap workstation positions",
        description="Swap the positions of two workstations in the ordering.",
        tags=["Workstations"],
        request={
            "type": "object",
            "properties": {
                "id1": {"type": "integer"},
                "id2": {"type": "integer"}
            },
            "required": ["id1", "id2"]
        },
        responses={
            200: {"description": "Positions swapped successfully"},
            400: {"description": "Bad Request - Both IDs are required"},
        },
        examples=[
            OpenApiExample(
                "Swap Positions Request",
                value={
                    "id1": 1,
                    "id2": 2
                },
                request_only=True,
            ),
            OpenApiExample(
                "Swap Positions Response",
                value={
                    "message": "Positions swapped successfully"
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"])
    def swap_positions(self, request):
        id1 = request.data.get("id1")
        id2 = request.data.get("id2")

        if not id1 or not id2:
            return Response(
                {"error": "Both IDs are required"}, status=status.HTTP_400_BAD_REQUEST
            )

        WorkStation.swap_positions(id1, id2)
        return Response(
            {"message": "Positions swapped successfully"}, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):

        serializer.save(managed_by=self.request.user)

    def get_permissions(self):
        return has_custom_permission(self, "workstation")
