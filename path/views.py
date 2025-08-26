from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.models import Declaracion
from helper.custom_pagination import CustomLimitOffsetPagination
from localcheckings.models import JourneyWithoutTruck
from workstations.models import WorkStation

from .models import Path, PathStation
from .serializers import PathSerializer, PathStationSerializer

# Create your views here.


def pathHasUnfinishedJourney(path_id):
    try:
        has_without_truck_journey = (
            JourneyWithoutTruck.objects.filter(status__in=["PENDING", "ON_GOING"])
            .filter(path_id=path_id)
            .exists()
        )
        has_with_truck_journey = (
            Declaracion.objects.filter(status__in=["PENDING", "ON_GOING"])
            .filter(path_id=path_id)
            .exists()
        )
        if has_without_truck_journey or has_with_truck_journey:
            return Response(
                {
                    "error": "this path has unfinished Journey So you can not change this path"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PathViewSet(viewsets.ModelViewSet):
    queryset = Path.objects.all()
    serializer_class = PathSerializer
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        queryset = Path.objects.all()

        if not isinstance(self.request.user, AnonymousUser):
            current_station = self.request.user.current_station
            # Assuming `PathStation` has a ForeignKey to `Path`, and `station__name` is the field to filter
            if current_station:
                queryset = queryset.filter(
                    path_stations__station=current_station
                ).distinct()

        return queryset


class PathViewSetWithStation(viewsets.ModelViewSet):
    queryset = Path.objects.all()
    serializer_class = PathSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        queryset = Path.objects.all()
        current_station = self.request.user.current_station

        if current_station:
            # Assuming `PathStation` has a ForeignKey to `Path`, and `station__name` is the field to filter
            queryset = queryset.filter(
                pathstation__station__name=current_station
            ).distinct()

        return queryset


class PathStationViewSet(viewsets.ModelViewSet):
    queryset = PathStation.objects.all()
    serializer_class = PathStationSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomLimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        try:
            # Get the object to be deleted
            instance = self.get_object()

            # Get the ID of the instance
            instance_id = instance.id
            path_id = instance.path_id

            response = pathHasUnfinishedJourney(path_id=path_id)
            if response:
                return response
            data = PathStation.objects.filter(path_id=path_id).order_by("order")
            data_order = [x for x in data if x.id != instance_id]
            new_station_sequence = "-".join(
                str(station.station.id) for station in data_order
            )
            # Perform the delete action
            existing_paths = PathStation.objects.values("path_id").distinct()
            for path_info in existing_paths:
                existing_path_stations = PathStation.objects.filter(
                    path_id=path_info["path_id"]
                ).order_by("order")
                existing_station_sequence = "-".join(
                    str(station.station_id) for station in existing_path_stations
                )
                print(existing_station_sequence, "existing station")
                # Check for an exact match
                if new_station_sequence == existing_station_sequence:
                    return Response(
                        {
                            "error": "A path with the same station sequence already exists."
                        },
                        status=400,
                    )

                # Check if new path is an extension of an existing path
                if new_station_sequence.startswith(existing_station_sequence):
                    # Allowed case: New path extends existing path
                    continue

                # Check if existing path is an extension of the new path
                if existing_station_sequence.startswith(new_station_sequence):
                    # Allowed case: New path is a subset of existing path
                    continue

            self.perform_destroy(instance)

            # Return the ID in the response
            return Response(
                {"message": "Path station deleted successfully.", "id": instance_id},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        # Perform the delete action
        instance.delete()


class AddPath(APIView):

    def post(self, request):
        try:
            data = request.data

            path_name = data.get("path_name")
            path_stations = data.get("path_stations")
            if not path_name or not path_stations:
                return Response({"error": "Invalid data"}, status=400)

                # Convert the station IDs to a string sequence for comparison
            new_station_sequence = "-".join(
                str(station_id) for station_id in path_stations
            )

            # Check for existing paths with the exact same sequence of stations
            existing_paths = PathStation.objects.values("path_id").distinct()
            for path_info in existing_paths:
                existing_path_stations = PathStation.objects.filter(
                    path_id=path_info["path_id"]
                ).order_by("order")
                existing_station_sequence = "-".join(
                    str(station.station_id) for station in existing_path_stations
                )

                # Check if the new path has the same sequence as any existing path
                if new_station_sequence == existing_station_sequence:
                    return Response(
                        {
                            "error": "A path with the same station sequence already exists."
                        },
                        status=400,
                    )

                # If new path is a prefix or an extension of an existing path, it's allowed
                if new_station_sequence.startswith(
                    existing_station_sequence
                ) or existing_station_sequence.startswith(new_station_sequence):
                    continue  # It's allowed if the new path is an extension or shorter version

            with transaction.atomic():

                path = Path.objects.create(name=path_name, created_by=request.user)
                for station in path_stations:

                    PathStation.objects.create(path=path, station_id=station)
            return Response({"message": "Path added successfully"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class AddPathStation(APIView):

    def post(self, request):
        try:
            data = request.data

            path_id = data.get("path_id")
            station_id = data.get("station_id")

            if not path_id or not station_id:
                return Response({"error": "Invalid data"}, status=400)

            response = pathHasUnfinishedJourney(path_id=path_id)
            if response:
                return response
            station_ids = PathStation.objects.filter(path_id=path_id).order_by("order")

            # Convert the station IDs to a string sequence for comparison
            new_station_sequence = "-".join(
                str(path_station.station_id) for path_station in station_ids
            )

            new_station_sequence = new_station_sequence + "-" + str(station_id)

            print(new_station_sequence, " like Error")

            # Check for existing paths with the exact same sequence of stations
            existing_paths = PathStation.objects.values("path_id").distinct()
            for path_info in existing_paths:
                existing_path_stations = PathStation.objects.filter(
                    path_id=path_info["path_id"]
                ).order_by("order")
                existing_station_sequence = "-".join(
                    str(station.station_id) for station in existing_path_stations
                )

                # Check if the new path has the same sequence
                if new_station_sequence == existing_station_sequence:
                    return Response(
                        {
                            "error": "A path with the same station sequence already exists."
                        },
                        status=400,
                    )

                # Check if the new sequence is a prefix of an existing sequence (allowed case)
                if existing_station_sequence.startswith(new_station_sequence):
                    continue  # It's allowed if the new sequence is shorter than the existing one

                # Check if the existing sequence is a prefix of the new sequence (also allowed)
                if new_station_sequence.startswith(existing_station_sequence):
                    continue  # It's allowed if the new sequence is an extension of an existing one

            last_path_station = (
                PathStation.objects.filter(path_id=path_id).order_by("-order").first()
            )
            order = last_path_station.order + 1 if last_path_station else 1
            PathStation.objects.create(
                path_id=path_id, station_id=station_id, order=order
            )
            return Response({"message": "path Station  added successfully"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UpdatePathStationOrder(APIView):
    def put(self, request):
        data = request.data
        path_id = data.get("path_id")
        stations_order = data.get(
            "stations_order"
        )  # List of station IDs in the new order
        response = pathHasUnfinishedJourney(path_id=path_id)
        if response:
            return response
        if not path_id or not stations_order:
            return Response(
                {"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST
            )

        last_order = (
            PathStation.objects.filter(path_id=path_id).order_by("-order").first().order
        )

        # Check for existing paths with the exact same sequence of stations
        station_ids = []
        for station in stations_order:
            station_ids.append(
                PathStation.objects.filter(id=station).first().station.id
            )

        new_station_sequence = "-".join(str(station) for station in station_ids)
        existing_paths = PathStation.objects.values("path_id").distinct()
        for path_info in existing_paths:
            existing_path_stations = PathStation.objects.filter(
                path_id=path_info["path_id"]
            ).order_by("order")
            existing_station_sequence = "-".join(
                str(station.station_id) for station in existing_path_stations
            )
            print(existing_station_sequence, "existing station")
            # Check for an exact match
            if new_station_sequence == existing_station_sequence:
                return Response(
                    {"error": "A path with the same station sequence already exists."},
                    status=400,
                )

            # Check if new path is an extension of an existing path
            if new_station_sequence.startswith(existing_station_sequence):
                # Allowed case: New path extends existing path
                continue

            # Check if existing path is an extension of the new path
            if existing_station_sequence.startswith(new_station_sequence):
                # Allowed case: New path is a subset of existing path
                continue

            # If none of the conditions are met, it's an invalid sequence
            # return Response(
            #     {"error": "Path sequence conflicts with existing paths."},
            #     status=400,
            # )
        try:
            with transaction.atomic():
                for order, station_id in enumerate(
                    stations_order, start=last_order + 1
                ):
                    print(order, " :Order: ", station_id)
                    PathStation.objects.filter(path_id=path_id, id=station_id).update(
                        order=order
                    )
            return Response({"status": "Order updated"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
