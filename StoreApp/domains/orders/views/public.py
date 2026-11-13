"""
Endpoints públicos de pedidos (e-commerce DAVENT).

- POST /api/stores/public/<slug>/orders/                  → crear pedido
  (customer JWT + captcha firmado + throttle, como reviews).
- GET  /api/stores/public/<slug>/orders/captcha/          → challenge.
- GET  /api/stores/public/<slug>/orders/<token>/          → seguimiento.
- GET  /api/stores/public/<slug>/orders/<token>/events/   → timeline (polling).
- POST /api/stores/public/<slug>/orders/<token>/proof/    → comprobante (multipart).
- GET  /api/stores/public/<slug>/orders/<token>/receipt/  → datos del comprobante NO FISCAL.

Anti-IDOR: el seguimiento usa `tracking_token` (secrets.token_urlsafe)
acotado a la tienda — el id numérico jamás aparece en rutas públicas.
"""
import logging
import uuid

from django.db import transaction
from django.http import Http404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import (
    PublicReadThrottle,
    ResilientAnonRateThrottle,
    ResilientUserRateThrottle,
)
from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.models import CustomerAddress
from StoreApp.domains.orders.models import Order, PaymentProof
from StoreApp.domains.orders.serializers import OrderCreateSerializer
from StoreApp.domains.orders.services.checkout import (
    INTERNAL_EVENT_KINDS,
    build_receipt_payload,
    create_order,
    find_order_by_token,
    order_public_payload,
    order_tracking_payload,
    public_store,
)
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services import issue_captcha, verify_captcha
from StoreApp.domains.stores.services.imaging import normalize_image
from StoreApp.domains.stores.services.storage import (
    _check_quota,
    _consume_quota,
    _delete_object,
    object_url,
    put_object,
    validate_image_file,
)

logger  =   logging.getLogger(__name__)
PROOF_MAX_BYTES  =   4 * 1024 * 1024   # mismo tope que el resto de imágenes
#=========================================
# THROTTLES (scopes propios con rate fija — no requieren tocar settings)
#=========================================
class OrderCreateThrottle(ResilientUserRateThrottle):
    """Alta de pedidos por comprador autenticado (10/h — muy por encima
    de un checkout legítimo, corta el flood de pedidos falsos)."""
    scope   =   'store_order_create'
    rate    =   '10/hour'
class OrderProofThrottle(ResilientAnonRateThrottle):
    """Subida de comprobantes por IP (10/h — cada una escribe en R2)."""
    scope   =   'store_order_proof'
    rate    =   '10/hour'
#=========================================
# HELPERS
#=========================================
def _sellable_or_404(slug, *, require_orders_enabled = True):
    store   =   public_store(slug, require_orders_enabled = require_orders_enabled)
    if store is None:
        raise Http404
    return store


def _order_or_404(store, tracking_token):
    order   =   find_order_by_token(store, tracking_token)
    if order is None:
        raise Http404
    return order


def _resolve_address(customer, data):
    """
    Dirección del pedido: `address_id` (CustomerAddress DEL comprador —
    IDOR: la de otro customer no matchea) tiene prioridad sobre el dict
    inline `address`. Devuelve el objeto/dict que create_order normaliza.
    """
    address_id  =   data.get('address_id')
    if address_id:
        address =   CustomerAddress.objects.filter(customer = customer, pk = address_id).first()
        if address is None:
            #IDOR/typo del cliente → 400 por campo (el checkout lo muestra
            #bajo el selector), no un 404 que parece "tienda inexistente".
            raise serializers.ValidationError({'address_id': 'La dirección elegida no existe o no es tuya.'})
        return address
    inline  =   data.get('address')
    return inline if isinstance(inline, dict) and inline else None


#=========================================
# CAPTCHA (mismo mecanismo firmado que reviews/contacto)
#=========================================
class OrderCaptchaView(APIView):
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [PublicReadThrottle]
    def get(self, request, slug):
        _sellable_or_404(slug)
        return Response(issue_captcha(slug), status = status.HTTP_200_OK)


