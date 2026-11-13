"""
Ciclo de vida del pedido: máquina de estados + confirmación de pago +
descuento de stock. CONTRATO con track C (storepayments):

- `mark_order_paid(order, *, source='manual'|'mp', reference='', actor=None) -> Order`
- `mark_order_refunded(order, *, actor=None) -> Order`

Ambos son IDOR-agnósticos (reciben la instancia) y concurrentes:
todo corre dentro de `transaction.atomic()` con `select_for_update()`
sobre la fila del pedido (y, en mark_order_paid, sobre las filas de
Product ordenadas por pk) — webhook MP duplicado, doble click del
dueño o dos workers de Celery se serializan y el segundo ve el estado
ya avanzado (no-op, no re-cobra ni duplica eventos).

`advance_order`/`cancel_order` son para el panel del dueño: validan la
tabla TRANSITIONS del modelo y registran el evento. Regla de roles:
`advance_order` solo admite los estados "hacia adelante" del flujo
logístico/reembolso — PAID se confirma por mark_order_paid (setea
paid_at + descuenta stock), CANCELLED por cancel_order y EXPIRED por
el cron expire_orders; ninguno de esos tres es alcanzable por advance.
"""
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers

from StoreApp.domains.catalog.models import Product
from StoreApp.domains.orders.models import Order
from StoreApp.domains.orders.services.events import append_event

logger  =   logging.getLogger(__name__)
#=========================================
# CONSTANTS
#=========================================
#kind del OrderEvent por estado destino (la bitácora usa el nombre del
#paso, no el del enum — 'packing' se lee mejor que 'PACKING' en el feed).
KIND_FOR_STATUS           =   {
    Order.Status.PAID        :   'paid',
    Order.Status.PACKING     :   'packing',
    Order.Status.SHIPPED     :   'shipped',
    Order.Status.DELIVERED   :   'delivered',
    Order.Status.EXPIRED     :   'expired',
    Order.Status.CANCELLED   :   'cancelled',
    Order.Status.REFUNDED    :   'refunded',
}
#Estados que el dueño puede pedir por advance_order (los pasos
#logísticos + reembolso manual). Los demás tienen su propia puerta:
#PAID→mark_order_paid, CANCELLED→cancel_order, EXPIRED→expire_orders.
OWNER_ADVANCE_TARGETS     =   {
    Order.Status.PACKING,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
    Order.Status.REFUNDED,
}
#=========================================
# HELPERS
#=========================================
def _lock(order):
    """Re-lee el pedido BLOQUEADO dentro del atomic del caller."""
    return (Order.objects
        .select_for_update()
        .select_related('store', 'customer')
        .get(pk = order.pk))

def _apply_status(locked, target, *, actor, kind = None, note = ''):
    """Transición ya validada: persiste status + evento append-only."""
    previous    =   locked.status
    locked.status   =   target
    locked.save(update_fields = ['status', 'updated_at'])
    append_event(
        locked,
        kind or KIND_FOR_STATUS.get(target, 'note'),
        actor       =   actor,
        note        =   note,
        status_from =   previous,
        status_to   =   target,
    )
    return locked

def _transition_error(locked, action = 'cambiar el estado de'):
    allowed =   sorted(Order.TRANSITIONS.get(locked.status, set()))
    return serializers.ValidationError({
        'status': f'No se puede {action} un pedido en estado "{locked.status}".'
                  + (f' Transiciones válidas: {", ".join(allowed)}.' if allowed else ' El pedido ya está cerrado.'),
    })

def _decrement_stock(order):
    """
    Descuenta stock SOLO de productos con control (stock NULL =
    ilimitado) al confirmar el pago — nunca al crear el pedido ni en el
    carrito. UPDATE condicional atómico (`stock >= qty` en el WHERE):
    Postgres toma el row lock del UPDATE y re-evalúa la condición sobre
    la versión más reciente — dos pagos concurrentes por la última
    unidad se serializan y el segundo no decrementa de más.

    Si no alcanza stock (otro pedido ganó la unidad entre la creación
    y el pago): el pago NO se revierte — el cliente ya pagó — se deja
    constancia con OrderEvent 'stock_conflict' para que el dueño
    resuelva (reponer, proponer alternativa o reembolsar).

    Antes de los UPDATE se bloquean las filas de Product con
    select_for_update ordenado por pk: dos mark_order_paid concurrentes
    (o un checkout validando disponibilidad — misma llave de lock)
    serializan acá en vez de competir/deadlockear en los UPDATE.
    """
    items   =   list(order.items.select_related('product').all())
    pks     =   sorted({item.product_id for item in items if item.product_id is not None})
    products    =   {}
    if pks:
        products    =   {
            product.pk: product
            for product in Product.objects.select_for_update().filter(pk__in = pks).order_by('pk')
        }
    for item in items:
        product =   products.get(item.product_id)
        if product is None or product.stock is None:
            continue
        updated =   Product.objects.filter(
            pk          =   product.pk,
            stock__gte  =   item.qty,
        ).update(stock = F('stock') - item.qty)
        if updated == 0:
            logger.warning('stock_conflict: order=%s product=%s qty=%s', order.pk, product.pk, item.qty)
            append_event(
                order,
                'stock_conflict',
                actor   =   'system',
                note    =   f'Stock insuficiente al confirmar el pago: "{item.name}" (pedido {item.qty}, disponible menos).',
            )
