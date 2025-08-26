from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10  # Number of items per page
    limit_query_param = "limit"
    offset_query_param = "offset"

    def get_paginated_response(self, data):
        total_items = self.count  # Total number of items
        limit = self.get_limit(self.request)  # Limit from request
        offset = self.get_offset(self.request)  # Offset from request
        limit = self.get_limit(self.request)  # Get limit from request or default
        offset = self.get_offset(self.request)
        # Calculate total pages and current page
        total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)
        current_page = (offset // limit) + 1

        return Response(
            {
                "total_items": total_items,  # Total number of items
                "limit": limit,  # Limit (page size)
                "offset": offset,  # Offset (starting index)
                "total_pages": total_pages,  # Total number of pages
                "current_page": current_page,  # Current page number
                "results": data,  # Paginated data
            }
        )
