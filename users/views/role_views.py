# users/views.py

from django.contrib.auth.models import Group, Permission
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from helper.custom_pagination import CustomLimitOffsetPagination
from users.serializers import GroupSerializer, PermissionSerializer, UserSerializer

from ..models import CustomUser
from .permissions import GroupPermission


class GroupViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing user groups/roles.
    
    Provides CRUD operations for Group entities with custom actions
    for assigning and removing permissions.
    """
    
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List all groups",
        description="Retrieve a paginated list of all user groups/roles in the system.",
        tags=["Users - Roles & Permissions"],
        responses={
            200: GroupSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new group",
        description="Create a new user group/role.",
        tags=["Users - Roles & Permissions"],
        request=GroupSerializer,
        responses={
            201: GroupSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific group",
        description="Get detailed information about a specific group by its ID.",
        tags=["Users - Roles & Permissions"],
        responses={
            200: GroupSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a group",
        description="Update all fields of an existing group.",
        tags=["Users - Roles & Permissions"],
        request=GroupSerializer,
        responses={
            200: GroupSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a group",
        description="Update specific fields of an existing group.",
        tags=["Users - Roles & Permissions"],
        request=GroupSerializer,
        responses={
            200: GroupSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a group",
        description="Permanently delete a group from the database.",
        tags=["Users - Roles & Permissions"],
        responses={
            204: {"description": "Group successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Assign permission to group",
        description="Add a permission to a group/role.",
        tags=["Users - Roles & Permissions"],
        request={
            "type": "object",
            "properties": {
                "permission_id": {"type": "integer"}
            },
            "required": ["permission_id"]
        },
        responses={
            200: {"description": "Permission assigned", "type": "object", "properties": {"status": {"type": "string"}}},
            400: {"description": "Bad Request"},
            404: {"description": "Group or permission not found"},
        },
        examples=[
            OpenApiExample(
                "Assign Permission Request",
                value={"permission_id": 5},
                request_only=True,
            ),
            OpenApiExample(
                "Assign Permission Response",
                value={"status": "permission assigned"},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def assign_permission(self, request, pk=None):
        group = self.get_object()
        permission = Permission.objects.get(id=request.data["permission_id"])
        group.permissions.add(permission)
        return Response({"status": "permission assigned"})

    @extend_schema(
        summary="Remove permission from group",
        description="Remove a permission from a group/role.",
        tags=["Users - Roles & Permissions"],
        request={
            "type": "object",
            "properties": {
                "permission_id": {"type": "integer"}
            },
            "required": ["permission_id"]
        },
        responses={
            200: {"description": "Permission removed", "type": "object", "properties": {"status": {"type": "string"}}},
            400: {"description": "Bad Request"},
            404: {"description": "Group or permission not found"},
        },
        examples=[
            OpenApiExample(
                "Remove Permission Request",
                value={"permission_id": 5},
                request_only=True,
            ),
            OpenApiExample(
                "Remove Permission Response",
                value={"status": "permission removed"},
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def remove_permission(self, request, pk=None):
        group = self.get_object()
        permission = Permission.objects.get(id=request.data["permission_id"])
        group.permissions.remove(permission)
        return Response({"status": "permission removed"})


class PermissionViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing system permissions.
    
    Provides CRUD operations for Permission entities.
    """
    
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

    @extend_schema(
        summary="List all permissions",
        description="Retrieve a list of all system permissions.",
        tags=["Users - Roles & Permissions"],
        responses={
            200: PermissionSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific permission",
        description="Get detailed information about a specific permission by its ID.",
        tags=["Users - Roles & Permissions"],
        responses={
            200: PermissionSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new permission",
        description="Create a new system permission.",
        tags=["Users - Roles & Permissions"],
        request=PermissionSerializer,
        responses={
            201: PermissionSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update a permission",
        description="Update all fields of an existing permission.",
        tags=["Users - Roles & Permissions"],
        request=PermissionSerializer,
        responses={
            200: PermissionSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a permission",
        description="Update specific fields of an existing permission.",
        tags=["Users - Roles & Permissions"],
        request=PermissionSerializer,
        responses={
            200: PermissionSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a permission",
        description="Permanently delete a permission from the database.",
        tags=["Users - Roles & Permissions"],
        responses={
            204: {"description": "Permission successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
