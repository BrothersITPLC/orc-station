import os
import time

import requests
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiExample
from helper.custom_pagination import CustomLimitOffsetPagination
from users.serializers import (
    AdminPasswordResetSerializer,
    PasswordChangeSerializer,
    UserSerializer,
)
from workstations.models import WorkedAt, WorkStation
from workstations.serializers import WorkedAtSerializer, WorkStationSerializer

from ..models import CustomUser
from users.utils.password_validator import validate_password_strength
from .permissions import GroupPermission


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.filter(is_superuser=False)
    serializer_class = UserSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_customuser"
    filter_backends = [filters.SearchFilter]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = CustomLimitOffsetPagination
    headers = {
        "Authorization": f"Bearer {os.environ.get('WEIGHTBRIDGE_TOKEN')}",
        "Content-Type": "application/json",
    }

    external_api_url = os.environ.get("EXTERNAL_URI_WEIGHT_BRIDGE")

    search_fields = [
        "first_name",
        "last_name",
        "username",
        "email",
        "phone_number",
        "current_station__name",
    ]

    def get_permissions(self):
        if self.action == "create":
            self.permission_required = "add_customuser"
        elif self.action == "list":
            self.permission_required = "view_customuser"
        elif self.action in ["update", "partial_update"]:
            self.permission_required = "change_customuser"
        elif self.action == "destroy":
            self.permission_required = "delete_customuser"
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_name = self.request.query_params.get("role_name", None)
        if role_name:
            queryset = queryset.filter(role__name=role_name)
        return queryset

    def serialize_user(self, user, password=None):
        """Helper to prepare user data for external API (UUID safe)."""
        data = {
            "id": str(user.id),
            "role": str(user.role.id) if user.role else None,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "username": user.username,
        }
        if password:
            data["password"] = password
        return data

    @extend_schema(
        summary="Update user details",
        description="""Update an existing user's information.
        
        **Process:**
        - Updates user details in local database
        - Synchronizes changes to external Weight Bridge API
        - Requires 'change_customuser' permission
        """,
        tags=["Users - Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "User not found"},
        },
        examples=[
            OpenApiExample(
                "User Update",
                value={
                    "username": "abebe_k",
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "email": "abebe@example.com",
                    "phone_number": "+251911223344",
                    "role": 2
                },
                request_only=True,
            ),
        ],
    )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        user_data = self.serialize_user(instance)

        try:
            response = requests.post(
                self.external_api_url, json=[user_data], headers=self.headers
            )
            print(response, " here is the response")
        except Exception as e:
            print("External API call failed:", e)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @transaction.atomic
    def perform_create(self, serializer):
        plain_password = serializer.validated_data["password"]
        user = serializer.save(password=plain_password)
        user_data = self.serialize_user(user, plain_password)
        user.set_password(plain_password)
        user.save()

    @extend_schema(
        summary="Create a new user",
        description="""Create a new user in the system.
        
        **Process:**
        - Validates user input
        - Hash password securely
        - Synchronizes new user to external Weight Bridge API
        - Requires 'add_customuser' permission
        """,
        tags=["Users - Management"],
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: {"description": "Bad Request"},
        },
        examples=[
            OpenApiExample(
                "User Create",
                value={
                    "username": "new_employee",
                    "password": "SecurePassword123!",
                    "first_name": "New",
                    "last_name": "Employee",
                    "email": "new.employee@example.com",
                    "phone_number": "+251922334455",
                    "role": 3
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


    @extend_schema(
        summary="List all users",
        description="""Retrieve a list of all users.
        
        **Filtering:**
        - Can filter by role name using `role_name` query parameter.
        - Search supported on name, email, username, phone.
        """,
        tags=["Users - Management"],
        responses={
            200: UserSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve user details",
        description="Get detailed information about a specific user by ID.",
        tags=["Users - Management"],
        responses={
            200: UserSerializer,
            404: {"description": "User not found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update user",
        description="Update specific fields of a user.",
        tags=["Users - Management"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "User not found"},
        },
        examples=[
            OpenApiExample(
                "User Partial Update",
                value={
                    "phone_number": "+251933445566"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete user",
        description="Permanently remove a user from the system.",
        tags=["Users - Management"],
        responses={
            204: {"description": "User deleted successfully"},
            404: {"description": "User not found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ChangePasswordView(APIView):
    @extend_schema(
        summary="Change user password",
        description="""Allow authenticated users to change their password.
        
        **Requirements:**
        - Old password must be correct
        - New password must meet security criteria
        """,
        tags=["Authentication"],
        request=PasswordChangeSerializer,
        responses={
            200: {"description": "Password changed successfully", "type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"description": "Bad Request - Wrong old password or invalid new password"},
        },
        examples=[
            OpenApiExample(
                "Change Password Request",
                value={
                    "old_password": "OldPass123!",
                    "new_password": "NewSecurePass456!"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"detail": "Password has been changed successfully."},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Validate new password strength
            new_password = serializer.validated_data["new_password"]
            is_valid, errors = validate_password_strength(new_password)
            
            if not is_valid:
                return Response(
                    {
                        "error": "New password does not meet security requirements",
                        "password_requirements": errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(new_password)
            user.save()
            return Response(
                {"detail": "Password has been changed successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="Get current user profile",
        description="Retrieve the profile of the currently authenticated user.",
        tags=["Users - Profile"],
        responses={
            200: UserSerializer,
        },
    )
    def profile(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

    @extend_schema(
        summary="Update current user profile",
        description="""Update profile information for the current user.
        
        **Note:** returns updated profile including current station info.
        """,
        tags=["Users - Profile"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: {"description": "Bad Request"},
        },
        examples=[
            OpenApiExample(
                "Profile Update",
                value={
                    "first_name": "UpdatedName",
                    "email": "updated.email@example.com"
                },
                request_only=True,
            ),
        ],
    )
    def update_profile(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response = serializer.data
            if user.current_station:
                response.update(
                    {
                        "current_station": WorkStationSerializer(
                            user.current_station
                        ).data
                    }
                )
            else:
                response.update({"current_station": None})

            response.update({"role": user.role.name if user.role else None})
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignWorkStation(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Assign user to workstation",
        description="""Assign a user to a specific workstation (Start Shift).
        
        **Process:**
        - Updates user's current station
        - Creates a 'WorkedAt' record to track history
        """,
        tags=["Users - Workstation Assignment"],
        request={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "workstation_id": {"type": "integer"}
            },
            "required": ["user_id", "workstation_id"]
        },
        responses={
            200: {"description": "Workstation assigned", "type": "object", "properties": {"message": {"type": "string"}}},
            404: {"description": "User or Workstation not found"},
        },
        examples=[
            OpenApiExample(
                "Assign Request",
                value={"user_id": 5, "workstation_id": 1},
                request_only=True,
            ),
        ],
    )
    def post(self, request, format=None):
        user_id = request.data.get("user_id")
        workstation_id = request.data.get("workstation_id")
        try:
            with transaction.atomic():
                user = CustomUser.objects.get(id=user_id)
                workstation = WorkStation.objects.get(id=workstation_id)
                user.current_station = workstation
                user.manager = self.request.user
                worked_at = WorkedAt(
                    employee=user, station=workstation, assigner=self.request.user
                )
                user.save()
                worked_at.save()
                return Response(
                    {"message": "Workstation assigned successfully."},
                    status=status.HTTP_200_OK,
                )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except WorkStation.DoesNotExist:
            return Response(
                {"error": "Workstation not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Unassign user from workstation",
        description="""Remove a user from their current workstation (End Shift).
        
        **Process:**
        - Clear's user's current station
        - Updates 'leave_time' in the 'WorkedAt' record
        """,
        tags=["Users - Workstation Assignment"],
        request={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"}
            },
            "required": ["user_id"]
        },
        responses={
            200: {"description": "Success", "type": "object", "properties": {"message": {"type": "string"}}},
            400: {"description": "Bad Request"},
        },
        examples=[
            OpenApiExample(
                "Unassign Request",
                value={"user_id": 5},
                request_only=True,
            ),
        ],
    )
    def put(self, request):
        try:
            user_id = request.data.get("user_id")
            user = CustomUser.objects.get(id=user_id)

            with transaction.atomic():
                station = (
                    WorkedAt.objects.filter(employee=user)
                    .order_by("-created_at")
                    .first()
                )

                if station and station.station.id == user.current_station.id:
                    station.leave_time = timezone.now()
                    station.save()

                user.current_station = None
                user.save()

            return Response({"message": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminPasswordResetView(APIView):
    """
    API view for admin to reset any user's password.
    
    Only users with proper admin permissions can access this endpoint.
    """
    
    permission_classes = [GroupPermission]
    permission_required = "change_customuser"

    @extend_schema(
        summary="Admin password reset",
        description="""Reset a user's password by admin without requiring the old password.
        
        **Process:**
        - Admin provides the user ID and new password
        - System validates the new password
        - Password is updated for the specified user
        - User can immediately log in with the new password
        
        **Security:**
        - Requires admin permissions (change_customuser)
        - Password must meet security requirements (minimum 8 characters)
        - Cannot reset superuser passwords
        """,
        tags=["User Management - Admin Operations"],
        request=AdminPasswordResetSerializer,
        responses={
            200: {
                "description": "Password reset successful",
                "type": "object",
                "properties": {
                    "success": {"type": "string"},
                    "user_id": {"type": "string"},
                },
            },
            400: {"description": "Invalid request data or validation error"},
            403: {"description": "Permission denied - admin access required"},
            404: {"description": "User not found"},
        },
        examples=[
            OpenApiExample(
                "Admin Password Reset Request",
                value={
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "new_password": "NewSecurePass123!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "success": "Password has been reset successfully.",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                },
                response_only=True,
            ),
            OpenApiExample(
                "User Not Found Response",
                value={"error": "User with this ID does not exist."},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = AdminPasswordResetSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data["user_id"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Prevent resetting superuser passwords
            if user.is_superuser:
                return Response(
                    {"error": "Cannot reset superuser password."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            # Validate password strength
            is_valid, errors = validate_password_strength(new_password)
            
            if not is_valid:
                return Response(
                    {
                        "error": "Password does not meet security requirements",
                        "password_requirements": errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set the new password
            user.set_password(new_password)
            user.save()

            return Response(
                {
                    "success": "Password has been reset successfully.",
                    "user_id": str(user.id),
                },
                status=status.HTTP_200_OK,
            )

        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User with this ID does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def custom_404_view(request, exception):
    response_data = {"error": "The requested resource was not found."}
    return JsonResponse(response_data, status=404)
