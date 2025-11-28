from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from path.models import PathStation
from trucks.models import Truck
from users.models import CustomUser
from workstations.models import WorkStation

from ..models import Checkin, Declaracion


class CheckTheTruck(APIView):
    """
    API view for checking trucks at weight bridges.
    
    Handles truck check-ins at weight bridges, creating or updating declarations
    and check-in records with weight measurements.
    """
    
    permission_classes = [AllowAny, HasAPIKey]

    def get_workstation(self, machine_number):
        try:
            return WorkStation.objects.filter(machine_number=machine_number).first()
        except WorkStation.DoesNotExist as e:
            raise e
        except Exception as e:
            raise e


    @extend_schema(
        summary="Check truck at weight bridge",
        description="""Record a truck check-in at a weight bridge with weight measurement.
        
        **Authentication:**
        - Requires API key authentication
        
        **Process:**
        1. Validates operator and truck
        2. Retrieves or creates declaration
        3. Validates path and station sequence
        4. Creates check-in record with weight
        5. Updates declaration status
        
        **Validation:**
        - Operator must exist
        - Truck must exist
        - Station must be in declaration path
        - Cannot skip stations
        - Previous station must be paid
        - Cannot check-in twice at same station
        
        **Status Logic:**
        - `unpaid`: net_weight > 0
        - `pass`: net_weight <= 0
        - Declaration status: ON_GOING → COMPLETED
        
        **Weight Tracking:**
        - Records net weight at each station
        - Calculates weight difference
        - Validates weight changes
        """,
        tags=["Declarations - Weight Bridge"],
        request={
            "type": "object",
            "required": ["machine_number", "truck_plate", "net_weight"],
            "properties": {
                "operator_username": {"type": "string", "description": "Username of the operator"},
                "machine_number": {"type": "string", "description": "Machine number of the workstation"},
                "commodity_name": {"type": "string", "description": "Name of commodity"},
                "commodity_id": {"type": "string", "description": "ID of commodity"},
                "truck_plate_image": {"type": "string", "format": "binary", "description": "Screenshot of truck plate"},
                "truck_plate": {"type": "string", "description": "Plate number of the truck"},
                "exporter_name": {"type": "string", "description": "Name of taxpayer"},
                "exporter_id": {"type": "string", "description": "ID of taxpayer"},
                "net_weight": {"type": "number", "description": "Net weight of cargo"}
            }
        },
        responses={
            201: {
                "description": "Check-in successfully created",
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "checkin": {"type": "integer"}
                }
            },
            200: {"description": "Check-in updated successfully"},
            400: {"description": "Bad Request - Already checked or validation error"},
            404: {"description": "Truck or operator not found"},
        },
        examples=[
            OpenApiExample(
                "Weight Bridge Check-in Request",
                value={
                    "operator_username": "operator1",
                    "machine_number": "WB001",
                    "truck_plate": "AA-12345",
                    "commodity_id": "3",
                    "commodity_name": "Coffee",
                    "exporter_id": "10",
                    "exporter_name": "Abebe Trading",
                    "net_weight": 15000.5
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "message": "success",
                    "checkin": 123
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Already Checked Error",
                value={"message": "already Checked"},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    @csrf_exempt
    def post(self, request):

        try:
            data = request.data
            machine_number = data.get("machine_number")
            truck_plate = data.get("truck_plate")
            net_weight = data.get("net_weight")
            net_weight = (
                float(net_weight) if "." in str(net_weight) else int(net_weight)
            )
            status_value = "unpaid" if net_weight > 0 else "pass"

            truck = Truck.objects.filter(plate_number=truck_plate).first()
            operator_user_name = data.get("operator_username")
            operator = CustomUser.objects.filter(username=operator_user_name).exists()
            if not operator:
                return Response(
                    {"error": "Operator with this  username is  not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not truck:
                return Response(
                    {"error": "Truck not found"}, status=status.HTTP_404_NOT_FOUND
                )

            declaracion = self.get_latest_declaracion(truck)

            workstation = self.get_workstation(machine_number)

            if not declaracion:
                return self.handle_new_declaracion(
                    truck=truck,
                    workstation=workstation,
                    net_weight=net_weight,
                    status_value=status_value,
                )

            else:
                current_checkin = Checkin.objects.filter(
                    declaracion=declaracion, station=workstation
                ).first()

                if current_checkin:

                    return Response(
                        {"message": "already Checked"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return self.handle_existing_declaracion(
                    declaracion=declaracion,
                    workstation=workstation,
                    net_weight=net_weight,
                    status_value=status_value,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def handle_existing_declaracion(
        self, declaracion, workstation, net_weight, status_value
    ):
        """Handle logic for an existing declaracion."""
        checkins = Checkin.objects.filter(declaracion=declaracion)

        if not checkins.exists():
            return self.create_checkin(
                declaracion, workstation, net_weight, status_value
            )

        latest_checkin = checkins.order_by("-checkin_time").first()
        path = declaracion.path

        if self.check_station_found_in_path(path=path, work_station=workstation):
            return self.error_response(
                "this station is not found in the selected path",
                status.HTTP_400_BAD_REQUEST,
            )

        if not self.validate_checkin_sequence(path, latest_checkin, workstation):

            return self.error_response(
                "The truck is skipping in the wrong direction",
                status.HTTP_400_BAD_REQUEST,
            )

        if latest_checkin.status in ["pending", "unpaid"]:
            return self.error_response(
                "The truck is not paid in the previous Station",
                status.HTTP_400_BAD_REQUEST,
            )

        return self.create_next_checkin(
            declaracion, workstation, latest_checkin, net_weight
        )

    def get_latest_declaracion(self, truck):
        """Fetch the latest declaracion that is not completed or cancelled."""
        return (
            Declaracion.objects.exclude(status__in=["COMPLETED", "CANCELLED"])
            .filter(truck=truck)
            .order_by("-created_at")
            .first()
        )

    def check_station_found_in_path(self, path, work_station):

        path_stations = PathStation.objects.filter(path=path)
        in_station = path_stations.filter(station=work_station).exists()

        return not in_station

    def handle_new_declaracion(self, truck, workstation, net_weight, status_value):
        """Handle logic for creating a new declaracion and check-in."""
        with transaction.atomic():
            new_declaracion = Declaracion.objects.create(
                truck=truck,
                status="ON_GOING",
            )

            check = Checkin.objects.create(
                declaracion=new_declaracion,
                station=workstation,
                net_weight=net_weight,
                status=status_value,
            )
            new_declaracion.save()
            check.save()

        return Response(
            {"message": "success", "checkin": check.id},
            status=status.HTTP_201_CREATED,
        )

    def create_checkin(self, declaracion, workstation, net_weight, status_value):
        """Create a new checkin when there are no existing checkins."""
        with transaction.atomic():
            check = Checkin.objects.create(
                declaracion=declaracion,
                station=workstation,
                net_weight=net_weight,
                status=status_value,
            )

            path = declaracion.path
            path_stations = PathStation.objects.filter(path=path)
            end_station = path_stations.order_by("order").last().station

            if end_station.id == workstation.id and net_weight <= 0:
                declaracion.status = "COMPLETED"
            else:
                declaracion.status = "ON_GOING"
            declaracion.save()

        return Response(
            {"message": "success", "checkin": check.id},
            status=status.HTTP_201_CREATED,
        )

    def create_next_checkin(self, declaracion, workstation, latest_checkin, net_weight):
        """Create the next checkin and validate weight and direction."""
        path = declaracion.path
        weight_difference = net_weight - latest_checkin.net_weight
        status_value = "unpaid" if weight_difference > 0 else "pass"
        path_station = PathStation.objects.filter(path=path).order_by("order").last()
        with transaction.atomic():
            if workstation == path_station.station and weight_difference <= 0:
                declaracion.status = "COMPLETED"
                declaracion.save()

            Checkin.objects.create(
                declaracion=declaracion,
                station=workstation,
                status=status_value,
                net_weight=net_weight,
            )

        return Response({"message": "success"}, status=status.HTTP_200_OK)

    def error_response(self, message, status_code):
        """Generate an error response."""
        return Response({"error": message}, status=status_code)

    def validate_checkin_sequence(self, path, latest_checkin, workstation):
        """Validate if the truck is skipping stations."""

        path_stations = PathStation.objects.filter(path=path)

        latest_station_order = (
            path_stations.filter(station=latest_checkin.station).first().order
        )
        current_station_order = path_stations.filter(station=workstation).first().order

        return (
            current_station_order > latest_station_order
            and not path_stations.filter(
                order__gt=latest_station_order, order__lt=current_station_order
            ).exists()
        )
