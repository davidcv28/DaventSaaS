"""
Endpoints del dueño para su cuenta de Mercado Pago y reembolsos.

Regla de secretos: NUNCA se devuelve un token — solo flags (`connected`,
`live_mode`, `mp_user_id`, `connected_at`). Todo acceso al access token
pasa por `StoreMpAccount.get_access_token()` dentro de los services.

OIDC/IDOR: el dueño solo opera sobre `request.user.profile.store` — no
hay parámetro de tienda en la URL, así que no existe forma de apuntar a
la cuenta MP de otro vendedor.
"""
import logging

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.models import StoreMpWebhookConfig
from StoreApp.domains.storepayments.serializers import MpConnectSerializer
from StoreApp.domains.storepayments.services import (
    MpApiError,
    OrdersUnavailableError,
    mp_client,
    orders_bridge,
)
from StoreApp.domains.storepayments.services.refunds import RefundError, refund_payment
from StoreApp.domains.stores.models import StoreMpAccount, StorePaymentConfig
from StoreApp.domains.stores.services.services import profile_has_benefit

logger  =   logging.getLogger(__name__)


#=========================================
# HELPERS
#=========================================
def owner_store(request):
    """
    Tienda del usuario autenticado (`user -> profile -> store`, OneToOne).
    Sin tienda -> 404 (IDOR: no hay tienda "ajena" que enumerar).
    """
    profile =   getattr(request.user, 'profile', None)
    store   =   getattr(profile, 'store', None) if profile is not None else None
    if store is None:
        raise NotFound('No tenés una tienda asociada')
    return store


_BENEFIT_DETAILS   =   {
    'has_ecommerce'     :   'Tu plan no incluye la venta online.',
    'has_customer_auth' :   'Tu plan no incluye cuentas de comprador.',
    'has_own_storage'   :   'Tu plan no incluye storage propio.',
}


def require_benefit(store, code):
    """
    Gate por plan del dueño: el endpoint responde 403 si el plan vigente
    no incluye `code`. Cada config del panel "Cobros" cuelga de un
    beneficio distinto (venta online / auth de compradores / R2 propio),
    así que el check va por vista y no dentro de `owner_store`.
    """
    if not profile_has_benefit(store.user, code):
        raise PermissionDenied(_BENEFIT_DETAILS.get(code, 'Tu plan no incluye esta función.'))


def mp_status_payload(store):
    """Payload público del estado MP — jamás tokens ni secretos."""
    #Las reverse OneToOne (mp_account/mp_webhook_config) pueden venir
    #CACHEADAS en la instancia `store` si otro código las tocó antes en
    #el mismo proceso/request (p.ej. force_authenticate reusando el
    #mismo User->profile->store entre requests, o un worker de larga
    #vida): una connect/disconnect reciente no se vería. Se releen por
    #ORM — el payload de estado siempre refleja la fila real.
    account         =   StoreMpAccount.objects.filter(store_id = store.id).first()
    has_config      =   StorePaymentConfig.objects.filter(store_id = store.id).exists()
    webhook_cfg     =   StoreMpWebhookConfig.objects.filter(store_id = store.id).first()
    return {
        'connected'         :   bool(account and account.is_connected),
        'live_mode'         :   bool(account.live_mode) if account else False,
        'mp_user_id'        :   account.mp_user_id if account else '',
        'connected_at'      :   account.connected_at.isoformat() if account and account.connected_at else None,
        'has_payment_config':   has_config,
        #El front necesita saber si el webhook puede validar firmas:
        #flag solamente, el secret jamás sale.
        'webhook_configured':   bool(webhook_cfg and webhook_cfg.has_secret),
    }


#=========================================
# MP STATUS (GET)
#=========================================
class MpStatusView(APIView):
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        return Response(mp_status_payload(store), status = status.HTTP_200_OK)


