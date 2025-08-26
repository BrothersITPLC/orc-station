from rest_framework import filters, generics, views, viewsets
from rest_framework.permissions import AllowAny

from .models import AuditLog
from .serializers import AuditLogSerializer, TableNameSerializer


class AuditLogViewSet(viewsets.ModelViewSet):
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["action", "table_name"]
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = AuditLog.objects.exclude(table_name="django_migrations").all()
        table_name = self.request.query_params.get("table_name", None)
        action = self.request.query_params.get("action", None)

        if table_name:
            queryset = queryset.filter(table_name=table_name)

        if action:
            queryset = queryset.filter(action=action)

        return queryset


class GetAuditLogTableName(generics.ListAPIView):
    serializer_class = TableNameSerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            AuditLog.objects.exclude(table_name="django_migrations")
            .values_list("table_name", flat=True)
            .distinct()
        )
        print(queryset)
        # Convert the list of table names to a list of dictionaries
        queryset = [{"table_name": table_name} for table_name in queryset]
        return queryset
        # without duplication
