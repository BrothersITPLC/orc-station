from django.urls import include, path
from rest_framework.routers import DefaultRouter

from exporters.view import ExporterViewSet, TaxPayerTypeViewSets

router = DefaultRouter()
router.register(r"exporters", ExporterViewSet)
router.register(r"taxpayertype", TaxPayerTypeViewSets)

urlpatterns = [
    path("", include(router.urls)),
]
