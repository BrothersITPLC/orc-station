from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.models import CustomUser
from users.serializers import UserSerializer
from users.views.permissions import GroupPermission

from .models import WorkedAt, WorkStation
from .serializers import WorkedAtSerializer, WorkStationSerializer


class WorkStationViewSet(viewsets.ModelViewSet):
    queryset = WorkStation.objects.all()
    serializer_class = WorkStationSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_workstation"
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "machine_number"]
    pagination_class = CustomLimitOffsetPagination

    @action(detail=False, methods=["post"])
    def add_with_position(self, request):
        name = request.data.get("name")
        machine_id = request.data.get("machine_id")
        location = request.data.get("location")
        position = request.data.get("position")

        if not name or not location or position is None:
            return Response(
                {"error": "Name, location, and position are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_station = WorkStation.add_with_position(
            name, machine_id, location, position
        )
        serializer = self.get_serializer(new_station)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def swap_positions(self, request):
        id1 = request.data.get("id1")
        id2 = request.data.get("id2")

        if not id1 or not id2:
            return Response(
                {"error": "Both IDs are required"}, status=status.HTTP_400_BAD_REQUEST
            )

        WorkStation.swap_positions(id1, id2)
        return Response(
            {"message": "Positions swapped successfully"}, status=status.HTTP_200_OK
        )

    def perform_create(self, serializer):

        serializer.save(managed_by=self.request.user)

    def get_permissions(self):
        return has_custom_permission(self, "workstation")


class WorkedAtViewSet(viewsets.ModelViewSet):
    queryset = WorkedAt.objects.all()
    serializer_class = WorkedAtSerializer

    def get_permissions(self):
        return has_custom_permission(self, "workedat")

    def destroy(self, request, station_id=None, employee_id=None):
        try:
            # Fetch the instance to delete
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


class WorkStationsByEmployee(APIView):
    def get(self, request, employee_id, format=None):
        # employee_id = request.query_params.get('employee_id', None)
        if employee_id is not None:
            worked_at = WorkedAt.objects.filter(Q(employee_id=employee_id))
            stations = []
            serializer = WorkedAtSerializer(worked_at, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


class UnEmployeeByWorkStation(APIView):
    def get(self, request, station_id, format=None):
        # station_id = request.query_params.get('station_id', None)
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
    def get(self, request, station_id, format=None):
        # station_id = request.query_params.get('station_id', None)
        if station_id is not None:
            employee = CustomUser.objects.filter(current_station=station_id)
            serializer = UserSerializer(employee, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )


class ControllerForSupervisor(APIView):
    def get(self, request, format=None):
        station_id = request.user.current_station
        if station_id is not None:
            employee = CustomUser.objects.filter(current_station=station_id)
            serializer = UserSerializer(employee, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "employee_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )
