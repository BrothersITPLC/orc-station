from rest_framework import viewsets,permissions
from users.serializers import DepartmentSerializer
from users.models import Department

class DepartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer