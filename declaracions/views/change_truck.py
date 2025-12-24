from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from declaracions.serializers import ChangeTruckSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import ChangeTruck, Checkin, Declaracion


class ChangeTruckViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing truck changes during a journey.
    
    Handles scenarios where a truck needs to be changed mid-journey,
    recording the change and updating the declaration.
    """
    
    serializer_class = ChangeTruckSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_changetruck"
    queryset = ChangeTruck.objects.all()
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):
        return has_custom_permission(self, "changetruck")

    @extend_schema(
        summary="List all truck changes",
        description="Retrieve a list of all truck change records.",
        tags=["Declarations - Truck Changes"],
        responses={
            200: ChangeTruckSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create truck change record",
        description="""Record a truck change for a declaration.
        
        **Process:**
        - Records the truck change
        - Updates the declaration with the new truck
        - Captures the station where change occurred
        - Records the latest check-in station
        
        **Automatic Fields:**
        - `created_by`: Set to current user
        - `station`: Set to current user's workstation
        - `latest_station`: Set to the station of the last check-in
        """,
        tags=["Declarations - Truck Changes"],
        request=ChangeTruckSerializer,
        responses={
            201: ChangeTruckSerializer,
            400: {"description": "Bad Request - Declaration not found or invalid data"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve truck change record",
        description="Get details of a specific truck change record.",
        tags=["Declarations - Truck Changes"],
        responses={
            200: ChangeTruckSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update truck change record",
        description="Update a truck change record.",
        tags=["Declarations - Truck Changes"],
        request=ChangeTruckSerializer,
        responses={
            200: ChangeTruckSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update truck change record",
        description="Partially update a truck change record.",
        tags=["Declarations - Truck Changes"],
        request=ChangeTruckSerializer,
        responses={
            200: ChangeTruckSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete truck change record",
        description="Delete a truck change record.",
        tags=["Declarations - Truck Changes"],
        responses={
            204: {"description": "Deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        station = user
        station = user.current_station
        declaracion = serializer.validated_data.get("declaracion")

        last_checkin = (
            Checkin.objects.filter(declaracion=declaracion)
            .order_by("-checkin_time")
            .first()
        )
        last_station = last_checkin.station if last_checkin else None
        print(serializer.validated_data, "   : here is the ID")
        declaracion = Declaracion.objects.filter(id=declaracion.id).first()

        if declaracion is None:
            raise ValueError("Journey not found with the provided ID.")
        declaracion.truck = serializer.validated_data.get("new_truck")

        serializer.save(created_by=user, station=station, latest_station=last_station)
        declaracion.save()
