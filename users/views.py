from .views.auth_views import LoginView, LogoutView, SignupView, VerifyEmail
from .views.department_views import DepartmentViewSet
from .views.diactivate_views import ActivateDiactivateView
from .views.password_reset_views import PasswordResetConfirmView
from .views.password_reset_views import (
    PasswordResetConfirmView as PasswordResetConfirmAPIView,
)
from .views.password_reset_views import PasswordResetRequestView
from .views.password_reset_views import (
    PasswordResetRequestView as PasswordResetRequestAPIView,
)
from .views.permissions import GroupPermission
from .views.role_views import GroupViewSet, PermissionViewSet
from .views.user_views import MyView, UserListView, UserViewSet
