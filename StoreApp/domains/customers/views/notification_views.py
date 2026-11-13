import json
import secrets
import time

from django.core import signing
from django.db import close_old_connections
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import BaseRenderer
from rest_framework.utils.encoders import JSONEncoder

from DaventProject.cache_utils import (
    CacheUnavailable,
    cache_add_strict,
    cache_delete,
)
from DaventProject.throttling import PublicReadThrottle

from StoreApp.domains.customers.authentication import (
    CustomerJWTAuthentication,
    IsCustomer,
)
from StoreApp.domains.customers.models import Customer, CustomerNotification
from StoreApp.domains.customers.serializers import CustomerNotificationSerializer
from StoreApp.domains.customers.views.auth_views import (
    CustomerApiThrottle,
)
from StoreApp.domains.stores.models import Store

"""
Avisos in-app del COMPRADOR en la web de tienda (campana + /cuenta).

- GET  /api/customer/notifications/        Bearer customer → lista
       (?store=<slug> acota a la tienda visitada) + `unread`.
- POST /api/customer/notifications/read/   {id} | {all: true, store?}
       → marca leído(s) — siempre scopeado al request.customer (IDOR:
       un id ajeno responde 404, nunca filtra existencia).
- POST /api/customer/notifications/stream-ticket/ → {ticket, expires_in}
       Ticket firmado (TimestampSigner vía signing.dumps) ligado a
       (customer, store) — EventSource no puede mandar Authorization,
       así que el Bearer se canjea por este ticket de vida corta que
       viaja en la query del stream.
- GET  /api/customer/notifications/stream/ ?ticket&store → SSE
       (text/event-stream). Cada conexión dura STREAM_MAX_SECONDS y el
       front reconecta con ticket nuevo: un stream más largo chocaría
       con el timeout de gunicorn (60s) y con los read-timeouts del
       proxy. Cada stream ocupa UN gthread: el corte corto + heartbeat
       liberan el hilo rápido en tabs cerradas.

Nada de esto toca el canal de mails: son dos avisos paralelos del mismo
evento (el mail llega al invitado; la campana solo al registrado).
"""

STREAM_SALT         =   'customer-notifications-stream'
TICKET_TTL          =   120         # segundos de vida del ticket de stream
STREAM_MAX_SECONDS  =   50          # < timeout de gunicorn (60s)
POLL_SECONDS        =   4           # cadencia de consulta a la base
PING_SECONDS        =   15          # heartbeat SSE (detecta tabs muertas)
LIST_LIMIT          =   50
#Un ticket abre UN stream (jti de un solo uso) y un customer no puede
#tener más de N streams abiertos a la vez: cada conexión ocupa un
#gthread ~50s — sin estos topes un solo cliente saturaba todos los
#workers del API (ver customers-sse:worker-exhaustion).
STREAM_MAX_PER_CUSTOMER =   3


class CustomerStreamThrottle(PublicReadThrottle):
    """Scope propio 'customer_notifications_stream' (settings): una
    conexión SSE no es una lectura — ocupa un worker-thread ~50s. El
    bucket es por IP+acción como PublicReadThrottle."""
    scope   =   'customer_notifications_stream'


def _session_epoch(customer):
    """Epoch de sesión sellado en el ticket: tokens_valid_after del
    customer (0 si nunca se selló). Si el comprador cierra sesión o se
    revocan tokens después de emitido el ticket, el epoch cambia y el
    ticket muere aunque no venció el TTL."""
    valid_after =   getattr(customer, 'tokens_valid_after', None)
    return int(valid_after.timestamp()) if valid_after else 0


def _claim_ticket(jti):
    """Un solo uso por jti: el primer connect gana; cualquier replay del
    mismo ticket dentro del TTL se rechaza. Fail-open si el cache cae
    (misma política que los throttles — el SSE no puede quedar en 500
    por una falla de Redis)."""
    try:
        return cache_add_strict(f'sse:ticket:{jti}', 1, TICKET_TTL)
    except CacheUnavailable:
        return True


def _acquire_stream_slot(customer_id):
    """Reclama un slot libre con cache_add atómico (SET NX): máximo
    STREAM_MAX_PER_CUSTOMER streams vivos por customer. Devuelve
    (permitido, slot_key): slot_key None cuando el cache está caído —
    fail-open igual que los throttles, no hay forma de contar sin él."""
    try:
        for i in range(STREAM_MAX_PER_CUSTOMER):
            key =   f'sse:stream:{customer_id}:{i}'
            if cache_add_strict(key, 1, STREAM_MAX_SECONDS + 30):
                return True, key
        return False, None
    except CacheUnavailable:
        return True, None


