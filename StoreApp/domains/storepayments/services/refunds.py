"""
Reembolso de un pedido pago con Mercado Pago (lo invoca el DUEÑO desde
su panel — el endpoint HTTP vive en views/mp.py como
POST /api/store-payments/mp/refund/<order_id>/ para no pisar las rutas
del dominio orders, que es del track B).

Llama POST /v1/payments/<id>/refunds con el token DEL VENDEDOR (reembolso
total — MP devuelve 201 con el objeto refund) y recién después marca el
pedido como REFUNDED vía el contrato de orders (`mark_order_refunded`).
Si MP rechaza, el pedido NO cambia de estado.
"""
import logging

from django.db import transaction
from rest_framework import serializers

from StoreApp.domains.storepayments.models import MpPayment
from StoreApp.domains.storepayments.services import mp_client, orders_bridge

logger  =   logging.getLogger(__name__)


class RefundError(Exception):
    """Error de negocio del reembolso (el view lo traduce a 400/502)."""


def _mp_payment_id_for(order):
    """
    payment_id de MP del pedido: primero el MpPayment aprobado registrado
    por el webhook; si no hay fila, `order.mp_payment_id` — campo que
    SOLO escribe mark_order_paid con source='mp' (el webhook, con el id
    que MP devolvió para ESTE pedido).

    NUNCA `order.payment_ref`: ese campo lo completa el dueño al
    confirmar pagos MANUALES (texto libre — alias, número de operación).
    Usarlo como id de pago MP permitiría disparar un refund contra el
    cobro de OTRO pedido copiando su referencia.
    """
    order_pk    =   getattr(order, 'pk', None) or getattr(order, 'id', None)
    record      =   (
        MpPayment.objects
        .filter(order_id = order_pk, status = MpPayment.Status.APPROVED)
        .exclude(mp_payment_id = '')
        .exclude(mp_payment_id__isnull = True)
        .order_by('-created_at')
        .first()
    )
    if record is not None and record.mp_payment_id:
        return record.mp_payment_id, record
    ref         =   str(getattr(order, 'mp_payment_id', '') or '')
    return (ref or None), None


def refund_payment(order, *, actor = None):
    """
    Reembolsa en MP el cobro aprobado del pedido y marca REFUNDED.
    `order` ya viene validado como del store del actor (IDOR resuelto en
    la vista). Devuelve el MpPayment actualizado (o None si el id salió
    del campo del pedido sin registro local).
    Lanza RefundError / serializers.ValidationError / MpApiError.
    """
    store   =   getattr(order, 'store', None)
    account =   getattr(store, 'mp_account', None) if store is not None else None
    access_token    =   account.get_access_token() if account else ''
    if not access_token:
        raise serializers.ValidationError({'detail': 'La tienda no tiene Mercado Pago conectado'})
    if str(getattr(order, 'payment_method', '') or '') != 'mp':
        raise serializers.ValidationError({'detail': 'El pedido no fue pagado con Mercado Pago'})
    #La máquina de estados permite REFUNDED desde PAID/PACKING/SHIPPED —
    #mark_order_paid auto-avanza a PACKING en la misma transacción, así que
    #exigir PAID exacto volvía el reembolso inalcanzable en la práctica.
    #El check de estado va BAJO select_for_update y ANTES de la llamada
    #externa a MP: dos refunds concurrentes se serializan en el lock — el
    #segundo ve REFUNDED y nunca llega a mover plata dos veces.
    Order   =   orders_bridge.order_model()
    order_pk    =   getattr(order, 'pk', None) or getattr(order, 'id', None)
    with transaction.atomic():
        #Orden de locks MpPayment -> Order, IGUAL que el webhook
        #(services/webhook.py bloquea el MpPayment y después el pedido
        #vía mark_paid/mark_refunded). Si acá se bloqueara el pedido
        #primero y el MpPayment al final (record.save), un webhook
        #'refunded' concurrente del mismo pago quedaría en deadlock
        #clásico: webhook tiene MpPayment y pide Order, refund tiene
        #Order y pide MpPayment. Bloqueando TODOS los MpPayment del
        #pedido (pk-ordenados, son pocos) antes del Order se serializa
        #contra cualquier webhook de sus pagos. order_pk None (doble de
        #test sin fila) no matchea nada: order_id es NULL-able y un
        #filtro IS NULL bloquearía filas ajenas.
        if order_pk is not None:
            list(
                MpPayment.objects
                .select_for_update()
                .filter(order_id = order_pk)
                .order_by('pk')
            )
        #La vista garantiza que el pedido existe y es de la tienda
        #(get_order_for_store); el `or order` solo cubre dobles de test
        #sin fila persistida — en producción locked es siempre la fila
        #real bloqueada.
        locked  =   (
            Order.objects
            .select_for_update()
            .filter(pk = order.pk, store_id = getattr(order, 'store_id', None))
            .first()
            or   order
        )
        if str(getattr(locked, 'status', '') or '') not in {'PAID', 'PACKING', 'SHIPPED'}:
            raise serializers.ValidationError({'detail': 'Solo se pueden reembolsar pedidos pagados no entregados'})
        payment_id, record  =   _mp_payment_id_for(locked)
        if not payment_id:
            raise serializers.ValidationError({'detail': 'No se encontró el pago de Mercado Pago del pedido'})
        #Reembolso total (body vacío). MP responde 201 con el objeto refund.
        try:
            mp_client.refund_mp_payment(payment_id, access_token)
        except mp_client.MpApiError as exc:
            logger.warning('Reembolso MP rechazado: order=%s payment=%s status=%s', getattr(order, 'pk', None), payment_id, exc.status_code)
            raise RefundError('Mercado Pago rechazó el reembolso') from exc
        #MP aceptó: recién ahora el pedido pasa a REFUNDED (mark_order_refunded
        #es idempotente según el contrato de orders).
        orders_bridge.mark_refunded(locked, actor = actor)
        if record is not None:
            record.status          =   MpPayment.Status.REFUNDED
            record.mp_status_detail=   'refund'
            record.save(update_fields = ['status', 'mp_status_detail', 'updated_at'])
    logger.info('Reembolso MP procesado: order=%s payment=%s actor=%s', getattr(order, 'pk', None), payment_id, getattr(actor, 'pk', None))
    return record
