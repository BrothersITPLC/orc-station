from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import CustomUser
from users.utils.password_validator import validate_password_strength


class PasswordResetRequestView(APIView):
    """
    API view for requesting a password reset.
    
    Sends a password reset email with a unique token to the user.
    """
    
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Request password reset",
        description="""Request a password reset email for a user account.
        
        **Process:**
        - User provides their username
        - System generates a unique reset token
        - Email is sent with reset link
        - Link expires after a certain period
        
        **Reset URL Format:**
        - `http://localhost:5173/password-reset-confirm/{uid}/{token}/`
        """,
        tags=["Authentication - Password Reset"],
        request={
            "type": "object",
            "properties": {
                "username": {"type": "string"}
            },
            "required": ["username"]
        },
        responses={
            200: {"description": "Password reset email sent", "type": "object", "properties": {"success": {"type": "string"}}},
            404: {"description": "User not found"},
            500: {"description": "Error sending email"},
        },
        examples=[
            OpenApiExample(
                "Password Reset Request",
                value={"username": "admin_user"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"success": "Password reset email has been sent."},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        username = request.data.get("username")
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = f"http://localhost:5173/password-reset-confirm/{uid}/{token}/"

        subject = "Password Reset"
        message = render_to_string(
            "password_reset_email.html", {"reset_url": reset_url}
        )

        try:
            send_mail(subject, message, None, [user.email], html_message=message)
        except Exception as e:
            print(e)
            return Response(
                {"error": "Error sending password reset email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": "Password reset email has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    API view for confirming password reset.
    
    Validates the reset token and updates the user's password.
    """
    
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Confirm password reset",
        description="""Reset user password using the token from the reset email.
        
        **Process:**
        - Validates the UID and token from the reset URL
        - Sets the new password if token is valid
        - Token can only be used once
        
        **URL Parameters:**
        - `uidb64`: Base64 encoded user ID
        - `token`: Password reset token
        """,
        tags=["Authentication - Password Reset"],
        request={
            "type": "object",
            "properties": {
                "new_password": {"type": "string"}
            },
            "required": ["new_password"]
        },
        responses={
            200: {"description": "Password reset successful", "type": "object", "properties": {"success": {"type": "string"}}},
            400: {"description": "Invalid or expired token"},
        },
        examples=[
            OpenApiExample(
                "Password Reset Confirm Request",
                value={"new_password": "NewSecurePass123!"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"success": "Password has been reset."},
                response_only=True,
            ),
            OpenApiExample(
                "Invalid Token Response",
                value={"error": "Invalid reset link or expired token."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            new_password = request.data.get("new_password")
            
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
            
            user.set_password(new_password)
            user.save()
            return Response(
                {"success": "Password has been reset."}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid reset link or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