def _release_stream_slot(slot_key):
    if slot_key:
        cache_delete(slot_key)


def _unread_count(customer_id, store_slug = ''):
    qs  =   CustomerNotification.objects.filter(customer_id = customer_id, read_at__isnull = True)
    if store_slug:
        qs  =   qs.filter(store__slug = store_slug)
    return qs.count()


class CustomerNotificationListView(APIView):
    """
    GET /api/customer/notifications/?store=<slug> →
    {notifications: [≤50 más recientes], unread: n}. `store` es un
    filtro opcional por slug (sin filtro devuelve todas las tiendas del
    comprador — su propio dato, no hay fuga).
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def get(self, request):
        customer    =   request.customer
        qs          =   CustomerNotification.objects.filter(customer = customer)
        slug        =   (request.query_params.get('store') or '').strip().lower()
        if slug:
            qs  =   qs.filter(store__slug = slug)
        notifications   =   CustomerNotificationSerializer(qs[:LIST_LIMIT], many = True).data
        return Response({'notifications': notifications, 'unread': _unread_count(customer.pk, slug)}, status = status.HTTP_200_OK)


class CustomerNotificationReadView(APIView):
    """
    POST /api/customer/notifications/read/ — {id} marca UN aviso propio
    (ajeno → 404); {all: true, store?} marca todos los no-leídos del
    comprador (acotado a la tienda si viene `store`).
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def post(self, request):
        customer    =   request.customer
        data        =   request.data if isinstance(request.data, dict) else {}
        slug        =   (data.get('store') or '').strip().lower()
        if data.get('all'):
            qs      =   CustomerNotification.objects.filter(customer = customer, read_at__isnull = True)
            if slug:
                qs  =   qs.filter(store__slug = slug)
            qs.update(read_at = timezone.now())
            return Response({'ok': True, 'unread': _unread_count(customer.pk)}, status = status.HTTP_200_OK)
        notification    =   CustomerNotification.objects.filter(pk = data.get('id'), customer = customer).first()
        if notification is None:
            return Response({'detail': 'No encontrada.'}, status = status.HTTP_404_NOT_FOUND)
        if notification.read_at is None:
            notification.read_at    =   timezone.now()
            notification.save(update_fields = ['read_at', 'updated_at'])
        return Response({'ok': True, 'unread': _unread_count(customer.pk)}, status = status.HTTP_200_OK)


class CustomerNotificationStreamTicketView(APIView):
    """
    POST /api/customer/notifications/stream-ticket/ {store} →
    {ticket, expires_in}. El ticket firma (customer.pk, slug) con vida
    TICKET_TTL — el front lo canjea en cada conexión del EventSource.
    """
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [CustomerApiThrottle]
    def post(self, request):
        slug    =   ((request.data or {}).get('store') or '').strip().lower()
        #jti de un solo uso + epoch de sesión: el ticket no es un bearer
        #replayable — abre UN stream y muere si la sesión se revocó.
        payload =   {
            'c' :   request.customer.pk,
            's' :   slug,
            'j' :   secrets.token_urlsafe(16),
            'e' :   _session_epoch(request.customer),
        }
        ticket  =   signing.dumps(payload, salt = STREAM_SALT)
        return Response({'ticket': ticket, 'expires_in': TICKET_TTL}, status = status.HTTP_200_OK)


class _EventStreamRenderer(BaseRenderer):
    """
    Registra `text/event-stream` en la negociación de contenido: sin un
    renderer con ese media type, DRF responde 406 antes de ejecutar el
    get() porque el EventSource pide `Accept: text/event-stream`. La
    respuesta es un StreamingHttpResponse — DRF nunca lo pasa por
    render(), así que el método queda inerte.
    """
    media_type  =   'text/event-stream'
    format      =   'event-stream'
    def render(self, data, accepted_media_type = None, renderer_context = None):
        return data


