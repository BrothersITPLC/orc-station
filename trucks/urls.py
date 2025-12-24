from django.urls import include, path
from rest_framework.routers import DefaultRouter

from trucks.views import TruckFetchViewSet, TruckViewSet

router = DefaultRouter()
router.register(r"trucks", TruckViewSet, basename="trucks")
router.register(r"vehicle", TruckFetchViewSet, basename="vehicle")
urlpatterns = [
    path("", include(router.urls)),
]
