from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet, GetAuditLogTableName

router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "audit-log-table-names/",
        GetAuditLogTableName.as_view(),
        name="audit-log-table-names",
    ),
]
