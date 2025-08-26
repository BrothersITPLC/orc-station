import os
import uuid

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class GetDerashPayment(APIView):
    permission_classes = [AllowAny]

    def get(self, request, bill_id):
        # Define the headers

        headers = {
            "Content-Type": "application/json",
            "api-key": os.getenv(
                "DERASH_API_KEY"
            ),  # Ensure this environment variable is set
            "api-secret": os.getenv(
                "DERASH_SECRET_KEY"
            ),  # Ensure this environment variable is set
        }

        # Make the GET request
        try:
            response = requests.get(
                f'{os.getenv("DERASH_END_POINT")}/biller/customer-bill-data?bill_id={bill_id}',
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            return Response({"data": response.json()}, status=status.HTTP_200_OK)
        except requests.exceptions.RequestException as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
