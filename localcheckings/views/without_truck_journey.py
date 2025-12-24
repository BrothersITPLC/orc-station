from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from localcheckings.serializers import JourneyWithoutTruckSerializer

from ..models import JourneyWithoutTruck


class WithoutTruckJourneyViewset(viewsets.ModelViewSet):
    """
    A viewset for managing journeys without trucks.
    
    Handles CRUD operations for local journeys where goods are transported
    without truck registration (e.g., hand-carried goods, small shipments).
    """
    
    serializer_class = JourneyWithoutTruckSerializer
    queryset = JourneyWithoutTruck.objects.all()

    @extend_schema(
        summary="List all journeys without trucks",
        description="Retrieve a list of all local journeys for goods transported without trucks.",
        tags=["Local Checkings - Journeys"],
        responses={
            200: JourneyWithoutTruckSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a journey without truck",
        description="Create a new local journey for goods without truck registration.",
        tags=["Local Checkings - Journeys"],
        request=JourneyWithoutTruckSerializer,
        responses={
            201: JourneyWithoutTruckSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific journey",
        description="Get detailed information about a specific journey without truck.",
        tags=["Local Checkings - Journeys"],
        responses={
            200: JourneyWithoutTruckSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a journey",
        description="Update all fields of an existing journey without truck.",
        tags=["Local Checkings - Journeys"],
        request=JourneyWithoutTruckSerializer,
        responses={
            200: JourneyWithoutTruckSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a journey",
        description="Update specific fields of an existing journey without truck.",
        tags=["Local Checkings - Journeys"],
        request=JourneyWithoutTruckSerializer,
        responses={
            200: JourneyWithoutTruckSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a journey",
        description="Permanently delete a journey without truck from the database.",
        tags=["Local Checkings - Journeys"],
        responses={
            204: {"description": "Journey successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
