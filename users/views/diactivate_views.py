from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser, UserStatus


class ActivateandDeactivateUser(APIView):
    """
    API view for activating and deactivating users.
    
    Allows admins to toggle user active status. Requires admin role.
    """
    
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Activate or deactivate a user",
        description="""Toggle user active status. Only admins can perform this action.
        
        **Process:**
        - Admin provides user ID
        - System checks current user status
        - Creates new status record (Active/Inactive)
        - Status history is maintained
        
        **Status Logic:**
        - If no status record exists → Set to Inactive
        - If current status is Active → Set to Inactive
        - If current status is Inactive → Set to Active
        
        **Permissions:**
        - Requires authenticated user with admin role
        """,
        tags=["Users - Management"],
        request={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"}
            },
            "required": ["user_id"]
        },
        responses={
            200: {
                "description": "Status changed successfully",
                "type": "object",
                "properties": {"message": {"type": "string"}}
            },
            400: {"description": "Bad Request"},
            403: {"description": "Forbidden - User is not an admin"},
        },
        examples=[
            OpenApiExample(
                "Deactivate User Request",
                value={"user_id": 5},
                request_only=True,
            ),
            OpenApiExample(
                "Deactivate Success Response",
                value={"message": "User deactivated successfully."},
                response_only=True,
            ),
            OpenApiExample(
                "Activate Success Response",
                value={"message": "User activated successfully."},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        try:
            print("dieactivate")
            if self.request.user.role.name == "admin":

                data = request.data
                user_id = data.get("user_id")
                user = CustomUser.objects.filter(id=user_id).first()
                status_record = (
                    UserStatus.objects.filter(user=user).order_by("-created_at").first()
                )

                if status_record is None:
                    created_status = UserStatus.objects.create(
                        user=user, status="Inactive", changed_by=self.request.user
                    )
                    created_status.save()
                    return Response(
                        {"message": "User deactivated successfully."},
                        status=status.HTTP_200_OK,
                    )

                elif status_record.status == "Active":
                    created_status = UserStatus.objects.create(
                        user=user, status="Inactive", changed_by=self.request.user
                    )
                    created_status.save()
                    return Response(
                        {"message": "User deactivated successfully."},
                        status=status.HTTP_200_OK,
                    )

                else:
                    created_status = UserStatus.objects.create(
                        user=user, status="Active", changed_by=self.request.user
                    )
                    created_status.save()
                    return Response(
                        {"message": "User activated successfully."},
                        status=status.HTTP_200_OK,
                    )
        except Exception as e:
            print(e, " error ")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
