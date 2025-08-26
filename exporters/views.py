from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from .models import Exporter, TaxPayerType
from .serializers import ExporterSerializer, TaxPayerTypeSerializer


class ExporterViewSet(viewsets.ModelViewSet):
    queryset = Exporter.objects.all()
    serializer_class = ExporterSerializer
    permission_classes = [GroupPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "first_name",
        "last_name",
        "license_number",
        "mother_name",
        "middle_name",
        "tin_number",
        "unique_id",
    ]
    permission_required = "view_exporter"
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            register_place=self.request.user.current_station,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data)
        except ValidationError as e:
            return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_permissions(self):
        return has_custom_permission(self, "exporter")


class TaxPayerTypeViewSets(viewsets.ModelViewSet):
    queryset = TaxPayerType.objects.all()
    serializer_class = TaxPayerTypeSerializer
    permission_classes = [GroupPermission]
    pagination_class = CustomLimitOffsetPagination
    permission_required = "view_taxpayertype"

    def get_permissions(self):
        return has_custom_permission(self, "taxpayertype")