class CustomerNotificationStreamView(APIView):
    """
    GET /api/customer/notifications/stream/?ticket&store → SSE.

    Sin DRF auth: la credencial es el ticket firmado (Bearer no puede
    viajar en EventSource). Emite `event: notification` por cada aviso
    nuevo (id > Last-Event-ID), `event: unread` cuando cambia el conteo
    y comentarios `: ping` de heartbeat. Cierra solo a los
    STREAM_MAX_SECONDS — EventSource reintenta y el front repite con un
    ticket fresco (ver composable useCustomerNotifications).
    """
    permission_classes      =   [AllowAny]
    authentication_classes  =   []
    throttle_classes        =   [CustomerStreamThrottle]
    renderer_classes        =   [_EventStreamRenderer]
    def get(self, request):
        ticket  =   (request.query_params.get('ticket') or '').strip()
        slug    =   (request.query_params.get('store') or '').strip().lower()
        try:
            data    =   signing.loads(ticket, salt = STREAM_SALT, max_age = TICKET_TTL)
        except signing.BadSignature:
            return Response({'detail': 'Ticket inválido o vencido.'}, status = status.HTTP_401_UNAUTHORIZED)
        if not isinstance(data, dict) or data.get('s') != slug:
            return Response({'detail': 'Ticket inválido.'}, status = status.HTTP_401_UNAUTHORIZED)
        customer    =   Customer.objects.filter(pk = data.get('c'), is_active = True).first()
        if customer is None:
            return Response({'detail': 'Sesión inválida.'}, status = status.HTTP_401_UNAUTHORIZED)
        #Epoch de sesión sellado al emitir el ticket: si el comprador
        #cerró sesión o se revocaron sus tokens después, el ticket
        #muere aunque no venció el TTL (replay post-logout).
        try:
            ticket_epoch =   int(data.get('e') or 0)
        except (TypeError, ValueError):
            ticket_epoch =   0
        if ticket_epoch != _session_epoch(customer):
            return Response({'detail': 'Sesión revocada.'}, status = status.HTTP_401_UNAUTHORIZED)
        #Un solo uso por jti: el mismo ticket no abre dos streams.
        if not data.get('j') or not _claim_ticket(data['j']):
            return Response({'detail': 'Ticket ya utilizado.'}, status = status.HTTP_401_UNAUTHORIZED)
        #Cupo de streams concurrentes por customer.
        allowed, slot_key  =   _acquire_stream_slot(customer.pk)
        if not allowed:
            return Response({'detail': 'Demasiadas conexiones simultáneas.'}, status = status.HTTP_429_TOO_MANY_REQUESTS)
        store_id    =   None
        if slug:
            store_id    =   Store.objects.filter(slug = slug).values_list('pk', flat = True).first()
        last_id     =   0
        try:
            last_id =   int(request.META.get('HTTP_LAST_EVENT_ID') or 0)
        except (TypeError, ValueError):
            last_id =   0
        response    =   StreamingHttpResponse(
            self._events(customer.pk, store_id, last_id, slot_key),
            content_type    =   'text/event-stream',
        )
        response['Cache-Control']       =   'no-cache'
        #Sin esto nginx buffera el stream y los eventos no llegan en vivo.
        response['X-Accel-Buffering']   =   'no'
        return response

    def _events(self, customer_id, store_id, last_id, slot_key = None):
        encoder     =   JSONEncoder()
        deadline    =   time.monotonic() + STREAM_MAX_SECONDS
        next_ping   =   time.monotonic() + PING_SECONDS
        sent_unread =   None
        try:
            yield ': conectado\n\n'
            while time.monotonic() < deadline:
                close_old_connections()
                qs      =   CustomerNotification.objects.filter(customer_id = customer_id)
                if store_id:
                    qs  =   qs.filter(store_id = store_id)
                for notification in qs.filter(id__gt = last_id).order_by('id')[:50]:
                    last_id =   notification.id
                    payload =   encoder.encode(CustomerNotificationSerializer(notification).data)
                    yield   f'id: {notification.id}\nevent: notification\ndata: {payload}\n\n'
                unread  =   qs.filter(read_at__isnull = True).count()
                if unread != sent_unread:
                    sent_unread =   unread
                    yield   f'event: unread\ndata: {json.dumps({"unread": unread})}\n\n'
                if time.monotonic() >= next_ping:
                    next_ping   =   time.monotonic() + PING_SECONDS
                    yield   ': ping\n\n'
                    #Re-check de sesión dentro del stream: el epoch del
                    #ticket solo se valida al conectar — un logout o una
                    #desactivación a mitad de stream debe cortarlo.
                    if not Customer.objects.filter(pk = customer_id, is_active = True).exists():
                        yield 'event: bye\ndata: {}\n\n'
                        return
                time.sleep(min(POLL_SECONDS, max(0.5, deadline - time.monotonic())))
            #Cierre limpio antes del timeout del worker/proxy: el front
            #reconecta con ticket nuevo (el viejo puede seguir vivo).
            yield 'event: bye\ndata: {}\n\n'
        except (BrokenPipeError, ConnectionResetError, GeneratorExit):
            return
        finally:
            _release_stream_slot(slot_key)
