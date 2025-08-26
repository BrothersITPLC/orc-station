from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser, Report
from users.serializers import ReportSerializer


class GiveReportIssueForEmployer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            user_id = data["user_id"]
            print(data, "here is the data for this one ")
            user = CustomUser.objects.filter(id=user_id).first()
            supervisor = request.user

            if supervisor.role.name != "supervisor":
                return Response(
                    {"error": "You are not allowed to give Report"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if supervisor.current_station.id != user.current_station.id:
                return Response(
                    {
                        "error": "You are not allowed to give Report on this user. reason you are not in the same station"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                Report.objects.create(
                    employee=user,
                    reporter=supervisor,
                    report=data["reason"],
                    station=supervisor.current_station,
                )

                return Response(
                    {"success": "Report has been sent successfully"},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReadReportIsue(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:

            admin = request.user
            if admin.role.name != "admin":
                return Response(
                    {"error": "You are not allowed to read Report"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = CustomUser.objects.filter(id=user_id).first()
            if user.role.name in ["controller"]:
                reports = Report.objects.filter(employee=user).order_by("-created_at")

                with transaction.atomic():
                    for report in reports:
                        if not report.is_seen:
                            report.is_seen = True
                            report.save()

                reports_data = ReportSerializer(reports, many=True).data
                return Response(
                    reports_data,
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "You are not allowed to read Report"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
