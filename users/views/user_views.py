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

from helper.custom_pagination import CustomLimitOffsetPagination
from users.serializers import PasswordChangeSerializer, UserSerializer
from workstations.models import WorkedAt, WorkStation
from workstations.serializers import WorkedAtSerializer, WorkStationSerializer

from ..models import CustomUser
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

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Prepare user data for external API
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

        # Prepare user data for external API
        user_data = self.serialize_user(user, plain_password)

        # Uncomment if external API must be called
        # try:
        #     response = requests.post(
        #         self.external_api_url, json=[user_data], headers=self.headers
        #     )
        #     print(response, "this is response")
        # except Exception as e:
        #     print("External API call failed:", e)

        # Encrypt password locally after sending to external API
        user.set_password(plain_password)
        user.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class ChangePasswordView(APIView):
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
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response(
                {"detail": "Password has been changed successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ViewSet):
    def profile(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

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


def custom_404_view(request, exception):
    response_data = {"error": "The requested resource was not found."}
    return JsonResponse(response_data, status=404)
