from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from declaracions.models import Checkin
from exporters.models import Exporter
from path.models import PathStation
from users.models import CustomUser
from workstations.models import WorkStation

from ..models import JourneyWithoutTruck


class CheckinWithoutTruckView(views.APIView):
    """
    API view for creating check-ins for journeys without trucks.
    
    Handles check-in creation and validation for local journeys where goods
    are transported without truck registration.
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
        summary="Create check-in for journey without truck",
        description="""Create or update a check-in for a journey without a truck.
        
        **Authentication:**
        - Requires API key authentication
        
        **Process:**
        1. Validates operator and exporter
        2. Retrieves or creates journey
        3. Validates path and station sequence
        4. Creates check-in record
        5. Updates journey status
        
        **Validation:**
        - Operator must exist
        - Exporter must exist
        - Station must be in journey path
        - Cannot skip stations
        - Previous station must be paid
        - Cannot check-in twice at same station
        
        **Status Logic:**
        - `unpaid`: net_weight > 0
        - `pass`: net_weight <= 0
        - Journey status: PENDING → ON_GOING → COMPLETED
        """,
        tags=["Local Checkings - Check-ins"],
        request={
            "type": "object",
            "required": ["machine_number", "exporter_unique_id", "net_weight"],
            "properties": {
                "operator_username": {"type": "string", "description": "Username of the operator"},
                "machine_number": {"type": "string", "description": "Machine number for the workstation"},
                "exporter_unique_id": {"type": "string", "description": "Unique identification of the exporter/taxpayer"},
                "name": {"type": "string", "description": "Name of the exporter"},
                "commodity_name": {"type": "string", "description": "Name of the commodity"},
                "commodity_id": {"type": "integer", "description": "ID of the commodity"},
                "net_weight": {"type": "number", "description": "Net weight of the load"}
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
            404: {"description": "Operator or exporter not found"},
        },
        examples=[
            OpenApiExample(
                "Check-in Request",
                value={
                    "operator_username": "controller1",
                    "machine_number": "M001",
                    "exporter_unique_id": "EXP-12345",
                    "name": "Abebe Trading",
                    "commodity_id": 5,
                    "commodity_name": "Coffee",
                    "net_weight": 1500.5
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
            operator_user_name = data.get("operator_username")
            operator = CustomUser.objects.filter(username=operator_user_name).exists()
            if not operator:
                return Response(
                    {"error": "Operator with this  username is  not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            uid = data.get("exporter_unique_id")
            net_weight = data.get("net_weight")
            net_weight = (
                float(net_weight) if "." in str(net_weight) else int(net_weight)
            )
            status_value = "unpaid" if net_weight > 0 else "pass"
            exporter = Exporter.objects.filter(unique_id=uid).first()
            if not exporter:
                return Response(
                    {"error": "TaxPayer with this  id is  not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            without_truck_journey = self.get_latest_journey(exporter=exporter)
            workstation = self.get_workstation(machine_number)

            if not without_truck_journey:
                return self.handle_new_journey(
                    exporter=exporter,
                    workstation=workstation,
                    net_weight=net_weight,
                    status_value=status_value,
                )

            else:

                current_checkin = Checkin.objects.filter(
                    localJourney=without_truck_journey, station=workstation
                ).first()

                if current_checkin:
                    return Response(
                        {"message": "already Checked"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                else:
                    return self.handle_existing_journey(
                        journey=without_truck_journey,
                        workstation=workstation,
                        net_weight=net_weight,
                        status_value=status_value,
                    )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def handle_existing_journey(self, journey, workstation, net_weight, status_value):
        """Handle logic for an existing declaracion."""
        checkins = Checkin.objects.filter(localJourney=journey)

        if not checkins.exists():
            return self.create_checkin(journey, workstation, net_weight, status_value)

        latest_checkin = checkins.order_by("-checkin_time").first()
        path = journey.path

        if self.check_station_found_in_path(path=path, work_station=workstation):
            return self.error_response(
                "this station is not found in the selected path",
                status.HTTP_400_BAD_REQUEST,
            )

        if not self.validate_checkin_sequence(path, latest_checkin, workstation):

            return self.error_response(
                "The Taxpayer is skipping in the wrong direction",
                status.HTTP_400_BAD_REQUEST,
            )

        if latest_checkin.status in ["pending", "unpaid"]:
            return self.error_response(
                "The Taxpayer is not paid in the previous Station",
                status.HTTP_400_BAD_REQUEST,
            )

        return self.create_next_checkin(
            journey, workstation, latest_checkin, net_weight
        )

    def get_latest_journey(self, exporter):
        """Fetch the latest declaracion that is not completed or cancelled."""
        return (
            JourneyWithoutTruck.objects.exclude(status__in=["COMPLETED", "CANCELLED"])
            .filter(exporter=exporter)
            .order_by("-created_at")
            .first()
        )

    def check_station_found_in_path(self, path, work_station):

        path_stations = PathStation.objects.filter(path=path)
        in_station = path_stations.filter(station=work_station).exists()

        return not in_station

    def handle_new_journey(self, exporter, workstation, net_weight, status_value):
        """Handle logic for creating a new declaracion and check-in."""
        with transaction.atomic():
            journey = JourneyWithoutTruck.objects.create(
                exporter=exporter,
                status="ON_GOING",
            )

            check = Checkin.objects.create(
                localJourney=journey,
                station=workstation,
                net_weight=net_weight,
                status=status_value,
            )
            journey.save()
            check.save()

        return Response(
            {"message": "success", "checkin": check.id},
            status=status.HTTP_201_CREATED,
        )

    def create_checkin(self, journey, workstation, net_weight, status_value):
        """Create a new checkin when there are no existing checkins."""
        with transaction.atomic():
            check = Checkin.objects.create(
                localJourney=journey,
                station=workstation,
                net_weight=net_weight,
                status=status_value,
            )

            path = journey.path
            path_stations = PathStation.objects.filter(path=path)
            end_station = path_stations.order_by("-order").first().station
            if end_station == workstation and net_weight <= 0:
                journey.status = "COMPLETED"
            else:
                journey.status = "ON_GOING"
            journey.save()

        return Response(
            {"message": "success", "checkin": check.id},
            status=status.HTTP_201_CREATED,
        )

    def create_next_checkin(self, journey, workstation, latest_checkin, net_weight):

        path = journey.path
        weight_difference = net_weight - latest_checkin.net_weight
        status_value = "unpaid" if weight_difference > 0 else "pass"
        path_stations = PathStation.objects.filter(path=path)
        end_station = path_stations.order_by("order").last().station
        with transaction.atomic():
            if workstation == end_station and weight_difference <= 0:
                journey.status = "COMPLETED"
                journey.save()

            Checkin.objects.create(
                localJourney=journey,
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
        destination_station = path_stations.order_by("-order").first().station

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
