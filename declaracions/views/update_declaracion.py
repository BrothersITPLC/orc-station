import base64
import uuid

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from declaracions.serializers import DeclaracionSerializer
from helper.custom_pagination import CustomLimitOffsetPagination
from users.views.permissions import GroupPermission

from ..models import Declaracion


def generate_short_uuid():
    uuid_str = uuid.uuid4()
    short_uuid = base64.urlsafe_b64encode(uuid_str.bytes).rstrip(b"=").decode("utf-8")
    return short_uuid


class UpdateDeclaracion(APIView):
    """
    API view for updating declaration details.
    
    Updates driver, exporter, commodity, and path for an existing declaration.
    Generates a new declaration number upon update.
    """
    
    permission_classes = [GroupPermission]
    permission_required = "change_declaracion"
    CustomLimitOffsetPagination = CustomLimitOffsetPagination

    @extend_schema(
        summary="Update declaration",
        description="""Update an existing declaration with new details.
        
        **Required Fields:**
        - `declaracion_id`: ID of the declaration to update
        - `driver_id`: New driver ID
        - `exporter_id`: New exporter ID
        - `commodity_id`: New commodity ID
        - `path_id`: New path ID
        
        **Process:**
        - Validates all required fields
        - Generates new declaration number
        - Updates all specified fields
        - Sets register_by to current user
        
        **Note:** A new declaration number is automatically generated.
        """,
        tags=["Declarations - Declarations"],
        request={
            "type": "object",
            "required": ["declaracion_id", "driver_id", "exporter_id", "commodity_id", "path_id"],
            "properties": {
                "declaracion_id": {"type": "integer"},
                "driver_id": {"type": "integer"},
                "exporter_id": {"type": "integer"},
                "commodity_id": {"type": "integer"},
                "path_id": {"type": "integer"}
            }
        },
        responses={
            200: DeclaracionSerializer,
            400: {"description": "Bad Request - Missing required fields or invalid declaration"},
        },
        examples=[
            OpenApiExample(
                "Update Declaration Request",
                value={
                    "declaracion_id": 123,
                    "driver_id": 5,
                    "exporter_id": 10,
                    "commodity_id": 3,
                    "path_id": 2
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
    def put(self, request):
        try:

            declaracion_id = request.data.get("declaracion_id")
            get_driver_id = request.data.get("driver_id")
            get_exporter_id = request.data.get("exporter_id")
            get_commodity_id = request.data.get("commodity_id")
            path_id = request.data.get("path_id")
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
                or path_id == ""
            ):
                raise ValidationError(
                    "Bad Request: Please fill the form properly. All fields are required."
                )
            register_by = self.request.user
            declaracion = Declaracion.objects.get(id=declaracion_id)
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
