import base64
import os
import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.models import Checkin, Declaracion, ManualPayment, PaymentMethod
from localcheckings.models import JourneyWithoutTruck
from path.models import Path, PathStation


def generate_short_uuid():
    uuid_str = uuid.uuid4()  # Generate a UUID
    short_uuid = base64.urlsafe_b64encode(uuid_str.bytes).rstrip(b"=").decode("utf-8")
    return short_uuid


class Paymanually(APIView):
    def post(self, request):
        try:
            data = request.data
            print(data, " ,data ")
            is_bank = data.get("is_bank")
            checkin_id = data.get("id")
            # reason = data.get("reason")
            payer_name = data.get("payer_name")
            user = self.request.user
            bank_name = data.get("bank_name")
            bank_account = data.get("bank_account")
            transaction_key = data.get("transaction_key")

            if is_bank is None:
                raise ValidationError("please fill the field properly")

            if is_bank:
                if (
                    bank_name is None
                    or bank_account is None
                    or bank_name == ""
                    or bank_account == ""
                ):
                    raise ValidationError("please fill the field properly")

            with transaction.atomic():
                try:
                    checkin = Checkin.objects.get(id=checkin_id)

                    if checkin.declaracion and checkin.declaracion.id:
                        decl = Declaracion.objects.filter(
                            id=checkin.declaracion.id
                        ).first()

                        path_stations = PathStation.objects.filter(path=decl.path)
                        end_station = path_stations.order_by("order").last().station

                        if decl:

                            if decl and end_station.id == checkin.station.id:
                                decl.status = "COMPLETED"
                                decl.save()
                    else:
                        localJourney = JourneyWithoutTruck.objects.filter(
                            id=checkin.localJourney.id
                        ).first()
                        path_stations = PathStation.objects.filter(
                            path=localJourney.path
                        )
                        end_station = path_stations.order_by("order").last().station
                        if localJourney and end_station.id == checkin.station.id:
                            localJourney.status = "COMPLETED"
                            localJourney.save()
                    checkin.transaction_key = transaction_key
                    checkin.status = "success"
                    checkin.payment_accepter = self.request.user
                    method = PaymentMethod.objects.filter(name="manual").first()
                    print(method)
                    if method is None:
                        raise ValidationError("Please Add this payment Method")
                    checkin.payment_method = method
                    checkin.employee = user

                    checkin.save()
                    if is_bank:
                        manual = ManualPayment.objects.create(
                            is_bank=True,
                            bank_name=bank_name,
                            payer_name=payer_name,
                            checkin=checkin,
                            bank_account=bank_account,
                        )
                        manual.save()
                    else:
                        manual = ManualPayment.objects.create(
                            is_bank=False,
                            payer_name=payer_name,
                            checkin=checkin,
                        )
                        manual.save()

                    return Response({"message": "success"}, status=status.HTTP_200_OK)

                except requests.RequestException as req_err:
                    print(f"Request error occurred: {req_err}")
                    # Rethrow exception to ensure transaction rollback
                    raise
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
