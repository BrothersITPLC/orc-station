from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from helper.custom_pagination import CustomLimitOffsetPagination
from trucks.serializers import TruckSerializer

from ..models import Truck, TruckOwner


class TruckFetchViewSet(viewsets.ModelViewSet):
    """
    A viewset for fetching and searching trucks.
    
    Provides read operations for Truck entities with search functionality.
    """
    
    queryset = Truck.objects.all()
    pagination_class = CustomLimitOffsetPagination
    serializer_class = TruckSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["truck_model", "plate_number"]

    @extend_schema(
        summary="List all trucks",
        description="Retrieve a paginated list of all trucks in the system. Supports search by truck model and plate number.",
        tags=["Trucks"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter trucks by model or plate number",
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
            200: TruckSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific truck",
        description="Get detailed information about a specific truck by its ID.",
        tags=["Trucks"],
        responses={
            200: TruckSerializer,
            404: {"description": "Not Found - Truck with the specified ID does not exist"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class TruckViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing trucks via API key authentication.
    
    Provides CRUD operations for Truck entities with automatic owner creation/lookup.
    This viewset is designed for external integrations using API keys.
    """
    
    queryset = Truck.objects.all()
    permission_classes = [HasAPIKey, AllowAny]
    serializer_class = TruckSerializer
    lookup_field = "truck_id"

    @extend_schema(
        summary="Create a new truck",
        description="""Create a new truck with owner information. The system will automatically create or find the truck owner based on the provided information.
        
        **Owner Information:** Provided as nested fields with 'owner.' prefix
        - If an owner with the same name and phone exists, they will be reused
        - Otherwise, a new owner will be created
        
        **Validation:**
        - Plate number must be unique
        - Chassis number must be unique
        - Engine number must be unique
        - Year of manufacture must be between 1886 and 2024
        """,
        tags=["Trucks - External API"],
        request=TruckSerializer,
        responses={
            201: {"description": "Truck created successfully", "type": "object", "properties": {"message": {"type": "string"}}},
            400: {"description": "Failed to create Truck. Invalid data provided."},
            409: {"description": "Truck with this plate number already exists."},
            500: {"description": "An unexpected error occurred."},
        },
        examples=[
            OpenApiExample(
                "Create Truck Request",
                description="Note: Owner information is provided with 'owner.' prefix in form data",
                value={
                    "owner.first_name": "Tadesse",
                    "owner.last_name": "Bekele",
                    "owner.phone_number": "+251911223344",
                    "owner.home_number": "0114567890",
                    "plate_number": "AA-12345",
                    "truck_brand": "Mercedes",
                    "country_of_origin": "Germany",
                    "truck_model": "Actros",
                    "year_of_manufacture": 2020,
                    "chassis_number": "WDB9634321L123456",
                    "engine_number": "OM47012345678",
                    "color": "White",
                    "oil_type": "Diesel",
                    "horse_power": 450,
                    "truck_weight": 18000.0,
                    "engine_displacement": 12800,
                    "truck_status": "Active",
                    "loading_capacity_kg": 25000,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Success Response",
                value={"message": "Truck created successfully."},
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Duplicate Plate Error",
                value={"message": "Truck with this plate number already exists."},
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        owner_data = {
            "first_name": request.data.get("owner.first_name", [None])[0],
            "last_name": request.data.get("owner.last_name", [None])[0],
            "phone_number": request.data.get("owner.phone_number", [None])[0],
            "home_number": request.data.get("owner.home_number", [""])[0],
        }
        data = request.data.copy()
        print(owner_data)
        if not owner_data:
            return Response(
                {"message": "Owner information is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plate_number = data.get("plate_number")
        if Truck.objects.filter(plate_number=plate_number).exists():
            return Response(
                {"message": "Truck with this plate number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            owner, created = TruckOwner.objects.get_or_create(
                first_name=owner_data["first_name"],
                last_name=owner_data["last_name"],
                woreda_id=owner_data.get("woreda"),
                kebele=owner_data.get("kebele"),
                phone_number=owner_data["phone_number"],
                defaults={
                    "home_number": owner_data.get("home_number", ""),
                },
            )

            data["owner"] = owner.id
            data["truck_image"] = request.FILES.get("truck_image")

            serializer = self.get_serializer(data=data)
            print("data")
            serializer.is_valid(raise_exception=True)

            serializer.save()

            return Response(
                {"message": "Truck created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {
                    "message": "Failed to create Truck. Invalid data provided.",
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError as e:
            return Response(
                {
                    "message": "Truck with this plate number already exists.",
                    "errors": str(e),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            return Response(
                {"message": "An unexpected error occurred.", "errors": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Retrieve a truck by truck_id",
        description="Get detailed information about a specific truck by its truck_id.",
        tags=["Trucks - External API"],
        responses={
            200: TruckSerializer,
            404: {"description": "Not Found - Truck with the specified truck_id does not exist"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a truck",
        description="""Update an existing truck. Can update both truck information and owner information.
        
        **Owner Update:**
        - If owner information is provided, the system will create or find the owner
        - The truck will be reassigned to the new/found owner
        
        **Validation:**
        - Plate number must remain unique (or unchanged)
        - Cannot modify truck_id
        """,
        tags=["Trucks - External API"],
        request=TruckSerializer,
        responses={
            200: {"description": "Truck updated successfully", "type": "object", "properties": {"message": {"type": "string"}}},
            400: {"description": "Invalid data provided"},
            409: {"description": "Truck with this plate number already exists"},
            500: {"description": "An unexpected error occurred"},
        },
        examples=[
            OpenApiExample(
                "Update Truck Request",
                value={
                    "plate_number": "AA-12345",
                    "truck_status": "Inactive",
                    "owner": {
                        "first_name": "Tadesse",
                        "last_name": "Bekele",
                        "phone_number": "+251911223344"
                    }
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Success Response",
                value={"message": "Truck updated successfully."},
                response_only=True,
            ),
        ],
    )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        plate_number = request.data.get("plate_number", instance.plate_number)

        if (
            Truck.objects.filter(plate_number=plate_number)
            .exclude(id=instance.id)
            .exists()
        ):
            return Response(
                {"message": "Truck with this plate number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        owner_data = request.data.get("owner")
        if owner_data:
            try:
                owner, created = TruckOwner.objects.get_or_create(
                    first_name=owner_data["first_name"],
                    last_name=owner_data["last_name"],
                    woreda_id=owner_data.get("woreda"),
                    kebele=owner_data.get("kebele"),
                    phone_number=owner_data["phone_number"],
                    defaults={
                        "home_number": owner_data.get("home_number", ""),
                    },
                )

                request.data["owner"] = owner.id
            except ValidationError as e:
                return Response(
                    {"message": "Invalid owner data provided.", "errors": e.detail},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                return Response(
                    {
                        "message": "An unexpected error occurred while updating the owner.",
                        "errors": str(e),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        request.data.pop("truck_id")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Truck updated successfully."}, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Partially update a truck",
        description="Update specific fields of an existing truck. Only provided fields will be updated.",
        tags=["Trucks - External API"],
        request=TruckSerializer,
        responses={
            200: TruckSerializer,
            400: {"description": "Invalid data provided"},
            404: {"description": "Truck not found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a truck",
        description="Permanently delete a truck from the database.",
        tags=["Trucks - External API"],
        responses={
            204: {"description": "Truck successfully deleted"},
            404: {"description": "Truck not found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="List all trucks",
        description="Retrieve a list of all trucks accessible via API key.",
        tags=["Trucks - External API"],
        responses={
            200: TruckSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

