"""
Otras vistas autenticadas del comprador: membresías por tienda.
"""
from rest_framework import generics

from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.models import StoreMembership
from StoreApp.domains.customers.serializers import CustomerMembershipSerializer
from StoreApp.domains.customers.views.auth_views import CustomerApiThrottle


class CustomerMembershipListView(generics.ListAPIView):
    """
    GET /api/customer/memberships/ — tiendas donde el comprador es cliente
    (status/tags/joined_at — contrato con track D). Solo lectura: la
    membresía la crean register/login/google/checkout, no el cliente.
    """
    serializer_class        =   CustomerMembershipSerializer
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerApiThrottle]

    def get_queryset(self):
        return (
            StoreMembership.objects
            .filter(customer = self.request.customer)
            .select_related('store__user')
            .order_by('-joined_at')
        )
