from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from .models import News
from .serializers import NewsSerializer


class NewsViewSet(ModelViewSet):
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    pagination_class = CustomLimitOffsetPagination
    permission_classes = [GroupPermission]
    permission_required = "view_news"
    filter_backends = [SearchFilter]
    search_fields = ["title", "content"]

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def get_permissions(self):
        return has_custom_permission(self, "news")
