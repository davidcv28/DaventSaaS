from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from StoreApp.domains.memberships.models import StorePlan, StoreSubscription
from StoreApp.domains.memberships.serializers import (
    StorePlanSerializer,
    StoreSubscriptionOwnerSerializer,
)
from StoreApp.domains.memberships.services.benefits import (
    grant_period,
    is_vigente,
)
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.public_cache import bump_public_store
from StoreApp.domains.stores.services.commerce import store_has_ecommerce

"""

Viewsets del DUEÑO (auth DAVENT JWT — request.user = auth.User).

Todo objeto cuelga de SU tienda (`Store.user__user = request.user`);
un id ajeno responde 404 — nunca 403 con filtrado de existencia
(IDOR). Los cambios que pueden alterar beneficios vigentes (plan
editado/guardado/borrado, suscripción activada/cancelada/vencida)
hacen bump_public_store: los productos is_exclusive cambian de
visibilidad en la web pública.

"""
#=========================================
# MIXIN — tienda del dueño autenticado (404 sin onboarding)
#=========================================
class _OwnerStoreMixin:
    _store  =   None
    def my_store(self):
        #Planes/suscripciones del comercio: superficie de venta online —
        #exige `has_ecommerce` en el plan vigente (403 si falta).
        if self._store is None:
            store   =   get_object_or_404(Store, user__user = self.request.user)
            if not store_has_ecommerce(store):
                raise PermissionDenied('Tu plan no incluye la venta online.')
            self._store =   store
        return self._store
