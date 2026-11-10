"""
Webhook de Mercado Pago del vendedor: POST /api/webhooks/store-mp/<slug>/

Copia el patrón de AdminApp/domains/payments/views/viewset.py (webhook de
suscripciones) con DOS diferencias propias del e-commerce:

1. El secreto HMAC NO es global: cada vendedor pega el webhook secret de
   SU app de MP al conectar (campo `webhook_secret` de mp/connect), que
   viaja cifrado en StoreMpWebhookConfig. La firma se valida contra el
   secret de ESE slug — un evento firmado por la app de otro vendedor no
   verifica acá.
2. La notificación se procesa con el access token DEL VENDEDOR de ese
   slug (nunca el de DAVENT) y el pedido se resuelve por
   external_reference ACOTADO a la tienda (anti-IDOR).

Reglas (idénticas al patrón):
- body <= 16KB (413), solo se procesa `data.id` del QUERY STRING (el
  firmado), id regex [A-Za-z0-9_-]{1,64},
- x-signature HMAC-SHA256 con ventana de frescura de 10 minutos,
- dedup por x-request-id en cache (fail-open: la idempotencia real está
  en MpPayment.mp_payment_id unique + estado del pedido),
- sin secret configurado: solo se procesa en dev con opt-in explícito
  STORE_MP_WEBHOOK_ALLOW_UNSIGNED=True además de DEBUG.
"""
import hashlib
import hmac
import logging
import re

from decouple import config
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.services.webhook import StoreMpWebhookQuery
from StoreApp.domains.stores.models import Store

logger  =   logging.getLogger(__name__)

#TTL del dedup de entregas (cubre la ventana de frescura de la firma).
WEBHOOK_DEDUP_SECONDS   =   600
#Un webhook legítimo de MP es un JSON chico; uno gigante es abuso -> 413.
WEBHOOK_MAX_BODY        =   16 * 1024
WEBHOOK_ID_RE           =   re.compile(r'[A-Za-z0-9_-]{1,64}')


#=========================================
# WEBHOOK SECRET + FIRMA (HMAC-SHA256, doc oficial de MP)
#=========================================
def _store_webhook_secret(store):
    """Secret del webhook de la app MP del vendedor (descifrado del vault)."""
    cfg     =   getattr(store, 'mp_webhook_config', None)
    return cfg.get_webhook_secret() if cfg else ''


def _verify_mp_signature(request, secret, resource_id) -> bool:
    """
    Valida x-signature + x-request-id: el manifest es
    'id:<data.id>;request-id:<x-request-id>;ts:<ts>;' firmado con
    HMAC-SHA256 y el webhook secret DEL VENDEDOR -> debe matchear el
    v1= del header (compare_digest).

    Sin secret configurado el evento se procesa igual SOLO en dev con
    opt-in explícito: exige DEBUG=True y STORE_MP_WEBHOOK_ALLOW_UNSIGNED
    =True en el .env — un DEBUG accidental en producción no deja el
    webhook sin verificar (un webhook sin firma permite forjar
    acreditaciones de pago).
    """
    if not secret:
        allow_unsigned  =   settings.DEBUG and config('STORE_MP_WEBHOOK_ALLOW_UNSIGNED', default = False, cast = bool)
        if allow_unsigned:
            logger.warning('Webhook MP sin secret configurado: evento procesado sin verificar firma (STORE_MP_WEBHOOK_ALLOW_UNSIGNED)')
            return True
        logger.error('Store sin webhook secret configurado: webhook de MP rechazado')
        return False
    x_signature     =   request.headers.get('x-signature', '')
    x_request_id    =   request.headers.get('x-request-id', '')
    parts           =   {}
    for pair in x_signature.split(','):
        if '=' in pair:
            key, value  =   pair.split('=', 1)
            parts[key.strip()]  =   value.strip()
    ts              =   parts.get('ts')
    v1              =   parts.get('v1')
    if not ts or not v1 or not x_request_id or not resource_id:
        return False
    #Ventana de frescura anti-replay (la doc de MP muestra ts en segundos,
    #pero hay despliegues en milisegundos: se aceptan ambos).
    try:
        ts_value    =   int(ts)
    except (TypeError, ValueError):
        return False
    if ts_value > 100_000_000_000:          # > año 5138 en segundos -> ms
        ts_value    =   ts_value / 1000
    if abs(timezone.now().timestamp() - ts_value) > 600:
        return False
    manifest        =   f'id:{resource_id};request-id:{x_request_id};ts:{ts};'
    expected        =   hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


