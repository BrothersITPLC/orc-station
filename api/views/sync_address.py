from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import StationCredential
from api.serializers import StationCredentialSerializer


class StationCredentialListCreateView(APIView):
    def get(self, request, format=None):

        sync_configs = StationCredential.objects.all()
        serializer = StationCredentialSerializer(sync_configs, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):

        serializer = StationCredentialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StationCredentialDetailView(APIView):

    def get_object(self, pk):

        try:
            return StationCredential.objects.get(pk=pk)
        except StationCredential.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        sync_config = self.get_object(pk)
        serializer = StationCredentialSerializer(sync_config)
        return Response(serializer.data)

    def patch(self, request, pk, format=None):
        sync_config = self.get_object(pk)
        serializer = StationCredentialSerializer(
            sync_config, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        sync_config = self.get_object(pk)
        sync_config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