#=========================================
# PUBLIC CONTRACT (track C + panel del dueño)
#=========================================
def mark_order_paid(order, *, source = 'manual', reference = '', actor = None):
    """
    Confirma el pago del pedido: PENDING_PAYMENT → PAID (paid_at +
    payment_ref si viene) → auto-avanza a PACKING y descuenta stock.

    IDEMPOTENTE: si el pedido ya no está PENDING_PAYMENT devuelve la
    instancia sin efecto — un webhook duplicado, un doble click del
    dueño o dos workers concurrentes no re-cobran ni duplican eventos
    (el select_for_update serializa la lectura del estado).

    `source`: 'manual' (dueño confirma transferencia/efectivo) | 'mp'
    (webhook de Mercado Pago — track C). `actor`: quién lo originó
    ('owner', 'mp', 'system'); si falta se deriva del source.
    """
    actor   =   actor or ('mp' if source == 'mp' else 'owner')
    reference   =   str(reference or '')[:120]
    with transaction.atomic():
        locked  =   _lock(order)
        if locked.status != Order.Status.PENDING_PAYMENT:
            #Ya pago / venció / canceló / reembolsó: no-op idempotente.
            return locked
        locked.paid_at          =   timezone.now()
        if reference:
            locked.payment_ref  =   reference
        if source == 'mp' and reference:
            #El webhook de MP deja el payment_id en su campo propio —
            #antes solo quedaba en payment_ref/MpPayment y la columna
            #mp_payment_id del modelo nunca se escribía.
            locked.mp_payment_id    =   reference[:64]
        locked.status           =   Order.Status.PAID
        locked.save(update_fields = ['status', 'paid_at', 'payment_ref', 'mp_payment_id', 'updated_at'])
        append_event(
            locked, 'paid',
            actor       =   actor,
            note        =   reference,
            status_from =   Order.Status.PENDING_PAYMENT,
            status_to   =   Order.Status.PAID,
        )
        #Auto-avance a PACKING (spec: el pago confirmado pasa directo a
        #preparación — el dueño no necesita un paso extra).
        _apply_status(locked, Order.Status.PACKING, actor = actor)
        _decrement_stock(locked)
        return locked

def mark_order_refunded(order, *, actor = None):
    """
    Pasa el pedido a REFUNDED si la máquina de estados lo permite
    (PAID/PACKING/SHIPPED). NO re-suma stock: la mercadería devuelta la
    decide el dueño a mano (puede estar rota, reingresada por otro
    camino o nunca haber salido) — documentado en OrderEvent.
    Lanza ValidationError si el estado actual no admite reembolso.
    """
    #actor llega como rol ('owner'/'system'/'mp') o como instancia User
    #desde la vista de reembolso de storepayments — el OrderEvent guarda
    #el ROL (choices), no el objeto: sin esta normalización append_event
    #lo degradaba a 'system' y se perdía quién reembolsó.
    if not actor:
        actor   =   'system'
    elif not isinstance(actor, str):
        actor   =   'owner'
    with transaction.atomic():
        locked  =   _lock(order)
        if Order.Status.REFUNDED not in Order.TRANSITIONS.get(locked.status, set()):
            raise _transition_error(locked, 'reembolsar')
        _apply_status(locked, Order.Status.REFUNDED, actor = actor)
        return locked

def advance_order(order, target_status, *, actor = 'owner', carrier = '', carrier_label = '', tracking_code = ''):
    """
    Avanza el pedido del dueño a un estado de OWNER_ADVANCE_TARGETS
    (PACKING/SHIPPED/DELIVERED/REFUNDED) validando TRANSITIONS.
    `target_status` fuera de la whitelist → ValidationError (PAID va por
    confirm-payment, CANCELLED por cancel, EXPIRED por el cron).
    """
    target  =   str(target_status or '').strip().upper()
    if target not in OWNER_ADVANCE_TARGETS:
        raise serializers.ValidationError({'status': f'Estado destino inválido: "{target_status}".'})
    with transaction.atomic():
        locked  =   _lock(order)
        if (target == Order.Status.REFUNDED
                and getattr(locked, 'payment_method', '') == Order.PaymentMethod.MP):
            #Un pedido MP marcado REFUNDED por acá NO devuelve la plata
            #(MP no se entera) y queda terminal: el reembolso real por la
            #endpoint de Cobros quedaría bloqueado para siempre. Los
            #pedidos MP solo se reembolsan vía store-payments (que llama
            #a la API de MP del vendedor antes de transicionar).
            raise serializers.ValidationError({
                'status': 'Los pedidos pagos con Mercado Pago se reembolsan desde Cobros → Mercado Pago (tiene que volver la plata en MP).',
            })
        if target not in Order.TRANSITIONS.get(locked.status, set()):
            raise _transition_error(locked)
        #Al despachar el pedido el dueño adjunta correo + código (o el de
        #la API del correo): viajan en el pedido y al comprador por track.
        if target == Order.Status.SHIPPED:
            locked.carrier          =   carrier
            locked.carrier_label    =   carrier_label
            locked.tracking_code    =   tracking_code
        _apply_status(locked, target, actor = actor)
        return locked

def cancel_order(order, *, actor = 'owner', reason = ''):
    """
    Cancela el pedido si TRANSITIONS lo permite (hoy solo
    PENDING_PAYMENT → CANCELLED: un pedido pago no se cancela, se
    reembolsa — no hay plata que "des-cancelar"). `reason` queda en la
    nota del evento para la bitácora.
    """
    reason  =   str(reason or '')[:300]
    with transaction.atomic():
        locked  =   _lock(order)
        if Order.Status.CANCELLED not in Order.TRANSITIONS.get(locked.status, set()):
            raise _transition_error(locked, 'cancelar')
        _apply_status(locked, Order.Status.CANCELLED, actor = actor, note = reason)
        return locked
