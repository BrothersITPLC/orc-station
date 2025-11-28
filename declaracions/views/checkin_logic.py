from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.serializers import CheckinSerializer, DeclaracionSerializer
from path.models import PathStation
from tax.models import Tax
from trucks.models import Truck
from users.views.permissions import GroupPermission
from workstations.serializers import WorkStationSerializer

from ..models import Checkin, Declaracion


def create_response(data, status_code=status.HTTP_200_OK):
    return Response(data, status=status_code)


class CheckinLogic(APIView):
    """
    API view for validating check-in logic for truck declarations.
    
    Validates declaration status, path sequence, and prepares check-in data
    with tax information before actual check-in creation.
    """

    permission_classes = [GroupPermission]

    def get_permissions(self):
        # Determine permission based on the HTTP method
        if self.request.method == "POST":
            self.permission_required = "add_checkin"
        elif self.request.method == "GET":
            print("I have this permission")
            self.permission_required = "view_checkin"
        elif self.request.method in ["PUT", "PATCH"]:
            self.permission_required = "change_checkin"
        elif self.request.method == "DELETE":
            self.permission_required = "delete_checkin"
        return [permission() for permission in self.permission_classes]

    @extend_schema(
        summary="Validate check-in logic for truck",
        description="""Validate and prepare check-in data for a truck declaration.
        
        **Process:**
        1. Retrieves truck and latest declaration
        2. Validates declaration status and path
        3. Checks if station is in path
        4. Validates station sequence (no skipping)
        5. Validates direction (no wrong direction)
        6. Checks payment status at previous station
        7. Retrieves applicable tax information
        8. Returns check-in data for processing
        
        **Validation Rules:**
        - Truck must exist
        - Declaration must exist and not be completed/cancelled
        - Exporter must be set
        - Current station must be in declaration path
        - Cannot skip stations
        - Cannot go in wrong direction
        - Previous station must be paid
        - Tax must exist for commodity and station
        
        **Response Data:**
        - `previousStations`: Array of previous check-ins
        - `currentStation`: Current check-in data with tax info
        - `declaracion`: Declaration details
        """,
        tags=["Declarations - Check-ins"],
        responses={
            200: {
                "description": "Check-in validation successful",
                "type": "object",
                "properties": {
                    "previousStations": {"type": "array"},
                    "currentStation": {"type": "object"},
                    "declaracion": {"type": "object"}
                }
            },
            404: {"description": "Truck or declaration not found"},
        },
        examples=[
            OpenApiExample(
                "Validation Success Response",
                value={
                    "previousStations": [
                        {
                            "id": 1,
                            "station": 1,
                            "net_weight": 15000.5,
                            "status": "paid",
                            "checkin_time": "2024-01-20T10:00:00Z"
                        }
                    ],
                    "currentStation": {
                        "id": 2,
                        "station": 2,
                        "net_weight": 14500.0,
                        "rate": 5.0,
                        "unit_price": 100.0,
                        "status": "unpaid"
                    },
                    "declaracion": {
                        "id": 123,
                        "truck": 5,
                        "driver": 3,
                        "exporter": 10,
                        "commodity": 3,
                        "path": 2,
                        "status": "ON_GOING"
                    }
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, truck_plate):
        user = self.request.user

        try:
            # Fetch the truck by plate number
            truck = self.get_truck(truck_plate=truck_plate)
            if not truck:
                return create_response(
                    {"message": "Truck not found"}, status.HTTP_200_OK
                )

            # Fetch the latest declaracion for the truck
            declaracion = self.get_latest_declaracion(truck=truck)
            if not declaracion:
                return create_response(
                    {"message": "Please check in at the WeightBridge first"},
                    status.HTTP_200_OK,
                )

            # Serialize the declaracion
            declaracion_serializer = DeclaracionSerializer(declaracion)

            # Check if exporter details are filled in
            path_stations = PathStation.objects.filter(path=declaracion.path).order_by(
                "order"
            )
            if (
                declaracion.status in ["COMPLETED", "CANCELLED"]
                and self.request.user.current_station
                != Checkin.objects.filter(declaracion=declaracion)
                .order_by("-checkin_time")
                .first()
                .station
            ):
                return Response(
                    {
                        "success": "Precede to Checkin to weight bridge",
                        "declaracion": {},
                    },
                    status=status.HTTP_200_OK,
                )
            if not declaracion.exporter:
                return create_response(
                    {
                        "message": "Please fill out the exporter details",
                        "declaracion": declaracion_serializer.data,
                    },
                    status.HTTP_200_OK,
                )

            # Fetch current check-in at the user's current station
            current_checkin = Checkin.objects.filter(
                declaracion=declaracion, station=user.current_station
            ).first()

            if current_checkin:

                return self._handle_existing_checkin(
                    current_checkin, declaracion, declaracion_serializer, user
                )

            # Handle scenarios where there is no current check-in
            return self._handle_no_current_checkin(
                declaracion, declaracion_serializer, user
            )

        except Exception as e:
            return create_response({"error": str(e)}, status.HTTP_404_NOT_FOUND)

    def _handle_existing_checkin(
        self, current_checkin, declaracion, declaracion_serializer, user
    ):
        """
        Handle the scenario where there is already a check-in at the user's current station.
        """
        # Fetch previous check-ins up to the current check-in time
        checkins = (
            Checkin.objects.filter(declaracion=declaracion)
            .exclude(checkin_time__gt=current_checkin.checkin_time)
            .order_by("checkin_time")
        )

        # Fetch and calculate tax if required
        tax = self.get_applicable_tax(declaracion=declaracion, user=user)

        if not tax:
            return create_response(
                {
                    "message": "No taxes found for this station and commodity and for this tax payer type please contact the admin",
                    "declaracion": declaracion_serializer.data,
                },
                status.HTTP_200_OK,
            )

        # Set rate and save current check-in if necessary
        if not current_checkin.rate and not current_checkin.employee:
            current_checkin.rate = tax.percentage
            current_checkin.unit_price = declaracion.commodity.unit_price
            current_checkin.employee = user
            current_checkin.save()

        serializer_current = CheckinSerializer(current_checkin)
        serializer_previous = CheckinSerializer(checkins, many=True)

        return create_response(
            {
                "previousStations": serializer_previous.data,
                "currentStation": serializer_current.data,
                "declaracion": declaracion_serializer.data,
            },
            status.HTTP_200_OK,
        )

    def _handle_no_current_checkin(self, declaracion, declaracion_serializer, user):
        """
        Handle scenarios where there is no current check-in for the declaracion at the user's current station.
        """
        # Fetch all stations on the path
        path = declaracion.path
        path_stations = PathStation.objects.filter(path=path).order_by("order")

        # Fetch all check-ins for this declaracion
        all_checkins_in_this_declaracion = Checkin.objects.filter(
            declaracion=declaracion
        )
        if not all_checkins_in_this_declaracion.exists():
            return self.allow_proceed_response(
                declaracion_serializer=declaracion_serializer
            )

        # Find the latest check-in for this declaracion
        latest_checkin = all_checkins_in_this_declaracion.order_by(
            "-checkin_time"
        ).first()

        is_in_station = path_stations.filter(station=user.current_station).exists()
        if not is_in_station:
            return Response(
                {
                    "message": "Your Current Station is not found in the selected path for this Truck Journey"
                },
                status=status.HTTP_200_OK,
            )
        starting = path_stations.order_by("order").first()
        ending = path_stations.order_by("-order").first()
        is_starting = starting == user.current_station
        is_ending = ending == user.current_station
        if is_starting and is_ending and declaracion.status in ["ON_GOING", "PENDING"]:

            return Response(
                {
                    "journey": declaracion_serializer.data,
                    "message": "this Truck is coming from wrong direction",
                },
                status=status.HTTP_200_OK,
            )

        if is_starting:

            return Response(
                {
                    "journey": declaracion_serializer.data,
                    "message": "this Truck is coming from wrong direction",
                },
                status=status.HTTP_200_OK,
            )
        if ending == latest_checkin.station:
            if declaracion.status in [
                "COMPLETED",
                "CANCELLED",
            ] and latest_checkin.status not in ["pending", "unpaid"]:
                return Response(
                    {"success": "Precede to Checkin to weight bridge"},
                    status=status.HTTP_200_OK,
                )

        # If the latest check-in is not at the start or destination station

        return self._check_direction_and_skipped_stations(
            path,
            path_stations,
            latest_checkin,
            user,
            declaracion,
            declaracion_serializer,
        )

        # Additional checks for start or destination stations

    def _check_direction_and_skipped_stations(
        self,
        path,
        path_stations,
        latest_checkin,
        user,
        declaracion,
        declaracion_serializer,
    ):
        """
        Check if the truck is coming in the wrong direction or has skipped stations.
        """
        latest_station = path_stations.filter(station=latest_checkin.station).first()
        current_station = user.current_station
        current_station_sequence = path_stations.filter(station=current_station).first()

        if latest_station and current_station_sequence:
            if latest_station.order > current_station_sequence.order:
                return create_response(
                    {
                        "message": "The Truck is coming in the wrong direction",
                        "station": WorkStationSerializer(latest_checkin.station).data,
                        "declaracion": declaracion_serializer.data,
                    },
                    status.HTTP_200_OK,
                )
            elif latest_station.order < current_station_sequence.order:
                path_stations_in_between = path_stations.filter(
                    order__gt=latest_station.order,
                    order__lt=current_station_sequence.order,
                ).order_by("order")
                print(latest_checkin.station)
                print(latest_station.order, "Ad", current_station_sequence.order)

                if path_stations_in_between.exists():
                    return create_response(
                        {
                            "message": "The truck skipped stations that need to be checked",
                            "station": WorkStationSerializer(
                                path_stations_in_between.first().station
                            ).data,
                            "declaracion": declaracion_serializer.data,
                        },
                        status.HTTP_200_OK,
                    )

                if latest_checkin.status in ["unpaid", "pending"]:
                    return create_response(
                        {
                            "message": "This truck is not paid in the previous station",
                            "station": CheckinSerializer(latest_checkin).data,
                            "declaracion": declaracion_serializer.data,
                        },
                        status.HTTP_200_OK,
                    )
                else:
                    return self.allow_proceed_response(
                        declaracion_serializer=declaracion_serializer
                    )

    def get_truck(self, truck_plate):
        return Truck.objects.filter(plate_number=truck_plate).first()

    def get_latest_declaracion(self, truck):
        return Declaracion.objects.filter(truck=truck).order_by("-created_at").first()

    def get_applicable_tax(self, declaracion, user):
        return Tax.objects.filter(
            commodity=declaracion.commodity,
            tax_payer_type=declaracion.exporter.type,
            station=user.current_station,
        ).first()

    def create_response(self, data, status_code=status.HTTP_200_OK):
        return Response(data, status=status_code)

    def allow_proceed_response(self, declaracion_serializer):
        return self.create_response(
            {
                "success": "Proceed to WeightBridge Checking and Recheck To Calculate Tax",
                "previousStations": [],
                "currentStation": {},
                "declaracion": declaracion_serializer.data,
            }
        )
