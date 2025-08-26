from django.db.models import Case, Count, IntegerField, Q, When
from rest_framework import filters, viewsets

from helper.custom_pagination import CustomLimitOffsetPagination
from users.models import CustomUser
from users.serializers import IssueUserSerializer

from .permissions import GroupPermission


class IssueEmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = IssueUserSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_customuser"
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "phone_number", "username"]
    pagination_class = CustomLimitOffsetPagination

    def get_queryset(self):
        return CustomUser.objects.annotate(
            total_reports=Count("employee_reports", distinct=True),
            unread_reports=Count(
                Case(
                    When(employee_reports__is_seen=False, then=1),
                    output_field=IntegerField(),
                ),
                distinct=True,
            ),
        ).filter(total_reports__gt=0)