#=========================================
# WEBHOOK VIEW
#=========================================
class StoreMpWebhookView(APIView):
    permission_classes      =   [AllowAny]
    #Sin sesión: la autenticación ES la firma HMAC (un JWT inválido no
    #debe convertir una notificación legítima de MP en 401).
    authentication_classes  =   []
    def post(self, request, slug):
        #Tamaño acotado: Content-Length y body real (un cliente puede
        #mentir el header; request.body queda cacheado para DRF).
        content_length  =   request.META.get('CONTENT_LENGTH')
        try:
            too_big     =   int(content_length or 0) > WEBHOOK_MAX_BODY
        except (TypeError, ValueError):
            too_big     =   True
        if not too_big:
            try:
                too_big =   len(request.body or b'') > WEBHOOK_MAX_BODY
            except Exception:
                too_big =   False
        if too_big:
            logger.warning('Webhook MP store=%s rechazado: body excede %s bytes', slug, WEBHOOK_MAX_BODY)
            return Response({'detail': 'Payload demasiado grande'}, status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        store       =   Store.objects.filter(slug = slug).first()
        if store is None:
            #Slug inexistente: 404 — MP reintenta un rato y abandona.
            return Response({'detail': 'Tienda no encontrada'}, status = status.HTTP_404_NOT_FOUND)
        #Body malformado (JSON escalar/array): se trata como {} — jamás 500.
        payload     =   request.data if isinstance(request.data, dict) else {}
        topic       =   payload.get('type') or request.query_params.get('topic')
        #El data.id FIRMADO es el del query string (la firma se arma con
        #ese valor); el del body NO está cubierto por la firma y se ignora.
        signed_id   =   request.query_params.get('data.id') or request.query_params.get('id')
        data        =   payload.get('data')
        body_id     =   data.get('id') if isinstance(data, dict) else None
        resource_id =   str(signed_id) if signed_id is not None else None
        if resource_id and not WEBHOOK_ID_RE.fullmatch(resource_id):
            logger.warning('Webhook MP store=%s rechazado: id con formato inválido', slug)
            return Response({'detail': 'Identificador inválido'}, status = status.HTTP_400_BAD_REQUEST)
        #Firma HMAC con el webhook secret DEL VENDEDOR de este slug.
        if not _verify_mp_signature(request, _store_webhook_secret(store), resource_id):
            logger.warning('Webhook MP store=%s rechazado: firma inválida (topic=%s id=%s)', slug, topic, resource_id)
            return Response({'detail': 'Firma de webhook inválida'}, status = status.HTTP_401_UNAUTHORIZED)
        if resource_id is None:
            #Solo alcanzable con el bypass dev (MP_WEBHOOK_ALLOW_UNSIGNED):
            #el id del body sirve de conveniencia local — en producción
            #jamás se procesa un id no firmado.
            resource_id =   str(body_id) if body_id is not None else None
            if resource_id and not WEBHOOK_ID_RE.fullmatch(resource_id):
                return Response({'detail': 'Identificador inválido'}, status = status.HTTP_400_BAD_REQUEST)
        elif body_id and str(body_id) != resource_id:
            logger.warning('Webhook MP store=%s: data.id del body ignorado (body=%s, firmado=%s)', slug, body_id, resource_id)
        #Dedup de entregas: MP reintenta el mismo evento y un replay dentro
        #de la ventana de frescura reenvía las mismas cabeceras.
        #cache.add es atómico; fail-open si el cache cae (la idempotencia
        #real está en MpPayment.mp_payment_id unique + estado del pedido).
        #Si el procesamiento explota se libera la marca para que el retry
        #de MP con el mismo request-id pueda reintentarlo.
        dedup_key       =   None
        x_request_id    =   request.headers.get('x-request-id', '')
        if x_request_id:
            dedup_key   =   f'store-mp-webhook:{slug}:{topic}:{resource_id}:{x_request_id}'
            try:
                if not cache.add(dedup_key, 1, WEBHOOK_DEDUP_SECONDS):
                    return Response({'detail': 'Notificación ya procesada'}, status = status.HTTP_200_OK)
            except Exception:
                dedup_key   =   None
        try:
            if topic == 'payment' and resource_id:
                StoreMpWebhookQuery(store, resource_id)
        except Exception:
            if dedup_key:
                try:
                    cache.delete(dedup_key)
                except Exception:
                    pass
            raise
        return Response({'detail': 'Notificación procesada'}, status = status.HTTP_200_OK)
