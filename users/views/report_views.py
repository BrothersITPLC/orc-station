from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser, Report
from users.serializers import ReportSerializer


class GiveReportIssueForEmployer(APIView):
    """
    API view for supervisors to report issues about employees.
    
    Allows supervisors to create reports for employees at their workstation.
    """
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create an employee report",
        description="""Create a report/issue for an employee. Only supervisors can create reports.
        
        **Permissions:**
        - User must be a supervisor
        - Supervisor and employee must be at the same workstation
        
        **Process:**
        - Supervisor provides employee ID and reason
        - System validates permissions and station match
        - Report is created and linked to the station
        """,
        tags=["Users - Reports"],
        request={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "ID of the employee being reported"},
                "reason": {"type": "string", "description": "Reason for the report"}
            },
            "required": ["user_id", "reason"]
        },
        responses={
            200: {"description": "Report created successfully", "type": "object", "properties": {"success": {"type": "string"}}},
            400: {"description": "Bad Request - Not a supervisor or different station"},
        },
        examples=[
            OpenApiExample(
                "Create Report Request",
                value={
                    "user_id": 5,
                    "reason": "Late arrival to work multiple times this week"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"success": "Report has been sent successfully"},
                response_only=True,
            ),
            OpenApiExample(
                "Permission Error",
                value={"error": "You are not allowed to give Report"},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
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
    """
    API view for admins to read employee reports.
    
    Allows admins to view all reports for a specific employee and marks them as seen.
    """
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Read employee reports",
        description="""Retrieve all reports for a specific employee. Only admins can read reports.
        
        **Permissions:**
        - User must be an admin
        - Can only read reports for controllers
        
        **Process:**
        - Admin provides employee user ID
        - System retrieves all reports for that employee
        - All unread reports are marked as seen
        - Reports are returned in descending order by creation date
        """,
        tags=["Users - Reports"],
        responses={
            200: ReportSerializer(many=True),
            400: {"description": "Bad Request - Not an admin or invalid user role"},
        },
        examples=[
            OpenApiExample(
                "Read Reports Response",
                value=[
                    {
                        "id": 1,
                        "employee": 5,
                        "reporter": 3,
                        "report": "Late arrival to work multiple times this week",
                        "station": 1,
                        "is_seen": True,
                        "created_at": "2024-01-20T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "employee": 5,
                        "reporter": 3,
                        "report": "Incomplete documentation",
                        "station": 1,
                        "is_seen": True,
                        "created_at": "2024-01-18T14:15:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
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
