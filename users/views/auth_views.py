import secrets
from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from exceptions import EmailSendError
from users.serializers import CustomTokenObtainPairSerializer, UserSerializer
from users.session_authentication import OneSessionPerUserAuthentication
from utils import send_verification_email, set_current_user
from workstations.serializers import WorkStationSerializer

from ..models import CustomUser, UserStatus


def generate_session_token():
    return secrets.token_urlsafe()


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
            400: {"description": "Bad Request - Invalid data provided or username/email already exists"},
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
                    "role": 2
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
                    "created_at": "2024-01-20T10:30:00Z"
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
                    "current_station": {"type": "object"}
                }
            },
            401: {"description": "Unauthorized - Invalid credentials or inactive user"},
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={
                    "username": "admin_user",
                    "password": "SecurePass123!"
                },
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
                    "current_station": {
                        "id": 1,
                        "name": "Main Office"
                    }
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
            expiry_date = datetime.now() + timedelta(days=7)
            expiry_str = expiry_date.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
            expiry_date_access = datetime.now() + timedelta(days=1)
            expiry_str_access = expiry_date_access.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
            user = CustomUser.objects.get(username=data["username"])
            session = generate_session_token()
            user.session_token = session
            set_current_user(None)
            user.save()
            # if not user.email_verified:
            #     return Response({'error': 'Email not verified'}, status=status.HTTP_403_FORBIDDEN)

            status_record = (
                UserStatus.objects.filter(user=user).order_by("-created_at").first()
            )

            print(status_record, "status")
            if status_record is not None:
                if status_record.status == "Inactive":
                    return Response(
                        {"error": "User is not active"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

            response = Response(
                {
                    "username": data["username"],
                    "access": data["access"],
                    "refresh": data["refresh"],
                    "role": data["role"],
                    "id": data["id"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "current_station": WorkStationSerializer(user.current_station).data,
                },
                status=status.HTTP_200_OK,
            )
            response.set_cookie(
                key="access",
                value=str(data["access"]),
                httponly=True,
                samesite="None",
                secure=True,
                expires=expiry_str_access,
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
                "properties": {
                    "message": {"type": "string"}
                }
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
        response = Response({"message": "Logout successful."})
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
                "properties": {
                    "message": {"type": "string"}
                }
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
