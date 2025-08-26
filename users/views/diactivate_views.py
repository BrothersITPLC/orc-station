from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser, UserStatus


class ActivateandDeactivateUser(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
