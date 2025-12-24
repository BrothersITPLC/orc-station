from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from users.admin_views import RateLimitedAdminLoginView


api_urlpatterns = [
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
    path("api/sync/", include("orcSync.urls")),
]

from users.views import custom_404_view

urlpatterns = [
    # API Schema and Documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Legacy endpoints for backward compatibility
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="schema-swagger-ui",
    ),
    path("api_schema/", SpectacularAPIView.as_view(), name="schema-json"),
    # Admin with rate-limited login (5 attempts per 5 minutes)
    path("admin/login/", RateLimitedAdminLoginView.as_view(), name='admin_login'),
    path("admin/", admin.site.urls),
]

urlpatterns += api_urlpatterns


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = custom_404_view
