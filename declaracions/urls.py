from django.urls import include, path
from rest_framework.routers import DefaultRouter

from declaracions.views import (
    AddDeduction,
    ChangeTruckViewSet,
    CheckinLogic,
    CheckinViewSet,
    CheckTheTruck,
    CommodityViewSet,
    CompletedJourney,
    DeclaracionViewSet,
    OnGoingDeclaracionViewSet,
    PaymentMethodViewSet,
    UpdateDeclaracion,
)

from .payment import getDerashBill, manualPayment, payderash

router = DefaultRouter()

router.register(r"declaracion", DeclaracionViewSet)
router.register(
    r"completed_declaracion", CompletedJourney, basename="completed_declaracion"
)
router.register(r"checkin", CheckinViewSet)
router.register(r"commodity", CommodityViewSet)
router.register(r"paymentMethod", PaymentMethodViewSet)
router.register(r"change_truck", ChangeTruckViewSet)
router.register(
    r"ongoing-journey", OnGoingDeclaracionViewSet, basename="ongoing_declaracion"
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
        UpdateDeclaracion.as_view(),
        name="update_declaracions",
    ),
    path("", include(router.urls)),
    path("manualPayment", manualPayment.Paymanually.as_view(), name="manualPayment"),
    path("addDeduction", AddDeduction.as_view(), name="addDeduction"),
]
