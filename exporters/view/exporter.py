from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from exporters.serializers import ExporterSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Exporter


class ExporterViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing exporters.
    
    Provides CRUD operations for Exporter entities with search functionality.
    Includes TIN number validation (must be exactly 10 digits).
    """
    
    queryset = Exporter.objects.all()
    serializer_class = ExporterSerializer
    permission_classes = [GroupPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "first_name",
        "last_name",
        "license_number",
        "mother_name",
        "middle_name",
        "tin_number",
        "unique_id",
        "phone_number",
    ]
    permission_required = "view_exporter"
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all exporters",
        description="Retrieve a paginated list of all exporters in the system. Supports search by name, license number, TIN number, unique ID, and phone number.",
        tags=["Exporters"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter exporters by name, license, TIN, or phone",
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
            200: ExporterSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view exporters"},
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
                            "first_name": "Chaltu",
                            "middle_name": "Bekele",
                            "last_name": "Tadesse",
                            "mother_name": "Almaz",
                            "gender": "Female",
                            "unique_id": "ORCa1b2c3d4",
                            "type": 1,
                            "woreda": 1,
                            "kebele": "03",
                            "phone_number": "+251911223344",
                            "tin_number": "1234567890",
                            "license_number": "EXP001",
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
        summary="Create a new exporter",
        description="Register a new exporter in the system. The license number and phone number must be unique. TIN number is optional but must be exactly 10 digits if provided. The exporter will be automatically associated with the current user and their workstation.",
        tags=["Exporters"],
        request=ExporterSerializer,
        responses={
            201: ExporterSerializer,
            400: {"description": "Bad Request - Invalid data provided, duplicate values, or TIN number validation failed"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create exporters"},
        },
        examples=[
            OpenApiExample(
                "Create Exporter Request - Full",
                value={
                    "first_name": "Chaltu",
                    "middle_name": "Bekele",
                    "last_name": "Tadesse",
                    "mother_name": "Almaz",
                    "gender": "Female",
                    "type": 1,
                    "woreda": 1,
                    "kebele": "03",
                    "phone_number": "+251911223344",
                    "tin_number": "1234567890",
                    "license_number": "EXP001"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Exporter Request - Minimal",
                value={
                    "first_name": "Chaltu",
                    "last_name": "Tadesse",
                    "gender": "Female",
                    "woreda": 1,
                    "phone_number": "+251911223344"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Exporter Response",
                value={
                    "id": 1,
                    "first_name": "Chaltu",
                    "middle_name": "Bekele",
                    "last_name": "Tadesse",
                    "mother_name": "Almaz",
                    "gender": "Female",
                    "unique_id": "ORCa1b2c3d4",
                    "type": 1,
                    "woreda": 1,
                    "kebele": "03",
                    "phone_number": "+251911223344",
                    "tin_number": "1234567890",
                    "license_number": "EXP001",
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
            OpenApiExample(
                "Validation Error - Invalid TIN",
                value={
                    "tin_number": ["TIN number must be exactly 10 digits."]
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific exporter",
        description="Get detailed information about a specific exporter by their ID.",
        tags=["Exporters"],
        responses={
            200: ExporterSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this exporter"},
            404: {"description": "Not Found - Exporter with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "first_name": "Chaltu",
                    "middle_name": "Bekele",
                    "last_name": "Tadesse",
                    "mother_name": "Almaz",
                    "gender": "Female",
                    "unique_id": "ORCa1b2c3d4",
                    "type": 1,
                    "woreda": 1,
                    "kebele": "03",
                    "phone_number": "+251911223344",
                    "tin_number": "1234567890",
                    "license_number": "EXP001",
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
        summary="Update an exporter",
        description="Update all fields of an existing exporter. All required fields must be provided. TIN number must be exactly 10 digits if provided.",
        tags=["Exporters"],
        request=ExporterSerializer,
        responses={
            200: ExporterSerializer,
            400: {"description": "Bad Request - Invalid data provided or TIN validation failed"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this exporter"},
            404: {"description": "Not Found - Exporter with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "first_name": "Chaltu",
                    "middle_name": "Bekele",
                    "last_name": "Tadesse",
                    "mother_name": "Almaz",
                    "gender": "Female",
                    "type": 1,
                    "woreda": 1,
                    "kebele": "03",
                    "phone_number": "+251911223344",
                    "tin_number": "9876543210",
                    "license_number": "EXP001"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update an exporter",
        description="Update specific fields of an existing exporter. Only provided fields will be updated. TIN number must be exactly 10 digits if provided.",
        tags=["Exporters"],
        request=ExporterSerializer,
        responses={
            200: ExporterSerializer,
            400: {"description": "Bad Request - Invalid data provided or TIN validation failed"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this exporter"},
            404: {"description": "Not Found - Exporter with the specified ID does not exist"},
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
                "Partial Update - TIN Number",
                value={
                    "tin_number": "9876543210"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Multiple Fields",
                value={
                    "middle_name": "Bekele",
                    "kebele": "05",
                    "type": 2
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data)
        except ValidationError as e:
            return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Delete an exporter",
        description="Permanently delete an exporter from the database.",
        tags=["Exporters"],
        responses={
            204: {"description": "No Content - Exporter successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this exporter"},
            404: {"description": "Not Found - Exporter with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            register_place=self.request.user.current_station,
        )

    def get_permissions(self):
        return has_custom_permission(self, "exporter")