#=========================================
# MP CONNECT (POST — credenciales pegadas, MVP)
#=========================================
class MpConnectView(APIView):
    """
    Conecta la cuenta MP del vendedor. Valida el access token contra
    GET /users/me ANTES de persistir (un token inválido -> 400 sin
    guardar nada). Acepta `webhook_secret` opcional para configurar la
    firma del webhook de SU app de MP (re-enviar connect lo actualiza).

    OAUTH Connect de MP queda como stretch fuera del MVP: el flujo
    authorization_code de MP requiere una app MP propia aprobada por
    MP — las credenciales pegadas cubren el caso real de los vendedores.
    """
    permission_classes    =   [IsAuthenticated]
    def post(self, request):
        serializer  =   MpConnectSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        store       =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        access_token    =   data['access_token']
        #VALIDACIÓN PREVIA: el token tiene que funcionar contra MP antes
        #de cifrarlo y guardarlo — un typo no deja la cuenta "conectada"
        #a medias.
        try:
            mp_user    =   mp_client.get_mp_user(access_token)
        except MpApiError as exc:
            logger.info('MP connect rechazado store=%s status=%s', store.slug, exc.status_code)
            return Response({'detail': 'Mercado Pago rechazó el access token'}, status = status.HTTP_400_BAD_REQUEST)
        #live_mode: si el dueño no lo declara se deriva del prefijo del
        #token (APP_USR- = producción, TEST- = prueba) — MP no lo expone
        #en /users/me.
        live_mode   =   data.get('live_mode')
        if live_mode is None:
            live_mode   =   access_token.startswith('APP_USR-')
        account, _  =   StoreMpAccount.objects.get_or_create(store = store)
        account.set_tokens(
            access_token,
            data.get('refresh_token') or '',
            live_mode    =   live_mode,
            mp_user_id   =   str(mp_user.get('id') or '')[:64],
        )
        account.save()
        #Webhook secret (opcional): campo presente (incluso vacío) lo
        #actualiza — '' lo limpia. Viaja cifrado por el vault.
        if 'webhook_secret' in data:
            webhook_cfg, _  =   StoreMpWebhookConfig.objects.get_or_create(store = store)
            webhook_cfg.set_webhook_secret(data['webhook_secret'])
            webhook_cfg.save()
        logger.info('MP connect store=%s mp_user=%s live=%s', store.slug, account.mp_user_id, account.live_mode)
        return Response(mp_status_payload(store), status = status.HTTP_200_OK)


#=========================================
# MP DISCONNECT (POST)
#=========================================
class MpDisconnectView(APIView):
    """
    Desconecta la cuenta MP: clear_tokens() borra las credenciales
    cifradas localmente. NO se revoca el token en MP — el access token
    del vendedor sigue válido hasta que él lo expire/revoque desde su
    panel de MP (documentado: la revocación real requeriría el flujo
    OAuth, fuera del MVP de credenciales pegadas).
    """
    permission_classes    =   [IsAuthenticated]
    def post(self, request):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        account =   getattr(store, 'mp_account', None)
        if account is not None:
            account.clear_tokens()
            account.save(update_fields = ['access_token_enc', 'refresh_token_enc', 'mp_user_id', 'scope', 'connected_at', 'updated_at'])
            logger.info('MP disconnect store=%s', store.slug)
        return Response(mp_status_payload(store), status = status.HTTP_200_OK)


#=========================================
# MP REFUND (POST /store-payments/mp/refund/<order_id>/)
#=========================================
class MpRefundView(APIView):
    """
    Reembolso del pedido por el dueño. La ruta vive en storepayments
    (no en /api/store-orders/) para no pisar el dominio orders del
    track B. IDOR: el pedido se busca ACOTADO a la tienda del usuario —
    un order_id ajeno devuelve 404.
    """
    permission_classes    =   [IsAuthenticated]
    def post(self, request, order_id):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        try:
            order   =   orders_bridge.get_order_for_store(store, order_id)
        except OrdersUnavailableError:
            return Response({'detail': 'El dominio de pedidos no está disponible'}, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        if order is None:
            raise NotFound('Pedido no encontrado')
        try:
            refund_payment(order, actor = request.user)
        except RefundError as exc:
            return Response({'detail': str(exc)}, status = status.HTTP_502_BAD_GATEWAY)
        except MpApiError:
            return Response({'detail': 'No se pudo comunicar con Mercado Pago'}, status = status.HTTP_502_BAD_GATEWAY)
        return Response({'detail': 'Reembolso procesado', 'status': 'refunded'}, status = status.HTTP_200_OK)
