from drf_spectacular.utils import extend_schema
from rest_framework import viewsets,permissions
from users.serializers import DepartmentSerializer
from users.models import Department

class DepartmentViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing departments.
    
    Provides CRUD operations for Department entities.
    """
    
    permission_classes = [permissions.AllowAny]
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    @extend_schema(
        summary="List all departments",
        description="Retrieve a list of all departments in the system.",
        tags=["Users - Departments"],
        responses={
            200: DepartmentSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new department",
        description="Create a new department.",
        tags=["Users - Departments"],
        request=DepartmentSerializer,
        responses={
            201: DepartmentSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific department",
        description="Get detailed information about a specific department by its ID.",
        tags=["Users - Departments"],
        responses={
            200: DepartmentSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a department",
        description="Update all fields of an existing department.",
        tags=["Users - Departments"],
        request=DepartmentSerializer,
        responses={
            200: DepartmentSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a department",
        description="Update specific fields of an existing department.",
        tags=["Users - Departments"],
        request=DepartmentSerializer,
        responses={
            200: DepartmentSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a department",
        description="Permanently delete a department from the database.",
        tags=["Users - Departments"],
        responses={
            204: {"description": "Department successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)