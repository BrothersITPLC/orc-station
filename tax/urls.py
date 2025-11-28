from django.urls import include, path
from rest_framework.routers import DefaultRouter

from tax.views import TaxViewSet

router = DefaultRouter()
router.register(r"tax", TaxViewSet)

urlpatterns = [path("", include(router.urls))]
