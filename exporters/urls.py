# exporters/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"exporters", views.ExporterViewSet)
router.register(r"taxpayertype", views.TaxPayerTypeViewSets)

urlpatterns = [
    path("", include(router.urls)),
]
