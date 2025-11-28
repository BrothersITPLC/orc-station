from django.urls import path
from rest_framework.routers import DefaultRouter

from localcheckings.views import (
    CheckinWithoutTruckView,
    UpdateLocalJourney,
    WithoutTruckCheckinLogic,
    WithoutTruckJourneyViewset,
)

router = DefaultRouter()
router.register(
    "journey_without_truck",
    WithoutTruckJourneyViewset,
    basename="journey_without_truck",
)
urlpatterns = [
    path(
        "without-truck-checkin",
        CheckinWithoutTruckView.as_view(),
        name="without_truck_checkin",
    ),
    path(
        "updating_without_truck_journey/<journey_id>",
        UpdateLocalJourney.as_view(),
        name="update_without_truck_journey",
    ),
    path(
        "without-truck-checking-logic/<unique_id>",
        WithoutTruckCheckinLogic.as_view(),
        name="without_truck_checkin_logic",
    ),
]
urlpatterns += router.urls
