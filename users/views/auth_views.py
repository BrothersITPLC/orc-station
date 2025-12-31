import secrets
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from exceptions import EmailSendError
from users.serializers import CustomTokenObtainPairSerializer, UserSerializer
from users.session_authentication import OneSessionPerUserAuthentication
from utils import send_verification_email, set_current_user
from workstations.serializers import WorkStationSerializer
from common.encryption import encrypt_json_response

from ..models import CustomUser, UserStatus, UserSession
from users.utils.password_validator import validate_password_strength


def generate_session_token():
    return secrets.token_urlsafe()


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_device_info(user_agent):
    """Extract device information from user agent string."""
    if not user_agent:
        return "Unknown Device"
    
    user_agent_lower = user_agent.lower()
    
    # Check for mobile devices
    if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
        if 'android' in user_agent_lower:
            return "Android Device"
        elif 'iphone' in user_agent_lower:
            return "iPhone"
        elif 'ipad' in user_agent_lower:
            return "iPad"
        else:
            return "Mobile Device"
    
    # Check for desktop browsers
    if 'windows' in user_agent_lower:
        if 'edge' in user_agent_lower:
            return "Windows - Edge"
        elif 'chrome' in user_agent_lower:
            return "Windows - Chrome"
        elif 'firefox' in user_agent_lower:
            return "Windows - Firefox"
        else:
            return "Windows - Browser"
    elif 'mac' in user_agent_lower or 'macintosh' in user_agent_lower:
        if 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return "Mac - Safari"
        elif 'chrome' in user_agent_lower:
            return "Mac - Chrome"
        elif 'firefox' in user_agent_lower:
            return "Mac - Firefox"
        else:
            return "Mac - Browser"
    elif 'linux' in user_agent_lower:
        return "Linux - Browser"
    
    return "Desktop Browser"


