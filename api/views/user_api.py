from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from api.serializers import CustomUserSerializer
from users.models import CustomUser


class CustomUserViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing users via API key authentication.
    
    Provides read operations for CustomUser entities (controllers and admins only).
    This viewset is designed for external integrations using API keys.
    Supports search by name, email, and username.
    """
    
    permission_classes = [HasAPIKey]
    queryset = CustomUser.objects.filter(role__name__in=["controller", "admin"])
    serializer_class = CustomUserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "username"]

    @extend_schema(
        summary="List all users (controllers and admins)",
        description="""Retrieve a list of all users with controller or admin roles.
        
        **Authentication:**
        - Requires API key authentication
        
        **Filtering:**
        - Only returns users with 'controller' or 'admin' roles
        - Supports search by first name, last name, email, and username
        
        **Use Case:**
        - Used by external systems to get a list of system users
        - Useful for synchronization between systems
        """,
        tags=["API - Users"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter users by name, email, or username",
                required=False,
            ),
        ],
        responses={
            200: CustomUserSerializer(many=True),
            401: {"description": "Unauthorized - Invalid or missing API key"},
            403: {"description": "Forbidden - API key does not have required permissions"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "username": "admin_user",
                        "first_name": "Admin",
                        "last_name": "User",
                        "email": "admin@example.com",
                        "role": "admin",
                        "current_station": 1,
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 5,
                        "username": "controller1",
                        "first_name": "Abebe",
                        "last_name": "Tadesse",
                        "email": "abebe@example.com",
                        "role": "controller",
                        "current_station": 2,
                        "is_active": True,
                        "created_at": "2024-01-16T09:00:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Retrieve a specific user",
        description="""Get detailed information about a specific user by ID or username.
        
        **Lookup Methods:**
        - By ID: Use the standard endpoint `/api/user/{id}/`
        - By username: Use query parameter `/api/user/{any_id}/?username=desired_username`
        
        **Note:** When using username lookup, the ID in the URL is ignored.
        
        **Error Responses:**
        - 400: Neither ID nor username provided
        - 404: User not found
        """,
        tags=["API - Users"],
        parameters=[
            OpenApiParameter(
                name="username",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Username to lookup (alternative to ID)",
                required=False,
            ),
        ],
        responses={
            200: CustomUserSerializer,
            400: {"description": "Bad Request - Provide either 'id' or 'username'"},
            401: {"description": "Unauthorized - Invalid or missing API key"},
            404: {"description": "Not Found - User does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve by ID Response",
                value={
                    "id": 1,
                    "username": "admin_user",
                    "first_name": "Admin",
                    "last_name": "User",
                    "email": "admin@example.com",
                    "role": "admin",
                    "current_station": 1,
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00Z"
                },
                response_only=True,
            ),
            OpenApiExample(
                "Retrieve by Username Response",
                description="GET /api/user/1/?username=controller1",
                value={
                    "id": 5,
                    "username": "controller1",
                    "first_name": "Abebe",
                    "last_name": "Tadesse",
                    "email": "abebe@example.com",
                    "role": "controller",
                    "current_station": 2,
                    "is_active": True,
                    "created_at": "2024-01-16T09:00:00Z"
                },
                response_only=True,
            ),
            OpenApiExample(
                "Missing Parameter Error",
                value={
                    "detail": "Provide either 'id' or 'username'."
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get("pk", None)
        username = request.query_params.get("username", None)

        if user_id:
            user = get_object_or_404(CustomUser, id=user_id)
        elif username:
            user = get_object_or_404(CustomUser, username=username)
        else:
            return Response(
                {"detail": "Provide either 'id' or 'username'."}, status=400
            )

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a new user",
        description="Create a new user via API. Requires API key authentication.",
        tags=["API - Users"],
        request=CustomUserSerializer,
        responses={
            201: CustomUserSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Invalid or missing API key"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update a user",
        description="Update all fields of an existing user.",
        tags=["API - Users"],
        request=CustomUserSerializer,
        responses={
            200: CustomUserSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Invalid or missing API key"},
            404: {"description": "Not Found - User does not exist"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a user",
        description="Update specific fields of an existing user.",
        tags=["API - Users"],
        request=CustomUserSerializer,
        responses={
            200: CustomUserSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Invalid or missing API key"},
            404: {"description": "Not Found - User does not exist"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a user",
        description="Delete a user from the system.",
        tags=["API - Users"],
        responses={
            204: {"description": "User successfully deleted"},
            401: {"description": "Unauthorized - Invalid or missing API key"},
            404: {"description": "Not Found - User does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
