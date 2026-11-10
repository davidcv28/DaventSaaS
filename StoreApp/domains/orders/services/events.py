"""
Bitácora de pedidos: ÚNICO punto de creación de OrderEvent.

Todo cambio de estado (services.payments), el alta del pedido
(services.checkout), los conflictos de stock y los avisos del track C
(webhook MP) pasa por `append_event` — nunca se crea un OrderEvent a
mano. El evento queda append-only (no hay update/delete).

HOOK PARA TRACK F (Ola 2 — emails de estado al comprador, Notification
in-app al dueño, SSE): `notify_order_event` ya despacha —
services.notify encola el mail por Celery (post-commit) y crea la
Notification 'order' del dueño dentro de la misma transacción.
"""
import logging

from StoreApp.domains.orders.models import OrderEvent

logger  =   logging.getLogger(__name__)

#Kinds conocidos (libres en DB — el front agrupa por kind; los servicios
#usan estos): created, paid, packing, shipped, delivered, expired,
#cancelled, refunded, note, stock_conflict, amount_mismatch.


def append_event(order, kind, *, actor = 'system', note = '', status_from = '', status_to = '', message = None, **_ignored):
    """
    Crea un OrderEvent y dispara el hook de notificaciones.

    `message` es alias de `note` — el puente de storepayments
    (services.orders_bridge.append_event) llama con `message=`; se
    acepta para no romper ese contrato. `**_ignored` traga kwargs
    extra de callers futuros sin romper la firma.
    """
    if not note and message:
        note    =   str(message)
    event   =   OrderEvent.objects.create(
        order       =   order,
        kind        =   str(kind)[:40],
        actor       =   actor if actor in OrderEvent.Actor.values else OrderEvent.Actor.SYSTEM,
        note        =   str(note or '')[:300],
        status_from =   str(status_from or '')[:20],
        status_to   =   str(status_to or '')[:20],
    )
    notify_order_event(order, event)
    return event


def notify_order_event(order, event):
    """
    Hook de notificaciones (TRACK F — Ola 2). Hoy es no-op: los emails
    de cambio de estado al comprador y la Notification in-app al dueño
    se enchufan acá (o F envuelve append_event). Best-effort por
    contrato: una falla de notificación NUNCA debe romper el flujo del
    pedido — cualquier excepción se loguea y se sigue.
    """
    try:
        _dispatch_order_event(order, event)
    except Exception:                                   # noqa: BLE001 — best-effort
        logger.warning('notify_order_event falló (order=%s kind=%s)', getattr(order, 'pk', None), getattr(event, 'kind', None), exc_info = True)


def _dispatch_order_event(order, event):
    """
    Track F: delega en services.notify.dispatch_order_event —
    Notification in-app 'order' al dueño (sync) + mail por Celery
    encolado post-commit. Import perezoso para no acoplar el orden de
    imports del paquete services (checkout/payments ya importan events).
    """
    from StoreApp.domains.orders.services import notify
    notify.dispatch_order_event(order, event)
