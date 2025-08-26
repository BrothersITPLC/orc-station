# users/views.py

from django.contrib.auth.models import Group, Permission
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from helper.custom_pagination import CustomLimitOffsetPagination

from ..models import CustomUser
from ..serializers import GroupSerializer, PermissionSerializer, UserSerializer
from .permissions import GroupPermission


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomLimitOffsetPagination

    @action(detail=True, methods=["post"])
    def assign_permission(self, request, pk=None):
        group = self.get_object()
        permission = Permission.objects.get(id=request.data["permission_id"])
        group.permissions.add(permission)
        return Response({"status": "permission assigned"})

    @action(detail=True, methods=["post"])
    def remove_permission(self, request, pk=None):
        group = self.get_object()
        permission = Permission.objects.get(id=request.data["permission_id"])
        group.permissions.remove(permission)
        return Response({"status": "permission removed"})


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
