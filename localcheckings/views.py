from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, views, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey

from declaracions.models import Checkin
from exporters.models import Exporter
from path.models import Path, PathStation
from users.models import CustomUser
from workstations.models import WorkStation

from .models import JourneyWithoutTruck
from .serializers import JourneyWithoutTruckSerializer


class WithoutTruckJourneyViewset(viewsets.ModelViewSet):
    serializer_class = JourneyWithoutTruckSerializer
    queryset = JourneyWithoutTruck.objects.all()


class UpdateLocalJourney(APIView):
    def put(self, request, journey_id):
        try:
            data = request.data
            commodity_id = data.get("commodity_id")
            created_by = request.user
            destination_point_id = data.get("destination_point_id")
            if (
                journey_id is None
                or journey_id == ""
                or commodity_id is None
                or commodity_id == ""
                # Assuming path_id is also required
                or destination_point_id is None
                or destination_point_id == ""
            ):
                raise ValidationError(
                    "Bad Request: Please fill the form properly. All fields are required."
                )
            journey = JourneyWithoutTruck.objects.filter(id=journey_id).first()
            journey.commodity_id = commodity_id
            journey.path_id = destination_point_id
            journey.created_by = created_by
            journey.save()

            return Response(
                JourneyWithoutTruckSerializer(journey).data, status=status.HTTP_200_OK
            )
        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class CheckinViewset(viewsets.ModelViewSet):
#     serializer_class
#     queryset = JourneyWithoutTruck.objects.all()


class CheckinWithoutTruckView(views.APIView):
    permission_classes = [AllowAny, HasAPIKey]

    def get_workstation(self, machine_number):
        try:
            return WorkStation.objects.filter(machine_number=machine_number).first()
        except WorkStation.DoesNotExist as e:
            raise e
        except Exception as e:
            raise e

    @swagger_auto_schema(
        operation_description="Create or update a check-in for a journey without a truck",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["machine_number", "exporter_unique_id", "net_weight"],
            properties={
                "operator_username": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The username of the operator",
                ),
                "machine_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Machine number for the workstation",
                ),
                "exporter_unique_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="the  unique identification  of the exporter or Tax payer",
                ),
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Name of the Exporter"
                ),
                "commodity_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Name of the Commodity"
                ),
                "commodity_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Id  of the Commodity"
                ),
                "net_weight": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Net weight of the load"
                ),
            },
        ),
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="Check-in successfully created",
                examples={"application/json": {"message": "success", "checkin": 1}},
            ),
            status.HTTP_200_OK: openapi.Response(
                description="Check-in already exists or other successful operations",
                examples={"application/json": {"message": "already Checked"}},
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Exporter not found",
                examples={
                    "application/json": {"error": "TaxPayer with this  id is not found"}
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Error occurred",
                examples={"application/json": {"error": "Detailed error message"}},
            ),
        },
    )
    @csrf_exempt
    def post(self, request):
        try:

            data = request.data
            # print("this is an application")
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

                # if there is current declaracion and also current checkin then it is already checked
                if current_checkin:
                    return Response(
                        {"message": "already Checked"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # if there is not current checkin and there is current declaracion
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
