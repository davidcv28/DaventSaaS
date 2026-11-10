"""
Panel del dueño — métricas y clientes del e-commerce (storeadmin).

Todo es LECTURA y store-scoped: la tienda se resuelve una vez por
request con `Store.user__user = request.user` (mismo patrón que
orders.views.owner / memberships.views.owner) y TODOS los querysets
filtran por ella — un customer/pedido ajeno es 404, nunca 403
filtrable (IDOR).

Auth: JWT DAVENT estándar (IsAuthenticated). Throttle: el default del
proyecto (ResilientUserRateThrottle 1000/día) — no hay scope propio
para exports (settings.py es de otro track); el tope de filas del CSV
(services.metrics.EXPORT_MAX_ROWS) es la defensa de costo.

Endpoints (bajo /api/):
- GET /api/store-admin/sales/summary/?from=&to=&payment_method=&status=
- GET /api/store-admin/sales/daily/?days=90|from=&to=
- GET /api/store-admin/sales/export.csv?from=&to=&payment_method=&status=
- GET /api/store-admin/customers/?q=&membership=&ordering=
- GET /api/store-admin/customers/<id>/
"""
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storeadmin.serializers import (
    StoreAdminCustomerDetailSerializer,
    StoreAdminCustomerListSerializer,
)
from StoreApp.domains.storeadmin.services.metrics import (
    build_customer_queryset,
    build_daily_series,
    build_sales_csv_response,
    build_sales_summary,
    clean_membership_filter,
    clean_ordering,
    clean_payment_method,
    clean_status,
    memberships_prefetch,
    resolve_daily_range,
    resolve_date_range,
)
from StoreApp.domains.stores.models import Store


class _StoreAdminMixin:
    """Tienda del dueño autenticado (404 si no tiene onboarding)."""
    _store  =   None
    def my_store(self):
        if self._store is None:
            self._store =   get_object_or_404(
                Store.objects.select_related('user'),
                user__user = self.request.user,
            )
        return self._store


class SalesSummaryView(_StoreAdminMixin, APIView):
    """
    GET /api/store-admin/sales/summary/

    Agregados de ventas del rango `from`/`to` (default últimos 30 días,
    máx 366): totales cobrados/pendientes/reembolsados, ticket
    promedio y cortes por método de pago y por estado. `payment_method`
    y `status` filtran TODO el agregado.
    """
    permission_classes  =   [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        store       =   self.my_store()
        d_from, d_to, start, end =   resolve_date_range(request.query_params)
        payment_method  =   clean_payment_method(request.query_params.get('payment_method'))
        order_status    =   clean_status(request.query_params.get('status'))
        payload =   build_sales_summary(
            store, d_from, d_to, start, end,
            payment_method = payment_method,
            status         = order_status,
        )
        return Response(payload, status = status.HTTP_200_OK)


class SalesDailyView(_StoreAdminMixin, APIView):
    """
    GET /api/store-admin/sales/daily/

    Serie diaria del rango: `days` (default 90, máx 366) o `from`/`to`
    explícitos. Un punto por día — {date, orders_count, total_cobrado,
    total_pendiente} — con ceros en los días sin pedidos.
    """
    permission_classes  =   [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        store       =   self.my_store()
        d_from, d_to, start, end =   resolve_daily_range(request.query_params)
        payment_method  =   clean_payment_method(request.query_params.get('payment_method'))
        order_status    =   clean_status(request.query_params.get('status'))
        series  =   build_daily_series(
            store, d_from, d_to, start, end,
            payment_method = payment_method,
            status         = order_status,
        )
        return Response({
            'from'      :   d_from.isoformat(),
            'to'        :   d_to.isoformat(),
            'series'    :   series,
        }, status = status.HTTP_200_OK)


class SalesExportView(_StoreAdminMixin, APIView):
    """
    GET /api/store-admin/sales/export.csv

    CSV de pedidos del rango (mismos filtros que el summary): fecha,
    code, cliente, método de pago, estado, subtotal, descuento, envío,
    total e invoice_ref. UTF-8+BOM, escape anti CSV-injection y tope de
    EXPORT_MAX_ROWS filas (400 si excede).
    """
    permission_classes  =   [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        store       =   self.my_store()
        d_from, d_to, start, end =   resolve_date_range(request.query_params)
        payment_method  =   clean_payment_method(request.query_params.get('payment_method'))
        order_status    =   clean_status(request.query_params.get('status'))
        return build_sales_csv_response(
            store, d_from, d_to, start, end,
            payment_method = payment_method,
            status         = order_status,
        )


class StoreAdminCustomerViewSet(_StoreAdminMixin, mixins.ListModelMixin,
                                mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET /api/store-admin/customers/?q=&membership=&ordering=
    GET /api/store-admin/customers/<customer_id>/

    Clientes DE la tienda: miembros (StoreMembership) ∪ compradores con
    pedidos — la unión y los agregados LTV viven en
    services.metrics.build_customer_queryset. `q` busca en
    nombre/apellido/email; `membership` = active|suspended|none;
    `ordering` tiene whitelist (ver CUSTOMER_ORDERING). Paginado con la
    paginación default del proyecto. IDOR → 404 (el queryset ya filtra
    por la tienda del dueño).
    """
    permission_classes  =   [IsAuthenticated]
    def get_queryset(self):
        store       =   self.my_store()
        params      =   self.request.query_params
        q           =   (params.get('q') or '').strip()
        membership  =   clean_membership_filter(params.get('membership'))
        ordering    =   clean_ordering(params.get('ordering'))
        return (build_customer_queryset(store, q = q, membership = membership)
            .prefetch_related(memberships_prefetch(store))
            .order_by(*ordering))
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StoreAdminCustomerDetailSerializer
        return StoreAdminCustomerListSerializer
    def get_serializer_context(self):
        #El detalle necesita la tienda para los últimos pedidos del
        #cliente (los agregados del queryset ya vienen anotados).
        context =   super().get_serializer_context()
        context['store']    =   self.my_store()
        return context
