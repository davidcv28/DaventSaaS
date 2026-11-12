import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from DaventProject.cache_utils import cache_add, cache_incr, cache_set
from StoreApp.domains.memberships.services.benefits import store_display_name
from StoreApp.domains.orders.services.checkout import find_order_by_token
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services import contact_target
from StoreApp.domains.support.models import SupportMessage, SupportThread

"""

Servicios del dominio support (hilos comprador <-> dueño de tienda).

- create_thread / post_message: ÚNICOS puntos de escritura — crean el
  mensaje, actualizan el denormalizado del thread y notifican al dueño
  cuando escribe el comprador (upsert_notification deduplicado por hilo
  + email best-effort vía task Celery; nada de esto puede romper el
  request: errores → log, nunca excepción).
- mark_thread_read: lectura por lado — marca los mensajes DE LA
  CONTRAPARTE como leídos por quien abrió el hilo.
- resolve_order_link: valida order_token contra (store, customer) —
  anti-IDOR doble: un token de otra tienda o de otro comprador no
  resuelve.
- notify_owner_message / deliver_support_email: avisos al dueño.
  target='inquiries' del dashboard (tab "Consultas" de Vender online).
"""
logger  =   logging.getLogger(__name__)
#Abuso: cota AGREGADA por tienda (todos los compradores juntos) y
#cadencia mínima entre emails al dueño por hilo — sin ellas, una cuenta
#descartable podía generar ~1.400 emails/día al contacto del negocio.
SUPPORT_STORE_MSGS_PER_HOUR  =   120
SUPPORT_EMAIL_MIN_INTERVAL   =   timedelta(minutes = 30)
#=========================================
# HELPERS
#=========================================
def customer_display_name(customer):
    """Nombre visible del comprador para títulos/payloads ('Ana Perez' → email)."""
    name    =   f'{customer.first_name} {customer.last_name}'.strip()
    return name or customer.email

def resolve_order_link(store, customer, order_token):
    """
    Pedido del comprador en ESA tienda por su tracking_token público.
    Devuelve Order o None (token vacío/ajeno/inexistente → None; la vista
    decide si eso es 400 o hilo sin pedido).
    """
    token   =   (order_token or '').strip()
    if not token:
        return None
    order   =   find_order_by_token(store, token)
    if order is None or order.customer_id != customer.pk:
        return None
    return order

def customer_visible_store(slug):
    """
    Tienda visible para un comprador: publicada, no bloqueada y con
    `has_ecommerce` en el plan del dueño (misma regla que
    memberships._public_store_or_404). NO exige orders_enabled: el
    soporte no es una venta — una tienda con el checkout apagado igual
    puede recibir mensajes — pero SÍ exige el beneficio de plan: abrir
    hilos nuevos es superficie del e-commerce (los hilos ya existentes
    siguen legibles, igual que el tracking de pedidos emitidos).
    """
    store   =   (
        Store.objects
        .filter(slug = (slug or '').strip().lower(), is_published = True, is_blocked = False)
        .select_related('user__user', 'customization')
        .first()
    )
    if store is None:
        return None
    from StoreApp.domains.stores.services.commerce import store_has_ecommerce
    if not store_has_ecommerce(store):
        return None
    return store

def _store_inbound_quota_ok(store):
    """
    Como mucho SUPPORT_STORE_MSGS_PER_HOUR mensajes de compradores por
    hora EN LA TIENDA (agregado de todos los customer). Contador en
    cache fail-open — misma política que los throttles: una caída de
    Redis no puede tumbar el canal de soporte (el throttle por cliente
    sigue activo como primera capa).
    """
    key     =   f'support:store:{store.pk}:msgs'
    if cache_add(key, 1, 3600):
        return True
    try:
        count   =   cache_incr(key)
    except ValueError:
        cache_set(key, 1, 3600)
        count   =   1
    if count is None:
        return True
    return count <= SUPPORT_STORE_MSGS_PER_HOUR

def _check_store_inbound_quota(store):
    if not _store_inbound_quota_ok(store):
        from rest_framework.exceptions import Throttled
        raise Throttled(detail = 'La tienda recibió demasiados mensajes. Probá más tarde.')
#=========================================
# ESCRITURA (único camino — lo usan las vistas de ambos lados)
#=========================================
def create_thread(*, customer, store, subject, body, order = None):
    """
    Crea el hilo + su primer mensaje (del comprador) en un atomic y
    dispara los avisos al dueño. Devuelve el SupportThread.
    """
    _check_store_inbound_quota(store)
    now     =   timezone.now()
    with transaction.atomic():
        thread  =   SupportThread.objects.create(
            store               =   store,
            customer            =   customer,
            order               =   order,
            subject             =   subject.strip()[:140],
            status              =   SupportThread.Status.OPEN,
            last_message_at     =   now,
            last_message_by     =   SupportMessage.Sender.CUSTOMER,
        )
        message =   SupportMessage.objects.create(
            thread              =   thread,
            sender              =   SupportMessage.Sender.CUSTOMER,
            body                =   body.strip(),
        )
    notify_owner_message(thread, message)
    enqueue_support_email(thread, message)
    return thread

