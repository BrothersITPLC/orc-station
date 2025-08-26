from django.urls import include, path
from rest_framework.routers import DefaultRouter

from declaracions.withWieghtedBridge import CheckTheTruck

from . import views
from .checkLogic import CheckinLogic
from .payment import getDerashBill, manualPayment, payderash

router = DefaultRouter()

router.register(r"declaracion", views.DeclaracionViewSet)
router.register(
    r"completed_declaracion", views.CompletedJourney, basename="completed_declaracion"
)
router.register(r"checkin", views.CheckinViewSet)
router.register(r"commodity", views.CommodityViewSet)
router.register(r"paymentMethod", views.PaymentMethodViewSet)
router.register(r"change_truck", views.ChangeTruckViewSet)
router.register(
    r"ongoing-journey", views.OnGoingDeclaracionViewSet, basename="ongoing_declaracion"
)

urlpatterns = [
    path("check-truck/", CheckTheTruck.as_view(), name="check-truck"),
    path(
        "getDerashBill/<str:bill_id>/",
        getDerashBill.GetDerashPayment.as_view(),
        name="getDerashPayment",
    ),
    path("payWithDerash", payderash.DerashPay.as_view(), name="derashpayment"),
    path(
        "check-logic/<str:truck_plate>/",
        CheckinLogic.as_view(),
        name="check-logic",
    ),
    path(
        "updatedeclaracion/",
        views.UpdateDeclaracion.as_view(),
        name="update_declaracions",
    ),
    path("", include(router.urls)),
    path("manualPayment", manualPayment.Paymanually.as_view(), name="manualPayment"),
    path("addDeduction", views.AddDeduction.as_view(), name="addDeduction"),
]
