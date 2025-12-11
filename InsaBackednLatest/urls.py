from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

from users.views import custom_404_view

urlpatterns = [
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("api_schema/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/", include("trucks.urls")),
    path("api/", include("workstations.urls")),
    path("api/", include("drivers.urls")),
    path("api/", include("declaracions.urls")),
    path("api/", include("exporters.urls")),
    path("api/", include("analysis.urls")),
    path("api/", include("tax.urls")),
    path("api/", include("address.urls")),
    path("api/", include("audit.urls")),
    path("api/", include("localcheckings.urls")),
    path("api/", include("path.urls")),
    path("api/", include("news.urls")),
    path("api/", include("api.urls")),
    path("api/", include("orcSync.urls")),
]

# ✅ Add static + media only when DEBUG=True
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = custom_404_view
