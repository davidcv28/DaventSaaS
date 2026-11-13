"""
Correos de estado de pedido (e-commerce DAVENT — track F).

Dos audiencias, nunca mezcladas:

- COMPRADOR (`order.customer_email` snapshot; fallback `customer.email`):
  los estados del ciclo de vida (paid → refunded) con link de
  seguimiento `{store_web}/seguimiento?token=<tracking_token>` — el
  token es la credencial pública del pedido (anti-IDOR).
- DUEÑO (`store.user.user.email` — Store.user es UserProfile, .user es
  auth.User): pedido nuevo y las incidencias que piden acción manual
  (amount_mismatch, stock_conflict) con link al panel.

El envío NUNCA ocurre en el request: `services.notify` encola
`tasks.send_order_event_email` por Celery (post-commit) y
`deliver_order_event_email` hace el SMTP acá — tolerante a fallos
(un mail caído se loguea y no rompe nada: el pedido ya está a salvo).

HTML: mismo `_mail_html` brand DAVENT que customers/services/mails.py
(tabla 560px, indigo) — se importa en vez de duplicar la plantilla.
`store_web_url` se importa PEREZOSO desde storepayments: orders no debe
acoplarse a storepayments a nivel módulo (storepayments ya importa
orders vía bridge lazy — un import top-level sería ciclo).
"""
import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from StoreApp.domains.customers.services.mails import FRONTEND_URL, _mail_html
from StoreApp.domains.orders.models import Order

logger  =   logging.getLogger(__name__)
#=========================================
# ROUTING — qué kind avisa a quién
#=========================================
#Estados del ciclo de vida → email al COMPRADOR.
CUSTOMER_EVENT_KINDS    =   frozenset({
    'paid', 'packing', 'shipped', 'delivered', 'expired', 'cancelled', 'refunded',
})
#Alta del pedido + incidencias manuales y de revisión de dinero → email
#al DUEÑO. Los kinds de revisión (duplicate_payment, paid_after_close,
#refund_after_delivery) son plata que entró/salió mal: mismo nivel de
#alerta que amount_mismatch/stock_conflict — nunca pueden quedar mudos.
OWNER_EVENT_KINDS       =   frozenset({
    'created', 'amount_mismatch', 'stock_conflict',
    'duplicate_payment', 'paid_after_close', 'refund_after_delivery',
})
#=========================================
# COPY es-AR
#=========================================
#Estado legible para el comprador (subject/intros). El `status_to` del
#evento manda; el kind es el fallback (eventos 'note' con status_to
#podrían llegar acá solo si el caller los encola — no pasa por routing).
STATUS_LABELS           =   {
    Order.Status.PAID          :   'pagado',
    Order.Status.PACKING       :   'en preparación',
    Order.Status.SHIPPED       :   'enviado',
    Order.Status.DELIVERED     :   'entregado',
    Order.Status.EXPIRED       :   'vencido',
    Order.Status.CANCELLED     :   'cancelado',
    Order.Status.REFUNDED      :   'reembolsado',
}
#Frase del estado para el comprador: "Tu pedido PED-0001 fue enviado".
CUSTOMER_STATUS_PHRASES  =   {
    'paid'          :   ('fue pagado', 'Confirmamos que tu pago fue acreditado y ya estamos preparando tu pedido.'),
    'packing'       :   ('está en preparación', 'Tu pedido ya está en preparación en el comercio.'),
    'shipped'       :   ('fue enviado', 'Tu pedido va en camino — podés seguir el estado desde el link.'),
    'delivered'     :   ('fue entregado', 'Tu pedido fue entregado. ¡Gracias por comprar!'),
    'expired'       :   ('venció', 'El plazo para pagar tu pedido finalizó. Si ya abonaste, escribile al comercio.'),
    'cancelled'     :   ('fue cancelado', 'Tu pedido fue cancelado. Si tenés dudas, escribile al comercio.'),
    'refunded'      :   ('fue reembolsado', 'Tu pedido fue reembolsado por el comercio.'),
}
ISSUE_PHRASES           =   {
    'stock_conflict'        :   'no alcanza el stock para completar el pago',
    'amount_mismatch'       :   'el monto declarado no coincide con el total del pedido',
    'duplicate_payment'     :   'se acreditó un segundo pago sobre un pedido ya pago',
    'paid_after_close'      :   'llegó un pago sobre un pedido ya cerrado',
    'refund_after_delivery' :   'hubo un reembolso/contracargo con el pedido ya entregado',
}
#=========================================
# HELPERS
#=========================================
def _money(amount):
    """Monto con formato es-AR ($12.000,00) — mismo criterio que checkout."""
    try:
        return f'${amount:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return '$0,00'


