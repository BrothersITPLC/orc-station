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


class AccessTokenBlacklistMiddleware:
    """
    Middleware to check if access token is blacklisted on every request.
    Prevents use of stolen/copied tokens after logout.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        import logging
        self.logger = logging.getLogger('security.blacklist')
    
    def __call__(self, request):
        # Skip validation for non-API endpoints and login/register
        skip_paths = ['/admin/', '/static/', '/media/', '/api/users/login', '/api/users/register']
        
        if any(request.path.startswith(path) for path in skip_paths):
            return self.get_response(request)
        
        # Check if access token is blacklisted
        access_token = request.COOKIES.get('access')
        
        if access_token:
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                
                # Decode token to get JTI
                token = AccessToken(access_token)
                jti = token.payload.get('jti')
                
                self.logger.info(f"Checking blacklist for JTI: {jti}, Path: {request.path}")
                
                # Check if blacklisted
                is_blacklisted = OutstandingToken.objects.filter(
                    jti=jti,
                    blacklistedtoken__isnull=False
                ).exists()
                
                if is_blacklisted:
                    self.logger.warning(f"BLACKLISTED TOKEN DETECTED! JTI: {jti}, Path: {request.path}")
                    
                    # Token is blacklisted - reject request
                    response = JsonResponse({
                        'error': 'Authentication credentials have been revoked',
                        'detail': 'This token has been blacklisted. Please log in again.',
                        'code': 'TOKEN_BLACKLISTED'
                    }, status=401)
                    
                    # Clear all cookies
                    response.delete_cookie('access')
                    response.delete_cookie('refresh')
                    response.delete_cookie('session')
                    response.delete_cookie('csrftoken')
                    
                    return response
                else:
                    self.logger.info(f"Token JTI {jti} is NOT blacklisted")
                    
            except Exception as e:
                # Log the error but don't block the request
                self.logger.error(f"Error checking blacklist: {e}", exc_info=True)
                pass
        
        return self.get_response(request)



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
                "admin-password-reset",
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
    
    def validate_session(self, user, session_token):
        """Validate if the session token is still active in the database."""
        if not session_token:
            return False
        
        # Check if user's current session token matches
        if user.session_token != session_token:
            return False
        
        # Check if session exists and is active
        from users.models import UserSession
        session_exists = UserSession.objects.filter(
            user=user,
            session_token=session_token,
            is_active=True
        ).exists()
        
        return session_exists

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
                "schema",
                "swagger-ui",
                "redoc",
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
        session_token = request.COOKIES.get("session")

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

        # ============================================================
        # FIXED: Validate and refresh token BEFORE processing request
        # ============================================================
        token_was_refreshed = False
        new_access_token = None
        new_refresh_token = None  # Track new refresh token for rotation
        
        try:
            # Try to decode the access token
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=[api_settings.ALGORITHM],
            )
            exp = payload["exp"]
            user_id = payload.get("user_id")
            
            # Validate session
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    if not self.validate_session(user, session_token):
                        new_response = JsonResponse(
                            {
                                "error": "Session invalidated. You have been logged out from this device.",
                                "session_invalidated": True
                            },
                            status=status.HTTP_401_UNAUTHORIZED,
                        )
                        new_response.delete_cookie("access")
                        new_response.delete_cookie("refresh")
                        new_response.delete_cookie("session")
                        new_response.delete_cookie("csrftoken")
                        return new_response
                except User.DoesNotExist:
                    pass
            
            if datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                try:
                    refresh = RefreshToken(refresh_token)
                    new_access_token = str(refresh.access_token)
                    # IMPORTANT: Get the NEW rotated refresh token (ROTATE_REFRESH_TOKENS=True)
                    new_refresh_token = str(refresh)
                    token_was_refreshed = True
                    
                    # Update request authorization header for the view
                    request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access_token}"
                    
                    user = get_user_from_token(new_access_token)
                    status_response = self.check_user_status(user)
                    if status_response:
                        return status_response
                        
                except TokenError as e:
                    new_response = JsonResponse(
                        {"error": "Invalid refresh token"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                    new_response.delete_cookie("access")
                    new_response.delete_cookie("refresh")
                    new_response.delete_cookie("session")
                    new_response.delete_cookie("csrftoken")
                    return new_response
                        
        except jwt.ExpiredSignatureError:
            # Token is expired - refresh it BEFORE processing the request
            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)
                # IMPORTANT: Get the NEW rotated refresh token (ROTATE_REFRESH_TOKENS=True)
                new_refresh_token = str(refresh)
                token_was_refreshed = True
                
                # Update request authorization header for the view
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access_token}"
                
                user = get_user_from_token(new_access_token)
                
                # Validate session with the refreshed token's user
                if user and not self.validate_session(user, session_token):
                    new_response = JsonResponse(
                        {
                            "error": "Session invalidated. You have been logged out from this device.",
                            "session_invalidated": True
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                    new_response.delete_cookie("access")
                    new_response.delete_cookie("refresh")
                    new_response.delete_cookie("session")
                    new_response.delete_cookie("csrftoken")
                    return new_response
                
                status_response = self.check_user_status(user)
                if status_response:
                    return status_response
                    
            except TokenError as e:
                new_response = JsonResponse(
                    {"error": "Invalid refresh token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                new_response.delete_cookie("access")
                new_response.delete_cookie("refresh")
                new_response.delete_cookie("session")
                new_response.delete_cookie("csrftoken")
                return new_response
                
        except jwt.InvalidTokenError as e:
            new_response = JsonResponse(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )
            new_response.delete_cookie("access")
            new_response.delete_cookie("refresh")
            new_response.delete_cookie("session")
            new_response.delete_cookie("csrftoken")
            return new_response

        # ============================================================
        # NOW process the request (token is valid or was just refreshed)
        # ============================================================
        response = self.get_response(request)

        # If token was refreshed, set the new access AND refresh token cookies on the response
        if token_was_refreshed and new_access_token:
            # IMPORTANT: Cookie expiration should match refresh token lifetime (days, not minutes)
            # so the cookie persists for future token refreshes
            cookie_expiration_days = settings.TOKEN_CONFIG['COOKIE_EXPIRATION_DAYS']
            cookie_expires = datetime.now(timezone.utc) + timedelta(days=cookie_expiration_days)
            
            response.set_cookie(
                "access",
                new_access_token,
                httponly=True,
                secure=True,
                samesite="Strict",
                expires=cookie_expires,
            )
            
            # CRITICAL: Also set the NEW rotated refresh token!
            # Without this, the old (now blacklisted) refresh token stays in the cookie
            if new_refresh_token:
                response.set_cookie(
                    "refresh",
                    new_refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="Strict",
                    expires=cookie_expires,
                )

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


class DisableCSRFForAPIMiddleware(MiddlewareMixin):
    """
    Middleware to disable CSRF validation for all /api/* endpoints.
    This allows testing with API clients like Postman, Bruno, etc.
    """
    def process_request(self, request):
        if request.path.startswith("/api/"):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None


class InputValidationMiddleware:
    """
    Middleware to validate and sanitize all incoming request data.
    
    Protects against:
    - XSS (Cross-Site Scripting) attacks
    - SQL Injection attacks
    - Command Injection attacks
    - Buffer overflow attempts
    
    This runs centrally for ALL requests without needing to modify individual views.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Import validators
        from common.validators import (
            validate_input,
            get_violation_type,
            validate_field_length,
        )
        self.validate_input = validate_input
        self.get_violation_type = get_violation_type
        self.validate_field_length = validate_field_length
        
    def __call__(self, request):
        # Skip validation for exempt paths
        if self._should_skip_validation(request):
            return self.get_response(request)
        
        # Only validate methods that send data
        if request.method in ['POST', 'PUT', 'PATCH']:
            import logging
            logger = logging.getLogger('security.validation')
            logger.info(f"Validating {request.method} request to {request.path}")
            
            try:
                self._validate_request_data(request)
                logger.info(f"Validation passed for {request.path}")
            except Exception as e:
                logger.warning(f"Validation failed for {request.path}: {str(e)}")
                return self._create_error_response(str(e), field=getattr(e, 'field_name', None))
        
        response = self.get_response(request)
        return response
    
    def _should_skip_validation(self, request):
        """
        Determine if validation should be skipped for this request.
        """
        # Get whitelist paths from settings
        whitelist_paths = getattr(settings, 'INPUT_VALIDATION', {}).get('WHITELIST_PATHS', [
            '/admin/',
            '/static/',
            '/media/',
        ])
        
        # Check if path is whitelisted
        for path in whitelist_paths:
            if request.path.startswith(path):
                return True
        
        # Check if validation is disabled
        if not getattr(settings, 'INPUT_VALIDATION', {}).get('ENABLED', True):
            return True
        
        return False
    
    def _validate_request_data(self, request):
        """
        Validate all data in the request (POST, PUT, PATCH).
        """
        import json
        from django.core.exceptions import ValidationError
        
        # Get validation settings
        validation_config = getattr(settings, 'INPUT_VALIDATION', {})
        strict_mode = validation_config.get('STRICT_MODE', True)
        max_string_length = validation_config.get('MAX_STRING_LENGTH', 255)
        max_text_length = validation_config.get('MAX_TEXT_LENGTH', 5000)
        field_limits = validation_config.get('FIELD_LENGTH_LIMITS', {})
        
        # Get request data
        data_to_validate = {}
        
        # Handle JSON data (most API requests)
        if request.content_type and 'application/json' in request.content_type:
            try:
                # Read body before it's consumed
                if request.body:
                    data_to_validate = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Invalid JSON - let Django handle the error
                return
        # Handle form data
        elif request.POST:
            data_to_validate = dict(request.POST)
        
        # If no data to validate, skip
        if not data_to_validate:
            return
        
        # Validate each field recursively
        self._validate_dict(data_to_validate, field_limits, max_string_length, strict_mode)
    
    def _validate_dict(self, data, field_limits, max_string_length, strict_mode, parent_key=''):
        """
        Recursively validate dictionary data.
        """
        for field_name, value in data.items():
            full_field_name = f"{parent_key}.{field_name}" if parent_key else field_name
            
            # Handle nested dictionaries
            if isinstance(value, dict):
                self._validate_dict(value, field_limits, max_string_length, strict_mode, full_field_name)
            # Handle lists
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._validate_dict(item, field_limits, max_string_length, strict_mode, f"{full_field_name}[{i}]")
                    elif isinstance(item, str):
                        self._validate_field(full_field_name, item, field_limits, max_string_length, strict_mode)
            # Handle strings
            elif isinstance(value, str):
                self._validate_field(field_name, value, field_limits, max_string_length, strict_mode)
    
    def _validate_field(self, field_name, value, field_limits, max_string_length, strict_mode):
        """
        Validate a single field value.
        """
        from django.core.exceptions import ValidationError
        from common.validators import validate_input
        
        # Determine max length for this field
        max_length = field_limits.get(field_name, max_string_length)
        
        # Special handling for text/content fields
        if field_name in ['content', 'description', 'message', 'text', 'body']:
            max_length = field_limits.get('content', 5000)
        
        # Use the comprehensive validate_input function from validators.py
        # This includes field character validation + XSS/SQL detection
        try:
            validate_input(value, field_name, max_length, strict_mode=True)
        except ValidationError as e:
            # Log the violation
            import logging
            logger = logging.getLogger('security.validation')
            logger.warning(f"Validation failed for field '{field_name}': {str(e)}")
            
            # Re-raise with field name attached
            e.field_name = field_name
            raise e
    
    def _log_security_violation(self, violation_type, field_name, value):
        """
        Log security violations for monitoring.
        """
        import logging
        
        # Only log if enabled in settings
        if not getattr(settings, 'INPUT_VALIDATION', {}).get('LOG_VIOLATIONS', True):
            return
        
        logger = logging.getLogger('security.violations')
        logger.warning(
            f"Security violation detected: {violation_type} in field '{field_name}'",
            extra={
                'violation_type': violation_type,
                'field_name': field_name,
                'value_preview': value[:100] if len(value) > 100 else value,
            }
        )
    
    def _create_error_response(self, error_message, field=None):
        """
        Create a standardized error response.
        """
        error_data = {
            'error': 'Security Violation' if 'dangerous' in error_message or 'SQL' in error_message or 'command' in error_message else 'Validation Error',
            'detail': error_message,
        }
        
        if field:
            error_data['field'] = field
        
        # Determine error code
        if 'XSS' in error_message or 'dangerous' in error_message:
            error_data['code'] = 'XSS_DETECTED'
        elif 'SQL' in error_message:
            error_data['code'] = 'SQL_INJECTION_DETECTED'
        elif 'command' in error_message:
            error_data['code'] = 'COMMAND_INJECTION_DETECTED'
        elif 'exceeds maximum length' in error_message:
            error_data['code'] = 'MAX_LENGTH_EXCEEDED'
        else:
            error_data['code'] = 'VALIDATION_ERROR'
        
        return JsonResponse(error_data, status=400)
