from django.core.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets

from declaracions.serializers import DeclaracionSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from users.models import CustomUser
from users.views.permissions import GroupPermission

from ..models import Declaracion


class DeclaracionViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing declarations.
    
    Provides CRUD operations for Declaracion entities with permission-based access control.
    Automatically filters declarations based on the current user's workstation.
    """
    
    queryset = Declaracion.objects.all()
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
        summary="List all declarations",
        description="""Retrieve a paginated list of declarations filtered by the current user's workstation.
        
        **Filtering:**
        - Only shows declarations that have check-ins at the user's current station
        
        **Search:**
        - Search by declaration number, truck model, plate number, driver license, or commodity name
        """,
        tags=["Declarations - Declarations"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term for filtering declarations",
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
        summary="Create a new declaration",
        description="""Create a new declaration. 
        
        **Automatic Fields:**
        - `register_by`: Set to current user
        - `starting_point`: Set to current user's workstation
        """,
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
        summary="Retrieve a specific declaration",
        description="Get detailed information about a specific declaration by its ID.",
        tags=["Declarations - Declarations"],
        responses={
            200: DeclaracionSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a declaration",
        description="Update all fields of an existing declaration.",
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
        summary="Partially update a declaration",
        description="Update specific fields of an existing declaration.",
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
        summary="Delete a declaration",
        description="Permanently delete a declaration from the database.",
        tags=["Declarations - Declarations"],
        responses={
            204: {"description": "Declaration successfully deleted"},
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

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Declaracion.objects.none()

        try:
            user = CustomUser.objects.filter(
                username=self.request.user.username
            ).first()

            if user is None:
                self.raise_permission_error("User not found.")
                declaracions = Declaracion.objects.filter(
                    checkins__station=user.current_station
                )

            return Declaracion.objects.filter(checkins__station=user.current_station)

        except PermissionDenied as e:
            self.raise_permission_error(str(e))
        except Exception as e:
            self.raise_permission_error(str(e))

    def raise_permission_error(self, message):
        raise PermissionDenied(message)

    def get_permissions(self):
        if self.action == "create":
            self.permission_required = "add_declaracion"
        elif self.action == "list" or self.action == "retrieve":
            self.permission_required = "view_declaracion"
        elif self.action == "update" or self.action == "partial":
            self.permission_required = "change_declaracion"
        elif self.action == "destroy":
            self.permission_required = "delete_declaracion"

        return [permission() for permission in self.permission_classes]
