from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from AdminApp.domains.notifications.models import ChangelogEntry, Notification

"""
Servicios del dominio notifications.

- upsert_notification: aviso deduplicado por (user, kind, dedupe_key) —
  el mismo evento que se repite actualiza el existente y lo devuelve a
  no-leído (created_at/updated_at se refrescan).
- notify_product_review / notify_staff_message: hooks de StoreApp y
  chat (imports perezosos para no acoplar el orden de las apps).
- sync_subscription_notification: se corre en cada GET del panel —
  mantiene vivo el aviso de fin de período sin esperar al cron de mails.
- notify_changelog: fan-out a todos los usuarios activos al publicar.
"""

NOTICE_DAYS     =   3


#=========================================
# UPSERT
#=========================================
def upsert_notification(user, kind : str, title : str, body : str = '', target : str = '', dedupe_key : str = ''):
    """
    Crea o actualiza el aviso deduplicado. Al actualizar se reescribe
    título/detacalle/destino, se limpia read_at y se refresca
    created_at para que vuelva a figurar como nuevo/no-leído.
    """
    now     =   timezone.now()
    notification, _  =   Notification.objects.update_or_create(
        user        =   user,
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


#=========================================
# TRIGGERS
#=========================================
def notify_product_review(store, product_name : str = ''):
    """Una opinión nueva en la web pública: UN solo aviso que se actualiza."""
    auth_user   =   getattr(store.user, 'user', None)
    if auth_user is None:
        return None
    body        =   f'Sobre {product_name}.' if product_name else ''
    return upsert_notification(
        auth_user,
        Notification.KIND_REVIEW,
        'Un producto acaba de recibir una opinión',
        body    =   body,
        target  =   'reviews',
    )


def notify_staff_message(thread):
    """El staff escribió en el hilo del cliente: aviso informativo (no abre el chat)."""
    return upsert_notification(
        thread.customer,
        Notification.KIND_ADMIN_MESSAGE,
        'Tenés un mensaje pendiente del equipo DAVENT',
        body    =   'Entrá a la sección Ayuda para verlo en la conversación.',
        target  =   'support',
    )


def notify_changelog(entry : ChangelogEntry):
    """Publicación de una novedad: una Notification por usuario activo."""
    now     =   timezone.now()
    rows    =   [
        Notification(
            user            =   user,
            kind            =   Notification.KIND_CHANGELOG,
            dedupe_key      =   f'changelog:{entry.pk}',
            title           =   'Se agregaron nuevas funcionalidades',
            body            =   entry.title,
            target          =   'changelog',
            created_at      =   now,
        )
        for user in User.objects.filter(is_active = True).only('id').iterator()
    ]
    if rows:
        Notification.objects.bulk_create(rows, ignore_conflicts = True)


#=========================================
# SUSCRIPCIÓN (espejo de subscription_notices, pero in-app)
#=========================================
def _subscription_of(user):
    return getattr(getattr(user, 'profile', None), 'suscription', None)


def sync_subscription_notification(user):
    """
    Mantiene el aviso de fin de período al día con cada lectura del panel:
    - por vencer (<= NOTICE_DAYS): dedupe por período, target 'plans'.
    - vencido: ídem; si el usuario renovó/canjeó otro plan el período
      cambia y el aviso viejo queda como historia (se puede limpiar a
      mano si molesta — nunca se borra solo).
    - débito automático vivo (auto_renew sin baja): igual que los mails,
      MP renueva solo y no hay nada que avisar; los avisos pendientes de
      ese tipo se marcan leídos para no contradecir el estado real.
    """
    suscription   =   _subscription_of(user)
    if suscription is None or suscription.status != suscription.STATUS_ACTIVE:
        return
    now         =   timezone.now()
    until       =   suscription.access_until()
    #Débito automático vivo: se saltea igual que en los mails.
    auto_alive  =   suscription.auto_renew and not suscription.cancelled_at
    if until is None:
        return
    if not auto_alive and until > now and until <= now + timedelta(days = NOTICE_DAYS):
        days_left   =   max(1, (until - now).days)
        upsert_notification(
            user,
            Notification.KIND_SUBSCRIPTION,
            f'Tu plan está por vencer en {days_left} {"día" if days_left == 1 else "días"}',
            body    =   f'Vence el {until.strftime("%d/%m/%Y")}. Renová antes para no perder tu web.',
            target  =   'plans',
            dedupe_key  =   f'subscription:ending:{until.date().isoformat()}',
        )
    elif until <= now and not auto_alive:
        upsert_notification(
            user,
            Notification.KIND_SUBSCRIPTION,
            'Tu plan venció',
            body    =   'Tu web pública está pausada. Elegí un plan para reactivarla.',
            target  =   'plans',
            dedupe_key  =   f'subscription:expired:{until.date().isoformat()}',
        )
    else:
        #Plan al día o renovación automática viva: los avisos de suscripción
        #sin leer ya no aplican — se marcan leídos para no confundir.
        user.notifications.filter(kind = Notification.KIND_SUBSCRIPTION, read_at__isnull = True).update(read_at = now)


#=========================================
# E-COMMERCE — PEDIDOS DE TIENDA (avisos al dueño)
#=========================================
#Los dispara StoreApp.domains.orders.services.notify vía append_event:
#el comprador NO tiene cuenta DAVENT (es Customer, no auth.User) — estos
#avisos son siempre para el DUEÑO de la tienda.
def _store_owner_user(store):
    """auth.User dueño de la tienda: Store.user = UserProfile → .user."""
    return getattr(getattr(store, 'user', None), 'user', None)


def _store_label(store):
    """Nombre público de la tienda para títulos de avisos."""
    customization    =   getattr(store, 'customization', None)
    display          =   (getattr(customization, 'display_name', '') or '').strip()
    return display or getattr(store, 'slug', '') or 'tu tienda'


def _ars(amount):
    """Monto con formato es-AR ($12.000,00) — mismo criterio que checkout."""
    try:
        return f'${amount:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return '$0,00'


def notify_order_created(store, order):
    """
    Pedido nuevo en la web de la tienda: UN aviso 'order' deduplicado
    por pedido — si el evento 'created' se re-procesa, el aviso vuelve
    a no-leído en vez de duplicarse.
    """
    auth_user   =   _store_owner_user(store)
    if auth_user is None:
        return None
    try:
        items_count =   sum(item.qty for item in order.items.all())
    except Exception:                                   # noqa: BLE001 — el aviso no puede romper el pedido
        items_count =   0
    return upsert_notification(
        auth_user,
        Notification.KIND_ORDER,
        f'Nuevo pedido {order.code}',
        body        =   f'{_store_label(store)} · {items_count} {"artículo" if items_count == 1 else "artículos"} · {_ars(order.total)}',
        target      =   'orders',
        dedupe_key  =   f'order:{order.pk}:created',
    )


#Títulos cortos por kind de incidencia (los demás caen al genérico).
_ORDER_ISSUE_TITLES  =   {
    'stock_conflict'    :   'Stock insuficiente en un pedido pago',
    'amount_mismatch'   :   'Monto del pedido a revisar',
}


def notify_order_issue(store, order, event):
    """
    Incidencia que requiere acción manual del dueño (stock_conflict,
    amount_mismatch): aviso 'order' deduplicado POR EVENTO — cada
    incidencia es un aviso distinto (el dedupe_key lleva el pk del
    OrderEvent, así dos conflictos del mismo pedido no se pisan).
    """
    auth_user   =   _store_owner_user(store)
    if auth_user is None:
        return None
    kind        =   getattr(event, 'kind', '') or 'issue'
    note        =   (getattr(event, 'note', '') or '')[:200]
    body        =   f'{order.code} · {_store_label(store)}'
    if note:
        body    +=  f' — {note}'
    return upsert_notification(
        auth_user,
        Notification.KIND_ORDER,
        _ORDER_ISSUE_TITLES.get(kind, f'Incidencia en el pedido {order.code}'),
        body        =   body,
        target      =   'orders',
        dedupe_key  =   f'order:{order.pk}:{kind}:{getattr(event, "pk", 0)}',
    )


#=========================================
# OPINIONES SIN LEER (badge del menú)
#=========================================
def _own_store(user):
    return getattr(getattr(user, 'profile', None), 'store', None)


def unread_reviews_count(user) -> int:
    """
    Opiniones creadas después del último 'visto' del dueño. Sin
    reviews_seen_at (tienda nueva) cuentan todas — son todas nuevas.
    """
    from StoreApp.domains.catalog.models import ProductReview
    from StoreApp.domains.stores.services import profile_has_benefit
    store   =   _own_store(user)
    if store is None or not profile_has_benefit(store.user, 'has_product_comments'):
        return 0
    qs      =   ProductReview.objects.filter(store = store)
    if store.reviews_seen_at is not None:
        qs  =   qs.filter(created_at__gt = store.reviews_seen_at)
    return qs.count()


def mark_reviews_seen(user):
    """El dueño abrió la sección Opiniones: todo lo anterior queda visto."""
    store   =   _own_store(user)
    if store is not None:
        store.reviews_seen_at   =   timezone.now()
        store.save(update_fields = ['reviews_seen_at'])
    return unread_reviews_count(user)
