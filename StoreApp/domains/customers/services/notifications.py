import logging

from django.utils import timezone

from StoreApp.domains.customers.models import CustomerNotification, StoreMembership

"""
Avisos in-app del COMPRADOR en la web de tienda (campana + /cuenta).

Espejo del dominio notifications de AdminApp pero para `Customer` (la
cuenta global del comprador — NO auth.User): cada fila cuelga de
(customer, store) porque la campana muestra solo los avisos de la
tienda que se está visitando.

- upsert_customer_notification: dedupe por (customer, kind,
  dedupe_key) — un evento que se repite actualiza el aviso y lo
  devuelve a no-leído en vez de duplicarlo.
- notify_customer_order / _support / _subscription: hooks de orders
  (OrderEvent), support (respuesta del dueño) y memberships (ciclo de
  la suscripción). Todos best-effort: el caller envuelve en try/except
  — una falla acá NUNCA puede romper el flujo del pedido/hilo/cobro.
- notify_store_discount: broadcast a los miembros activos de la tienda
  cuando el dueño crea/reactiva un descuento (ofertas y ofertas
  especiales = campaña del calendario).

`target` es la vista de /cuenta destino del click ('pedidos',
'suscripciones', 'soporte') o 'catalogo'; '' = solo marca leído.
"""
logger  =   logging.getLogger(__name__)


#=========================================
# UPSERT
#=========================================
def upsert_customer_notification(customer, store, kind : str, title : str, body : str = '', target : str = '', dedupe_key : str = ''):
    """
    Crea o actualiza el aviso deduplicado. Al actualizar se reescribe
    título/detalle/destino, se limpia read_at y se refresca created_at
    para que vuelva a figurar como nuevo (misma semántica que
    AdminApp.upsert_notification).
    """
    now     =   timezone.now()
    notification, _  =   CustomerNotification.objects.update_or_create(
        customer    =   customer,
        store       =   store,
        kind        =   kind,
        dedupe_key  =   dedupe_key,
        defaults    =   {
            'title'     :   title,
            'body'      :   body,
            'target'    :   target,
            'read_at'   :   None,
            'created_at':   now,
        },
    )
    return notification


def _store_label(store):
    """Nombre público de la tienda para los textos de los avisos."""
    customization   =   getattr(store, 'customization', None)
    display         =   (getattr(customization, 'display_name', '') or '').strip()
    return display or getattr(store, 'slug', '') or 'la tienda'


#=========================================
# PEDIDO — estado de seguimiento (OrderEvent → comprador registrado)
#=========================================
def notify_customer_order(order, event):
    """
    Un aviso 'order' deduplicado por pedido: cada cambio de estado lo
    re-aviva (pagado → enviado → entregado pisa el anterior). Solo si el
    pedido tiene Customer registrado (order.customer) — el comprador
    invitado no tiene campana; su aviso es el mail.
    """
    customer    =   getattr(order, 'customer', None)
    store       =   getattr(order, 'store', None)
    if customer is None or store is None:
        return None
    from StoreApp.domains.orders.services.mails import CUSTOMER_STATUS_PHRASES
    kind        =   getattr(event, 'kind', '') or ''
    phrase, detail  =   CUSTOMER_STATUS_PHRASES.get(kind, ('se actualizó', ''))
    return upsert_customer_notification(
        customer,
        store,
        CustomerNotification.KIND_ORDER,
        f'Tu pedido {order.code} {phrase}'[:200],
        body        =   f'{_store_label(store)} · {detail}'[:500],
        target      =   'pedidos',
        dedupe_key  =   f'order:{order.pk}',
    )


#=========================================
# SOPORTE — respuesta del comercio en un hilo del comprador
#=========================================
def notify_customer_support(thread, message):
    """
    El dueño respondió en el hilo: UN aviso 'support' deduplicado por
    hilo que se re-aviva con cada respuesta nueva (mismo criterio que el
    'store_message' del dueño).
    """
    customer    =   getattr(thread, 'customer', None)
    store       =   getattr(thread, 'store', None)
    if customer is None or store is None:
        return None
    subject     =   (getattr(thread, 'subject', '') or '').strip()
    preview     =   (getattr(message, 'body', '') or '').strip()
    body        =   f'{subject} — {preview[:300]}' if subject else preview[:500]
    return upsert_customer_notification(
        customer,
        store,
        CustomerNotification.KIND_SUPPORT,
        f'Nueva respuesta de {_store_label(store)}'[:200],
        body        =   body[:500],
        target      =   'soporte',
        dedupe_key  =   f'support:{thread.pk}',
    )


#=========================================
# SUSCRIPCIÓN — ciclo de la membresía de tienda del comprador
#=========================================
_SUB_TITLES =   {
    'pending'   :   'Tu suscripción quedó pendiente de pago',
    'active'    :   'Tu suscripción está activa',
    'past_due'  :   'Tu suscripción tiene el pago vencido',
    'cancelled' :   'Tu suscripción fue cancelada',
    'expired'   :   'Tu suscripción venció',
}


