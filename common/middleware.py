import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import Resolver404, resolve
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError

from users.models import CustomUser
from utils import set_current_user

User = get_user_model()


def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user_id = access_token["user_id"]
        user = User.objects.get(id=user_id)
        set_current_user(user)
        return user
    except User.DoesNotExist:
        return None
    except Exception:
        return None


class AttachJWTTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith(settings.STATIC_URL)
            or request.path.startswith(settings.MEDIA_URL)
            or request.path.startswith("/admin/")
        ):
            return self.get_response(request)

        try:
            url_name = resolve(path=request.path).url_name
        except Resolver404:
            url_name = None
        if (
            url_name
            in [
                "tax-list",
                "update-profile",
                "assign-station",
                "declaracion-list",
                "workstationsbyemployee",
                "addDeduction",
                "profile",
                "exporter-list",
                "customuser-detail",
                "exporter-detail",
                "workedat-list",
                "trucks-detail",
                "driver-list",
                "driver-detail",
                "checkin-list",
                # "logout",
                "view",
                "api-root",
                "user-list",
                "customuser-list",
                "workstations-list",
                "declaracion-list",
                "checkin-fetch-checkins",
                "workstations-detail",
                "employeebyworkstation",
                "unemployeebyworkstation",
                "workedat-delete",
                "permission-list",
                "group-list",
                "check-logic",
                "change-password",
                "derashpayment",
                "getDerashPayment",
                "activating_diactivate",
                "give_report",
                "read_report",
                "commodity-list",
                "commodity-detail",
                "taxpayertype-list",
                "taxpayertype-detail",
                "update_declaracions",
                "regionorcity-list",
                "regionorcity-detail",
                "zoneorsubcity-list",
                "zoneorsubcity-detail",
                "woreda-list",
                "woreda-detail",
                "zoneorsubcity-get-by-region",
                "woreda-get-by-ZoneSubcity",
                "tax-detail",
                "manualPayment",
                "update_without_truck_journey",
                "without_truck_checkin_logic",
                "journey_without_truck-list",
                "issueEmployee",
                "audit-log",
                "add_path",
                "news-list",
                "news-detail",
                "path-list",
                "update_path",
                "path-detail",
                "add_path_station",
                "audit-log-table-names",
                "audit-log-list",
                "change_truck-list",
                "change_truck-detail",
                "model_report",
                "revenue_report",
                "yearly_revenue_report",
                "monthly_revenue_report",
                "daily_revenue_report",
                "top_exporters_report",
                "top_trucks_report",
                "workstation_revenue_report",
                "daily_revenue_reporttop_exporters_report",
                "vehicle-list",
                "vehicle-detail",
                "declaracion-detail",
                "revenue_and_number",
                "controllerbyworkstation",
                "department-list",
                "changetruck-list",
                "ongoing_declaracion-list",
                "ongoing_declaracion-detail",
                "station-revenue-report",
                "weekly-trends",
                "station-tax-payer",
                "completed_declaracion-list",
                "completed_declaracion-detail",
                "zoime-sync-user-list",
                "zoime-sync-user-trigger",
            ]
            and request.path != "/admin/login/"
        ):
            token = request.COOKIES.get("access")
            csrf_token = request.COOKIES.get("csrftoken")
            if token:
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
            if csrf_token:
                request.META["HTTP_X_CSRFTOKEN"] = csrf_token

        response = self.get_response(request)
        return response


class RefreshTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def check_user_status(self, user):
        if user is not None:
            set_current_user(user)
            if user.get_latest_status() is not None:
                if user.get_latest_status() == "Inactive":
                    return JsonResponse(
                        {"error": "Your Account is InActive please Contact the Admin"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
        return None

    def __call__(self, request):
        exempt_paths = [
            "/admin/",
            "/admin/login/",
            "/user/register/",
            "/user/login",
            "/user/signup",
            "/user/logout",
            "/sync/get-pending/",
            "/sync/push/",
            "/sync/acknowledge/",
            "/users/register/",
            "/users/login",
            "/users/signup",
            "/users/logout",
            "/api/sync/get-pending/",
            "/api/sync/push/",
            "/api/sync/acknowledge/",
            "/api/users/register/",
            "/api/users/login",
            "/api/users/signup",
            "/api/users/logout",
            settings.STATIC_URL,
            settings.MEDIA_URL,
        ]

        path_is_exempt = any(
            request.path.startswith(path) for path in exempt_paths if path
        )

        url_name_is_exempt = False
        resolved_url_name = None
        try:
            resolved_url_name = resolve(path=request.path).url_name
            if resolved_url_name in [
                "login",
                "verify-email",
                "signup",
                "forget",
                "truck-list",
                "check-truck",
                "weighbridgerecord-list",
                "password_reset_confirm",
                "check-logic",
                "logout",
                "schema-json",
                "schema-swagger-ui",
                "user-api-detail",
                "user-api-list",
                "trucks-list",
                "without_truck_checkin",
                "trucks-detail",
                "revenue_trends_report",
                "station-revenue-report",
                "stats-overview",
                "tax-rate-analysis",
                "employee-revenue-report",
                "tax-payer-revenue-trends",
                "deleteTax",
                "controller-today-report",
                "controller-revenue-by-date-type",
                "controller-combined-revenue-by-date-type",
            ]:
                url_name_is_exempt = True
        except Resolver404:
            pass

        if path_is_exempt or url_name_is_exempt:
            set_current_user(None)
            return self.get_response(request)

        token = request.COOKIES.get("access")
        refresh_token = request.COOKIES.get("refresh")

        if not token:
            return JsonResponse(
                {"error": "No access token provided"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not refresh_token:
            return JsonResponse(
                {"error": "No refresh token provided"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = self.get_response(request)

        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=[api_settings.ALGORITHM],
            )
            exp = payload["exp"]

            if datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                try:
                    refresh = RefreshToken(refresh_token)
                    access_token = str(refresh.access_token)
                    request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

                    user = get_user_from_token(access_token)
                    status_response = self.check_user_status(user)
                    if status_response:
                        return status_response

                    response.set_cookie(
                        "access",
                        access_token,
                        httponly=True,
                        secure=True,
                        samesite="Strict",
                        expires=datetime.now() + timedelta(days=1),
                    )
                    return response

                except TokenError:
                    new_response = JsonResponse(
                        {"error": "Invalid refresh token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                    new_response.delete_cookie("access")
                    new_response.delete_cookie("refresh")
                    return new_response
        except jwt.ExpiredSignatureError:
            try:
                refresh = RefreshToken(refresh_token)
                access_token = str(refresh.access_token)
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

                user = get_user_from_token(access_token)
                status_response = self.check_user_status(user)
                if status_response:
                    return status_response

                response.set_cookie(
                    "access",
                    access_token,
                    httponly=True,
                    secure=True,
                    samesite="Strict",
                    expires=datetime.now() + timedelta(days=1),
                )
                return response

            except TokenError:
                new_response = JsonResponse(
                    {"error": "Invalid refresh token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                new_response.delete_cookie("access")
                new_response.delete_cookie("refresh")
                return new_response
        except jwt.InvalidTokenError:
            new_response = JsonResponse(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )
            new_response.delete_cookie("access")
            new_response.delete_cookie("refresh")
            return new_response

        return response


class DisplayCurrentUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if (
            request.path.startswith(settings.STATIC_URL)
            or request.path.startswith(settings.MEDIA_URL)
            or request.path.startswith("/admin/")
        ):
            set_current_user(None)
            return None

        jwt_authenticator = JWTAuthentication()
        try:
            user, token = jwt_authenticator.authenticate(request)
            if user:
                request.user = user
                set_current_user(user)
            else:
                set_current_user(None)
        except Exception:
            set_current_user(None)
        return None
