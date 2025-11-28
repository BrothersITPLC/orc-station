from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework import filters, viewsets

from audit.serializers import AuditLogSerializer

from ..models import AuditLog


class AuditLogViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing audit logs.
    
    Provides read operations for AuditLog entities with filtering by table name and action.
    Audit logs track all create, update, and delete operations in the system.
    """
    
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["action", "table_name"]

    @extend_schema(
        summary="List all audit logs",
        description="""Retrieve a list of all audit logs in the system, excluding django_migrations. 
        
        **Filtering:**
        - Filter by `table_name` to see logs for a specific model/table
        - Filter by `action` to see specific types of operations (create, update, delete, custom)
        - Use search to find logs by action or table name
        
        **Audit Log Information:**
        - Tracks user actions across the system
        - Stores before/after snapshots of data changes
        - Includes timestamp and user information
        """,
        tags=["Audit"],
        parameters=[
            OpenApiParameter(
                name="table_name",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter logs by specific table/model name (e.g., 'exporter', 'driver', 'truck')",
                required=False,
            ),
            OpenApiParameter(
                name="action",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter logs by action type: 'create', 'update', 'delete', or 'custom'",
                required=False,
                enum=["create", "update", "delete", "custom"],
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter logs by action or table name",
                required=False,
            ),
        ],
        responses={
            200: AuditLogSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view audit logs"},
        },
        examples=[
            OpenApiExample(
                "List All Logs Response",
                value=[
                    {
                        "id": 1,
                        "user": 1,
                        "action": "create",
                        "object_id": "5",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "previous_snapshot": None,
                        "updated_snapshot": {
                            "first_name": "Abebe",
                            "last_name": "Tadesse",
                            "license_number": "DL123456"
                        },
                        "table_name": "driver",
                        "description": "Created new driver",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    },
                    {
                        "id": 2,
                        "user": 1,
                        "action": "update",
                        "object_id": "5",
                        "timestamp": "2024-01-15T14:20:00Z",
                        "previous_snapshot": {
                            "phone_number": "+251911111111"
                        },
                        "updated_snapshot": {
                            "phone_number": "+251922222222"
                        },
                        "table_name": "driver",
                        "description": "Updated driver phone number",
                        "created_at": "2024-01-15T14:20:00Z",
                        "updated_at": "2024-01-15T14:20:00Z"
                    }
                ],
                response_only=True,
            ),
            OpenApiExample(
                "Filter by Table Name",
                description="Example: GET /api/audit/?table_name=exporter",
                value=[
                    {
                        "id": 10,
                        "user": 2,
                        "action": "create",
                        "object_id": "3",
                        "timestamp": "2024-01-16T09:00:00Z",
                        "previous_snapshot": None,
                        "updated_snapshot": {
                            "first_name": "Chaltu",
                            "last_name": "Bekele",
                            "tin_number": "1234567890"
                        },
                        "table_name": "exporter",
                        "description": "Created new exporter",
                        "created_at": "2024-01-16T09:00:00Z",
                        "updated_at": "2024-01-16T09:00:00Z"
                    }
                ],
                response_only=True,
            ),
            OpenApiExample(
                "Filter by Action",
                description="Example: GET /api/audit/?action=delete",
                value=[
                    {
                        "id": 15,
                        "user": 1,
                        "action": "delete",
                        "object_id": "8",
                        "timestamp": "2024-01-17T11:30:00Z",
                        "previous_snapshot": {
                            "first_name": "Test",
                            "last_name": "User",
                            "license_number": "TEST123"
                        },
                        "updated_snapshot": None,
                        "table_name": "driver",
                        "description": "Deleted driver",
                        "created_at": "2024-01-17T11:30:00Z",
                        "updated_at": "2024-01-17T11:30:00Z"
                    }
                ],
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific audit log",
        description="Get detailed information about a specific audit log entry by its ID.",
        tags=["Audit"],
        responses={
            200: AuditLogSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this audit log"},
            404: {"description": "Not Found - Audit log with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "user": 1,
                    "action": "update",
                    "object_id": "5",
                    "timestamp": "2024-01-15T14:20:00Z",
                    "previous_snapshot": {
                        "phone_number": "+251911111111",
                        "email": "old@example.com"
                    },
                    "updated_snapshot": {
                        "phone_number": "+251922222222",
                        "email": "new@example.com"
                    },
                    "table_name": "driver",
                    "description": "Updated driver contact information",
                    "created_at": "2024-01-15T14:20:00Z",
                    "updated_at": "2024-01-15T14:20:00Z"
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create an audit log entry",
        description="Manually create an audit log entry. Typically, audit logs are created automatically by the system, but this endpoint allows for custom audit entries.",
        tags=["Audit"],
        request=AuditLogSerializer,
        responses={
            201: AuditLogSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
        },
        examples=[
            OpenApiExample(
                "Create Custom Audit Log",
                value={
                    "action": "custom",
                    "object_id": "123",
                    "table_name": "custom_operation",
                    "description": "Manual system adjustment performed",
                    "updated_snapshot": {
                        "operation": "data_migration",
                        "records_affected": 150
                    }
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update an audit log entry",
        description="Update an existing audit log entry. Note: Modifying audit logs should be done with caution as it affects audit trail integrity.",
        tags=["Audit"],
        request=AuditLogSerializer,
        responses={
            200: AuditLogSerializer,
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update an audit log entry",
        description="Partially update an audit log entry. Typically used to add additional description or metadata.",
        tags=["Audit"],
        request=AuditLogSerializer,
        responses={
            200: AuditLogSerializer,
            400: {"description": "Bad Request"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
        },
        examples=[
            OpenApiExample(
                "Update Description",
                value={
                    "description": "Updated description with additional context"
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete an audit log entry",
        description="Delete an audit log entry. Warning: Deleting audit logs should be avoided as it compromises audit trail integrity.",
        tags=["Audit"],
        responses={
            204: {"description": "Audit log successfully deleted"},
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = AuditLog.objects.exclude(table_name="django_migrations").all()
        table_name = self.request.query_params.get("table_name", None)
        action = self.request.query_params.get("action", None)

        if table_name:
            queryset = queryset.filter(table_name=table_name)

        if action:
            queryset = queryset.filter(action=action)

        return queryset
