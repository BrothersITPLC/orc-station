from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.serializers import CheckinSerializer

from ..models import Checkin


class AddDeduction(APIView):
    """
    API view for adding deductions to check-ins.
    
    Allows adding a deduction amount to an existing check-in record.
    """

    @extend_schema(
        summary="Add deduction to check-in",
        description="""Add a deduction amount to an existing check-in.
        
        **Use Case:**
        - Apply deductions for various reasons (e.g., weight discrepancies, quality issues)
        - Update check-in financial records
        
        **Required Fields:**
        - `checkin_id`: ID of the check-in to update
        - `deduction_amount`: Amount to deduct
        """,
        tags=["Declarations - Check-ins"],
        request={
            "type": "object",
            "properties": {
                "checkin_id": {"type": "integer"},
                "deduction_amount": {"type": "number"}
            },
            "required": ["checkin_id", "deduction_amount"]
        },
        responses={
            200: CheckinSerializer,
            400: {"description": "Bad Request - Check-in not found or invalid data"},
        },
        examples=[
            OpenApiExample(
                "Add Deduction Request",
                value={
                    "checkin_id": 123,
                    "deduction_amount": 50.00
                },
                request_only=True,
            ),
        ],
    )
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
