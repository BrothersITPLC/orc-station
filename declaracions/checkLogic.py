from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from path.models import Path, PathStation
from tax.models import Tax
from trucks.models import Truck
from users.views.permissions import GroupPermission
from workstations.models import WorkStation
from workstations.serializers import WorkStationSerializer

from .models import Checkin, Declaracion
from .serializers import CheckinSerializer, DeclaracionSerializer


def create_response(data, status_code=status.HTTP_200_OK):

    return Response(data, status=status_code)


class CheckinLogic(APIView):

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

        # return create_response(
        #     {"message": "No valid sequence found."}, status.HTTP_200_OK
        # )

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
