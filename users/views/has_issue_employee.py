from django.db.models import Case, Count, IntegerField, Q, When
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, viewsets

from helper.custom_pagination import CustomLimitOffsetPagination
from users.models import CustomUser
from users.serializers import IssueUserSerializer

from .permissions import GroupPermission


class IssueEmployeeViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing employees with reported issues.
    
    Returns users who have at least one report, with counts of total and unread reports.
    """
    
    serializer_class = IssueUserSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_customuser"
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "phone_number", "username"]
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        summary="List employees with issues",
        description="""Retrieve a list of employees who have reported issues.
        
        **Features:**
        - Returns only users with at least one report
        - Includes total report count
        - Includes unread report count
        - Supports search by name, email, phone, username
        
        **Use Case:**
        - Monitoring employee issues
        - Tracking unresolved reports
        - Admin oversight
        """,
        tags=["Users - Management"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter by name, email, phone, or username",
                required=False,
            ),
        ],
        responses={
            200: IssueUserSerializer(many=True),
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
