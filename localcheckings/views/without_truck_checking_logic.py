from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.models import Checkin
from declaracions.serializers import CheckinSerializer
from exporters.models import Exporter
from localcheckings.serializers import JourneyWithoutTruckSerializer
from path.models import PathStation
from tax.models import Tax
from users.views.permissions import GroupPermission
from workstations.serializers import WorkStationSerializer

from ..models import JourneyWithoutTruck


def create_response(data, status_code=status.HTTP_200_OK):

    return Response(data, status=status_code)


class WithoutTruckCheckinLogic(APIView):
    """
    API view for validating check-in logic for journeys without trucks.
    
    Validates journey status, path sequence, and prepares check-in data
    before actual check-in creation.
    """

    permission_classes = [GroupPermission]

    def get_permissions(self):
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
        summary="Validate check-in logic for journey without truck",
        description="""Validate and prepare check-in data for a journey without truck.
        
        **Process:**
        1. Retrieves exporter and latest journey
        2. Validates journey status and path
        3. Checks if station is in path
        4. Validates station sequence (no skipping)
        5. Validates direction (no wrong direction)
        6. Checks payment status at previous station
        7. Retrieves tax information
        8. Returns check-in data for processing
        
        **Validation Rules:**
        - Exporter must exist
        - Journey must exist and not be completed/cancelled
        - Commodity and path must be set
        - Current station must be in journey path
        - Cannot skip stations
        - Cannot go in wrong direction
        - Previous station must be paid
        - Tax must exist for commodity and station
        
        **Response Data:**
        - `previousStations`: Array of previous check-ins
        - `currentStation`: Current check-in data with tax info
        - `journey`: Journey details
        """,
        tags=["Local Checkings - Check-ins"],
        responses={
            200: {
                "description": "Check-in validation successful",
                "type": "object",
                "properties": {
                    "previousStations": {"type": "array"},
                    "currentStation": {"type": "object"},
                    "journey": {"type": "object"}
                }
            },
            404: {"description": "Exporter or journey not found"},
        },
        examples=[
            OpenApiExample(
                "Validation Success Response",
                value={
                    "previousStations": [
                        {
                            "id": 1,
                            "station": 1,
                            "net_weight": 1500.5,
                            "status": "paid",
                            "checkin_time": "2024-01-20T10:00:00Z"
                        }
                    ],
                    "currentStation": {
                        "id": 2,
                        "station": 2,
                        "net_weight": 1450.0,
                        "rate": 5.0,
                        "unit_price": 100.0,
                        "status": "unpaid"
                    },
                    "journey": {
                        "id": 123,
                        "exporter": 5,
                        "commodity": 3,
                        "path": 2,
                        "status": "ON_GOING"
                    }
                },
                response_only=True,
            ),
            OpenApiExample(
                "Missing Journey Error",
                value={"message": "Please checkin in the WeightBridge first"},
                response_only=True,
            ),
            OpenApiExample(
                "Wrong Direction Error",
                value={
                    "message": "The TaxPayer is coming in the wrong direction",
                    "station": {"id": 1, "name": "Station A"},
                    "journey": {"id": 123}
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, unique_id):

        user = self.request.user

        try:
            exporter = Exporter.objects.filter(unique_id=unique_id).first()

            if not exporter:
                return Response(
                    {"message": "Exporter not found with this id"},
                    status=status.HTTP_200_OK,
                )

            journey = (
                JourneyWithoutTruck.objects.filter(exporter=exporter)
                .order_by("-created_at")
                .first()
            )

            if not journey:
                return Response(
                    {"message": "Please checkin in the WeightBridge first"},
                    status=status.HTTP_200_OK,
                )
            path = journey.path
            path_stations = PathStation.objects.filter(path=path)
            if (
                journey.status in ["COMPLETED", "CANCELLED"]
                and not path_stations.filter(
                    station=self.request.user.current_station
                ).exists()
            ):
                return Response(
                    {
                        "success": "Please Check using Weightbridge",
                    },
                    status=status.HTTP_200_OK,
                )
            journey_serializer = JourneyWithoutTruckSerializer(journey)

            if not journey.commodity or not journey.path:
                return Response(
                    {
                        "message": "please fill out",
                        "journey": journey_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            current_checkin = Checkin.objects.filter(
                localJourney=journey, station=user.current_station
            ).first()

            if not current_checkin:
                return self._handle_no_current_checkin(
                    local_journey=journey,
                    journey_serializer=journey_serializer,
                    user=user,
                )

            checkins = (
                Checkin.objects.filter(
                    localJourney=journey,
                )
                .exclude(checkin_time__gt=current_checkin.checkin_time)
                .order_by("checkin_time")
            )

            if current_checkin:

                tax = Tax.objects.filter(
                    commodity=journey.commodity,
                    tax_payer_type=journey.exporter.type,
                    station=user.current_station,
                ).first()

                if not tax:
                    return Response(
                        {
                            "message": "No taxes found for this station and commodity and for this tax payer type",
                            "journey": journey_serializer.data,
                        },
                        status=status.HTTP_200_OK,
                    )

                if not current_checkin.rate and not current_checkin.employee:

                    current_checkin.rate = tax.percentage
                    current_checkin.unit_price = journey.commodity.unit_price
                    current_checkin.employee = user
                    current_checkin.save()

                serializer_current = CheckinSerializer(current_checkin)
                serializer_previous = CheckinSerializer(checkins, many=True)

                return Response(
                    {
                        "previousStations": serializer_previous.data,
                        "currentStation": serializer_current.data,
                        "journey": journey_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def _handle_no_current_checkin(self, local_journey, journey_serializer, user):
        """
        Handle scenarios where there is no current check-in for the journey at the user's current station.
        """
        path = local_journey.path
        path_stations = PathStation.objects.filter(path=path)

        first_station = path_stations.order_by("order").first()
        last_station = path_stations.order_by("-order").first()

        all_checkins_in_this_journey = Checkin.objects.filter(
            localJourney=local_journey
        )
        if not all_checkins_in_this_journey.exists():
            return self.allow_proceed_response(journey_serializer=journey_serializer)

        latest_checkin = all_checkins_in_this_journey.order_by("-checkin_time").first()

        is_start_station = first_station == latest_checkin.station
        is_destination_station = last_station == latest_checkin.station

        is_in_station = path_stations.filter(station=user.current_station).exists()
        if not is_in_station:
            return Response(
                {
                    "journey": journey_serializer.data,
                    "message": "Your Current Station is not found in the selected path for this journey",
                },
                status=status.HTTP_200_OK,
            )

        return self._check_direction_and_skipped_stations(
            path,
            path_stations,
            latest_checkin,
            user,
            local_journey=local_journey,
            journey_serializer=journey_serializer,
        )

    def allow_proceed_response(self, journey_serializer):
        return create_response(
            {
                "success": "Proceed to WeightBridge Checking and Recheck To Calculate Tax",
                "previousStations": [],
                "currentStation": {},
                "journey": journey_serializer.data,
            }
        )

    def _check_direction_and_skipped_stations(
        self,
        path,
        path_stations,
        latest_checkin,
        user,
        local_journey,
        journey_serializer,
    ):
        """
        Check if the truck is coming in the wrong direction or has skipped stations.
        """
        latest_station_sequence = path_stations.filter(
            station=latest_checkin.station
        ).first()
        current_station = user.current_station
        current_station_sequence = path_stations.filter(station=current_station).first()

        if latest_station_sequence and current_station_sequence:
            if latest_station_sequence.order > current_station_sequence.order:
                return create_response(
                    {
                        "message": "The TaxPayer is coming in the wrong direction",
                        "station": WorkStationSerializer(latest_checkin.station).data,
                        "journey": journey_serializer.data,
                    },
                    status.HTTP_200_OK,
                )
            elif latest_station_sequence.order < current_station_sequence.order:
                path_stations_in_between = path_stations.filter(
                    order__gt=latest_station_sequence.order,
                    order__lt=current_station_sequence.order,
                ).order_by("order")

                if path_stations_in_between.exists():
                    return create_response(
                        {
                            "message": "The Tax Payer skipped stations that need to be checked",
                            "station": WorkStationSerializer(
                                path_stations_in_between.first().station
                            ).data,
                            "journey": journey_serializer.data,
                        },
                        status.HTTP_200_OK,
                    )

                if latest_checkin.status in ["unpaid", "pending"]:
                    return create_response(
                        {
                            "message": "This truck is not paid in the previous station",
                            "station": CheckinSerializer(latest_checkin).data,
                            "journey": journey_serializer.data,
                        },
                        status.HTTP_200_OK,
                    )
                else:
                    return self.allow_proceed_response(
                        journey_serializer=journey_serializer
                    )
