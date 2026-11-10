"""
Procesamiento del webhook de Mercado Pago del vendedor
(`POST /api/webhooks/store-mp/<slug>/`).

Flujo (mismo patrón que AdminApp/domains/payments, pero con el token y el
webhook secret DEL VENDEDOR — la firma x-signature se valida en la vista,
acá llega el payment_id ya autenticado):

1. GET /v1/payments/<id> con el access token del vendedor de ESE slug
   (mp_client) — MP es la fuente de verdad, nunca el body.
2. `_reject_test_payment`: live_mode=False en producción -> rechazo
   (copia de la regla de suscripciones: con credenciales TEST cualquiera
   puede fabricar un payment aprobado falso).
3. `external_reference` (`ord:<tracking_token>`) -> pedido ACOTADO a la
   tienda del slug (IDOR: un pedido de otra tienda jamás matchea).
4. Moneda ARS obligatoria; monto vs order.total -> si difieren NO se
   marca paid: se crea OrderEvent 'amount_mismatch' (una sola vez por
   cobro, flag `amount_mismatch` en MpPayment) para revisión manual.
5. Status:
   - approved -> mark_order_paid(order, source='mp', reference=<id>)
     (solo si el pedido sigue PENDING_PAYMENT y el cobro no está ya
     acreditado — idempotencia por estado del pedido + MpPayment).
   - refunded/charged_back -> mark_order_refunded si el pedido estaba PAID.
   - rejected/cancelled/otros -> solo se registra el estado en MpPayment.
6. Idempotencia: `mp_payment_id` UNIQUE + re-fetch del payment antes de
   actuar + transacción con select_for_update sobre MpPayment. Un webhook
   duplicado no produce un segundo efecto.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from rest_framework import serializers

from StoreApp.domains.storepayments.models import MpPayment
from StoreApp.domains.storepayments.services import mp_client, orders_bridge

logger  =   logging.getLogger(__name__)

EXTERNAL_REF_PREFIX     =   'ord:'
MP_STATUS_REFUNDED      =   ('refunded', 'charged_back')


#=========================================
# REGLAS MP (copiadas del patrón de suscripciones)
#=========================================
def _reject_test_payment(mp_payment):
    #Un cobro con credenciales TEST de MP devuelve live_mode=False: en
    #producción jamás debe acreditar un pedido (mismo criterio que
    #AdminApp/domains/payments/services._reject_test_payment).
    from django.conf import settings
    if not settings.DEBUG and mp_payment.get('live_mode') is False:
        raise serializers.ValidationError({'payment_id': 'Pago de prueba de Mercado Pago rechazado en producción'})


def _tracking_token_from(mp_payment):
    """external_reference -> tracking_token (acepta 'ord:' y token pelado)."""
    ref     =   str(mp_payment.get('external_reference') or '').strip()
    if ref.startswith(EXTERNAL_REF_PREFIX):
        ref =   ref[len(EXTERNAL_REF_PREFIX):]
    return ref


def _amount_or_none(mp_payment):
    try:
        return Decimal(str(mp_payment.get('transaction_amount', '0')))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _map_status(mp_status):
    return {
        'approved'      :   MpPayment.Status.APPROVED,
        'rejected'      :   MpPayment.Status.REJECTED,
        'cancelled'     :   MpPayment.Status.CANCELLED,
        'refunded'      :   MpPayment.Status.REFUNDED,
        'charged_back'  :   MpPayment.Status.REFUNDED,
    }.get(mp_status, MpPayment.Status.PENDING)


#=========================================
# REGISTRO IDEMPOTENTE DEL PAGO VISTO
#=========================================
def _get_or_create_record(store, order, payment_id, mp_payment, amount):
    """
    Localiza o crea el MpPayment del payment_id. Si existe una fila de
    intento (preference_id, mp_payment_id NULL) para el mismo pedido, la
    adopta — MP no devuelve preference_id en el payment, así que el
    intento más reciente sin pago es la mejor correspondencia (documentado;
    la trazabilidad fuerte queda en order_id/tracking_token).
    """
    record  =   MpPayment.objects.filter(mp_payment_id = payment_id).first()
    if record is not None:
        return record
    attempt =   (
        MpPayment.objects
        .filter(order_id = order.pk if hasattr(order, 'pk') else getattr(order, 'id', None), mp_payment_id__isnull = True)
        .exclude(preference_id = '')
        .order_by('-created_at')
        .first()
    )
    try:
        with transaction.atomic():
            if attempt is not None:
                #Se adopta la fila del intento y se la marca vista por MP,
                #pero el status final lo decide el bloque de transición
                #(acá NO se mapea 'approved' todavía: si se guardara
                #approved antes, old_status==APPROVED saltearía mark_paid
                #y el pedido nunca se acreditaría).
                attempt.mp_payment_id   =   payment_id
                attempt.status          =   MpPayment.Status.PENDING
                attempt.amount          =   amount if amount is not None else attempt.amount
                attempt.currency        =   str(mp_payment.get('currency_id') or 'ARS')[:3]
                attempt.live_mode       =   mp_payment.get('live_mode')
                attempt.mp_status_detail=   str(mp_payment.get('status_detail') or '')[:255]
                attempt.save()
                return attempt
            return MpPayment.objects.create(
                store               =   store,
                order_id            =   getattr(order, 'pk', None) or getattr(order, 'id', None),
                tracking_token      =   str(getattr(order, 'tracking_token', '') or '')[:128],
                mp_payment_id       =   payment_id,
                #PENDING a propósito: el estado real de MP se aplica en el
                #bloque atómico posterior junto con los efectos (mark_paid).
                status              =   MpPayment.Status.PENDING,
                amount              =   amount if amount is not None else Decimal('0'),
                currency            =   str(mp_payment.get('currency_id') or 'ARS')[:3],
                live_mode           =   mp_payment.get('live_mode'),
                mp_status_detail    =   str(mp_payment.get('status_detail') or '')[:255],
            )
    except IntegrityError:
        #Carrera entre dos entregas del mismo payment_id: la constraint
        #unique decide y se relee la fila ganadora.
        record  =   MpPayment.objects.filter(mp_payment_id = payment_id).first()
        if record is not None:
            return record
        raise


#=========================================
# WEBHOOK QUERY (punto de entrada del service)
#=========================================
def StoreMpWebhookQuery(store, payment_id):
    """
    Procesa una notificación de pago de MP para la tienda `store`.
    Devuelve el MpPayment registrado o None si el evento no aplica
    (sin cuenta conectada, pedido desconocido/ajeno, errores permanentes).
    """
    account     =   getattr(store, 'mp_account', None)
    access_token    =   account.get_access_token() if account else ''
    if not access_token:
        logger.warning('Webhook MP store=%s: cuenta no conectada, evento ignorado', store.slug)
        return None
    #404 de MP = payment inexistente: evento permanente, no reintentable.
    try:
        mp_payment  =   mp_client.get_mp_payment(payment_id, access_token)
    except mp_client.MpApiError as exc:
        if exc.status_code == 404:
            logger.info('Webhook MP store=%s: payment %s inexistente en MP', store.slug, payment_id)
            return None
        raise
    _reject_test_payment(mp_payment)
    #IDOR: el pedido se resuelve por external_reference ACOTADO al slug —
    #un token de otra tienda o un reference manipulado no matchea nada.
    token       =   _tracking_token_from(mp_payment)
    if not token:
        logger.warning('Webhook MP store=%s: payment %s sin external_reference usable', store.slug, payment_id)
        return None
    try:
        order   =   orders_bridge.find_order_by_token(store, token)
    except orders_bridge.OrdersUnavailableError:
        logger.error('Webhook MP store=%s: dominio orders no disponible', store.slug)
        return None
    if order is None:
        logger.info('Webhook MP store=%s: pedido no encontrado para el token recibido', store.slug)
        return None
    #Doble chequeo de pertenencia (el filtro ya lo garantiza; defensa en
    #profundidad por si el bridge se relaja): order.store_id == store.id.
    if getattr(order, 'store_id', None) != store.id:
        logger.warning('Webhook MP store=%s: pedido ajeno ignorado (payment=%s)', store.slug, payment_id)
        return None
    #MONEDA: los pedidos son ARS; otro currency_id nunca acredita.
    if (mp_payment.get('currency_id') or 'ARS') != 'ARS':
        logger.error('Webhook MP store=%s: payment %s en moneda %s — ignorado', store.slug, payment_id, mp_payment.get('currency_id'))
        return None
    mp_status   =   str(mp_payment.get('status') or '')
    amount      =   _amount_or_none(mp_payment)
    record      =   _get_or_create_record(store, order, str(payment_id), mp_payment, amount)
    try:
        order_total =   Decimal(str(getattr(order, 'total', '0')))
    except (InvalidOperation, TypeError, ValueError):
        order_total =   None
    with transaction.atomic():
        #Bloqueo pesimista + relectura: dos webhooks concurrentes del MISMO
        #pago no duplican efectos (mismo patrón que PaymentWebhookQuery).
        record          =   MpPayment.objects.select_for_update(of = ('self',)).get(pk = record.pk)
        old_status      =   record.status
        order_status    =   str(getattr(order, 'status', '') or '')
        if mp_status == 'approved':
            #MONTO: si difiere del total del pedido NO se acredita — queda
            #flag + evento para revisión manual del dueño. Un monto
            #ausente/inparseable (amount=None) tampoco acredita: sin
            #verificación de monto no hay auto-credit (fail-closed).
            if amount is None or order_total is None or amount != order_total:
                if not record.amount_mismatch:
                    record.amount_mismatch =   True
                    orders_bridge.append_event(
                        order,
                        kind        =   'amount_mismatch',
                        message     =   f'Pago MP {payment_id} por ${amount} distinto al total del pedido (${order_total})',
                    )
                    logger.error('Webhook MP store=%s: monto distinto payment=%s amount=%s total=%s', store.slug, payment_id, amount, order_total)
            elif order_status != 'PAID' and old_status != MpPayment.Status.APPROVED:
                orders_bridge.mark_paid(
                    order,
                    source      =   'mp',
                    reference   =   str(payment_id),
                    actor       =   None,
                )
                order_status    =   'PAID'
        elif mp_status in MP_STATUS_REFUNDED:
            #Reembolso detectado por MP (ej. desde el panel del vendedor):
            #mark_order_paid auto-avanza a PACKING en la misma transacción,
            #así que PAID nunca es el estado persistido — aceptar todos los
            #estados desde los que Order.TRANSITIONS permite llegar a
            #REFUNDED (mismo set que el reembolso del dueño en refunds.py).
            if order_status in {'PAID', 'PACKING', 'SHIPPED'}:
                orders_bridge.mark_refunded(order, actor = None)
                order_status    =   'REFUNDED'
        #Estado final: reflejar el estado mapeado de MP (approved/rejected/
        #cancelled/refunded; estados intermedios de MP -> PENDING).
        record.status          =   _map_status(mp_status)
        record.live_mode       =   mp_payment.get('live_mode')
        record.mp_status_detail=   str(mp_payment.get('status_detail') or '')[:255]
        record.amount          =   amount if amount is not None else record.amount
        record.save(update_fields = ['status', 'live_mode', 'mp_status_detail', 'amount', 'amount_mismatch', 'updated_at'])
    logger.info('Webhook MP store=%s payment=%s status=%s -> %s', store.slug, payment_id, mp_status, record.status)
    return record
