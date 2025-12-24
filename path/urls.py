from django.urls import include, path
from rest_framework.routers import DefaultRouter

from path.views import (
    AddPath,
    AddPathStation,
    PathStationViewSet,
    PathViewSet,
    UpdatePathStationOrder,
)

router = DefaultRouter()
router.register(r"path", PathViewSet)
router.register(r"pathstation", PathStationViewSet)
urlpatterns = [
    path("", include(router.urls)),
    path("add_path/", AddPath.as_view(), name="add_path"),
    path(
        "update_path/",
        UpdatePathStationOrder.as_view(),
        name="update_path",
    ),
    path("add_path_station/", AddPathStation.as_view(), name="add_path_station"),
]
