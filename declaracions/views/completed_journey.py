from django.core.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets

from declaracions.serializers import DeclaracionSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from users.models import CustomUser
from users.views.permissions import GroupPermission

from ..models import Declaracion


class CompletedJourney(viewsets.ReadOnlyModelViewSet):
    """
    A read-only viewset for viewing completed declarations.
    
    Filters declarations to show only completed journeys at the user's workstation.
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
        summary="List completed declarations",
        description="""Retrieve completed declarations filtered by the user's workstation.
        
        **Filtering:**
        - Only shows declarations with status "COMPLETED"
        - Only shows declarations with check-ins at user's current station
        
        **Search:**
        - Search by declaration number, truck details, driver license, or commodity
        
        **Note:** This is a read-only viewset (list and retrieve only).
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
        summary="Retrieve completed declaration",
        description="Get detailed information about a specific completed declaration.",
        tags=["Declarations - Declarations"],
        responses={
            200: DeclaracionSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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

            return Declaracion.objects.filter(
                checkins__station=user.current_station, status="COMPLETED"
            )

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
