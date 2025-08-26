import base64
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from trucks.models import Truck
from users.models import CustomUser
from users.views.permissions import GroupPermission
from workstations.models import WorkStation

from .models import ChangeTruck, Checkin, Commodity, Declaracion, PaymentMethod
from .serializers import (
    ChangeTruckSerializer,
    CheckinSerializer,
    CommoditySerializer,
    DeclaracionSerializer,
    PaymentMethodSerializer,
)


def generate_short_uuid():
    uuid_str = uuid.uuid4()  # Generate a UUID
    short_uuid = base64.urlsafe_b64encode(uuid_str.bytes).rstrip(b"=").decode("utf-8")
    return short_uuid


class DeclaracionViewSet(viewsets.ModelViewSet):
    queryset = Declaracion.objects.all()
    serializer_class = DeclaracionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "declaracio_number",
        "truck__truck_model",
        "truck__plate_number",
        "driver__license_number",
        "commodity__name",
    ]
    permission_classes = [GroupPermission]
    permission_required = "view_declaracion"
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            starting_point=self.request.user.current_station,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # Return empty queryset for schema generation
            return Declaracion.objects.none()

        try:
            user = CustomUser.objects.filter(
                username=self.request.user.username
            ).first()

            if user is None:
                self.raise_permission_error("User not found.")
                # starting_point=user.current_station
                declaracions = Declaracion.objects.filter(
                    checkins__station=user.current_station
                )
                # for declaracion in declaracions:
                #     checkin  = Checkin.objects.filter(declaracion=declaracion).order_by('-checkin_time')
            return Declaracion.objects.filter(checkins__station=user.current_station)

        except PermissionDenied as e:
            # Handle permission denied errors
            self.raise_permission_error(str(e))
        except Exception as e:
            # Handle other exceptions
            self.raise_permission_error(str(e))

    def raise_permission_error(self, message):
        # Helper method to raise a permission error
        raise PermissionDenied(message)

    def get_permissions(self):
        if self.action == "create":
            self.permission_required = "add_declaracion"
        elif self.action == "list" or self.action == "retrieve":
            self.permission_required = "view_declaracion"
        elif self.action == "update" or self.action == "partial":
            self.permission_required = "change_declaracion"
        elif self.action == "destroy":
            self.permission_required = "delete_declaracion"

        return [permission() for permission in self.permission_classes]


class OnGoingDeclaracionViewSet(viewsets.ModelViewSet):
    queryset = Declaracion.objects.filter(driver__isnull=False)
    serializer_class = DeclaracionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "declaracio_number",
        "truck__truck_model",
        "truck__plate_number",
        "driver__license_number",
        "commodity__name",
    ]
    permission_classes = [GroupPermission]
    permission_required = "view_declaracion"
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            starting_point=self.request.user.current_station,
        )

    def raise_permission_error(self, message):
        # Helper method to raise a permission error
        raise PermissionDenied(message)

    def get_permissions(self):

        return has_custom_permission(self, "declaracion")


class UpdateDeclaracion(APIView):
    permission_classes = [GroupPermission]
    permission_required = "change_declaracion"
    CustomLimitOffsetPagination = CustomLimitOffsetPagination

    def put(self, request):
        try:

            declaracion_id = request.data.get("declaracion_id")
            get_driver_id = request.data.get("driver_id")
            get_exporter_id = request.data.get("exporter_id")
            get_commodity_id = request.data.get("commodity_id")
            path_id = request.data.get("path_id")
            # declaracion_number = request.data.get("declaracion_number")
            # allowed_weight = request.data.get("allowed_weight")
            if (
                declaracion_id is None
                or declaracion_id == ""
                or get_driver_id is None
                or get_driver_id == ""
                or get_exporter_id is None
                or get_exporter_id == ""
                or get_commodity_id is None
                or get_commodity_id == ""
                or path_id is None
                or path_id == ""  # Assuming path_id is also required
            ):
                raise ValidationError(
                    "Bad Request: Please fill the form properly. All fields are required."
                )
            register_by = self.request.user
            declaracion = Declaracion.objects.get(id=declaracion_id)
            # declaracion.allowed_weight = allowed_weight
            declaracion.declaracio_number = generate_short_uuid()
            declaracion.driver_id = get_driver_id
            declaracion.exporter_id = get_exporter_id
            declaracion.commodity_id = get_commodity_id
            declaracion.register_by = register_by
            declaracion.path_id = path_id

            declaracion.save()
            return Response(
                DeclaracionSerializer(declaracion).data, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# @method_decorator(csrf_exempt, name="dispatch")
class CommodityViewSet(viewsets.ModelViewSet):
    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_commodity"
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):

        return has_custom_permission(self, "commodity")

    def get_queryset(self):
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer


