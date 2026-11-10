from django.db.models import Count
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from DaventProject.pagination import DaventPageNumberPagination
from DaventProject.throttling import _ResilientThrottleMixin
from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.views.auth_views import CustomerApiThrottle
from StoreApp.domains.support.models import SupportMessage, SupportThread
from StoreApp.domains.support.serializers import (
    SupportMessageCreateSerializer,
    SupportMessageSerializer,
    SupportThreadCreateSerializer,
    SupportThreadCustomerDetailSerializer,
    SupportThreadCustomerSerializer,
)
from StoreApp.domains.support.services import (
    create_thread,
    customer_visible_store,
    mark_thread_read,
    post_message,
    resolve_order_link,
    set_thread_status,
    unread_messages_q,
)

"""

Endpoints del COMPRADOR (customer JWT — request.customer, Bearer
`customer_access`; nunca autentica con el JWT DAVENT del dueño).

- GET/POST /api/support/threads/                  → bandeja + alta de hilo.
- GET      /api/support/threads/<id>/             → detalle + mensajes
  (leer el hilo marca como leídos los mensajes DEL DUEÑO).
- POST     /api/support/threads/<id>/messages/    → responder {body}.
- POST     /api/support/threads/<id>/close/       → cerrar (solo el
  comprador cierra; reabrir es decisión del dueño — ver owner.py).

IDOR: todo queryset cuelga de `customer=request.customer` — un hilo
ajeno es 404, nunca 403 con filtrado de existencia. La tienda del alta
se valida publicada/no bloqueada (customer_visible_store) y el order_token
opcional debe ser un pedido DEL comprador en ESA tienda
(resolve_order_link — token ajeno/otra tienda = 400 genérico).

Throttles: lecturas con la bolsa 'user' del comprador (CustomerApiThrottle,
keyed c<pk>); escrituras con scopes propios más estrictos.
"""
#=========================================
# THROTTLES (keyed por customer.pk — 'c' evita colisión con auth.User)
#=========================================
class _CustomerScopedThrottle(_ResilientThrottleMixin, SimpleRateThrottle):
    def get_cache_key(self, request, view):
        customer    =   getattr(request, 'customer', None)
        if customer is not None:
            ident   =   f'c{customer.pk}'
        else:
            ident   =   self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class SupportThreadCreateThrottle(_CustomerScopedThrottle):
    """Alta de hilos por comprador (10/h — muy por encima de un uso real)."""
    scope   =   'support_thread_create'
    rate    =   '10/hour'


class SupportMessageThrottle(_CustomerScopedThrottle):
    """Mensajes/cierres por comprador (60/h — una conversación real no llega)."""
    scope   =   'support_message'
    rate    =   '60/hour'
#=========================================
# HELPERS
#=========================================
def _threads_qs(customer):
    """
    Hilos del comprador con store+order prefetcheados y unread_count
    anotado (mensajes de la contraparte sin read_by_customer_at).
    """
    return (
        SupportThread.objects
        .filter(customer = customer)
        .select_related('store__customization', 'store__user', 'order')
        .annotate(unread_count = Count(
            'messages', filter = unread_messages_q('customer'), distinct = True,
        ))
        .order_by('-last_message_at', '-id')
    )

def _thread_or_404(customer, pk):
    """Hilo DEL comprador o 404 (IDOR: ajeno/inexistente indistinguible)."""
    thread  =   _threads_qs(customer).filter(pk = pk).first()
    if thread is None:
        raise Http404
    return thread
#=========================================
# LIST + CREATE
#=========================================
class CustomerSupportThreadListCreateView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    def get_throttles(self):
        if self.request.method == 'POST':
            return [SupportThreadCreateThrottle()]
        return [CustomerApiThrottle()]
    def get(self, request):
        paginator   =   DaventPageNumberPagination()
        page        =   paginator.paginate_queryset(_threads_qs(request.customer), request)
        if page is not None:
            return paginator.get_paginated_response(SupportThreadCustomerSerializer(page, many = True).data)
        return Response(SupportThreadCustomerSerializer(_threads_qs(request.customer), many = True).data, status = status.HTTP_200_OK)
    def post(self, request):
        serializer  =   SupportThreadCreateSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        #La tienda tiene que ser visible públicamente (publicada y no
        #bloqueada): un slug desconocido/inactivo es 404, no 400.
        store       =   customer_visible_store(data['store'])
        if store is None:
            raise Http404
        #Pedido opcional de contexto: tiene que ser DEL comprador en ESA
        #tienda — un token ajeno o de otra tienda se rechaza genérico.
        order       =   resolve_order_link(store, request.customer, data.get('order_token') or '')
        if data.get('order_token') and order is None:
            return Response(
                {'order_token': ['No encontramos ese pedido en tu cuenta para esta tienda.']},
                status = status.HTTP_400_BAD_REQUEST,
            )
        thread      =   create_thread(
            customer    =   request.customer,
            store       =   store,
            subject     =   data['subject'],
            body        =   data['body'],
            order       =   order,
        )
        payload =   SupportThreadCustomerDetailSerializer(_thread_or_404(request.customer, thread.pk)).data
        return Response(payload, status = status.HTTP_201_CREATED)
#=========================================
# DETAIL (leer marca los mensajes del dueño como leídos)
#=========================================
class CustomerSupportThreadDetailView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request, pk):
        thread  =   _thread_or_404(request.customer, pk)
        #Leer el hilo = leer la conversación: los mensajes DEL DUEÑO
        #quedan leídos por el comprador (los propios ya lo están).
        mark_thread_read(thread, 'customer')
        #Re-fetch: el unread_count anotado se calculó antes del marcado.
        thread  =   _threads_qs(request.customer).get(pk = thread.pk)
        return Response(SupportThreadCustomerDetailSerializer(thread).data, status = status.HTTP_200_OK)
#=========================================
# REPLY + CLOSE
#=========================================
class CustomerSupportMessageCreateView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [SupportMessageThrottle]
    def post(self, request, pk):
        thread  =   _thread_or_404(request.customer, pk)
        #IDOR primero: un hilo ajeno es 404 aunque el body sea inválido.
        if thread.status == SupportThread.Status.CLOSED:
            return Response(
                {'detail': 'Este hilo está cerrado. Podés abrir uno nuevo o esperar a que la tienda lo reabra.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        serializer  =   SupportMessageCreateSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        message =   post_message(thread, sender = SupportMessage.Sender.CUSTOMER, body = serializer.validated_data['body'])
        return Response(SupportMessageSerializer(message).data, status = status.HTTP_201_CREATED)


class CustomerSupportThreadCloseView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [SupportMessageThrottle]
    def post(self, request, pk):
        thread  =   _thread_or_404(request.customer, pk)
        set_thread_status(thread, SupportThread.Status.CLOSED)
        return Response(SupportThreadCustomerSerializer(_threads_qs(request.customer).get(pk = thread.pk)).data, status = status.HTTP_200_OK)
