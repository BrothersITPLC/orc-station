from django.urls import path

from .views.adminCombinedTaxpayerReport import admin_combined_taxpayer_report
from .views.adminEachStationRegularRevenueByDateType import (
    admin_each_station_regular_revenue_by_date_type,
)
from .views.adminEachStationRevenueByDateType import (
    admin_each_station_revenue_by_date_type,
)
from .views.adminEachStationRevenueByDateTypeNoSum import (
    admin_each_station_revenue_by_date_type_no_sum,
)
from .views.adminEachStationRevenueTodayData import (
    admin_each_station_revenue_today_data,
)
from .views.adminEachStationWalkinRevenueByDateType import (
    admin_each_station_walkin_revenue_by_date_type,
)
from .views.adminEachStationWeightByDateType import (
    admin_each_station_weight_by_date_type,
)
from .views.adminRegisteredDriverEachStationByDateType import (
    admin_registered_driver_each_station_by_date_type,
)
from .views.adminRegisteredExportersEachStationByDateType import (
    admin_registered_exporters_each_station_by_date_type,
)
from .views.adminRevenueAndIssues import admin_revenue_and_issues
from .views.adminRevenueByStationAndController import (
    admin_revenue_by_station_and_controller,
)
from .views.adminTopRegularTaxPayerReport import admin_top_regular_taxpayer_report
from .views.adminTopTrucksReport import admin_top_trucks_report
from .views.adminTopWalkinTaxPayersReport import admin_top_walkin_taxpayer_report
from .views.byStationAndByTaxPayerType import stationTaxpayer_revenue_report
from .views.cashierCombinedRevenueByDateType import (
    cashier_combined_revenue_by_date_type,
)
from .views.cashierDriversRegisteredByDateType import (
    cashier_drivers_registered_by_date_type,
)
from .views.cashierRevenueByDateType import cashier_revenue_by_date_type
from .views.cashierTaxPayersRegisteredByDateType import (
    cashier_tax_payers_registered_by_date_type,
)
from .views.cashierTodayReport import cashier_today_report
from .views.cashierWeightByDateType import cashier_weight_by_date_type
from .views.controllerCombinedRevenueByDateType import (
    controller_combined_revenue_by_date_type,
)
from .views.controllerDriversRegisteredByDateType import (
    controller_drivers_registered_by_date_type,
)
from .views.controllerRevenueByDateType import controller_revenue_by_date_type
from .views.controllerTaxPayersRegisteredByDateType import (
    controller_tax_payers_registered_by_date_type,
)
from .views.controllerTodayReport import controller_today_report
from .views.controllerWeightByDateType import controller_weight_by_date_type

################################################################
from .views.dailyDashbord import daily_revenue_report, revenue_and_number
from .views.driverView import model_report
from .views.employeeRevenueReport import employee_revenue_report
from .views.monthlyDashbord import monthly_revenue_report
from .views.newRevenueTrends import revenue_trends_report
from .views.revenueBreakdown import revenue_breakdown_report
from .views.revenueReport import revenue_report
from .views.stationRevenue import station_revenue_report
from .views.statsOverview import stats_overview
from .views.taxPayerRevenueTrends import tax_payer_revenue_trends
from .views.taxRateAnalysis import tax_rate_analysis
from .views.topExportersReport import top_exporters_report
from .views.topTrucksReport import top_trucks_report
from .views.weekly_trends import weekly_revenue_report
from .views.workstationRevenueReport import workstation_revenue_report
from .views.yearlyDashbord import yearly_revenue_report

################################################################


