"""
Vistas de perfil del comprador (Bearer customer_access).

- /api/customer/profile/  ≡ /api/customer-auth/me/ (mismo view).
- /api/customer/addresses/ + /<id>/ — direcciones de envío, scopeadas al
  customer autenticado (IDOR → 404, nunca 403-leak).
- /api/customer/memberships/ — sus membresías por tienda (lectura).
"""
import logging

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.models import CustomerAddress
from StoreApp.domains.customers.serializers import (
    CustomerAddressSerializer,
    CustomerProfileUpdateSerializer,
    CustomerSerializer,
)
from StoreApp.domains.customers.services.customers import (
    promote_default_address,
    save_address_defaults,
)
from StoreApp.domains.customers.views.auth_views import CustomerApiThrottle

logger  =   logging.getLogger(__name__)


class CustomerProfileView(APIView):
    """
    GET/PATCH /api/customer/profile/ — alias REST del perfil (misma
    lógica que customer-auth/me). PATCH: whitelist de
    CustomerProfileUpdateSerializer.
    """
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerApiThrottle]

    def get(self, request):
        return Response({'customer': CustomerSerializer(request.customer).data})

    def patch(self, request):
        serializer  =   CustomerProfileUpdateSerializer(request.customer, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response({'customer': CustomerSerializer(request.customer).data})


class CustomerAddressListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /api/customer/addresses/ — solo las del customer autenticado.
    `is_default` único por cliente lo garantiza save_address_defaults.
    """
    serializer_class        =   CustomerAddressSerializer
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerApiThrottle]

    def get_queryset(self):
        return CustomerAddress.objects.filter(customer = self.request.customer)

    def perform_create(self, serializer):
        address =   serializer.save(customer = self.request.customer)
        save_address_defaults(address, address.is_default)


class CustomerAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/customer/addresses/<id>/ — IDOR: el queryset ya
    está scopeado al customer; una dirección ajena devuelve 404.
    """
    serializer_class        =   CustomerAddressSerializer
    permission_classes      =   [IsCustomer]
    authentication_classes  =   [CustomerJWTAuthentication]
    throttle_classes        =   [CustomerApiThrottle]
    http_method_names       =   ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return CustomerAddress.objects.filter(customer = self.request.customer)

    def perform_update(self, serializer):
        address =   serializer.save()
        save_address_defaults(address, address.is_default)

    def perform_destroy(self, instance):
        was_default    =   instance.is_default
        customer       =   instance.customer
        instance.delete()
        if was_default:
            #La principal quedó huérfana: promover la más reciente.
            promote_default_address(customer)
