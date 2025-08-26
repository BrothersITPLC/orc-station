from django.shortcuts import get_object_or_404
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey

from api.serializers import CustomUserSerializer
from users.models import CustomUser


class CustomUserViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAPIKey]
    queryset = CustomUser.objects.filter(role__name__in=["controller", "admin"])
    serializer_class = CustomUserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "email", "username"]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user_id = kwargs.get("pk", None)
        username = request.query_params.get("username", None)

        if user_id:
            user = get_object_or_404(CustomUser, id=user_id)
        elif username:
            user = get_object_or_404(CustomUser, username=username)
        else:
            return Response(
                {"detail": "Provide either 'id' or 'username'."}, status=400
            )

        serializer = self.get_serializer(user)
        return Response(serializer.data)
