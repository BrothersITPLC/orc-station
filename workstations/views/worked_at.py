from django.contrib.auth.models import Group
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from helper.permission import has_custom_permission
from users.models import CustomUser
from users.serializers import UserSerializer
from workstations.serializers import WorkedAtSerializer

from ..models import WorkedAt


class WorkedAtViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing employee-workstation assignments.
    
    Provides CRUD operations for WorkedAt entities that track which employees
    work at which workstations and their assignment history.
    """
    
    queryset = WorkedAt.objects.all()
    serializer_class = WorkedAtSerializer

    @extend_schema(
        summary="List all workstation assignments",
        description="Retrieve a list of all employee-workstation assignments in the system.",
        tags=["Workstations - Assignments"],
        responses={
            200: WorkedAtSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view assignments"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value=[
                    {
                        "id": 1,
                        "station": 1,
                        "employee": 5,
                        "leave_time": None,
                        "assigner": 1,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "station": 2,
                        "employee": 6,
                        "leave_time": "2024-01-20T15:00:00Z",
                        "assigner": 1,
                        "created_at": "2024-01-15T11:00:00Z",
                        "updated_at": "2024-01-20T15:00:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new workstation assignment",
        description="Assign an employee to a workstation. The assigner will be automatically set to the current user.",
        tags=["Workstations - Assignments"],
        request=WorkedAtSerializer,
        responses={
            201: WorkedAtSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create assignments"},
        },
        examples=[
            OpenApiExample(
                "Create Assignment Request",
                value={
                    "station": 1,
                    "employee": 5
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create Assignment Response",
                value={
                    "id": 1,
                    "station": 1,
                    "employee": 5,
                    "leave_time": None,
                    "assigner": 1,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific assignment",
        description="Get detailed information about a specific workstation assignment by its ID.",
        tags=["Workstations - Assignments"],
        responses={
            200: WorkedAtSerializer,
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found - Assignment with the specified ID does not exist"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update an assignment",
        description="Update all fields of an existing workstation assignment.",
        tags=["Workstations - Assignments"],
        request=WorkedAtSerializer,
        responses={
            200: WorkedAtSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update an assignment",
        description="Update specific fields of an existing assignment. Commonly used to set the leave_time when an employee leaves a workstation.",
        tags=["Workstations - Assignments"],
        request=WorkedAtSerializer,
        responses={
            200: WorkedAtSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
        },
        examples=[
            OpenApiExample(
                "Set Leave Time",
                value={
                    "leave_time": "2024-01-20T15:00:00Z"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete an assignment by station and employee",
        description="Delete a workstation assignment using station_id and employee_id.",
        tags=["Workstations - Assignments"],
        responses={
            204: {"description": "No Content - Assignment successfully deleted"},
            400: {"description": "Bad Request"},
            404: {"description": "Not Found - WorkedAt entry not found"},
        },
    )
    def destroy(self, request, station_id=None, employee_id=None):
        try:
            worked_at_instance = WorkedAt.objects.get(
                station_id=station_id, employee_id=employee_id
            )
            worked_at_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WorkedAt.DoesNotExist:
            return Response(
                {"error": "WorkedAt entry not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        return has_custom_permission(self, "workedat")


class WorkStationsByEmployee(APIView):
    """
    API view to retrieve all workstations where a specific employee has worked.
    """
    
    @extend_schema(
        summary="Get workstations by employee",
        description="Retrieve all workstation assignments for a specific employee, including current and past assignments.",
        tags=["Workstations - Assignments"],
        responses={
            200: WorkedAtSerializer(many=True),
            400: {"description": "Bad Request - employee_id is required"},
        },
        examples=[
            OpenApiExample(
                "Employee Workstations Response",
                value=[
                    {
                        "id": 1,
                        "station": 1,
                        "employee": 5,
                        "leave_time": None,
                        "assigner": 1,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "station": 2,
                        "employee": 5,
                        "leave_time": "2024-01-10T15:00:00Z",
                        "assigner": 1,
                        "created_at": "2024-01-01T09:00:00Z",
                        "updated_at": "2024-01-10T15:00:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, employee_id, format=None):
        if employee_id is not None:
            worked_at = WorkedAt.objects.filter(Q(employee_id=employee_id))
            stations = []
            serializer = WorkedAtSerializer(worked_at, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


class UnEmployeeByWorkStation(APIView):
    """
    API view to retrieve unassigned employees (controllers and supervisors) available for assignment.
    """
    
    @extend_schema(
        summary="Get unassigned employees for a workstation",
        description="Retrieve all controllers and supervisors who are not currently assigned to any workstation and are available for assignment.",
        tags=["Workstations - Assignments"],
        responses={
            200: UserSerializer(many=True),
            400: {"description": "Bad Request - employee_id is required"},
            404: {"description": "Not Found - Employee not found"},
        },
        examples=[
            OpenApiExample(
                "Unassigned Employees Response",
                value=[
                    {
                        "id": 10,
                        "username": "controller1",
                        "first_name": "Abebe",
                        "last_name": "Tadesse",
                        "email": "abebe@example.com",
                        "current_station": None,
                        "role": "controller"
                    },
                    {
                        "id": 11,
                        "username": "supervisor2",
                        "first_name": "Chaltu",
                        "last_name": "Bekele",
                        "email": "chaltu@example.com",
                        "current_station": None,
                        "role": "supervisor"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, station_id, format=None):
        if station_id is not None:
            try:
                group = Group.objects.filter(name__in=["controller", "supervisor"])
                employee = CustomUser.objects.filter(
                    role__in=group, current_station=None
                )
                serializer = UserSerializer(employee, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


class EmployeeByWorkStation(APIView):
    """
    API view to retrieve all employees currently assigned to a specific workstation.
    """
    
    @extend_schema(
        summary="Get employees by workstation",
        description="Retrieve all employees currently assigned to a specific workstation.",
        tags=["Workstations - Assignments"],
        responses={
            200: UserSerializer(many=True),
            400: {"description": "Bad Request - employee_id is required"},
        },
        examples=[
            OpenApiExample(
                "Workstation Employees Response",
                value=[
                    {
                        "id": 5,
                        "username": "controller1",
                        "first_name": "Abebe",
                        "last_name": "Tadesse",
                        "email": "abebe@example.com",
                        "current_station": 1,
                        "role": "controller"
                    },
                    {
                        "id": 6,
                        "username": "supervisor1",
                        "first_name": "Chaltu",
                        "last_name": "Bekele",
                        "email": "chaltu@example.com",
                        "current_station": 1,
                        "role": "supervisor"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, station_id, format=None):
        if station_id is not None:
            employee = CustomUser.objects.filter(current_station=station_id)
            serializer = UserSerializer(employee, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


class ControllerForSupervisor(APIView):
    """
    API view to retrieve all controllers at the current user's workstation.
    """
    
    @extend_schema(
        summary="Get controllers for supervisor's workstation",
        description="Retrieve all employees (typically controllers) assigned to the current user's workstation. Used by supervisors to see their team.",
        tags=["Workstations - Assignments"],
        responses={
            200: UserSerializer(many=True),
            400: {"description": "Bad Request - employee_id is required"},
        },
        examples=[
            OpenApiExample(
                "Controllers Response",
                value=[
                    {
                        "id": 5,
                        "username": "controller1",
                        "first_name": "Abebe",
                        "last_name": "Tadesse",
                        "email": "abebe@example.com",
                        "current_station": 1,
                        "role": "controller"
                    },
                    {
                        "id": 7,
                        "username": "controller2",
                        "first_name": "Mulugeta",
                        "last_name": "Haile",
                        "email": "mulugeta@example.com",
                        "current_station": 1,
                        "role": "controller"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, format=None):
        station_id = request.user.current_station
        if station_id is not None:
            employee = CustomUser.objects.filter(current_station=station_id)
            serializer = UserSerializer(employee, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )
