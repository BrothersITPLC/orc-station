from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics

from audit.serializers import TableNameSerializer

from ..models import AuditLog


class GetAuditLogTableName(generics.ListAPIView):
    """
    API view to retrieve all unique table names that have audit log entries.
    
    This endpoint is useful for populating filter dropdowns or getting an overview
    of which tables/models have been audited.
    """
    
    serializer_class = TableNameSerializer

    @extend_schema(
        summary="Get all audited table names",
        description="""Retrieve a list of all unique table names that have audit log entries.
        
        This endpoint returns distinct table names from the audit log, excluding 'django_migrations'.
        Useful for:
        - Populating filter dropdowns in audit log viewers
        - Getting an overview of which models are being tracked
        - Building audit reports by table
        """,
        tags=["Audit"],
        responses={
            200: TableNameSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view audit information"},
        },
        examples=[
            OpenApiExample(
                "Table Names Response",
                value=[
                    {"table_name": "driver"},
                    {"table_name": "exporter"},
                    {"table_name": "truck"},
                    {"table_name": "truck_owner"},
                    {"table_name": "workstation"},
                    {"table_name": "tax"},
                    {"table_name": "news"},
                    {"table_name": "declaration"},
                    {"table_name": "commodity"}
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            AuditLog.objects.exclude(table_name="django_migrations")
            .values_list("table_name", flat=True)
            .distinct()
        )
        print(queryset)
        queryset = [{"table_name": table_name} for table_name in queryset]
        return queryset