class CheckinViewSet(viewsets.ModelViewSet):
    queryset = Checkin.objects.order_by("-checkin_time")
    serializer_class = CheckinSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_checkin"
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):
        return has_custom_permission(self, "checkin")

    def get_current_checkin(self, declaracion_id, station_id):
        """
        Fetches the current check-in instance based on declaracion and station.
        """
        current_checkin = Checkin.objects.filter(
            declaracion_id=declaracion_id, station_id=station_id
        ).first()
        return current_checkin


class AddDeduction(APIView):
    def post(self, request):
        try:
            checkin_id = request.data.get("checkin_id")
            deduction_amount = request.data.get("deduction_amount")

            checkin = Checkin.objects.get(id=checkin_id)
            checkin.deduction = deduction_amount
            checkin.save()
            return Response(CheckinSerializer(checkin).data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangeTruckViewSet(viewsets.ModelViewSet):
    serializer_class = ChangeTruckSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_changetruck"
    queryset = ChangeTruck.objects.all()
    pagination_class = CustomLimitOffsetPagination

    def get_permissions(self):
        return has_custom_permission(self, "changetruck")

    def perform_create(self, serializer):
        user = self.request.user
        station = user
        station = user.current_station  # Get the user's current station
        declaracion = serializer.validated_data.get("declaracion")

        # Get the last station (e.g., from the latest check-in for the declaration)
        last_checkin = (
            Checkin.objects.filter(declaracion=declaracion)
            .order_by("-checkin_time")
            .first()
        )
        last_station = last_checkin.station if last_checkin else None
        print(serializer.validated_data, "   : here is the ID")
        declaracion = Declaracion.objects.filter(id=declaracion.id).first()

        # Save the change truck data with the current station and last station

        if declaracion is None:
            # Handle the case where no Declaracion is found
            raise ValueError("Journey not found with the provided ID.")
        declaracion.truck = serializer.validated_data.get("new_truck")

        serializer.save(created_by=user, station=station, latest_station=last_station)
        declaracion.save()


class CompletedJourney(viewsets.ReadOnlyModelViewSet):
    queryset = Declaracion.objects.all()
    serializer_class = DeclaracionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "declaracio_number",
        "truck__truck_model",
        "truck__plate_number",
        "driver__license_number",
        "commodity__name",
    ]
    permission_classes = [GroupPermission]
    permission_required = "view_declaracion"
    pagination_class = CustomLimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(
            register_by=self.request.user,
            starting_point=self.request.user.current_station,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # Return empty queryset for schema generation
            return Declaracion.objects.none()

        try:
            user = CustomUser.objects.filter(
                username=self.request.user.username
            ).first()

            if user is None:
                self.raise_permission_error("User not found.")
                # starting_point=user.current_station
                declaracions = Declaracion.objects.filter(
                    checkins__station=user.current_station
                )
                # for declaracion in declaracions:
                #     checkin  = Checkin.objects.filter(declaracion=declaracion).order_by('-checkin_time')
            return Declaracion.objects.filter(
                checkins__station=user.current_station, status="COMPLETED"
            )

        except PermissionDenied as e:
            # Handle permission denied errors
            self.raise_permission_error(str(e))
        except Exception as e:
            # Handle other exceptions
            self.raise_permission_error(str(e))

    def raise_permission_error(self, message):
        # Helper method to raise a permission error
        raise PermissionDenied(message)

    def get_permissions(self):
        if self.action == "create":
            self.permission_required = "add_declaracion"
        elif self.action == "list" or self.action == "retrieve":
            self.permission_required = "view_declaracion"
        elif self.action == "update" or self.action == "partial":
            self.permission_required = "change_declaracion"
        elif self.action == "destroy":
            self.permission_required = "delete_declaracion"

        return [permission() for permission in self.permission_classes]
