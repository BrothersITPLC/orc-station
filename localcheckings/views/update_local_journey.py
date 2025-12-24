from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from localcheckings.serializers import JourneyWithoutTruckSerializer

from ..models import JourneyWithoutTruck


class UpdateLocalJourney(APIView):
    """
    API view for updating journey without truck details.
    
    Allows updating commodity and destination path for an existing journey.
    """

    @extend_schema(
        summary="Update journey without truck",
        description="""Update commodity and destination path for an existing local journey.
        
        **Required Fields:**
        - `commodity_id`: ID of the commodity being transported
        - `destination_point_id`: ID of the destination path
        
        **Process:**
        - Validates all required fields are provided
        - Updates journey commodity and path
        - Sets created_by to current user
        
        **Validation:**
        - All fields are required
        - Journey must exist
        """,
        tags=["Local Checkings - Journeys"],
        request={
            "type": "object",
            "properties": {
                "commodity_id": {"type": "integer"},
                "destination_point_id": {"type": "integer"}
            },
            "required": ["commodity_id", "destination_point_id"]
        },
        responses={
            200: JourneyWithoutTruckSerializer,
            400: {"description": "Bad Request - Missing required fields or invalid journey"},
        },
        examples=[
            OpenApiExample(
                "Update Journey Request",
                value={
                    "commodity_id": 5,
                    "destination_point_id": 3
                },
                request_only=True,
            ),
            OpenApiExample(
                "Validation Error",
                value={
                    "error": "Bad Request: Please fill the form properly. All fields are required."
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
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
