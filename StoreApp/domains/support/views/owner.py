from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from DaventProject.pagination import DaventPageNumberPagination
from DaventProject.throttling import _ResilientThrottleMixin
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.commerce import store_has_ecommerce
from StoreApp.domains.support.models import SupportMessage, SupportThread
from StoreApp.domains.support.serializers import (
    SupportMessageCreateSerializer,
    SupportMessageSerializer,
    SupportThreadOwnerDetailSerializer,
    SupportThreadOwnerSerializer,
)
from StoreApp.domains.support.services import (
    mark_thread_read,
    post_message,
    set_thread_status,
    unread_messages_q,
)

"""

Panel del DUEÑO: hilos de soporte DE SU TIENDA (tenant-scoped en el
queryset — un hilo de otra tienda es 404, nunca 403 filtrable).

Auth: JWT DAVENT estándar (auth.User del dueño). El scope de tienda se
resuelve UNA vez por request con `Store.user__user = request.user` —
mismo patrón que orders.owner / memberships.owner.

- GET  /api/store-support/threads/?status=&unread=   → bandeja.
- GET  /api/store-support/threads/<id>/              → detalle + mensajes
  (leer marca leídos los mensajes DEL COMPRADOR).
- POST /api/store-support/threads/<id>/messages/     → responder {body}.
- POST /api/store-support/threads/<id>/close/        → cerrar.
- POST /api/store-support/threads/<id>/reopen/       → reabrir (solo el
  dueño reabre: si el comprador cerró y vuelve a escribir, el hilo se
  reabre desde acá antes de responder).

Ciclo de vida: hilo cerrado → 400 al escribir (ambos lados); el dueño
lo reabre con /reopen/ y recién ahí se puede seguir la conversación.
"""
#=========================================
# THROTTLE (escrituras del dueño — keyed por auth.User.pk)
#=========================================
class SupportOwnerWriteThrottle(_ResilientThrottleMixin, UserRateThrottle):
    """Respuestas/cierres del dueño (120/h — atiende a muchos compradores)."""
    scope   =   'support_owner_write'
    rate    =   '120/hour'
#=========================================
# VIEWSET
#=========================================
class StoreSupportThreadViewSet(viewsets.GenericViewSet):
    permission_classes  =   [IsAuthenticated]
    lookup_field        =   'pk'
    _store              =   None
    pagination_class    =   DaventPageNumberPagination
    #=========================================
    # TENANT SCOPE
    #=========================================
    def my_store(self):
        """
        Tienda del dueño autenticado (404 si no tiene onboarding). El
        soporte de tienda es superficie de venta online: exige
        `has_ecommerce` en el plan vigente — 403 si falta.
        """
        if self._store is None:
            store   =   get_object_or_404(
                Store.objects.select_related('user'),
                user__user = self.request.user,
            )
            if not store_has_ecommerce(store):
                raise PermissionDenied('Tu plan no incluye la venta online.')
            self._store =   store
        return self._store
    def get_queryset(self):
        """
        Hilos DE SU TIENDA con customer+order prefetcheados y unread_count
        anotado (mensajes del comprador sin read_by_owner_at). ?status=
        filtra por estado válido (inválido → lista vacía); ?unread=1 deja
        solo hilos con mensajes sin leer del comprador.
        """
        qs  =   (
            SupportThread.objects
            .filter(store = self.my_store())
            .select_related('customer', 'store', 'order')
            .annotate(unread_count = Count(
                'messages', filter = unread_messages_q('owner'), distinct = True,
            ))
            .order_by('-last_message_at', '-id')
        )
        status_param    =   (self.request.query_params.get('status') or '').strip().lower()
        if status_param:
            qs  =   qs.filter(status = status_param)
        if (self.request.query_params.get('unread') or '').strip() in ('1', 'true', 'yes'):
            qs  =   qs.filter(unread_count__gt = 0)
        return qs
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SupportThreadOwnerDetailSerializer
        return SupportThreadOwnerSerializer
    def get_throttles(self):
        #Solo las escrituras llevan throttle propio; las lecturas caen en
        #los default del proyecto (ResilientUserRateThrottle scope 'user').
        if self.action in ('messages', 'close', 'reopen'):
            return [SupportOwnerWriteThrottle()]
        return super().get_throttles()
    #=========================================
    # READ
    #=========================================
    def list(self, request, *args, **kwargs):
        queryset    =   self.filter_queryset(self.get_queryset())
        page        =   self.paginate_queryset(queryset)
        if page is not None:
            serializer  =   self.get_serializer(page, many = True)
            return self.get_paginated_response(serializer.data)
        serializer    =   self.get_serializer(queryset, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    def retrieve(self, request, *args, **kwargs):
        thread  =   self.get_object()   # queryset ya filtra por tienda → IDOR = 404
        #Leer el hilo = leer la conversación: los mensajes DEL COMPRADOR
        #quedan leídos por el dueño.
        mark_thread_read(thread, 'owner')
        #Re-fetch: el unread_count anotado se calculó antes del marcado.
        thread  =   self.get_queryset().get(pk = thread.pk)
        return Response(self.get_serializer(thread).data, status = status.HTTP_200_OK)
    #=========================================
    # ACTIONS
    #=========================================
    @action(detail = True, methods = ['post'])
    def messages(self, request, pk = None):
        """Responder al comprador {body} — el hilo tiene que estar abierto."""
        thread  =   self.get_object()
        if thread.status == SupportThread.Status.CLOSED:
            return Response(
                {'detail': 'Este hilo está cerrado. Reabrilo para poder responder.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        serializer  =   SupportMessageCreateSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        message =   post_message(thread, sender = SupportMessage.Sender.OWNER, body = serializer.validated_data['body'])
        return Response(SupportMessageSerializer(message).data, status = status.HTTP_201_CREATED)
    @action(detail = True, methods = ['post'])
    def close(self, request, pk = None):
        """Cerrar el hilo (idempotente — ya cerrado devuelve 200 igual)."""
        thread  =   self.get_object()
        set_thread_status(thread, SupportThread.Status.CLOSED)
        return Response(self.get_serializer(thread).data, status = status.HTTP_200_OK)
    @action(detail = True, methods = ['post'])
    def reopen(self, request, pk = None):
        """Reabrir un hilo cerrado (idempotente — solo el dueño reabre)."""
        thread  =   self.get_object()
        set_thread_status(thread, SupportThread.Status.OPEN)
        return Response(self.get_serializer(thread).data, status = status.HTTP_200_OK)
