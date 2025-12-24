from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from tax.serializers import TaxSerializer
from users.views.permissions import GroupPermission

from ..models import Tax


class TaxViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing tax configurations.

    Provides CRUD operations for Tax entities. Each tax is uniquely identified by
    the combination of station, tax payer type, and commodity.
    """

    queryset = Tax.objects.all()
    serializer_class = TaxSerializer
    permission_classes = [IsAuthenticated, GroupPermission]
    perermission_required = "view_tax"
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all taxes",
        description="Retrieve a paginated list of all tax configurations in the system. Each tax defines a percentage rate for a specific combination of workstation, tax payer type, and commodity.",
        tags=["Tax"],
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
            200: TaxSerializer(many=True),
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view taxes"
            },
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
                            "name": "Coffee Export Tax",
                            "station": 1,
                            "tax_payer_type": 1,
                            "commodity": 1,
                            "percentage": "5.50",
                            "created_by": 1,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                        },
                        {
                            "id": 2,
                            "name": "Sesame Export Tax",
                            "station": 1,
                            "tax_payer_type": 2,
                            "commodity": 2,
                            "percentage": "3.25",
                            "created_by": 1,
                            "created_at": "2024-01-15T11:00:00Z",
                            "updated_at": "2024-01-15T11:00:00Z",
                        },
                    ],
                },
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new tax configuration",
        description="Add a new tax configuration to the database. The combination of station, tax payer type, and commodity must be unique. Percentage should be between 0.00 and 100.00.",
        tags=["Tax"],
        request=TaxSerializer,
        responses={
            201: TaxSerializer,
            400: {
                "description": "Bad Request - Invalid data provided or duplicate combination"
            },
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to create taxes"
            },
        },
        examples=[
            OpenApiExample(
                "Create Tax Request",
                value={
                    "name": "Coffee Export Tax",
                    "station": 1,
                    "tax_payer_type": 1,
                    "commodity": 1,
                    "percentage": "5.50",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Tax Response",
                value={
                    "id": 1,
                    "name": "Coffee Export Tax",
                    "station": 1,
                    "tax_payer_type": 1,
                    "commodity": 1,
                    "percentage": "5.50",
                    "created_by": 1,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Validation Error - Duplicate",
                value={
                    "non_field_errors": [
                        "The fields station, tax_payer_type, commodity must make a unique set."
                    ]
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific tax configuration",
        description="Get detailed information about a specific tax configuration by its ID.",
        tags=["Tax"],
        responses={
            200: TaxSerializer,
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to view this tax"
            },
            404: {
                "description": "Not Found - Tax with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "name": "Coffee Export Tax",
                    "station": 1,
                    "tax_payer_type": 1,
                    "commodity": 1,
                    "percentage": "5.50",
                    "created_by": 1,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a tax configuration",
        description="Update all fields of an existing tax configuration. All fields are required. The combination of station, tax payer type, and commodity must remain unique.",
        tags=["Tax"],
        request=TaxSerializer,
        responses={
            200: TaxSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this tax"
            },
            404: {
                "description": "Not Found - Tax with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "name": "Coffee Export Tax - Updated",
                    "station": 1,
                    "tax_payer_type": 1,
                    "commodity": 1,
                    "percentage": "6.00",
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a tax configuration",
        description="Update specific fields of an existing tax configuration. Only provided fields will be updated.",
        tags=["Tax"],
        request=TaxSerializer,
        responses={
            200: TaxSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to update this tax"
            },
            404: {
                "description": "Not Found - Tax with the specified ID does not exist"
            },
        },
        examples=[
            OpenApiExample(
                "Partial Update - Percentage Only",
                value={"percentage": "7.25"},
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Name and Percentage",
                value={"name": "Updated Tax Name", "percentage": "4.50"},
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a tax configuration",
        description="Permanently delete a tax configuration from the database.",
        tags=["Tax"],
        responses={
            204: {"description": "No Content - Tax successfully deleted"},
            401: {
                "description": "Unauthorized - Authentication credentials were not provided or are invalid"
            },
            403: {
                "description": "Forbidden - You do not have permission to delete this tax"
            },
            404: {
                "description": "Not Found - Tax with the specified ID does not exist"
            },
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_required = None
            return [permission() for permission in self.permission_classes]

        return has_custom_permission(self, "tax")

    def perform_create(self, serializer):

        serializer.save(created_by=self.request.user)