def _store_name(store):
    customization    =   getattr(store, 'customization', None)
    display          =   (getattr(customization, 'display_name', '') or '').strip()
    return display or getattr(store, 'slug', '') or 'la tienda'


def _tracking_url(store, order):
    """Link público de seguimiento — el token ES la credencial (anti-IDOR)."""
    #Import perezoso: orders→storepayments solo a nivel función (ver
    #docstring del módulo — storepayments ya importa orders vía bridge).
    from StoreApp.domains.storepayments.services.preferences import store_web_url
    return f'{store_web_url(store)}/seguimiento?token={order.tracking_token}'


def _panel_url():
    """Panel del dueño (sección Pedidos del dashboard — track J la monta)."""
    return f'{FRONTEND_URL.rstrip("/")}/dashboard?s=orders'


def _owner_email(store):
    """Email del auth.User dueño: Store.user = UserProfile → .user = User."""
    user    =   getattr(getattr(store, 'user', None), 'user', None)
    return (getattr(user, 'email', '') or '').strip()


def _customer_email(order):
    """Snapshot del pedido primero; si está vacío, el email actual."""
    email   =   (order.customer_email or '').strip()
    if email:
        return email
    return (getattr(getattr(order, 'customer', None), 'email', '') or '').strip()


def _items_count(order):
    try:
        return sum(item.qty for item in order.items.all())
    except Exception:                                   # noqa: BLE001 — nunca rompe el mail
        return 0


def _send(to_email, *, subject, body, html, log_context):
    """Envío tolerante: un fallo de SMTP se loguea y no rompe el flujo."""
    try:
        mail    =   EmailMultiAlternatives(
            subject     =   subject,
            body        =   body,
            from_email  =   settings.DEFAULT_FROM_EMAIL,
            to          =   [to_email],
        )
        mail.attach_alternative(html, 'text/html')
        mail.send(fail_silently = False)
    except Exception:
        logger.exception('No se pudo enviar el correo "%s" (%s)', subject, log_context)


#=========================================
# PLANTILLAS
#=========================================
def _customer_status_mail(order, event):
    """(to, subject, body, html) del aviso de estado para el comprador."""
    store       =   order.store
    store_name  =   _store_name(store)
    kind        =   event.status_to if event.status_to in STATUS_LABELS else event.kind
    phrase      =   CUSTOMER_STATUS_PHRASES.get(event.kind) or (
        f'está {STATUS_LABELS.get(kind, "actualizado")}',
        f'Tu pedido {order.code} cambió de estado.',
    )
    verb, intro =   phrase
    status_label    =   STATUS_LABELS.get(kind, event.kind)
    link            =   _tracking_url(store, order)
    name            =   (order.customer_first_name or '').strip() or 'hola'
    total           =   _money(order.total)
    to              =   _customer_email(order)
    subject         =   f'Tu pedido {order.code} {verb} — {store_name}'
    body            =   (
        f'Hola {name},\n\n'
        f'{intro} Estado actual: {status_label}.\n\n'
        f'Seguimiento: {link}\n\n'
        f'Pedido {order.code} · {store_name} · Total {total}\n\n'
        f'— DAVENT'
    )
    html            =   _mail_html(
        title           =   f'Tu pedido {order.code} {verb}',
        intro           =   f'Hola {escape(name)}, {intro} Estado actual: <strong>{escape(status_label)}</strong>.',
        button_label    =   'Ver seguimiento',
        link            =   link,
        note            =   f'Pedido {order.code} · {escape(store_name)} · Total {escape(total)}. Si no reconocés este correo, ignoralo.',
    )
    return to, subject, body, html