#=========================================
# STORE PLAN VIEWSET (CRUD de planes del dueño)
#=========================================
class StorePlanViewSet(_OwnerStoreMixin, mixins.ListModelMixin, mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes  =   [IsAuthenticated]
    serializer_class    =   StorePlanSerializer
    def get_queryset(self):
        now     =   timezone.now()
        return (
            StorePlan.objects
            .filter(store = self.my_store())
            .annotate(
                #distinct=True: dos agregados sobre la misma relación no
                #se pisan aunque Django abra joins separados.
                subscriptions_count        =   Count('subscriptions', distinct = True),
                active_subscriptions_count =   Count(
                    'subscriptions', distinct = True,
                    filter = Q(subscriptions__status = StoreSubscription.STATUS_ACTIVE, subscriptions__vigente_hasta__gt = now),
                ),
            )
        )
    def list(self, request, *args, **kwargs):
        #Sin paginación: los planes de una tienda son pocos (mismo
        #criterio que el catálogo del dueño — array plano, no {results}).
        queryset    =   self.filter_queryset(self.get_queryset())
        serializer  =   self.get_serializer(queryset, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    def create(self, request, *args, **kwargs):
        serializer  =   self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save(store = self.my_store())
        #Un plan nuevo puede cambiar beneficios de futuras suscripciones;
        #si ya tiene alguna, la edición del plan mueve la aguja del catálogo.
        bump_public_store(self.my_store().pk)
        return Response({'Exito': 'El plan se creó correctamente', 'item': serializer.data}, status = status.HTTP_201_CREATED)
    def update(self, request, *args, **kwargs):
        partial     =   kwargs.pop('partial', False)
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance, data = request.data, partial = partial)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        #Editar beneficios/% del plan cambia lo que otorgan las
        #suscripciones vigentes -> la web pública (exclusivos) se refresca.
        bump_public_store(instance.store_id)
        return Response({'Exito': 'El plan se actualizó correctamente', 'item': serializer.data})
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial']   =   True
        return self.update(request, *args, **kwargs)
    def perform_destroy(self, instance):
        #Un plan con CUALQUIER suscripción (historial incluido) no se
        #borra — se desactiva: las filas viejas conservan su plan
        #on_delete=PROTECT y el historial de cobros queda íntegro.
        if instance.subscriptions.exists():
            instance.is_active    =   False
            instance.save(update_fields = ['is_active'])
            bump_public_store(instance.store_id)
            return 'deactivated'
        bump_public_store(instance.store_id)
        instance.delete()
        return 'deleted'
    def destroy(self, request, *args, **kwargs):
        instance    =   self.get_object()
        outcome     =   self.perform_destroy(instance)
        if outcome == 'deactivated':
            return Response(
                {'Exito': 'El plan tiene suscripciones registradas: se desactivó en vez de eliminarse para conservar el historial.', 'item': StorePlanSerializer(instance).data},
                status = status.HTTP_200_OK,
            )
        return Response({'Exito': 'El plan se eliminó correctamente'})
#=========================================
# STORE SUBSCRIPTION VIEWSET (gestión del dueño)
#=========================================
class StoreSubscriptionViewSet(_OwnerStoreMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes  =   [IsAuthenticated]
    serializer_class    =   StoreSubscriptionOwnerSerializer
    def get_queryset(self):
        #Cero N+1: customer del membership y plan viajan en el join.
        return (
            StoreSubscription.objects
            .filter(membership__store = self.my_store())
            .select_related('membership__customer', 'plan')
            .order_by('-created_at', '-id')
        )
    def list(self, request, *args, **kwargs):
        queryset    =   self.filter_queryset(self.get_queryset())
        status_filter   =   (request.query_params.get('status') or '').strip()
        if status_filter:
            valid   =   {choice for choice, _ in StoreSubscription.STATUS_CHOICES}
            if status_filter not in valid:
                return Response({'status': f'Estado inválido. Opciones: {", ".join(sorted(valid))}.'}, status = status.HTTP_400_BAD_REQUEST)
            queryset    =   queryset.filter(status = status_filter)
        serializer  =   self.get_serializer(queryset, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #La acción comparte el queryset scopeado: pk ajeno -> 404 (IDOR).
    def _locked_subscription(self, pk):
        #Read-modify-write bajo lock: dos clicks de activate/cancel no
        #pueden pisarse (activate idempotente + transiciones atómicas).
        return StoreSubscription.objects.select_for_update().select_related('plan', 'membership__store').get(pk = pk)
    @action(detail = True, methods = ['post'])
    def activate(self, request, pk = None):
        """
        pending/expired/cancelled/past_due -> active + período del plan
        (grant_period). Idempotente: una suscripción ya vigente se
        devuelve igual sin regenerar fechas ni duplicar efectos.
        """
        subscription    =   self.get_object()      #404 si es de otra tienda
        with transaction.atomic():
            subscription    =   self._locked_subscription(subscription.pk)
            if is_vigente(subscription):
                data    =   StoreSubscriptionOwnerSerializer(subscription).data
                return Response({'Exito': 'La suscripción ya estaba activa.', 'item': data}, status = status.HTTP_200_OK)
            grant_period(subscription, actor = request.user)
        #La suscripción vigente cambia la visibilidad de los exclusivos.
        bump_public_store(subscription.membership.store_id)
        return Response(
            {'Exito': 'La suscripción se activó y el plan quedó vigente.', 'item': StoreSubscriptionOwnerSerializer(subscription).data},
            status = status.HTTP_200_OK,
        )
    @action(detail = True, methods = ['post'])
    def cancel(self, request, pk = None):
        """
        -> cancelled. Semántica: los helpers exigen status='active', así
        que cancelar CORTA los beneficios al instante (no espera al fin
        del período pago — ver docstring de benefits.py). Idempotente.
        """
        subscription    =   self.get_object()
        with transaction.atomic():
            subscription    =   self._locked_subscription(subscription.pk)
            if subscription.status in (StoreSubscription.STATUS_CANCELLED, StoreSubscription.STATUS_EXPIRED):
                data    =   StoreSubscriptionOwnerSerializer(subscription).data
                return Response({'Exito': 'La suscripción ya estaba finalizada.', 'item': data}, status = status.HTTP_200_OK)
            subscription.status     =   StoreSubscription.STATUS_CANCELLED
            subscription.save(update_fields = ['status', 'updated_at'])
        bump_public_store(subscription.membership.store_id)
        return Response(
            {'Exito': 'La suscripción se canceló.', 'item': StoreSubscriptionOwnerSerializer(subscription).data},
            status = status.HTTP_200_OK,
        )
    @action(detail = True, methods = ['post'])
    def expire(self, request, pk = None):
        """
        Fuerza 'expired' sobre una suscripción activa o past_due (p.ej.
        cobro que nunca se acreditó). 'pending' se cancela, no se vence;
        'cancelled'/'expired' son terminales -> 400 salvo ya expired
        (idempotente).
        """
        subscription    =   self.get_object()
        with transaction.atomic():
            subscription    =   self._locked_subscription(subscription.pk)
            if subscription.status == StoreSubscription.STATUS_EXPIRED:
                data    =   StoreSubscriptionOwnerSerializer(subscription).data
                return Response({'Exito': 'La suscripción ya estaba vencida.', 'item': data}, status = status.HTTP_200_OK)
            if subscription.status not in (StoreSubscription.STATUS_ACTIVE, StoreSubscription.STATUS_PAST_DUE):
                return Response(
                    {'detail': 'Solo se puede vencer una suscripción activa o con pago pendiente de acreditación.'},
                    status = status.HTTP_400_BAD_REQUEST,
                )
            subscription.status     =   StoreSubscription.STATUS_EXPIRED
            subscription.save(update_fields = ['status', 'updated_at'])
        bump_public_store(subscription.membership.store_id)
        return Response(
            {'Exito': 'La suscripción quedó vencida.', 'item': StoreSubscriptionOwnerSerializer(subscription).data},
            status = status.HTTP_200_OK,
        )
