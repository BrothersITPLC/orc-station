from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from helper.custom_pagination import CustomLimitOffsetPagination

from .models import Truck, TruckOwner
from .serializers import TruckOwnerSerializer, TruckSerializer


@method_decorator(csrf_exempt, name="dispatch")
class TruckOwnerViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing truck owners.
    """

    queryset = TruckOwner.objects.all()
    serializer_class = TruckOwnerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name"]

    @swagger_auto_schema(
        operation_summary="List all truck owners",
        operation_description="Retrieve a list of all registered truck owners.",
        tags=["TruckOwner"],
        responses={200: TruckOwnerSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific truck owner",
        operation_description="Retrieve details of a specific truck owner by their ID.",
        tags=["TruckOwner"],
        responses={200: TruckOwnerSerializer()},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new truck owner",
        operation_description="Register a new truck owner.",
        tags=["TruckOwner"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class TruckFetchViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    pagination_class = CustomLimitOffsetPagination
    serializer_class = TruckSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["truck_model", "plate_number"]


class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all()
    permission_classes = [HasAPIKey, AllowAny]
    serializer_class = TruckSerializer
    lookup_field = "truck_id"

    @swagger_auto_schema(
        operation_description="Create a new Truck",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "owner",
                "plate_number",
                "country_of_origin",
                "truck_model",
                "year_of_manufacture",
                "chassis_number",
                "engine_number",
                "color",
                "oil_type",
                "horse_power",
                "engine_displacement",
                "loading_capacity_kg",
                "truck_image",
                "truck_plate_image",
            ],
            properties={
                # Define the properties as before
            },
        ),
        responses={
            status.HTTP_201_CREATED: "Truck created successfully.",
            status.HTTP_400_BAD_REQUEST: "Failed to create Truck. Invalid data provided.",
            status.HTTP_409_CONFLICT: "Truck with this plate number already exists.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "An unexpected error occurred.",
        },
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

        # Check if the plate number already exists
        plate_number = data.get("plate_number")
        if Truck.objects.filter(plate_number=plate_number).exists():
            return Response(
                {"message": "Truck with this plate number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            # Check if the owner exists or create a new owner
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

            # Add the owner ID (not the object) to the truck data
            data["owner"] = owner.id
            data["truck_image"] = request.FILES.get("truck_image")

            # Serialize and validate the truck data
            serializer = self.get_serializer(data=data)
            print("data")
            serializer.is_valid(raise_exception=True)

            # Save the truck data
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

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        plate_number = request.data.get("plate_number", instance.plate_number)

        # Check if another truck with the same plate number exists
        if (
            Truck.objects.filter(plate_number=plate_number)
            .exclude(id=instance.id)
            .exists()
        ):
            return Response(
                {"message": "Truck with this plate number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        # Check if owner details are provided for update
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

                # Add the owner ID (not the object) to the request data
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

        # Serialize and validate the truck data for update
        request.data.pop("truck_id")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Truck updated successfully."}, status=status.HTTP_200_OK
        )