class SignupView(APIView):
    """
    API view for user registration.

    Allows new users to create an account in the system.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="""Create a new user account in the system.
        
        **Registration Process:**
        - User data is validated
        - Account is created in an atomic transaction
        - Email verification can be enabled (currently commented out)
        
        **Required Fields:**
        - username
        - password
        - email
        - first_name
        - last_name
        - role
        """,
        tags=["Authentication"],
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: {
                "description": "Bad Request - Invalid data provided or username/email already exists"
            },
            500: {"description": "Internal Server Error - Email verification failed"},
        },
        examples=[
            OpenApiExample(
                "Signup Request",
                value={
                    "username": "newuser",
                    "password": "SecurePass123!",
                    "email": "newuser@example.com",
                    "first_name": "Abebe",
                    "last_name": "Tadesse",
                    "role": 2,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Signup Success Response",
                value={
                    "id": 10,
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "first_name": "Abebe",
                    "last_name": "Tadesse",
                    "role": 2,
                    "is_active": True,
                    "created_at": "2024-01-20T10:30:00Z",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request, format=None):

        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    # send_verification_email(user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except EmailSendError:
                return Response(
                    {
                        "detail": "User registration failed. Verification email could not be sent."
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    API view for user authentication.

    Handles user login and JWT token generation with session management.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    # authentication_classes = [OneSessionPerUserAuthentication]

    @method_decorator(ratelimit(key='ip', rate='5/5m', method='POST', block=True))
    @extend_schema(
        summary="Login user",
        description="""Authenticate a user and return JWT tokens.
        
        **Authentication Process:**
        - Validates username and password
        - Checks if user is active
        - Generates JWT access and refresh tokens
        - Sets secure HTTP-only cookies for tokens
        - Returns user information and current workstation
        
        **Cookies Set:**
        - `access`: JWT access token (expires in 1 day)
        - `refresh`: JWT refresh token (expires in 7 days)
        - `session`: Session token for tracking
        - `csrftoken`: CSRF protection token
        
        **Error Responses:**
        - 401: Invalid credentials or inactive user
        """,
        tags=["Authentication"],
        request=CustomTokenObtainPairSerializer,
        responses={
            200: {
                "description": "Login successful",
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "role": {"type": "string"},
                    "id": {"type": "integer"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "current_station": {"type": "object"},
                },
            },
            401: {"description": "Unauthorized - Invalid credentials or inactive user"},
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={"username": "admin_user", "password": "SecurePass123!"},
                request_only=True,
            ),
            OpenApiExample(
                "Login Success Response",
                value={
                    "username": "admin_user",
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "role": "admin",
                    "id": 1,
                    "first_name": "Admin",
                    "last_name": "User",
                    "current_station": {"id": 1, "name": "Main Office"},
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            # Get token expiration settings from centralized config
            cookie_max_age_seconds = settings.TOKEN_CONFIG['COOKIE_MAX_AGE_SECONDS']
            
            # IMPORTANT: Cookie expiration should match or exceed JWT refresh token lifetime
            # The cookie must persist so middleware can read the expired JWT and refresh it.
            # All cookies (access, refresh, session) should have the same expiration.
            expiry_date = datetime.now() + timedelta(seconds=cookie_max_age_seconds)
            expiry_str = expiry_date.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
            user = CustomUser.objects.get(username=data["username"])
            
            # Check user status
            status_record = (
                UserStatus.objects.filter(user=user).order_by("-created_at").first()
            )
            if status_record is not None:
                if status_record.status == "Inactive":
                    return Response(
                        {"error": "User is not active"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            
            # Get device and IP information
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            device_info = get_device_info(user_agent)
            
            # Single session enforcement: Invalidate all previous sessions
            # Blacklist all existing refresh tokens for this user EXCEPT the one we just created
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                # Get the jti (token ID) of the newly created refresh token
                new_refresh_token = data["refresh"]
                new_token_jti = RefreshToken(new_refresh_token).payload.get("jti")
                
                # Blacklist all tokens EXCEPT the new one (identified by jti)
                outstanding_tokens = OutstandingToken.objects.filter(user=user).exclude(jti=new_token_jti)
                for token in outstanding_tokens:
                    try:
                        RefreshToken(token.token).blacklist()
                    except Exception:
                        pass  # Token might already be blacklisted or expired
            except Exception as e:
                pass  # Silently continue if blacklisting fails
            
            # Deactivate all previous sessions
            UserSession.objects.filter(user=user, is_active=True).update(
                is_active=False,
                logged_out_at=timezone.now()
            )
            
            # Clear Django admin sessions for this user
            # This prevents concurrent logins in Django admin panel
            try:
                from django.contrib.sessions.models import Session
                from django.contrib.auth import logout as django_logout
                
                # Find and delete all Django sessions for this user
                all_sessions = Session.objects.all()
                for session in all_sessions:
                    session_data = session.get_decoded()
                    if session_data.get('_auth_user_id') == str(user.pk):
                        session.delete()
            except Exception as e:
                # Log but don't fail login if session clearing fails
                print(f"Warning: Could not clear Django sessions: {e}")
            
            # Generate new session token
            session = generate_session_token()
            user.session_token = session
            set_current_user(None)
            user.save()
            
            # Create new session record
            UserSession.objects.create(
                user=user,
                session_token=session,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                is_active=True
            )

            # Prepare response data
            response_data = {
                "username": data["username"],
                "role": data["role"],
                "id": data["id"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "current_station": WorkStationSerializer(user.current_station).data,
            }
            
            # Encrypt the response
            encrypted_data, encryption_key = encrypt_json_response(response_data)
            
            # Send encrypted data in response body
            response = Response(
                {"data": encrypted_data},
                status=status.HTTP_200_OK,
            )
            
            # Send decryption key via custom security header
            response['X-Content-Security-Key'] = encryption_key
            response.set_cookie(
                key="access",
                value=str(data["access"]),
                httponly=True,
                samesite="None",
                secure=True,
                expires=expiry_str,  # Use same expiration as refresh token (7 days)
            )
            response.set_cookie(
                key="refresh",
                value=str(data["refresh"]),
                httponly=True,
                samesite="None",
                secure=True,
                expires=expiry_str,
            )

            response.set_cookie(
                key="session",
                value=session,
                httponly=True,
                samesite="None",
                secure=True,
                expires=expiry_str,
            )
            csrf_token = get_token(request)
            response.set_cookie(
                key="csrftoken",
                value=csrf_token,
                httponly=True,
                samesite="None",
                secure=True,
            )

            return response
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """
    API view for user logout.
    Clears authentication cookies and ends the user session.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Logout user",
        description="""Log out the current user by clearing all authentication cookies.
        **Cookies Cleared:**
        - access
        - refresh
        - session
        - csrftoken
        """,
        tags=["Authentication"],
        request=None,
        responses={
            200: {
                "description": "Logout successful",
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
        },
        examples=[
            OpenApiExample(
                "Logout Response",
                value={"message": "Logout successful."},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        try:
            # Get tokens from cookies
            access_token = request.COOKIES.get('access')
            refresh_token = request.COOKIES.get('refresh')
            session_token = request.COOKIES.get('session')
            
            # Blacklist the access token (prevents immediate reuse of stolen tokens)
            if access_token:
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
                    
                    token = AccessToken(access_token)
                    jti = token.payload.get('jti')
                    user_id = token.payload.get('user_id')
                    exp = token.payload.get('exp')
                    
                    # Create OutstandingToken record if it doesn't exist
                    outstanding_token, created = OutstandingToken.objects.get_or_create(
                        jti=jti,
                        defaults={
                            'token': str(access_token),
                            'user_id': user_id,
                            'expires_at': datetime.fromtimestamp(exp, tz=dt_timezone.utc)
                        }
                    )
                    
                    # Blacklist the access token
                    BlacklistedToken.objects.get_or_create(token=outstanding_token)
                    print(f"Access token blacklisted: {jti}")
                except Exception as e:
                    print(f"Error blacklisting access token: {e}")
            
            # Blacklist the refresh token
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    print(f"Refresh token blacklisted")
                except Exception as e:
                    print(f"Error blacklisting refresh token: {e}")
            
            # Clear session token from database and deactivate session
            if request.user.is_authenticated:
                user = request.user
                user.session_token = None
                user.save(update_fields=['session_token'])
                
                # Deactivate the current session
                if session_token:
                    UserSession.objects.filter(
                        session_token=session_token,
                        user=user
                    ).update(
                        is_active=False,
                        logged_out_at=timezone.now()
                    )
            
            # Create response and delete all cookies
            response = Response({"message": "Logout successful."})
            response.delete_cookie("access")
            response.delete_cookie("refresh")
            response.delete_cookie("session")
            response.delete_cookie("csrftoken")
            
            return response
            
        except Exception as e:
            print(f"Logout error: {e}")
            # Even if there's an error, clear cookies
            response = Response(
                {"message": "Logout completed."},
                status=status.HTTP_200_OK
            )
            response.delete_cookie("access")
            response.delete_cookie("refresh")
            response.delete_cookie("session")
            response.delete_cookie("csrftoken")
            return response


class VerifyEmail(generics.GenericAPIView):
    """
    API view for email verification.

    Verifies user email address using a verification token.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Verify email address",
        description="""Verify a user's email address using the verification token sent via email.
        
        **Process:**
        - Token is validated
        - User's email_verified flag is set to True
        - User can now fully access the system
        """,
        tags=["Authentication"],
        responses={
            200: {
                "description": "Email verified successfully",
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
            404: {"description": "Not Found - Invalid verification token"},
        },
        examples=[
            OpenApiExample(
                "Verify Email Response",
                value={"message": "Email successfully verified"},
                response_only=True,
            ),
        ],
    )
    def get(self, request, token):
        # Perform logic to verify the email
        user = get_object_or_404(CustomUser, email_verification_token=token)
        user.email_verified = True
        user.save()
        # Redirect or return success message
        return Response(
            {"message": "Email successfully verified"}, status=status.HTTP_200_OK
        )

    def get_serializer(self, *args, **kwargs):
        if getattr(self, "swagger_fake_view", False):
            return None
        return super().get_serializer(*args, **kwargs)


class VerifyUserView(APIView):
    """
    Endpoint for frontend to verify user role against backend.
    Returns the same format as login response (without tokens).
    Used to detect localStorage tampering.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        operation_id="verify_user",
        summary="Verify User Data",
        description="""
        Returns the authenticated user's data in the same format as login.
        Used by frontend to verify that localStorage hasn't been tampered with.
        
        **Security Note:**
        This endpoint reads user data from the authenticated JWT token,
        making it impossible to fake via localStorage manipulation.
        """,
        tags=["Authentication"],
        responses={
            200: {
                "description": "User data verified",
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string"},
                    "role": {"type": "string"},
                    "id": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "current_station": {"type": "object"},
                },
            },
            401: {"description": "Unauthorized - Invalid or expired token"},
        },
    )
    def get(self, request):
        user = request.user
        
        # Return user data in the same format as login response
        response_data = {
            "username": user.username,
            "email": user.email,
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.name if user.role else None,
            "current_station": user.current_station.id if user.current_station else None,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

