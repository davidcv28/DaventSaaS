"""
Despacho de notificaciones de pedidos (e-commerce DAVENT — track F).

`append_event` (services/events.py) llama `notify_order_event` en cada
OrderEvent; `_dispatch_order_event` delega acá. Dos canales
best-effort e independientes:

1. NOTIFICATION in-app al DUEÑO (AdminApp notifications, kind='order'):
   síncrona — viaja en la misma transacción del evento (si el pedido
   hace rollback, el aviso también).
2. EMAIL por Celery: `transaction.on_commit` + `.delay()` — un rollback
   no manda correos y el SMTP jamás corre dentro del request.
3. CustomerNotification al COMPRADOR registrado (dominio customers,
   kind='order' — campana + /cuenta de la web de tienda): también
   síncrona. Solo cuando el pedido tiene Customer vinculado — el
   comprador invitado no tiene campana y queda cubierto por el mail.

El mapa kind→audiencia vive en services/mails.py
(CUSTOMER_EVENT_KINDS / OWNER_EVENT_KINDS): un kind no listado (note,
created ya cubierto, futuros) no dispara nada — routing explícito.
"""
import logging

from django.db import transaction

from StoreApp.domains.orders.services.mails import (
    CUSTOMER_EVENT_KINDS,
    OWNER_EVENT_KINDS,
)

logger  =   logging.getLogger(__name__)
#Kinds que además de mail generan Notification in-app al dueño. Los de
#revisión de dinero van incluidos: plata mal acreditada/devuelta es la
#alerta más urgente del panel.
OWNER_NOTIFY_KINDS   =   frozenset({
    'created', 'amount_mismatch', 'stock_conflict',
    'duplicate_payment', 'paid_after_close', 'refund_after_delivery',
})


def dispatch_order_event(order, event):
    """
    Punto único de salida del hook: notificación in-app + encolado del
    mail. Cada canal va en su propio try/except — una falla de uno no
    puede impedir el otro ni romper append_event (que además envuelve
    todo en best-effort).
    """
    kind    =   getattr(event, 'kind', '') or ''
    #1) Notification in-app al dueño (sync, misma tx que el evento).
    if kind in OWNER_NOTIFY_KINDS:
        try:
            _notify_owner(order, event)
        except Exception:                                   # noqa: BLE001 — best-effort
            logger.warning('notify_order_event: notification falló (order=%s kind=%s)', getattr(order, 'pk', None), kind, exc_info = True)
    #2) Email por Celery post-commit (nunca SMTP en el request).
    if kind in CUSTOMER_EVENT_KINDS or kind in OWNER_EVENT_KINDS:
        try:
            #Captura order/event por pk: el worker re-lee fresco — la
            #instancia del request puede quedar stale para el correo.
            transaction.on_commit(lambda: _enqueue_order_email(order.pk, event.pk))
        except Exception:                                   # noqa: BLE001 — best-effort
            logger.warning('notify_order_event: encolado de mail falló (order=%s kind=%s)', getattr(order, 'pk', None), kind, exc_info = True)
    #3) Notification in-app al COMPRADOR registrado (campana + /cuenta):
    #   mismo canal sync que el aviso al dueño — el comprador invitado
    #   (order.customer None) solo recibe el mail del canal 2.
    if kind in CUSTOMER_EVENT_KINDS and getattr(order, 'customer_id', None):
        try:
            _notify_customer(order, event)
        except Exception:                                   # noqa: BLE001 — best-effort
            logger.warning('notify_order_event: notification del comprador falló (order=%s kind=%s)', getattr(order, 'pk', None), kind, exc_info = True)


def _notify_customer(order, event):
    """CustomerNotification 'order' (seguimiento) para el comprador."""
    from StoreApp.domains.customers.services.notifications import notify_customer_order
    notify_customer_order(order, event)


def _notify_owner(order, event):
    """Notification 'order' in-app para el dueño de la tienda."""
    from AdminApp.domains.notifications.services.services import (
        notify_order_created,
        notify_order_issue,
    )
    kind    =   getattr(event, 'kind', '') or ''
    store   =   getattr(order, 'store', None)
    if store is None:
        return
    if kind == 'created':
        notify_order_created(store, order)
    else:
        notify_order_issue(store, order, event)


def _enqueue_order_email(order_id, event_id):
    """Encola la task de mail (import perezoso — celery solo si hace falta)."""
    from StoreApp.domains.orders.tasks import send_order_event_email
    send_order_event_email.delay(order_id, event_id)
