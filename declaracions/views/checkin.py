from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets

from declaracions.serializers import CheckinSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Checkin


class CheckinViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing check-ins.
    
    Provides CRUD operations for Checkin entities with permission-based access control.
    Check-ins are ordered by check-in time in descending order.
    """
    
    queryset = Checkin.objects.order_by("-checkin_time")
    serializer_class = CheckinSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_checkin"
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):
        return has_custom_permission(self, "checkin")

    @extend_schema(
        summary="List all check-ins",
        description="Retrieve a paginated list of all check-ins, ordered by check-in time (most recent first).",
        tags=["Declarations - Check-ins"],
        responses={
            200: CheckinSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new check-in",
        description="Create a new check-in record for a declaration at a workstation.",
        tags=["Declarations - Check-ins"],
        request=CheckinSerializer,
        responses={
            201: CheckinSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific check-in",
        description="Get detailed information about a specific check-in by its ID.",
        tags=["Declarations - Check-ins"],
        responses={
            200: CheckinSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a check-in",
        description="Update all fields of an existing check-in.",
        tags=["Declarations - Check-ins"],
        request=CheckinSerializer,
        responses={
            200: CheckinSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a check-in",
        description="Update specific fields of an existing check-in.",
        tags=["Declarations - Check-ins"],
        request=CheckinSerializer,
        responses={
            200: CheckinSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a check-in",
        description="Permanently delete a check-in from the database.",
        tags=["Declarations - Check-ins"],
        responses={
            204: {"description": "Check-in successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_current_checkin(self, declaracion_id, station_id):
        """
        Fetches the current check-in instance based on declaracion and station.
        """
        current_checkin = Checkin.objects.filter(
            declaracion_id=declaracion_id, station_id=station_id
        ).first()
        return current_checkin
