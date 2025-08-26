from django.contrib.auth.models import Group, Permission
from rest_framework import permissions


class GroupPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # If the user is not authenticated or does not belong to any group, deny access

        if not request.user.is_authenticated or not request.user.role:
            return False

        # Get the required permission from the view
        required_permission = view.permission_required

        # Check if any of the user's groups have the required permission
        try:
            group = Group.objects.get(name=request.user.role)
            # user_permissions = request.user.get_user_permissions()
            # print(
            #     user_permissions, " : this is the user permission given to him or her"
            # )
        except Group.DoesNotExist:

            return False
        permissions = group.permissions.all()

        if permissions.filter(codename=required_permission).exists():
            return True

        return False