def _owner_new_order_mail(order):
    """(to, subject, body, html) del aviso de pedido nuevo para el dueño."""
    store       =   order.store
    store_name  =   _store_name(store)
    buyer       =   f'{order.customer_first_name} {order.customer_last_name}'.strip() or order.customer_email
    link        =   _panel_url()
    method      =   dict(Order.PaymentMethod.choices).get(order.payment_method, order.payment_method)
    to          =   _owner_email(store)
    subject     =   f'Nuevo pedido {order.code} — {store_name}'
    body        =   (
        f'Tenés un pedido nuevo en {store_name}.\n\n'
        f'Pedido: {order.code}\n'
        f'Comprador: {buyer} ({order.customer_email})\n'
        f'Items: {_items_count(order)} · Total: {_money(order.total)}\n'
        f'Pago: {method}\n\n'
        f'Revisalo en tu panel: {link}\n\n'
        f'— DAVENT'
    )
    html        =   _mail_html(
        title           =   f'Nuevo pedido {order.code}',
        intro           =   f'{escape(store_name)} recibió un pedido de <strong>{escape(buyer)}</strong> por <strong>{escape(_money(order.total))}</strong>.',
        button_label    =   'Ver pedidos',
        link            =   link,
        note            =   f'Pedido {order.code} · {escape(str(_items_count(order)))} {"artículo" if _items_count(order) == 1 else "artículos"} · pago por {escape(str(method))}.',
    )
    return to, subject, body, html


def _owner_issue_mail(order, event):
    """(to, subject, body, html) de una incidencia que requiere acción."""
    store       =   order.store
    store_name  =   _store_name(store)
    issue       =   ISSUE_PHRASES.get(event.kind, 'hay una incidencia para revisar')
    note        =   (event.note or '').strip()
    link        =   _panel_url()
    to          =   _owner_email(store)
    subject     =   f'Pedido {order.code} necesita revisión — {store_name}'
    body        =   (
        f'El pedido {order.code} de {store_name} {issue}.\n\n'
        + (f'Detalle: {note}\n\n' if note else '\n')
        + f'Revisalo en tu panel: {link}\n\n'
        f'— DAVENT'
    )
    html        =   _mail_html(
        title           =   f'Pedido {order.code} necesita revisión',
        intro           =   f'{escape(store_name)}: el pedido <strong>{order.code}</strong> {escape(issue)}.',
        button_label    =   'Revisar pedido',
        link            =   link,
        note            =   escape(note) if note else 'Entrá al panel para resolverlo.',
    )
    return to, subject, body, html


#=========================================
# ENTREGA (la llama la task Celery — nunca el request)
#=========================================
def deliver_order_event_email(order_id, event_id):
    """
    Punto de entrada de la task: re-lee pedido+evento frescos y manda
    el mail que corresponda al kind. Best-effort total: si el pedido o
    el evento ya no existen (rollback, borrado) o el mail falla, solo
    se loguea — jamás propaga excepción al flujo del pedido.
    """
    try:
        order   =   (
            Order.objects
            .filter(pk = order_id)
            .select_related('store__user__user', 'store__customization', 'store__domain', 'customer')
            .prefetch_related('items', 'events', 'proof')
            .first()
        )
        if order is None:
            logger.warning('deliver_order_event_email: pedido %s no existe', order_id)
            return
        event   =   order.events.filter(pk = event_id).first()
        if event is None:
            logger.warning('deliver_order_event_email: evento %s no existe (order=%s)', event_id, order_id)
            return
        kind    =   event.kind
        if kind in CUSTOMER_EVENT_KINDS:
            #El alta de comprador no prueba la titularidad del email:
            #mandar lifecycle mail a una dirección sin verificar convierte
            #cancelaciones/disparos del dueño en spam/phishing con marca
            #DAVENT a terceros arbitrarios. Solo se escribe a correos
            #verificados (la verificación queda como puerta del flujo).
            customer    =   getattr(order, 'customer', None)
            if customer is not None and not customer.email_verified:
                logger.info('deliver_order_event_email: email no verificado, mail omitido (order=%s kind=%s)', order.pk, kind)
                return
            to, subject, body, html =   _customer_status_mail(order, event)
            _send(to, subject = subject, body = body, html = html,
                  log_context = f'order={order.pk} kind={kind}')
        elif kind in OWNER_EVENT_KINDS:
            to, subject, body, html =   (_owner_new_order_mail(order) if kind == 'created'
                                         else _owner_issue_mail(order, event))
            if not to:
                logger.warning('deliver_order_event_email: dueño sin email (order=%s)', order.pk)
                return
            _send(to, subject = subject, body = body, html = html,
                  log_context = f'order={order.pk} kind={kind}')
        else:
            #KIND sin mail (note, etc.): no-op silencioso — el routing es
            #explícito para que un kind nuevo jamás mande correo por
            #accidente.
            logger.debug('deliver_order_event_email: kind sin mail: %s (order=%s)', kind, order.pk)
    except Exception:
        logger.exception('deliver_order_event_email falló (order=%s event=%s)', order_id, event_id)
