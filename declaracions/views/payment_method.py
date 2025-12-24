from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from declaracions.serializers import PaymentMethodSerializer

from ..models import PaymentMethod


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing payment methods.
    
    Provides CRUD operations for PaymentMethod entities.
    """
    
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer

    @extend_schema(
        summary="List all payment methods",
        description="Retrieve a list of all available payment methods.",
        tags=["Declarations - Payment Methods"],
        responses={
            200: PaymentMethodSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new payment method",
        description="Create a new payment method.",
        tags=["Declarations - Payment Methods"],
        request=PaymentMethodSerializer,
        responses={
            201: PaymentMethodSerializer,
            400: {"description": "Bad Request"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific payment method",
        description="Get detailed information about a specific payment method by its ID.",
        tags=["Declarations - Payment Methods"],
        responses={
            200: PaymentMethodSerializer,
            404: {"description": "Not Found"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a payment method",
        description="Update all fields of an existing payment method.",
        tags=["Declarations - Payment Methods"],
        request=PaymentMethodSerializer,
        responses={
            200: PaymentMethodSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a payment method",
        description="Update specific fields of an existing payment method.",
        tags=["Declarations - Payment Methods"],
        request=PaymentMethodSerializer,
        responses={
            200: PaymentMethodSerializer,
            400: {"description": "Bad Request"},
            404: {"description": "Not Found"},
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a payment method",
        description="Permanently delete a payment method from the database.",
        tags=["Declarations - Payment Methods"],
        responses={
            204: {"description": "Payment method successfully deleted"},
            404: {"description": "Not Found"},
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