#=========================================
# CREATE ORDER (customer JWT + captcha + throttle)
#=========================================
class PublicOrderCreateView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [OrderCreateThrottle]
    def post(self, request, slug):
        store       =   _sellable_or_404(slug)
        customer    =   request.customer
        serializer  =   OrderCreateSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        #Honeypot: con `website` lleno es un bot — se rechaza genérico
        #(un pedido falso no puede "salir bien" como en las reviews).
        if data.get('website'):
            return Response({'detail': 'No se pudo crear el pedido.'}, status = status.HTTP_400_BAD_REQUEST)
        if not verify_captcha(slug, data['challenge_id'], data['captcha_answer']):
            return Response(
                {'captcha_answer': 'El captcha venció o la respuesta no es correcta. Probá de nuevo.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        #Carrito server-side: use_cart (o el alias `cart`) lee el Cart del
        #cliente para ESTA tienda — orders importa cart (sin ciclo).
        cart    =   None
        if data.get('use_cart') or data.get('cart'):
            from StoreApp.domains.cart.models import Cart
            cart    =   Cart.objects.filter(customer = customer, store = store).prefetch_related('items').first()
            if cart is None or not cart.items.exists():
                return Response({'items': 'Tu carrito está vacío para esta tienda.'}, status = status.HTTP_400_BAD_REQUEST)
        address =   _resolve_address(customer, data)
        items   =   data.get('items') if not (data.get('use_cart') or data.get('cart')) else None
        order, created  =   create_order(
            store               =   store,
            customer            =   customer,
            items               =   items,
            address             =   address,
            shipping_method     =   data.get('shipping_method') or Order.ShippingMethod.HOME,
            payment_method      =   data['payment_method'],
            idempotency_key     =   data.get('idempotency_key') or '',
            cart                =   cart,
        )
        payload =   order_public_payload(order, store)
        return Response(payload, status = status.HTTP_201_CREATED if created else status.HTTP_200_OK)


#=========================================
# TRACKING (público por token — sin login)
#=========================================
class PublicOrderTrackView(APIView):
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [PublicReadThrottle]
    def get(self, request, slug, tracking_token):
        store   =   _sellable_or_404(slug, require_orders_enabled = False)
        order   =   _order_or_404(store, tracking_token)
        return Response(order_tracking_payload(order), status = status.HTTP_200_OK)


class PublicOrderEventsView(APIView):
    """
    Timeline de eventos del pedido (últimos 50, más viejo→nuevo no:
    ordering del modelo es created_at asc — la vista los da descendente
    para que el polling pinte lo último arriba sin recorrer todo).
    Compatible con polling cada ~5s; track F puede montar SSE encima.
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [PublicReadThrottle]
    def get(self, request, slug, tracking_token):
        store   =   _sellable_or_404(slug, require_orders_enabled = False)
        order   =   _order_or_404(store, tracking_token)
        events  =   order.events.order_by('-created_at', '-id')[:50]
        return Response([
            {
                'kind'          :   event.kind,
                'status_from'   :   event.status_from,
                'status_to'     :   event.status_to,
                'created_at'    :   event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
            if event.kind not in INTERNAL_EVENT_KINDS
        ], status = status.HTTP_200_OK)


#=========================================
# PROOF UPLOAD (multipart → WebP → R2)
#=========================================
class PublicOrderProofView(APIView):
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [OrderProofThrottle]
    def post(self, request, slug, tracking_token):
        store   =   _sellable_or_404(slug, require_orders_enabled = False)
        order   =   _order_or_404(store, tracking_token)
        #Solo métodos manuales y pedido pendiente de pago: MP acredita
        #solo por webhook y un pedido pago/cerrado no admite comprobante.
        if order.status != Order.Status.PENDING_PAYMENT or order.payment_method == Order.PaymentMethod.MP:
            return Response({'detail': 'Este pedido no admite comprobante de pago.'}, status = status.HTTP_400_BAD_REQUEST)
        #First-write-wins: el tracking_token es una credencial pública
        #(viaja en mails/WhatsApp) — si se permitiera reemplazar el
        #comprobante, cualquier poseedor del link podría pisar la
        #evidencia del comprador antes de que el dueño la revise.
        #PaymentProof no tiene estado "revisado": aceptado = el pedido
        #sale de PENDING_PAYMENT (gate de arriba) y un cierre sin pago
        #libera la fila (release_proof), así que una re-subida legítima
        #solo puede darse con un proof aún sin revisar — caso que no se
        #puede distinguir del ataque anónimo. Se rechaza todo re-upload.
        if hasattr(order, 'proof'):
            return Response({'detail': 'Este pedido ya tiene un comprobante cargado.'}, status = status.HTTP_400_BAD_REQUEST)
        upload  =   request.FILES.get('image') or request.FILES.get('file')
        if upload is None:
            return Response({'image': 'Adjuntá la foto del comprobante.'}, status = status.HTTP_400_BAD_REQUEST)
        error   =   validate_image_file(upload, PROOF_MAX_BYTES)
        if error:
            return Response({'image': error}, status = status.HTTP_400_BAD_REQUEST)
        try:
            body, _ext, content_type  =   normalize_image(upload, kind = 'chat')
        except Exception:
            return Response({'image': 'No pudimos procesar la imagen. Probá con otra.'}, status = status.HTTP_400_BAD_REQUEST)
        #Los comprobantes ocupan cuota de storage del plan como
        #cualquier imagen: fast-path sin lock antes de subir el objeto
        #(sin reemplazo posible — el proof es first-write-wins).
        size    =   len(body)
        try:
            _check_quota(store, size, replacing_bytes = 0)
        except ValueError as exc:
            return Response({'image': str(exc)}, status = status.HTTP_400_BAD_REQUEST)
        key     =   f'stores/{store.id}/proofs/{uuid.uuid4().hex}.webp'
        try:
            put_object(key, body, content_type)
        except ValueError as exc:
            return Response({'image': str(exc)}, status = status.HTTP_400_BAD_REQUEST)
        #Locks Store → Order (mismo orden que checkout/expire/cancel):
        #serializan uploads concurrentes del mismo pedido (OneToOne) y
        #el ajuste de cuota contra otras subidas de la tienda.
        try:
            with transaction.atomic():
                locked_store    =   Store.objects.select_for_update().get(pk = store.pk)
                Order.objects.select_for_update().filter(pk = order.pk).first()
                locked_order    =   Order.objects.select_related('proof').get(pk = order.pk)
                #Re-check bajo lock: dos uploads concurrentes del mismo
                #pedido pasan el fast-path de arriba a la vez — el segundo
                #espera el lock, ve el proof del primero y aborta (su
                #objeto R2 se borra en el except de abajo).
                if getattr(locked_order, 'proof', None) is not None:
                    raise ValueError('Este pedido ya tiene un comprobante cargado.')
                new_used        =   _check_quota(locked_store, size, replacing_bytes = 0)
                PaymentProof.objects.create(
                    order       =   locked_order,
                    image_key   =   key,
                    size        =   size,
                )
                _consume_quota(locked_store, new_used)
        except ValueError as exc:
            #El objeto ya subido quedaría huérfano si la cuota se agotó
            #en la re-validación bajo lock: se borra antes de responder.
            _delete_object(key)
            return Response({'image': str(exc)}, status = status.HTTP_400_BAD_REQUEST)
        logger.info('Comprobante subido: order=%s store=%s', order.pk, store.slug)
        return Response({'proof_uploaded': True, 'image': object_url(key, private = True)}, status = status.HTTP_201_CREATED)


#=========================================
# RECEIPT (datos del comprobante NO FISCAL — el PDF lo arma el front)
#=========================================
class PublicOrderReceiptView(APIView):
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [PublicReadThrottle]
    def get(self, request, slug, tracking_token):
        store   =   _sellable_or_404(slug, require_orders_enabled = False)
        order   =   _order_or_404(store, tracking_token)
        return Response(build_receipt_payload(order), status = status.HTTP_200_OK)
