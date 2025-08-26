from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from .models import Tax
from .serializers import TaxSerializer

# Create your views here.


class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer
    permission_classes = [IsAuthenticated, GroupPermission]
    perermission_required = "view_tax"
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):
        return has_custom_permission(self, "tax")

    def perform_create(self, serializer):

        serializer.save(created_by=self.request.user)
