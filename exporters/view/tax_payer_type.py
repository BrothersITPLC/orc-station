from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import viewsets

from exporters.serializers import TaxPayerTypeSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import TaxPayerType


class TaxPayerTypeViewSets(viewsets.ModelViewSet):
    """
    A viewset for managing tax payer types.
    
    Provides CRUD operations for TaxPayerType entities.
    """
    
    queryset = TaxPayerType.objects.all()
    serializer_class = TaxPayerTypeSerializer
    permission_classes = [GroupPermission]
    pagination_class = CustomLimitOffsetPagination
    permission_required = "view_taxpayertype"

    @extend_schema(
        summary="List all tax payer types",
        description="Retrieve a paginated list of all tax payer types in the system.",
        tags=["Exporters - Tax Payer Types"],
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
            200: TaxPayerTypeSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view tax payer types"},
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
                            "name": "Individual",
                            "description": "Individual tax payer",
                            "created_by": 1,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z"
                        },
                        {
                            "id": 2,
                            "name": "Corporate",
                            "description": "Corporate tax payer",
                            "created_by": 1,
                            "created_at": "2024-01-15T11:00:00Z",
                            "updated_at": "2024-01-15T11:00:00Z"
                        },
                        {
                            "id": 3,
                            "name": "Partnership",
                            "description": "Partnership tax payer",
                            "created_by": 1,
                            "created_at": "2024-01-15T11:30:00Z",
                            "updated_at": "2024-01-15T11:30:00Z"
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
        summary="Create a new tax payer type",
        description="Add a new tax payer type to the database. The name must be unique.",
        tags=["Exporters - Tax Payer Types"],
        request=TaxPayerTypeSerializer,
        responses={
            201: TaxPayerTypeSerializer,
            400: {"description": "Bad Request - Invalid data provided or duplicate name"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create tax payer types"},
        },
        examples=[
            OpenApiExample(
                "Create Tax Payer Type Request",
                value={
                    "name": "Individual",
                    "description": "Individual tax payer"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Tax Payer Type Response",
                value={
                    "id": 1,
                    "name": "Individual",
                    "description": "Individual tax payer",
                    "created_by": 1,
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
        summary="Retrieve a specific tax payer type",
        description="Get detailed information about a specific tax payer type by its ID.",
        tags=["Exporters - Tax Payer Types"],
        responses={
            200: TaxPayerTypeSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this tax payer type"},
            404: {"description": "Not Found - Tax payer type with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Individual",
                    "description": "Individual tax payer",
                    "created_by": 1,
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
        summary="Update a tax payer type",
        description="Update all fields of an existing tax payer type. All fields are required.",
        tags=["Exporters - Tax Payer Types"],
        request=TaxPayerTypeSerializer,
        responses={
            200: TaxPayerTypeSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this tax payer type"},
            404: {"description": "Not Found - Tax payer type with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "name": "Individual",
                    "description": "Updated description for individual tax payer"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a tax payer type",
        description="Update specific fields of an existing tax payer type. Only provided fields will be updated.",
        tags=["Exporters - Tax Payer Types"],
        request=TaxPayerTypeSerializer,
        responses={
            200: TaxPayerTypeSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this tax payer type"},
            404: {"description": "Not Found - Tax payer type with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Description Only",
                value={
                    "description": "Updated description"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Name Only",
                value={
                    "name": "Corporate Entity"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a tax payer type",
        description="Permanently delete a tax payer type from the database. This will fail if there are exporters using this type.",
        tags=["Exporters - Tax Payer Types"],
        responses={
            204: {"description": "No Content - Tax payer type successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this tax payer type"},
            404: {"description": "Not Found - Tax payer type with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        return has_custom_permission(self, "taxpayertype")
