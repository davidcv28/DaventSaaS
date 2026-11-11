"""
Pedidos del COMPRADOR logueado (e-commerce DAVENT — track F).

- GET /api/customer/orders/                    → sus pedidos en TODAS las
  tiendas donde compró (más nuevos primero, paginado por el default del
  proyecto). Filtros opcionales: `store=<slug>` y `status=<STATUS>`
  (validado contra Order.Status — un valor inválido devuelve lista
  vacía, nunca un 500 ni un filtro laxo).
- GET /api/customer/orders/<tracking_token>/   → detalle del pedido
  PROPIO por la misma payload pública de seguimiento
  (`order_tracking_payload`: ya audita PII — sin email/teléfono/
  documento del snapshot).

Auth: CustomerJWTAuthentication + IsCustomer (request.customer — la
cuenta global del comprador, NO auth.User). Anti-IDOR: el queryset y el
detalle filtran `customer=request.customer` — el token de otro
comprador es 404, igual que un token inexistente (no se revela que
existe). El tracking_token viaja en la lista porque ES la credencial
que el front usa para linkear /seguimiento; el id numérico no sale.

Gate por plan: NINGUNO a propósito — son lecturas de pedidos YA
emitidos del propio comprador (misma doctrina que el tracking público
por token: el cliente ya pagó, su historial no desaparece si el dueño
pierde `has_ecommerce`). Lo que el plan apaga son las ventas NUEVAS
(orders/cart/checkout vía orders_enabled), no los datos existentes.
"""
from django.http import Http404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.views.auth_views import CustomerApiThrottle
from StoreApp.domains.orders.models import Order
from StoreApp.domains.orders.serializers.serializers import (
    CustomerOrderListSerializer,
)
from StoreApp.domains.orders.services.checkout import order_tracking_payload


class CustomerOrderListView(generics.ListAPIView):
    """
    Bandeja de pedidos del comprador autenticado. Paginado DRF
    (DaventPageNumberPagination, PAGE_SIZE=10) — la respuesta es
    {count, next, previous, results} como el resto de listados.
    """
    serializer_class        =   CustomerOrderListSerializer
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get_queryset(self):
        qs  =   (
            Order.objects
            .filter(customer = self.request.customer)
            .select_related('store', 'store__customization', 'store__user')
            .prefetch_related('items')
            .order_by('-created_at', '-id')
        )
        store_slug  =   (self.request.query_params.get('store') or '').strip().lower()
        if store_slug:
            qs  =   qs.filter(store__slug = store_slug)
        status_param    =   (self.request.query_params.get('status') or '').strip().upper()
        if status_param:
            #Validación contra los choices del modelo: inválido →
            #queryset vacío (mismo criterio que la bandeja del dueño).
            qs  =   qs.filter(status = status_param) if status_param in Order.Status.values else qs.none()
        return qs


class CustomerOrderDetailView(APIView):
    """
    Detalle del pedido propio por tracking_token. Devuelve la payload
    pública de seguimiento (events + items + totales + dirección de
    envío propia) — PII sensible (email/teléfono/documento) NUNCA sale.
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request, tracking_token):
        token   =   (tracking_token or '').strip()
        if not token:
            raise Http404
        order   =   (
            Order.objects
            .filter(customer = request.customer, tracking_token = token)
            .select_related(
                'store', 'customer',
                'store__customization', 'store__fiscal_profile',
                'store__payment_config', 'store__mp_account', 'store__user',
            )
            .prefetch_related('items', 'events', 'proof')
            .first()
        )
        if order is None:
            #Token ajeno, de otra tienda o inexistente → mismo 404:
            #no se revela que el pedido existe.
            raise Http404
        return Response(order_tracking_payload(order), status = status.HTTP_200_OK)
