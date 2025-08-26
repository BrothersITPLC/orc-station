from django.shortcuts import render
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from helper.permission import has_custom_permission
from users.views.permissions import GroupPermission

from .models import RegionOrCity, Woreda, ZoneOrSubcity
from .serializers import (
    RegionOrCitySerializer,
    WoredaSerializer,
    ZoneOrSubcitySerializer,
)

# Create your views here.


class RegionorCityViewset(viewsets.ModelViewSet):
    """
    A viewset for managing regions or cities.
    """

    queryset = RegionOrCity.objects.all()
    serializer_class = RegionOrCitySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_regionorcity"

    @swagger_auto_schema(
        operation_summary="List all regions or cities",
        operation_description="Retrieve a list of all regions or cities.",
        tags=["RegionOrCity"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new region or city",
        operation_description="Add a new region or city to the database.",
        tags=["RegionOrCity"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

        return [permission() for permission in self.permission_classes]

    def get_permissions(self):
        return has_custom_permission(self, "regionorcity")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)


class ZoneorSubcityViewset(viewsets.ModelViewSet):
    """
    A viewset for managing zones or sub-cities.
    """

    queryset = ZoneOrSubcity.objects.all()
    serializer_class = ZoneOrSubcitySerializer
    permission_classes = [GroupPermission]
    permission_required = "view_zoneorsubcity"

    @swagger_auto_schema(
        operation_summary="Retrieve zones or sub-cities by region",
        operation_description="Get all zones or sub-cities within a specific region.",
        tags=["ZoneOrSubcity"],
        manual_parameters=[
            openapi.Parameter(
                "region_id",
                openapi.IN_PATH,
                description="ID of the region to filter zones by",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={200: ZoneOrSubcitySerializer(many=True)},
    )

    # the endpoint will be curl -X GET http://localhost:8000/zones/by-region/1/
    @action(detail=False, methods=["get"], url_path="by-region/(?P<region_id>[^/.]+)")
    def get_by_region(self, request, region_id=None):

        zones = self.queryset.filter(region_id=region_id)
        serializer = self.get_serializer(zones, many=True)
        return Response(serializer.data)

    def get_permissions(self):

        if self.action == "get_by_region":
            self.action = "list"
        return has_custom_permission(self, "zoneorsubcity")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)


class WoredaViewset(viewsets.ModelViewSet):
    """
    A viewset for managing woredas.
    """

    queryset = Woreda.objects.all()
    serializer_class = WoredaSerializer
    permission_classes = [GroupPermission]
    permission_required = "view_woreda"

    @swagger_auto_schema(
        operation_summary="Retrieve woredas by zone or sub-city",
        operation_description="Get all woredas within a specific zone or sub-city.",
        tags=["Woreda"],
        manual_parameters=[
            openapi.Parameter(
                "zone_id",
                openapi.IN_PATH,
                description="ID of the zone or sub-city to filter woredas by",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={200: WoredaSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="by-zone/(?P<zone_id>[^/.]+)")
    @action(detail=False, methods=["get"], url_path="by-zone/(?P<zone_id>[^/.]+)")
    def get_by_ZoneSubcity(self, request, zone_id=None):
        woredas = self.queryset.filter(zone_id=zone_id)
        serializer = self.get_serializer(woredas, many=True)
        return Response(serializer.data)

    def get_permissions(self):

        if self.action == "get_by_ZoneSubcity":
            self.action = "list"
        return has_custom_permission(self, "woreda")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)
