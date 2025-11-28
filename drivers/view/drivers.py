from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, viewsets

from drivers.serializers import DriverSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Driver


class DriverViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing drivers.
    
    Provides CRUD operations for Driver entities with search functionality.
    """
    
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_driver"
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "license_number",
    ]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all drivers",
        description="Retrieve a paginated list of all drivers in the system. Supports search by first name, last name, email, phone number, and license number.",
        tags=["Drivers"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter drivers by name, email, phone, or license number",
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
            200: DriverSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view drivers"},
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
                            "first_name": "Abebe",
                            "last_name": "Kebede",
                            "email": "abebe.kebede@example.com",
                            "phone_number": "+251911234567",
                            "license_number": "DL123456",
                            "woreda": 1,
                            "kebele": "05",
                            "register_by": {
                                "id": 1,
                                "username": "admin"
                            },
                            "register_place": {
                                "id": 1,
                                "name": "Main Office"
                            },
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
        summary="Create a new driver",
        description="Register a new driver in the system. The license number must be unique. The driver will be automatically associated with the current user and their workstation.",
        tags=["Drivers"],
        request=DriverSerializer,
        responses={
            201: DriverSerializer,
            400: {"description": "Bad Request - Invalid data provided or duplicate license number"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create drivers"},
        },
        examples=[
            OpenApiExample(
                "Create Driver Request",
                value={
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "email": "abebe.kebede@example.com",
                    "phone_number": "+251911234567",
                    "license_number": "DL123456",
                    "woreda": 1,
                    "kebele": "05"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Driver Response",
                value={
                    "id": 1,
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "email": "abebe.kebede@example.com",
                    "phone_number": "+251911234567",
                    "license_number": "DL123456",
                    "woreda": 1,
                    "kebele": "05",
                    "register_by": {
                        "id": 1,
                        "username": "admin"
                    },
                    "register_place": {
                        "id": 1,
                        "name": "Main Office"
                    },
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
        summary="Retrieve a specific driver",
        description="Get detailed information about a specific driver by their ID.",
        tags=["Drivers"],
        responses={
            200: DriverSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this driver"},
            404: {"description": "Not Found - Driver with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "email": "abebe.kebede@example.com",
                    "phone_number": "+251911234567",
                    "license_number": "DL123456",
                    "woreda": 1,
                    "kebele": "05",
                    "register_by": {
                        "id": 1,
                        "username": "admin"
                    },
                    "register_place": {
                        "id": 1,
                        "name": "Main Office"
                    },
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
        summary="Update a driver",
        description="Update all fields of an existing driver. All fields are required.",
        tags=["Drivers"],
        request=DriverSerializer,
        responses={
            200: DriverSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this driver"},
            404: {"description": "Not Found - Driver with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "email": "abebe.updated@example.com",
                    "phone_number": "+251911234567",
                    "license_number": "DL123456",
                    "woreda": 1,
                    "kebele": "05"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a driver",
        description="Update specific fields of an existing driver. Only provided fields will be updated.",
        tags=["Drivers"],
        request=DriverSerializer,
        responses={
            200: DriverSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this driver"},
            404: {"description": "Not Found - Driver with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Phone Number",
                value={
                    "phone_number": "+251922334455"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Email",
                value={
                    "email": "new.email@example.com"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a driver",
        description="Permanently delete a driver from the database.",
        tags=["Drivers"],
        responses={
            204: {"description": "No Content - Driver successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this driver"},
            404: {"description": "Not Found - Driver with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        register_by = self.request.user
        print(register_by.current_station.id, "logged In user")
        serializer.save(
            register_by=self.request.user,
            register_place=register_by.current_station,
        )

    def get_permissions(self):
        return has_custom_permission(self, "driver")
