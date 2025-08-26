from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RegionorCityViewset, WoredaViewset, ZoneorSubcityViewset

router = DefaultRouter()
router.register(r"regions", RegionorCityViewset)
router.register(r"zones", ZoneorSubcityViewset)
router.register(r"woredas", WoredaViewset)

urlpatterns = [
    path("", include(router.urls)),
]
