from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from declaracions.serializers import CommoditySerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from ..models import Commodity


class CommodityViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing commodities.

    Provides CRUD operations for Commodity entities with permission-based access control.
    """

    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_commodity"
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:
            self.permission_required = None
            return [permission() for permission in self.permission_classes]

        return has_custom_permission(self, "commodity")

    @extend_schema(
        summary="List all commodities",
        description="Retrieve a paginated list of all commodities in the system.",
        tags=["Declarations - Commodities"],
        responses={
            200: CommoditySerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new commodity",
        description="Create a new commodity. The created_by field is automatically set to the current user.",
        tags=["Declarations - Commodities"],
        request=CommoditySerializer,
        responses={
            201: CommoditySerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific commodity",
        description="Get detailed information about a specific commodity by its ID.",
        tags=["Declarations - Commodities"],
        responses={
            200: CommoditySerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a commodity",
        description="Update all fields of an existing commodity.",
        tags=["Declarations - Commodities"],
        request=CommoditySerializer,
        responses={
            200: CommoditySerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a commodity",
        description="Update specific fields of an existing commodity.",
        tags=["Declarations - Commodities"],
        request=CommoditySerializer,
        responses={
            200: CommoditySerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a commodity",
        description="Permanently delete a commodity from the database.",
        tags=["Declarations - Commodities"],
        responses={
            204: {"description": "Commodity successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
