from django.core.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets

from declaracions.serializers import DeclaracionSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Declaracion


class OnGoingDeclaracionViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing ongoing declarations.
    
    Filters declarations to show only those with assigned drivers (ongoing journeys).
    """
    
    queryset = Declaracion.objects.filter(driver__isnull=False)
    serializer_class = DeclaracionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "declaracio_number",
        "truck__truck_model",
        "truck__plate_number",
        "driver__license_number",
        "commodity__name",
    ]
    permission_classes = [GroupPermission]
    permission_required = "view_declaracion"
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List ongoing declarations",
        description="""Retrieve ongoing declarations (those with assigned drivers).
        
        **Filtering:**
        - Only shows declarations where driver is not null
        
        **Search:**
        - Search by declaration number, truck details, driver license, or commodity
        """,
        tags=["Declarations - Declarations"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term",
                required=False,
            ),
        ],
        responses={
            200: DeclaracionSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create ongoing declaration",
        description="Create a new ongoing declaration with automatic field assignment.",
        tags=["Declarations - Declarations"],
        request=DeclaracionSerializer,
        responses={
            201: DeclaracionSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve ongoing declaration",
        description="Get details of a specific ongoing declaration.",
        tags=["Declarations - Declarations"],
        responses={
            200: DeclaracionSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update ongoing declaration",
        description="Update an ongoing declaration.",
        tags=["Declarations - Declarations"],
        request=DeclaracionSerializer,
        responses={
            200: DeclaracionSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update ongoing declaration",
        description="Partially update an ongoing declaration.",
        tags=["Declarations - Declarations"],
        request=DeclaracionSerializer,
        responses={
            200: DeclaracionSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete ongoing declaration",
        description="Delete an ongoing declaration.",
        tags=["Declarations - Declarations"],
        responses={
            204: {"description": "Deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            starting_point=self.request.user.current_station,
        )

    def raise_permission_error(self, message):
        raise PermissionDenied(message)

    def get_permissions(self):

        return has_custom_permission(self, "declaracion")
