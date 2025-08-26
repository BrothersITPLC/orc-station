from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ControllerForSupervisor,
    EmployeeByWorkStation,
    UnEmployeeByWorkStation,
    WorkedAtViewSet,
    WorkStationsByEmployee,
    WorkStationViewSet,
)

router = DefaultRouter()
router.register(r"workstations", WorkStationViewSet, basename="workstations")
router.register(r"workedat", WorkedAtViewSet, basename="workedat")
urlpatterns = [
    path("", include(router.urls)),
    path(
        "workstationsbyemployee/<int:employee_id>/",
        WorkStationsByEmployee.as_view(),
        name="workstationsbyemployee",
    ),
    path(
        "unemployeebyworkstation/<int:station_id>/",
        UnEmployeeByWorkStation.as_view(),
        name="unemployeebyworkstation",
    ),
    path(
        "employeebyworkstation/<int:station_id>/",
        EmployeeByWorkStation.as_view(),
        name="employeebyworkstation",
    ),
    path(
        "workedat/<int:station_id>/<int:employee_id>/",
        WorkedAtViewSet.as_view({"delete": "destroy"}),
        name="workedat-delete",
    ),
    path(
        "controllerbySupervisor/",
        ControllerForSupervisor.as_view(),
        name="controllerbyworkstation",
    ),
]