def notify_customer_subscription(subscription, status_to = '', title = '', body = '', dedupe_key = ''):
    """
    Aviso 'membership' del ciclo de la suscripción del comprador en la
    tienda. Por defecto deduplica por suscripción (un aviso que refleja
    el estado actual); el aviso de "por vencer" pasa su propio
    dedupe_key para no pisar el de estado.
    """
    membership  =   getattr(subscription, 'membership', None)
    customer    =   getattr(membership, 'customer', None)
    store       =   getattr(membership, 'store', None)
    if customer is None or store is None:
        return None
    plan_name   =   getattr(getattr(subscription, 'plan', None), 'name', '') or 'tu plan'
    headline    =   (title or _SUB_TITLES.get(status_to) or 'Tu suscripción se actualizó')[:200]
    detail      =   (body or f'{_store_label(store)} · {plan_name}')[:500]
    return upsert_customer_notification(
        customer,
        store,
        CustomerNotification.KIND_MEMBERSHIP,
        headline,
        body        =   detail,
        target      =   'suscripciones',
        dedupe_key  =   dedupe_key or f'sub:{subscription.pk}',
    )


def notify_customer_subscription_expiring(subscription):
    """
    "Por vencer" del cron membership_expiry_notices: aviso propio (no
    pisa el de estado) deduplicado por vigencia — si renueva y vuelve a
    acercarse el fin, se re-avisa.
    """
    until       =   getattr(subscription, 'vigente_hasta', None)
    when        =   f'Vence el {until.strftime("%d/%m/%Y")}.' if until else ''
    plan_name   =   getattr(getattr(subscription, 'plan', None), 'name', '') or 'tu plan'
    return notify_customer_subscription(
        subscription,
        title       =   f'Tu suscripción a {plan_name} está por vencer'[:200],
        body        =   f'{when} Renová para no perder los beneficios.'[:500],
        dedupe_key  =   f'subexp:{subscription.pk}:{until.date().isoformat() if until else ""}',
    )


#=========================================
# OFERTA — descuento del dueño → miembros de la tienda
#=========================================
def notify_store_discount(store, discount):
    """
    Broadcast: UNA notificación 'offer' por miembro activo de la tienda,
    deduplicada por (descuento, comprador) — re-procesar el mismo
    descuento no duplica. Descuentos con campaña del calendario
    (SpecialOfferCampaign) salen como "oferta especial".
    """
    if store is None or discount is None:
        return 0
    campaign    =   getattr(discount, 'campaign', None)
    is_special  =   bool(campaign and campaign.is_running())
    percent     =   getattr(discount, 'percent', 0)
    name        =   (getattr(discount, 'name', '') or 'Oferta').strip()
    ends_at     =   getattr(discount, 'ends_at', None)
    starts_at   =   getattr(discount, 'starts_at', None)
    now         =   timezone.now()
    if starts_at and starts_at > now:
        detail  =   f'-{percent}% · empieza el {starts_at.strftime("%d/%m/%Y")}'
    elif ends_at:
        detail  =   f'-{percent}% · hasta el {ends_at.strftime("%d/%m/%Y")}'
    else:
        detail  =   f'-{percent}%'
    title       =   (f'Oferta especial: {name}' if is_special else f'Oferta: {name}')[:200]
    rows        =   [
        CustomerNotification(
            customer    =   membership.customer,
            store       =   store,
            kind        =   CustomerNotification.KIND_OFFER,
            dedupe_key  =   f'offer:{discount.pk}',
            title       =   title,
            body        =   f'{_store_label(store)} · {detail}'[:500],
            target      =   'catalogo',
            created_at  =   now,
        )
        for membership in (
            StoreMembership.objects
            .filter(store = store, status = StoreMembership.STATUS_ACTIVE, customer__is_active = True)
            .select_related('customer')
            .iterator()
        )
    ]
    if not rows:
        return 0
    return len(CustomerNotification.objects.bulk_create(rows, ignore_conflicts = True, batch_size = 500))


#=========================================
# NOVEDAD — post nuevo del feed → miembros de la tienda
#=========================================
def notify_store_feed_post(store, post):
    """
    Broadcast: UNA notificación 'feed' por miembro activo de la tienda
    cuando el dueño publica una publicación en Novedades, deduplicada
    por (post, comprador) — republicar o re-procesar no duplica. El
    click lleva a la página /novedades (target 'novedades').
    """
    if store is None or post is None:
        return 0
    caption     =   (getattr(post, 'caption', '') or '').strip()
    kind_label  =   {
        'poll': 'encuesta', 'video': 'video', 'image': 'foto',
        'embed': 'publicación de sus redes',
    }.get(getattr(post, 'kind', ''), 'publicación')
    title       =   f'{_store_label(store)} publicó una {kind_label} nueva'[:200]
    body        =   caption[:500] if caption else 'Mirá lo último en Novedades.'
    now         =   timezone.now()
    rows        =   [
        CustomerNotification(
            customer    =   membership.customer,
            store       =   store,
            kind        =   CustomerNotification.KIND_FEED,
            dedupe_key  =   f'feed:{post.pk}',
            title       =   title,
            body        =   body,
            target      =   'novedades',
            created_at  =   now,
        )
        for membership in (
            StoreMembership.objects
            .filter(store = store, status = StoreMembership.STATUS_ACTIVE, customer__is_active = True)
            .select_related('customer')
            .iterator()
        )
    ]
    if not rows:
        return 0
    return len(CustomerNotification.objects.bulk_create(rows, ignore_conflicts = True, batch_size = 500))
