from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet

from helper.custom_pagination import CustomLimitOffsetPagination
from helper.permission import has_custom_permission
from news.serializers import NewsSerializer
from users.views.permissions import GroupPermission

from ..models import News


class NewsViewSet(ModelViewSet):
    """
    A viewset for managing news articles.
    
    Provides CRUD operations for News entities with search functionality.
    The author is automatically set to the current user when creating news.
    """
    
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    pagination_class = CustomLimitOffsetPagination
    permission_classes = [GroupPermission]
    permission_required = "view_news"
    filter_backends = [SearchFilter]
    search_fields = ["title", "content"]

    @extend_schema(
        summary="List all news articles",
        description="Retrieve a paginated list of all news articles in the system. Supports search by title and content.",
        tags=["News"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search term to filter news by title or content",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of results to return per page",
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="The initial index from which to return the results",
                required=False,
            ),
        ],
        responses={
            200: NewsSerializer(many=True),
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view news"},
        },
        examples=[
            OpenApiExample(
                "List Response Example",
                value={
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "title": "New Tax Regulations Announced",
                            "content": "The Oromia Revenue Commission has announced new tax regulations effective from next month...",
                            "image": "/media/news/tax_regulations.jpg",
                            "published_at": "2024-01-15T10:30:00Z",
                            "author": 1,
                            "created_at": "2024-01-15T10:00:00Z",
                            "updated_at": "2024-01-15T10:00:00Z"
                        },
                        {
                            "id": 2,
                            "title": "System Maintenance Scheduled",
                            "content": "The ORC system will undergo scheduled maintenance this weekend...",
                            "image": None,
                            "published_at": "2024-01-16T09:00:00Z",
                            "author": 1,
                            "created_at": "2024-01-16T08:30:00Z",
                            "updated_at": "2024-01-16T08:30:00Z"
                        }
                    ]
                },
                response_only=True,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new news article",
        description="Create a new news article. The author will be automatically set to the current authenticated user. Images can be uploaded as multipart/form-data.",
        tags=["News"],
        request=NewsSerializer,
        responses={
            201: NewsSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to create news"},
        },
        examples=[
            OpenApiExample(
                "Create News Request",
                value={
                    "title": "New Tax Regulations Announced",
                    "content": "The Oromia Revenue Commission has announced new tax regulations effective from next month. All exporters are advised to review the updated guidelines.",
                    "published_at": "2024-01-15T10:30:00Z"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create News Response",
                value={
                    "id": 1,
                    "title": "New Tax Regulations Announced",
                    "content": "The Oromia Revenue Commission has announced new tax regulations effective from next month. All exporters are advised to review the updated guidelines.",
                    "image": None,
                    "published_at": "2024-01-15T10:30:00Z",
                    "author": 1,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z"
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific news article",
        description="Get detailed information about a specific news article by its ID.",
        tags=["News"],
        responses={
            200: NewsSerializer,
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to view this news article"},
            404: {"description": "Not Found - News article with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Retrieve Response",
                value={
                    "id": 1,
                    "title": "New Tax Regulations Announced",
                    "content": "The Oromia Revenue Commission has announced new tax regulations effective from next month. All exporters are advised to review the updated guidelines.",
                    "image": "/media/news/tax_regulations.jpg",
                    "published_at": "2024-01-15T10:30:00Z",
                    "author": 1,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z"
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a news article",
        description="Update all fields of an existing news article. All fields are required.",
        tags=["News"],
        request=NewsSerializer,
        responses={
            200: NewsSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this news article"},
            404: {"description": "Not Found - News article with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Update Request",
                value={
                    "title": "Updated: New Tax Regulations Announced",
                    "content": "The Oromia Revenue Commission has announced new tax regulations effective from next month. All exporters are advised to review the updated guidelines. Additional details have been added.",
                    "published_at": "2024-01-15T10:30:00Z"
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a news article",
        description="Update specific fields of an existing news article. Only provided fields will be updated.",
        tags=["News"],
        request=NewsSerializer,
        responses={
            200: NewsSerializer,
            400: {"description": "Bad Request - Invalid data provided"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to update this news article"},
            404: {"description": "Not Found - News article with the specified ID does not exist"},
        },
        examples=[
            OpenApiExample(
                "Partial Update - Title Only",
                value={
                    "title": "Updated: New Tax Regulations Announced"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Partial Update - Content Only",
                value={
                    "content": "Updated content with more details about the new regulations."
                },
                request_only=True,
            ),
        ],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a news article",
        description="Permanently delete a news article from the database.",
        tags=["News"],
        responses={
            204: {"description": "No Content - News article successfully deleted"},
            401: {"description": "Unauthorized - Authentication credentials were not provided or are invalid"},
            403: {"description": "Forbidden - You do not have permission to delete this news article"},
            404: {"description": "Not Found - News article with the specified ID does not exist"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def get_permissions(self):
        return has_custom_permission(self, "news")
