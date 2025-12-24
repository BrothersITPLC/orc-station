from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from trucks.serializers import TruckOwnerSerializer

from ..models import TruckOwner


class TruckOwnerViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing truck owners.
    
    Provides CRUD operations for TruckOwner entities with search functionality.
    """
    
    queryset = TruckOwner.objects.all()
    serializer_class = TruckOwnerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name"]

    @extend_schema(
        summary="List all truck owners",
        description="Retrieve a list of all registered truck owners. Supports search by first name and last name.",
        tags=["Trucks - Owners"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter truck owners by name",
                required=False,
            ),
        ],
        responses={
            200: TruckOwnerSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "first_name": "Tadesse",
                        "last_name": "Bekele",
                        "woreda": 1,
                        "kebele": "02",
                        "phone_number": "+251911223344",
                        "home_number": "0114567890",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "first_name": "Almaz",
                        "last_name": "Tesfaye",
                        "woreda": 2,
                        "kebele": "05",
                        "phone_number": "+251922334455",
                        "home_number": None,
                        "created_at": "2024-01-15T11:00:00Z",
                        "updated_at": "2024-01-15T11:00:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific truck owner",
        description="Retrieve details of a specific truck owner by their ID.",
        tags=["Trucks - Owners"],
        responses={
            200: TruckOwnerSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            404: {"description": "Not Found - Truck owner with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "first_name": "Tadesse",
                    "last_name": "Bekele",
                    "woreda": 1,
                    "kebele": "02",
                    "phone_number": "+251911223344",
                    "home_number": "0114567890",
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
        summary="Create a new truck owner",
        description="Register a new truck owner. Phone number must be unique.",
        tags=["Trucks - Owners"],
        request=TruckOwnerSerializer,
        responses={
            201: TruckOwnerSerializer,
            400: {"description": "Bad Request - Invalid data provided or duplicate phone number"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
        },
        examples=[
            OpenApiExample(
                "Create Truck Owner Request",
                value={
                    "first_name": "Tadesse",
                    "last_name": "Bekele",
                    "woreda": 1,
                    "kebele": "02",
                    "phone_number": "+251911223344",
                    "home_number": "0114567890"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Truck Owner Response",
                value={
                    "id": 1,
                    "first_name": "Tadesse",
                    "last_name": "Bekele",
                    "woreda": 1,
                    "kebele": "02",
                    "phone_number": "+251911223344",
                    "home_number": "0114567890",
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
        summary="Update a truck owner",
        description="Update all fields of an existing truck owner. All fields are required.",
        tags=["Trucks - Owners"],
        request=TruckOwnerSerializer,
        responses={
            200: TruckOwnerSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            404: {"description": "Not Found - Truck owner with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "first_name": "Tadesse",
                    "last_name": "Bekele",
                    "woreda": 1,
                    "kebele": "03",
                    "phone_number": "+251911223344",
                    "home_number": "0114567890"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a truck owner",
        description="Update specific fields of an existing truck owner. Only provided fields will be updated.",
        tags=["Trucks - Owners"],
        request=TruckOwnerSerializer,
        responses={
            200: TruckOwnerSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            404: {"description": "Not Found - Truck owner with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Phone Number",
                value={
                    "phone_number": "+251933445566"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a truck owner",
        description="Permanently delete a truck owner from the database. This will fail if there are trucks associated with this owner.",
        tags=["Trucks - Owners"],
        responses={
            204: {"description": "No Content - Truck owner successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            404: {"description": "Not Found - Truck owner with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
