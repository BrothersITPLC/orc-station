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

from declaracions.models import Checkin, Declaracion, PaymentMethod
from localcheckings.models import JourneyWithoutTruck
from orcSync.permissions import WorkstationHasAPIKey
from path.models import Path, PathStation
from users.models import CustomUser


def generate_short_uuid():
    uuid_str = uuid.uuid4()  # Generate a UUID
    short_uuid = base64.urlsafe_b64encode(uuid_str.bytes).rstrip(b"=").decode("utf-8")
    return short_uuid


class DerashPay(APIView):
    # permission_classes = [AllowAny]
    # permission_classes = [WorkstationHasAPIKey]

    def post(self, request):
        try:
            data = request.data
            reason = data.get("reason")
            name = data.get("name")
            mobile = data.get("mobile")
            email = data.get("email")
            bill_id = generate_short_uuid()
            checkin_id = data.get("id")
            user = request.user
            print(bill_id)
            headers = {
                "Content-Type": "application/json",
                "api-key": os.getenv(
                    "DERASH_API_KEY"
                ),  # Ensure this environment variable is set
                "api-secret": os.getenv(
                    "DERASH_SECRET_KEY"
                ),  # Ensure this environment variable is set
            }

            with transaction.atomic():
                try:
                    checkin = Checkin.objects.get(id=checkin_id)

                    previous_checkin = (
                        Checkin.objects.filter(declaracion=checkin.declaracion)
                        .exclude(checkin_time__gte=checkin.checkin_time)
                        .order_by("-checkin_time")
                        .first()
                    )
                    print("this is price:", checkin.unit_price)
                    weight = checkin.net_weight
                    if previous_checkin:
                        weight = max(
                            0, checkin.net_weight - previous_checkin.net_weight
                        )
                    print("Previous Checkin weight calculation:", weight)
                    amount = (
                        Decimal(weight)
                        * Decimal(checkin.unit_price)
                        / 100
                        * Decimal(checkin.rate)
                        / 100
                    )
                    print("Calculated amount:", amount)
                    amount = (
                        amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        - checkin.deduction
                    )
                    print("rounded Amount is: ", amount)
                    payment_data = {
                        "bill_id": bill_id,
                        "reason": reason,
                        "amount_due": float(
                            amount
                        ),  # Assuming a static amount due for demonstration
                        "due_date": datetime.now().isoformat(),
                        "name": name,
                        "mobile": mobile,
                        "email": email,
                    }

                    response = requests.post(
                        f'{os.getenv("DERASH_END_POINT")}/biller/customer-bill-data',
                        json=payment_data,
                        headers=headers,
                        timeout=15,
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    print("Response data from Derash API:", response_data)

                    method = PaymentMethod.objects.filter(name="derash").first()
                    if method is None:
                        raise ValidationError(
                            "No Derash Payment  please Add this payment Method"
                        )
                    if checkin.declaracion and checkin.declaracion.id:

                        decl = Declaracion.objects.filter(
                            id=checkin.declaracion.id
                        ).first()
                        if decl:
                            path_stations = PathStation.objects.filter(path=decl.path)
                            end_station = path_stations.order_by("order").last().station

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

                    checkin.transaction_key = bill_id
                    checkin.status = "success"
                    checkin.payment_accepter = user
                    checkin.payment_method = method
                    checkin.confirmation_code = response_data["confirmation_code"]
                    checkin.save()

                    return Response({"data": response_data}, status=status.HTTP_200_OK)
                except requests.RequestException as req_err:
                    print(f"Request error occurred: {req_err}")
                    # Rethrow exception to ensure transaction rollback
                    raise
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
