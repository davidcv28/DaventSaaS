"""
Checkout MP del comprador (público, sin auth DAVENT — el comprador no es
usuario de la plataforma; Track A maneja su auth de cliente si aplica).

POST /api/stores/public/<slug>/orders/<tracking_token>/pay/

Gates (en orden):
1. Tienda publicada y no bloqueada por slug -> 404 (no se filtra que
   existe pero no vende).
2. orders_enabled(store) (ecommerce_enabled + perfil fiscal completo)
   -> 404, misma política de ocultamiento que el resto de la API pública.
3. StoreMpAccount conectado + payment_config.mp_enabled -> 400 (la
   tienda existe y vende, pero MP no está disponible como método).
4. Pedido por tracking_token ACOTADO a la tienda -> 404 (IDOR).
5. order.status == 'PENDING_PAYMENT' -> 409 si ya avanzó.
6. order.payment_method == 'mp' -> 400. DECISIÓN: no se permite cambiar
   el método de pago de un pedido ya creado — el comprador que eligió
   transferencia debe coordinar por los métodos manuales; cambiar a MP
   implicaría rehacer el pedido (documentado en el contrato).

Respuesta: {init_point, sandbox_init_point, preference_id, checkout_url}
— el front redirige a checkout_url (sandbox si el token es TEST-).
"""
import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.services import (
    MpApiError,
    OrdersUnavailableError,
    create_order_preference,
    orders_bridge,
)
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.commerce import orders_enabled

logger  =   logging.getLogger(__name__)


class PublicOrderPayView(APIView):
    permission_classes      =   [AllowAny]
    #Endpoint de máquina (comprador anónimo): sin JWT — una cookie/header
    #espurio no debe convertirlo en 401.
    authentication_classes  =   []
    def post(self, request, slug, tracking_token):
        store   =   (
            Store.objects
            .filter(slug = slug, is_published = True, is_blocked = False)
            .select_related('customization', 'fiscal_profile', 'mp_account', 'payment_config', 'domain', 'user')
            .first()
        )
        if store is None or not orders_enabled(store):
            raise NotFound('Tienda no encontrada')
        account         =   getattr(store, 'mp_account', None)
        payment_config  =   getattr(store, 'payment_config', None)
        #Sin fila de config se asumen los defaults del modelo (mp_enabled=True).
        mp_enabled      =   payment_config.mp_enabled if payment_config is not None else True
        if not (account and account.is_connected and mp_enabled):
            return Response({'detail': 'Esta tienda no tiene Mercado Pago habilitado'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            order   =   orders_bridge.find_order_by_token(store, tracking_token)
        except OrdersUnavailableError:
            return Response({'detail': 'El checkout de pedidos no está disponible'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        if order is None:
            raise NotFound('Pedido no encontrado')
        order_status    =   str(getattr(order, 'status', '') or '')
        if order_status != 'PENDING_PAYMENT':
            return Response({'detail': f'El pedido ya no admite pago (estado: {order_status or "desconocido"})'}, status = status.HTTP_409_CONFLICT)
        if str(getattr(order, 'payment_method', '') or '') != 'mp':
            return Response({'detail': 'Este pedido no está configurado para pagar con Mercado Pago'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            _mp_payment, preference  =   create_order_preference(order, store)
        except MpApiError:
            logger.warning('Preferencia MP falló: store=%s order=%s', store.slug, getattr(order, 'pk', None))
            return Response({'detail': 'No se pudo iniciar el pago en Mercado Pago'}, status = status.HTTP_502_BAD_GATEWAY)
        #Con token TEST- de MP el checkout real es sandbox_init_point
        #(mismo criterio que el checkout de suscripciones DAVENT).
        is_test     =   account.get_access_token().startswith('TEST-')
        init_point  =   preference.get('init_point')
        sandbox     =   preference.get('sandbox_init_point')
        checkout_url    =   sandbox if (is_test and sandbox) else (init_point or sandbox)
        logger.info('Pay MP iniciado: store=%s order_id=%s preference=%s', store.slug, getattr(order, 'pk', None), preference.get('id'))
        return Response({
            'init_point'            :   init_point,
            'sandbox_init_point'    :   sandbox,
            'preference_id'         :   preference.get('id'),
            'checkout_url'          :   checkout_url,
        }, status = status.HTTP_200_OK)