def post_message(thread, *, sender, body):
    """
    Agrega un mensaje append-only al hilo y refresca su denormalizado.
    Solo se llama con el hilo ya validado (propio + status open) por la
    vista. Devuelve el SupportMessage. Si escribe el comprador avisa al
    dueño; si escribe el dueño no notifica a nadie (él ya está en el panel).
    """
    if sender == SupportMessage.Sender.CUSTOMER:
        _check_store_inbound_quota(thread.store)
    message =   SupportMessage.objects.create(
        thread  =   thread,
        sender  =   sender,
        body    =   body.strip(),
    )
    #Denormalizado del hilo + updated_at (auto_now viaja en update_fields).
    thread.last_message_at     =   message.created_at
    thread.last_message_by     =   sender
    thread.save(update_fields = ['last_message_at', 'last_message_by', 'updated_at'])
    if sender == SupportMessage.Sender.CUSTOMER:
        notify_owner_message(thread, message)
        enqueue_support_email(thread, message)
    else:
        #Respuesta del dueño → campana del comprador (CustomerNotification
        #'support', dedupe por hilo). Best-effort como los avisos al dueño.
        try:
            from StoreApp.domains.customers.services.notifications import notify_customer_support
            notify_customer_support(thread, message)
        except Exception:
            logger.exception('No se pudo crear la notificación del comprador %s', thread.pk)
    return message

def set_thread_status(thread, status):
    """open <-> closed. Idempotente: setear el estado actual es no-op."""
    if thread.status == status:
        return thread
    thread.status  =   status
    thread.save(update_fields = ['status', 'updated_at'])
    return thread

def mark_thread_read(thread, reader):
    """
    Marca como leídos POR `reader` ('customer'/'owner') todos los mensajes
    de la contraparte del hilo. Devuelve cuántos se marcaron.
    """
    now             =   timezone.now()
    if reader == 'customer':
        field   =   'read_by_customer_at'
        other   =   SupportMessage.Sender.OWNER
    else:
        field   =   'read_by_owner_at'
        other   =   SupportMessage.Sender.CUSTOMER
    return thread.messages.filter(sender = other, **{f'{field}__isnull': True}).update(**{field: now})
#=========================================
# UNREAD (conteos por lado — anotados en los querysets de las vistas)
#=========================================
def unread_messages_q(reader):
    """
    Q para anotar `unread_count`: mensajes de la CONTRAPARTE que `reader`
    todavía no leyó. reader='customer' → enviados por el dueño sin
    read_by_customer_at; 'owner' → enviados por el comprador sin
    read_by_owner_at.
    """
    if reader == 'customer':
        return Q(messages__sender = SupportMessage.Sender.OWNER, messages__read_by_customer_at__isnull = True)
    return Q(messages__sender = SupportMessage.Sender.CUSTOMER, messages__read_by_owner_at__isnull = True)
#=========================================
# NOTIFICACIONES / EMAIL AL DUEÑO
#=========================================
def notify_owner_message(thread, message):
    """
    Aviso in-app al dueño por mensaje del comprador: UN solo Notification
    'store_message' deduplicado por hilo (dedupe_key=support:<pk>) que se
    re-aviva con cada mensaje nuevo. Best-effort: nunca rompe el request.
    """
    auth_user   =   getattr(thread.store.user, 'user', None)
    if auth_user is None:
        return
    try:
        from AdminApp.domains.notifications.models import Notification
        from AdminApp.domains.notifications.services import upsert_notification
        store_name  =   store_display_name(thread.store)
        customer    =   customer_display_name(thread.customer)
        upsert_notification(
            auth_user,
            Notification.KIND_STORE_MESSAGE,
            f'Nuevo mensaje de {customer} — {store_name}'[:200],
            body        =   f'{thread.subject} — {message.body[:300]}'[:500],
            target      =   'inquiries',
            dedupe_key  =   f'support:{thread.pk}',
        )
    except Exception:
        logger.exception('No se pudo crear la notificación de soporte %s', thread.pk)

def enqueue_support_email(thread, message):
    """
    Email best-effort al contacto del negocio por mensaje del comprador.
    El SMTP corre en Celery (mismo patrón que legalpages); sin broker o
    con el task caído, la notificación in-app ya quedó.

    Cadencia: como mucho UN email por hilo cada SUPPORT_EMAIL_MIN_INTERVAL
    — el resto de mensajes del comprador queda cubierto por la
    notificación in-app (deduplicada por hilo). El primer mensaje del
    hilo siempre avisa.
    """
    prev    =   (
        thread.messages
        .filter(sender = SupportMessage.Sender.CUSTOMER, created_at__lt = message.created_at)
        .order_by('-created_at')
        .values_list('created_at', flat = True)
        .first()
    )
    if prev is not None and message.created_at - prev < SUPPORT_EMAIL_MIN_INTERVAL:
        return
    try:
        from StoreApp.domains.support.tasks import send_support_message_email
        send_support_message_email.delay(message.pk)
    except Exception:
        logger.exception('No se pudo encolar el email de soporte %s', message.pk)

def deliver_support_email(message):
    """
    Envío real del aviso (lo corre la task de Celery). Texto plano al
    contact_email de la tienda o al email del dueño. False sin destino o
    con SMTP caído — el caller (task) reintenta.
    """
    thread  =   message.thread
    store   =   thread.store
    target  =   contact_target(store)
    if not target:
        return False
    store_name  =   store_display_name(store)
    customer    =   customer_display_name(thread.customer)
    order_bit   =   f'\nPedido: {thread.order.code}' if thread.order_id else ''
    body        =   (
        f'{customer} te escribió desde la web de {store_name}.\n\n'
        f'Asunto: {thread.subject}{order_bit}\n\n'
        f'{message.body}\n\n'
        'Podés responderlo desde el panel → sección Soporte.'
    )
    try:
        send_mail(
            subject         =   f'[Web] Nuevo mensaje de {customer} — {store_name}'[:200],
            message         =   body,
            from_email      =   settings.DEFAULT_FROM_EMAIL,
            recipient_list  =   [target],
            fail_silently   =   False,
        )
    except Exception:
        logger.exception('No se pudo enviar el email de soporte %s', message.pk)
        return False
    return True
