from rest_framework import filters, viewsets

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from .models import Driver
from .serializers import DriverSerializer


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_driver"
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "license_number",
    ]
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        register_by = self.request.user
        print(register_by.current_station.id, "logged In user")
        serializer.save(
            register_by=self.request.user,
            register_place=register_by.current_station,
        )

    def get_permissions(self):
        return has_custom_permission(self, "driver")
