from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import WorkStationSerializer
from workstations.models import WorkStation


class WorkStationListView(APIView):

    def get(self, request, format=None):
        workstations = WorkStation.objects.all()
        serializer = WorkStationSerializer(workstations, many=True)
        return Response(serializer.data)
