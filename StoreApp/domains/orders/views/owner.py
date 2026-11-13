"""
Panel del dueño: pedidos de SU tienda (tenant-scoped en el queryset —
un pedido de otra tienda es 404, nunca 403 filtrable).

- GET  /api/store-orders/?status=&page=      → bandeja (paginada).
- GET  /api/store-orders/<id>/               → detalle completo.
- POST /api/store-orders/<id>/confirm-payment/ {reference?}
- POST /api/store-orders/<id>/advance/       {status}
- POST /api/store-orders/<id>/cancel/        {reason?}
- POST /api/store-orders/<id>/invoice-ref/   {invoice_ref}

Auth: JWT DAVENT estándar (el dueño logueado). El scope de tienda se
resuelve UNA vez por request con `Store.user__user = request.user` —
mismo patrón que catalog.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from StoreApp.domains.orders.models import Order
from StoreApp.domains.orders.serializers import (
    OrderInvoiceRefSerializer,
    OrderOwnerAdvanceSerializer,
    OrderOwnerCancelSerializer,
    OrderOwnerConfirmSerializer,
    StoreOrderDetailSerializer,
    StoreOrderListSerializer,
)
from StoreApp.domains.orders.services.events import append_event
from StoreApp.domains.orders.services.payments import (
    advance_order,
    cancel_order,
    mark_order_paid,
)
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.commerce import store_has_ecommerce


class StoreOrderViewSet(viewsets.GenericViewSet):
    permission_classes  =   [IsAuthenticated]
    lookup_field        =   'pk'
    _store              =   None
    #=========================================
    # TENANT SCOPE
    #=========================================
    def my_store(self):
        """
        Tienda del dueño autenticado (404 si no tiene onboarding). El
        panel de ventas exige `has_ecommerce` en el plan vigente — sin
        el beneficio es 403 aunque la tienda haya vendido antes.
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
        TODOS los pedidos de la tienda del dueño, más nuevos primero,
        con items/events/proof prefetcheados (bandeja y detalle sin
        N+1). El filtro ?status= valida contra los choices del modelo —
        un valor inválido devuelve lista vacía, no un 500.
        """
        qs  =   (Order.objects
            .filter(store = self.my_store())
            .select_related('store', 'customer')
            .prefetch_related('items', 'events', 'proof')
            .order_by('-created_at', '-id'))
        status_param    =   (self.request.query_params.get('status') or '').strip().upper()
        if status_param:
            qs  =   qs.filter(status = status_param)
        return qs
    def get_serializer_class(self):
        if self.action in ('retrieve', 'confirm_payment', 'advance', 'cancel', 'invoice_ref'):
            return StoreOrderDetailSerializer
        return StoreOrderListSerializer
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
        order       =   self.get_object()   # queryset ya filtra por tienda → IDOR = 404
        serializer  =   self.get_serializer(order)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # ACTIONS (todas mutan vía services con lock + validación de estados)
    #=========================================
    def _fresh_detail(self, order):
        """Re-lee el pedido con los mismos related/prefetch del detail —
        la instancia que devuelve el service no trae la cache de
        prefetch del get_object original (eventos recién agregados
        visibles sin recarga manual)."""
        return (Order.objects
            .select_related('store', 'customer')
            .prefetch_related('items', 'events', 'proof')
            .get(pk = order.pk))
    @action(detail = True, methods = ['post'], url_path = 'confirm-payment')
    def confirm_payment(self, request, pk = None):
        """El dueño acredita el pago manual (transferencia/efectivo/MP
        verificado a mano). mark_order_paid es idempotente: un segundo
        POST devuelve el pedido sin duplicar eventos ni stock."""
        #IDOR primero: un pedido ajeno es 404 aunque el body sea inválido
        #(no se valida input de objetos que el dueño no puede ver).
        order       =   self.get_object()
        serializer  =   OrderOwnerConfirmSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        mark_order_paid(
            order,
            source      =   'manual',
            reference   =   serializer.validated_data.get('reference') or '',
            actor       =   'owner',
        )
        return Response(StoreOrderDetailSerializer(self._fresh_detail(order)).data, status = status.HTTP_200_OK)
    @action(detail = True, methods = ['post'])
    def advance(self, request, pk = None):
        """Avanza el pedido (PACKING/SHIPPED/DELIVERED/REFUNDED) — la
        máquina de estados del modelo decide si la transición es válida."""
        order       =   self.get_object()
        serializer  =   OrderOwnerAdvanceSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        carrier, carrier_label, tracking_code = (
            data.get('carrier') or '', data.get('carrier_label') or '', data.get('tracking_code') or '')
        if data['status'] == 'SHIPPED' and data.get('generate'):
            #Generación por API del correo del dueño (credenciales de su
            #contrato en Cobros → Envíos): devuelve carrier+código.
            #La transición se valida BAJO LOCK antes de pegarle a la API
            #externa — un estado inválido ya no genera el envío (ni manda
            #la PII del comprador) para después fallar en advance_order.
            from django.db import transaction
            from rest_framework import serializers
            from StoreApp.domains.orders.services.carriers import generate_shipment
            with transaction.atomic():
                locked  =   Order.objects.select_for_update().get(pk = order.pk)
                if Order.Status.SHIPPED not in Order.TRANSITIONS.get(locked.status, set()):
                    raise serializers.ValidationError({
                        'status': f'No se puede enviar un pedido en estado "{locked.status}".',
                    })
                carrier, tracking_code    =   generate_shipment(locked.store, locked)
                carrier_label             =   ''
                advance_order(
                    locked, Order.Status.SHIPPED, actor = 'owner',
                    carrier = carrier, carrier_label = carrier_label, tracking_code = tracking_code,
                )
            return Response(StoreOrderDetailSerializer(self._fresh_detail(order)).data, status = status.HTTP_200_OK)
        advance_order(
            order, data['status'], actor = 'owner',
            carrier = carrier, carrier_label = carrier_label, tracking_code = tracking_code,
        )
        return Response(StoreOrderDetailSerializer(self._fresh_detail(order)).data, status = status.HTTP_200_OK)
    @action(detail = True, methods = ['post'])
    def cancel(self, request, pk = None):
        """Cancela el pedido si está pendiente de pago (los pagos se
        reembolsan, no se cancelan — ver services.payments.cancel_order)."""
        order       =   self.get_object()
        serializer  =   OrderOwnerCancelSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        cancel_order(
            order,
            actor   =   'owner',
            reason  =   serializer.validated_data.get('reason') or '',
        )
        return Response(StoreOrderDetailSerializer(self._fresh_detail(order)).data, status = status.HTTP_200_OK)
    @action(detail = True, methods = ['post'], url_path = 'invoice-ref')
    def invoice_ref(self, request, pk = None):
        """Guarda el nº de factura/CAE real que el vendedor emitió — el
        comprobante NO FISCAL pasa a tener referencia fiscal."""
        order       =   self.get_object()
        serializer  =   OrderInvoiceRefSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        order.invoice_ref   =   serializer.validated_data['invoice_ref']
        order.save(update_fields = ['invoice_ref', 'updated_at'])
        append_event(order, 'note', actor = 'owner', note = f'Factura/CAE: {order.invoice_ref}')
        return Response(StoreOrderDetailSerializer(self._fresh_detail(order)).data, status = status.HTTP_200_OK)
