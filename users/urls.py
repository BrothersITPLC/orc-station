from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"groups", views.GroupViewSet)
router.register(r"permissions", views.PermissionViewSet)
router.register(r"departments", views.DepartmentViewSet)
# router.register(r'profile', views.UserProfileViewSet, basename='profile')
urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("signup", views.SignupView.as_view(), name="signup"),
    path("forget", views.PasswordResetRequestView.as_view(), name="forget"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "issue_employee/",
        views.IssueEmployeeViewSet.as_view({"get": "list"}),
        name="issueEmployee",
    ),
    path("logout", views.LogoutView.as_view(), name="logout"),
    # path("view",views.MyView.as_view(),name="view"),
    path(
        "profile", views.UserProfileViewSet.as_view({"get": "profile"}), name="profile"
    ),
    path(
        "update-profile",
        views.UserProfileViewSet.as_view({"patch": "update_profile"}),
        name="update-profile",
    ),
    path("assign-station", views.AssignWorkStation.as_view(), name="assign-station"),
    path(
        "activate_diactivate",
        views.ActivateandDeactivateUser.as_view(),
        name="activating_diactivate",
    ),
    path("give_report", views.GiveReportIssueForEmployer.as_view(), name="give_report"),
    path(
        "read_report/<uuid:user_id>", views.ReadReportIsue.as_view(), name="read_report"
    ),    
    path(
        "admin-password-reset",
        views.AdminPasswordResetView.as_view(),
        name="admin-password-reset",
    ),
    path("verify-user", views.VerifyUserView.as_view(), name="verify-user"),
]

urlpatterns += router.urls
# path('view', views.MyView.as_view(), name='logout'),
