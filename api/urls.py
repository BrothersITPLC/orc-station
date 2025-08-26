from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import CustomUserViewSet

router = DefaultRouter()
router.register(r"user", CustomUserViewSet, basename="user-api")

urlpatterns = [
    path("", include(router.urls)),
]
