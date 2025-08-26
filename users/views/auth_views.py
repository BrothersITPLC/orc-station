import secrets
from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from exceptions import EmailSendError
from users.session_authentication import OneSessionPerUserAuthentication
from utils import send_verification_email, set_current_user
from workstations.serializers import WorkStationSerializer

from ..models import CustomUser, UserStatus
from ..serializers import CustomTokenObtainPairSerializer, UserSerializer

# from telebirr import Telebirr


def generate_session_token():
    return secrets.token_urlsafe()


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    # authentication_classes = [OneSessionPerUserAuthentication]

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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response({"message": "Logout successful."})
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        response.delete_cookie("session")
        response.delete_cookie("csrftoken")
        return response


class VerifyEmail(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

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