urlpatterns = [
    path("report/<str:model_name>/", model_report, name="model_report"),
    path("revenue-report/", revenue_report, name="revenue_report"),
    path("yearly_revenue_report/", yearly_revenue_report, name="yearly_revenue_report"),
    path(
        "monthly_revenue_report/", monthly_revenue_report, name="monthly_revenue_report"
    ),
    path("daily_revenue_report/", daily_revenue_report, name="daily_revenue_report"),
    path("top_exporters_report/", top_exporters_report, name="top_exporters_report"),
    path("top_trucks_report/", top_trucks_report, name="top_trucks_report"),
    path(
        "workstation_revenue_report/",
        workstation_revenue_report,
        name="workstation_revenue_report",
    ),
    path(
        "revenue_and_number/",
        revenue_and_number,
        name="revenue_and_number",
    ),
    path("revenue-trends-report/", revenue_trends_report, name="revenue_trends_report"),
    path(
        "revenue-breakdown-report/",
        revenue_breakdown_report,
        name="revenue-breakdown-report",
    ),
    path(
        "station-revenue-report/",
        station_revenue_report,
        name="station-revenue-report",
    ),
    path("weekly-trends/", weekly_revenue_report, name="weekly-trends"),
    path(
        "stats-overview/",
        stats_overview,
        name="stats-overview",
    ),
    path(
        "tax-rate-analysis/",
        tax_rate_analysis,
        name="tax-rate-analysis",
    ),
    path(
        "station-taxpayer/",
        stationTaxpayer_revenue_report,
        name="station-tax-payer",
    ),
    path(
        "employee-revenue-report/",
        employee_revenue_report,
        name="employee-revenue-report",
    ),
    path(
        "tax-payer-revenue-trends/",
        tax_payer_revenue_trends,
        name="tax-payer-revenue-trends",
    ),
    ###############################################
    path(
        "controller-today-report/",
        controller_today_report,
        name="controller-today-report",
    ),
    path(
        "controller-revenue-by-date-type/",
        controller_revenue_by_date_type,
        name="controller-revenue-by-date-type",
    ),
    path(
        "controller-weight-by-date-type/",
        controller_weight_by_date_type,
        name="controller-weight-by-date-type",
    ),
    path(
        "controller-combined-revenue-by-date-type/",
        controller_combined_revenue_by_date_type,
        name="controller-combined-revenue-by-date-type",
    ),
    path(
        "controller-drivers-registered-by-date-type/",
        controller_drivers_registered_by_date_type,
        name="controller-drivers-registered-by-date-type",
    ),
    path(
        "controller-tax-payers-registered-by-date-type/",
        controller_tax_payers_registered_by_date_type,
        name="controller-tax-payers-registered-by-date-type",
    ),
    ###############################################
    path(
        "cashier-today-report/",
        cashier_today_report,
        name="cashier-today-report",
    ),
    path(
        "cashier-revenue-by-date-type/",
        cashier_revenue_by_date_type,
        name="cashier-revenue-by-date-type",
    ),
    path(
        "cashier-weight-by-date-type/",
        cashier_weight_by_date_type,
        name="cashier-weight-by-date-type",
    ),
    path(
        "cashier-combined-revenue-by-date-type/",
        cashier_combined_revenue_by_date_type,
        name="cashier-combined-revenue-by-date-type",
    ),
    path(
        "cashier-drivers-registered-by-date-type/",
        cashier_drivers_registered_by_date_type,
        name="cashier-drivers-registered-by-date-type",
    ),
    path(
        "cashier-tax-payers-registered-by-date-type/",
        cashier_tax_payers_registered_by_date_type,
        name="cashier-tax-payers-registered-by-date-type",
    ),
    ###############################################
    path(
        "admin-each-station-revenue-today-data/",
        admin_each_station_revenue_today_data,
        name="admin-each-station-revenue-today-data",
    ),
    path(
        "admin-each-station-revenue-by-date-type/",
        admin_each_station_revenue_by_date_type,
        name="admin-each-station-revenue-by-date-type",
    ),
    path(
        "admin-each-station-regular-revenue-by-date-type/",
        admin_each_station_regular_revenue_by_date_type,
        name="admin-each-station-regular-revenue-by-date-type",
    ),
    path(
        "admin-each-station-walkin-revenue-by-date-type/",
        admin_each_station_walkin_revenue_by_date_type,
        name="admin-each-station-walkin-revenue-by-date-type",
    ),
    path(
        "admin-each-station-revenue-by-date-type-no-sum/",
        admin_each_station_revenue_by_date_type_no_sum,
        name="admin-each-station-revenue-by-date-type-no-sum",
    ),
    path(
        "admin-each-station-weight-by-date-type/",
        admin_each_station_weight_by_date_type,
        name="admin-each-station-weight-by-date-type",
    ),
    path(
        "admin-registered-exporters-each-station-by-date-type/",
        admin_registered_exporters_each_station_by_date_type,
        name="admin-registered-exporters-each-station-by-date-type",
    ),
    path(
        "admin-registered-driver-each-station_by-date-type/",
        admin_registered_driver_each_station_by_date_type,
        name="admin-registered-driver-each-station_by-date-type",
    ),
    path(
        "admin-top-trucks-report/",
        admin_top_trucks_report,
        name="admin-top-trucks-report",
    ),
    path(
        "admin-combined-taxpayer-report/",
        admin_combined_taxpayer_report,
        name="admin-combined-taxpayer-report",
    ),
    path(
        "admin-top-regular-taxpayer-report/",
        admin_top_regular_taxpayer_report,
        name="admin-top-regular-taxpayer-report",
    ),
    path(
        "admin-top-walkin-taxpayer-report/",
        admin_top_walkin_taxpayer_report,
        name="admin-top-walkin-taxpayer-report",
    ),
    path(
        "admin-revenue-by-station-and-controller/",
        admin_revenue_by_station_and_controller,
        name="admin-revenue-by-station-and-controller",
    ),
    path(
        "admin-revenue-and-issues/",
        admin_revenue_and_issues,
        name="admin-revenue-and-issues",
    ),
]
