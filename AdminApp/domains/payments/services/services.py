import logging
import math
import re
from datetime import timedelta
from decimal import Decimal

import mercadopago
import requests
from decouple import config
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from AdminApp.domains.invoices.services import IssueInvoiceQuery
from AdminApp.domains.payments.models import DailyRevenue, MonthlyRevenue, Payment
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan

logger          =   logging.getLogger(__name__)
sdk             =   mercadopago.SDK(config('SECRET_MP_KEY'))
FRONTEND_URL    =   config('FRONTEND_URL', default = 'http://localhost:5173')
BACKEND_URL     =   config('BACKEND_URL', default = '')
#Con credenciales TEST, MP exige que el payer del preapproval sea un usuario de
#prueba del mismo site: MP_PAYER_EMAIL lo fuerza en dev; en prod queda vacío
#y se usa el email de registro del cliente.
MP_PAYER_EMAIL  =   config('MP_PAYER_EMAIL', default = '')

MP_STATUS_MAP   =   {
    'approved'      :   Payment.Status.APPROVED,
    'rejected'      :   Payment.Status.REJECTED,
    'refunded'      :   Payment.Status.REFUNDED,
    'charged_back'  :   Payment.Status.REFUNDED,
    #'cancelled' (MP) = cobro anulado antes de procesarse: estado terminal,
    #sin él el pago quedaba PENDING para siempre y el barrido lo salteaba.
    'cancelled'     :   Payment.Status.REJECTED,
}
#El preapproval no existe (o ya no existe) en MP: es el ÚNICO error que
#justifica recrear el débito — un 5xx/timeout es transitorio y tratarlo
#como "inválido" pisaba preapproval_id y podía dejar dos débitos vivos.
class MercadoPagoNotFound(Exception):
    pass
#ESTADOS DE SUSCRIPCIÓN (fuente de verdad: constantes del modelo)
SUSCRIPTION_STATUS_ACTIVE           =   Suscription.STATUS_ACTIVE
SUSCRIPTION_STATUS_PENDING_PAYMENT  =   Suscription.STATUS_PENDING_PAYMENT
#=================================
# MERCADO PAGO HELPERS
#=================================
def GetMercadoPagoPayment(payment_id) -> dict:
    mp_result       =   sdk.payment().get(payment_id)
    if mp_result.get('status') != 200:
        raise serializers.ValidationError({'payment_id': 'No se pudo verificar el pago en Mercado Pago'})
    return mp_result['response']

#=================================
# PAYMENT MODEL QUERYS
#=================================
def _reject_test_payment(mp_payment : dict):
    #Un cobro con credenciales TEST de MP devuelve live_mode=False: en
    #producción jamás debe acreditar un plan (con el token TEST cualquiera
    #puede generar un payment aprobado falso). None (MP no lo informó)
    #no bloquea: el campo queda registrado para trazabilidad.
    if not settings.DEBUG and mp_payment.get('live_mode') is False:
        raise serializers.ValidationError({'payment_id': 'Pago de prueba de Mercado Pago rechazado en producción'})


#PAYMENT CREATE QUERY (verificación MP + idempotencia + atomicidad)
def CreatePaymentQuery(validated_data : dict, mp_payment : dict = None) -> Payment:
    data                =   validated_data.copy()
    payment_id          =   data.pop('payment_id')
    suscription         =   data['suscription']
    #IDEMPOTENCIA: el id de pago de Mercado Pago es único
    payment_exists      =   Payment.objects.select_related('suscription__pending_plan_suscription').filter(external_reference = str(payment_id)).first()
    if payment_exists:
        #El pago ya registrado pertenece a otra suscripción: no se devuelve
        #el objeto ajeno (IDOR mínimo) ni se le aplica el plan pendiente.
        if payment_exists.suscription_id != suscription.id:
            raise serializers.ValidationError({'payment_id': 'El pago no corresponde a esta suscripción.'})
        #El pago ya está aprobado: NO se re-aplica el plan pendiente ni se
        #reinicia el período — este camino también lo alcanzan replays del
        #webhook, /sync/ con payment_id y POST /payments/ con un pago ya
        #acreditado, y ninguno implica un cobro nuevo.
        return payment_exists
    if mp_payment is None:
        mp_payment      =   GetMercadoPagoPayment(payment_id)
    _reject_test_payment(mp_payment)
    #OWNERSHIP DEL COBRO: la preferencia se crea con external_reference = id de
    #la suscripción. Sin este chequeo, un payment_id ajeno (el monto solo se
    #compara con el precio del plan) podía registrarse en la suscripción de
    #otro usuario — misma regla que aplica PaymentWebhookQuery.
    if str(mp_payment.get('external_reference') or '') != str(suscription.id):
        raise serializers.ValidationError({'payment_id': 'El pago no corresponde a esta suscripción.'})
    #MONEDA: los precios son ARS; un cobro en otra moneda con el mismo número
    #no debe acreditar el plan.
    if (mp_payment.get('currency_id') or 'ARS') != 'ARS':
        raise serializers.ValidationError({'payment_id': 'La moneda del pago no es ARS.'})
    #VERIFICACIÓN DE MONTO: precio completo del plan (pendiente si existe)
    #o el cargo prorrateado de un upgrade (pending_charge). Un pago a
    #precio completo con upgrade pendiente también es válido: cubre el
    #cambio a período completo y ApplyPendingPlanQuery reinicia las fechas.
    amount              =   Decimal(str(mp_payment.get('transaction_amount', '0')))
    pending_plan        =   suscription.pending_plan_suscription
    plan_price          =   (pending_plan or suscription.plan_suscription).price
    expected_amount     =   suscription.pending_charge if suscription.pending_charge is not None else plan_price
    #Montos legítimos: el esperado (prorrateo o plan pendiente/vigente), el
    #precio del plan vigente (un débito MP realineado tarde sale al monto
    #viejo) y CUALQUIER precio de plan pago — una preferencia o débito
    #emitido antes de un cambio de plan queda con el monto viejo y
    #rechazarlo dejaba un cobro real de MP sin registrar (webhook 500 ->
    #reintentos eternos -> plata cobrada sin Payment ni plan).
    #Decimal(str(...)): una instancia en memoria puede tener precios como
    #float y Decimal('666.67') != 666.67 (float no es exacto en decimal).
    accepted_amounts    =   {
        Decimal(str(plan_price)),
        Decimal(str(suscription.plan_suscription.price)),
        *(Decimal(str(p)) for p in SuscriptionPlan.objects.filter(is_trial = False).values_list('price', flat = True)),
    }
    if suscription.pending_charge is not None:
        #str()->Decimal: una instancia en memoria puede tener el campo como
        #float y Decimal('666.67') != 666.67 (comparación exacto vs float).
        accepted_amounts.add(Decimal(str(suscription.pending_charge)))
    if amount not in accepted_amounts:
        raise serializers.ValidationError({
            'payment_id':   f'El monto del pago (${amount}) no coincide con el importe esperado (${expected_amount})'
        })
    status              =   MP_STATUS_MAP.get(mp_payment.get('status'), Payment.Status.PENDING)
    paid_at             =   parse_datetime(mp_payment['date_approved']) if status == Payment.Status.APPROVED and mp_payment.get('date_approved') else None
    try:
        with transaction.atomic():
            #ATOMICIDAD: el pago se crea completo o no se crea
            new_payment =   Payment.objects.create(
                user                =   data['user'],
                suscription         =   suscription,
                amount              =   amount,
                currency            =   mp_payment.get('currency_id', 'ARS'),
                status              =   status,
                external_reference  =   str(mp_payment.get('id', payment_id)),
                live_mode           =   mp_payment.get('live_mode'),
                mp_status_detail    =   str(mp_payment.get('status_detail') or '')[:255],
                paid_at             =   paid_at
            )
            #PLAN PENDIENTE: se establece la suscripción cuando el pago se acredita
            if status == Payment.Status.APPROVED:
                ApplyPendingPlanQuery(suscription, renew = True, paid_amount = new_payment.amount, payment = new_payment)
                UpdateRevenueRollupsQuery(new_payment)
                #FACTURA: se emite dentro de la misma transacción que el cobro
                IssueInvoiceQuery(new_payment)

            return new_payment
    except IntegrityError:
        #IDEMPOTENCIA (constraint unique): la referencia ya fue registrada
        payment_exists  =   Payment.objects.filter(external_reference = str(payment_id)).first()
        if payment_exists:
            return payment_exists
        raise

#PAYMENT WEBHOOK QUERY (notificaciones IPN de MP: registra o actualiza el pago, acredita el plan)
def PaymentWebhookQuery(payment_id):
    payment             =   Payment.objects.select_related('suscription__pending_plan_suscription').filter(external_reference = str(payment_id)).first()
    mp_payment          =   GetMercadoPagoPayment(payment_id)
    _reject_test_payment(mp_payment)
    if not payment:
        #El webhook puede llegar antes que cualquier redirect/confirmación: se registra igual.
        #external_reference = id de suscripción, seteado al crear la preferencia.
        suscription     =   Suscription.objects.select_related('user', 'plan_suscription', 'pending_plan_suscription').filter(pk = mp_payment.get('external_reference')).first()
        if not suscription:
            return None
        return CreatePaymentQuery(
            {'user' : suscription.user, 'suscription' : suscription, 'payment_id' : payment_id},
            mp_payment = mp_payment
        )
    new_status          =   MP_STATUS_MAP.get(mp_payment.get('status'), payment.status)
    paid_at             =   parse_datetime(mp_payment['date_approved']) if mp_payment.get('date_approved') else None
    paid_at             =   paid_at or payment.paid_at
    with transaction.atomic():
        #Bloqueo pesimista + relectura del estado: dos webhooks concurrentes
        #del MISMO pago leían old_status PENDING los dos y duplicaban rollups
        #y factura. Serializado, el segundo ve APPROVED y no hace efectos.
        #of=('self',): FOR UPDATE no puede aplicarse al lado nulable de un
        #outer join (pending_plan_suscription) — se bloquea solo la tabla base.
        payment             =   Payment.objects.select_for_update(of = ('self',)).select_related('suscription__pending_plan_suscription').get(pk = payment.pk)
        old_status              =   payment.status
        payment.status          =   new_status
        payment.paid_at         =   paid_at
        #Trazabilidad MP: live_mode/status_detail llegan del payload verificado.
        if 'live_mode' in mp_payment:
            payment.live_mode           =   mp_payment.get('live_mode')
        if mp_payment.get('status_detail'):
            payment.mp_status_detail    =   str(mp_payment.get('status_detail'))[:255]
        payment.save(update_fields = ['status', 'paid_at', 'live_mode', 'mp_status_detail', 'updated_at'])
        #PLAN PENDIENTE: solo en la transición real a approved — un replay
        #del webhook sobre un pago ya aprobado no puede re-aplicar el plan
        #ni reiniciar el período (sería un upgrade gratis).
        if new_status == Payment.Status.APPROVED and old_status != Payment.Status.APPROVED:
            ApplyPendingPlanQuery(payment.suscription, renew = True, paid_amount = payment.amount, payment = payment)
        #ROLLUPS: solo se suma cuando el pago entra en approved; se descuenta si sale de approved
        if new_status == Payment.Status.APPROVED and old_status != Payment.Status.APPROVED:
            UpdateRevenueRollupsQuery(payment, sign = 1)
            #FACTURA: se emite dentro de la misma transacción que el cobro
            IssueInvoiceQuery(payment)
        elif old_status == Payment.Status.APPROVED and new_status != Payment.Status.APPROVED:
            UpdateRevenueRollupsQuery(payment, sign = -1)
            #REFUND/CHARGEBACK del pago que abrió el período vigente: la
            #plata ya no está -> el acceso se revoca. Si el refund es de
            #un pago más viejo (período ya superado) o de un prorrateo,
            #period_payment_id no matchea y el acceso queda intacto.
            _revoke_period_if_granted(payment)
    return payment

def _revoke_period_if_granted(payment):
    with transaction.atomic():
        suscription =   Suscription.objects.select_for_update().filter(pk = payment.suscription_id).first()
        if not suscription or suscription.period_payment_id != payment.pk:
            return
        now         =   timezone.now()
        update_fields   =   ['period_payment_id', 'period_end_before']
        #Período ya vencido: el refund no puede revocar un acceso que ya no
        #existe ni pisar el pending_plan del próximo ciclo — solo se limpia
        #el puntero para que un segundo evento no lo reprocese.
        if not (suscription.end_date and suscription.end_date > now):
            suscription.period_payment_id       =   None
            suscription.period_end_before       =   None
            suscription.save(update_fields = update_fields)
            return
        #Restaura los días que OTRO cobro/cupón ya había pago (period_end_before)
        #si el pago devuelto fue un stacked sobre un período vigente. Si no
        #hay previos, el acceso corta AHORA: end_date = now - GRACE_DAYS hace
        #que access_until() (que suma gracia mientras auto_renew) dé exactly
        #now — un refund no puede dejar días de gracia de un cobro devuelto.
        previous    =   suscription.period_end_before
        if previous and previous > now:
            suscription.end_date    =   previous
        else:
            suscription.end_date    =   now - timedelta(days = Suscription.GRACE_DAYS)
        suscription.pending_plan_suscription    =   None
        suscription.pending_charge              =   None
        suscription.period_payment_id           =   None
        suscription.period_end_before           =   None
        suscription.save(update_fields = update_fields + ['end_date', 'pending_plan_suscription', 'pending_charge'])

#REVENUE ROLLUPS QUERY (mantiene DailyRevenue / MonthlyRevenue materializados para dashboards)
def UpdateRevenueRollupsQuery(payment, sign = 1):
    """Suma (sign=1) o descuenta (sign=-1) el pago en los rollups diario y mensual.
    Se llama únicamente cuando un pago entra o sale del estado APPROVED."""
    effective           =   payment.paid_at or payment.created_at or timezone.now()
    day                 =   timezone.localtime(effective).date() if timezone.is_aware(effective) else effective.date()
    amount              =   payment.amount * sign
    #Updates atómicos con F(): el read-modify-write anterior perdía pagos
    #concurrentes del mismo día/mes (típico con webhooks y confirmaciones
    #en paralelo). Greatest evita que un refund deje el contador negativo.
    daily, _            =   DailyRevenue.objects.get_or_create(date = day)
    DailyRevenue.objects.filter(pk = daily.pk).update(
        total_amount    =   F('total_amount') + amount,
        payments_count  =   Greatest(F('payments_count') + sign, 0),
        updated_at      =   timezone.now(),
    )
    monthly, _          =   MonthlyRevenue.objects.get_or_create(year = day.year, month = day.month)
    MonthlyRevenue.objects.filter(pk = monthly.pk).update(
        total_amount    =   F('total_amount') + amount,
        payments_count  =   Greatest(F('payments_count') + sign, 0),
        updated_at      =   timezone.now(),
    )

#APPLY PENDING PLAN QUERY (establece el plan una vez acreditado el pago)
#PRECONDICIÓN: llamar dentro de transaction.atomic — la fila se bloquea con
#select_for_update para serializar extensiones concurrentes del plan.
def _plan_paid_for(suscription, paid_amount):
    """
    Plan que el monto cobrado acredita. `paid_amount` ya fue validado
    contra accepted_amounts en CreatePaymentQuery (pending_charge se
    resuelve aparte como prorrateo): acá solo importan precios de plan.
    Empate de precio entre planes: pending_plan > plan vigente > menor pk
    (determinista). None si ningún plan coincide — no debería pasar tras
    la validación, y el caller cae al comportamiento anterior.
    """
    try:
        amount  =   Decimal(str(paid_amount))
    except Exception:
        return None
    plans   =   list(SuscriptionPlan.objects.filter(is_trial = False))
    seen    =   {p.pk for p in plans}
    #El plan vigente puede ser trial histórico o un plan despublicado:
    #su precio también era aceptado — se incluye si falta en la lista.
    for extra in (suscription.pending_plan_suscription, suscription.plan_suscription):
        if extra is not None and extra.pk not in seen:
            plans.append(extra)
            seen.add(extra.pk)
    matches =   [p for p in plans if Decimal(str(p.price)) == amount]
    if not matches:
        return None
    def _rank(plan):
        if suscription.pending_plan_suscription_id == plan.pk:
            return 0
        if suscription.plan_suscription_id == plan.pk:
            return 1
        return 2
    return min(matches, key = lambda p: (_rank(p), p.pk))

def ApplyPendingPlanQuery(suscription, renew = False, paid_amount = None, payment = None):
    suscription         =   Suscription.objects.select_for_update().get(pk = suscription.pk)
    pending_plan        =   suscription.pending_plan_suscription
    is_pending_payment  =   suscription.status == SUSCRIPTION_STATUS_PENDING_PAYMENT
    if not pending_plan and not is_pending_payment and not renew:
        return suscription
    now                 =   timezone.now()
    update_fields       =   ['status', 'start_date', 'end_date', 'pending_charge']
    #UPGRADE PRORRATEADO (pending_charge): el cobro fue solo la diferencia
    #del plan por los días restantes — el plan cambia pero el período NO se
    #reinicia: la fecha de facturación se mantiene y el próximo débito ya
    #sale al precio nuevo (la preapproval se realineó al pedir el cambio).
    prorated            =   (
        pending_plan is not None
        and suscription.pending_charge is not None
        and paid_amount is not None
        and Decimal(str(paid_amount)) == suscription.pending_charge
    )
    #PLAN ACREDITADO = el plan que el monto pagado compra, nunca un plan
    #más caro que el cobrado: una preferencia/débito MP emitido antes del
    #cambio de plan conserva el monto viejo y, sin este binding, aplicaba
    #pending_plan (el plan caro) por un pago del plan barato. Si el pago
    #fue de OTRO plan, pending_plan queda pendiente hasta que llegue un
    #cobro a su precio (prorrateo o precio completo).
    granted_plan        =   pending_plan
    if not prorated and paid_amount is not None:
        granted_plan    =   _plan_paid_for(suscription, paid_amount) or pending_plan
    if granted_plan is not None:
        suscription.plan_suscription            =   granted_plan
        update_fields                          +=   ['plan_suscription']
        if pending_plan is not None and granted_plan.pk == pending_plan.pk:
            suscription.pending_plan_suscription    =   None
            update_fields                          +=   ['pending_plan_suscription']
    suscription.pending_charge    =   None
    #Todo cobro aprobado a precio completo renueva por 30 días desde el
    #cobro (máx. 30). max() con el end_date vigente: un pago viejo
    #registrado tarde por el barrido o una renovación anticipada nunca
    #recorta días ya pagos. El prorrateado de upgrade no toca las fechas.
    if not prorated:
        suscription.start_date  =   now
        period_end              =   now + timedelta(days = 30)
        previous_end            =   suscription.end_date
        if previous_end and previous_end > period_end:
            period_end          =   previous_end
        suscription.end_date    =   period_end
        #El pago solo pasa a ser dueño del período si REALMENTE lo extendió:
        #un cobro que cae dentro de días ya pagos (renovación anticipada,
        #período largo de cupón) no mueve end_date y su refund no puede
        #revocar lo que otro pago/cupón otorgó — el puntero queda donde
        #estaba. Cuando sí extiende, period_end_before guarda el fin
        #previo para que el revoke restaure esos días.
        if previous_end is None or period_end > previous_end:
            suscription.period_end_before       =   previous_end
            suscription.period_payment_id       =   payment.pk if payment is not None else None
            update_fields                      +=   ['period_payment_id', 'period_end_before']
    suscription.status      =   SUSCRIPTION_STATUS_ACTIVE
    suscription.save(update_fields = update_fields)
    return suscription

#SYNC PAYMENTS QUERY (registra los pagos ya hechos en MP; no depende del redirect del checkout)
def SyncSuscriptionPaymentsQuery(suscription, payment_id = None):
    #El redirect de back_urls puede no ejecutarse; MP es la fuente de verdad.
    #Si llega un payment_id puntual (retorno del checkout), se verifica directo:
    #es la vía instantánea, sin depender del barrido de search.
    if payment_id:
        try:
            mp_payment  =   GetMercadoPagoPayment(payment_id)
            if str(mp_payment.get('external_reference')) != str(suscription.id):
                return []
            return [CreatePaymentQuery({
                'user'          :   suscription.user,
                'suscription'   :   suscription,
                'payment_id'    :   payment_id,
            }, mp_payment = mp_payment)]
        except serializers.ValidationError:
            return []
    now             =   timezone.now()
    #MP rechaza microsegundos y offsets (+00:00): fechas en UTC con formato ISO-8601 con Z.
    base_params     =   {
        'sort'          :   'date_created',
        'criteria'      :   'desc',
        'limit'         :   100,
    }
    date_params     =   {
        'begin_date'    :   (now - timedelta(days = 90)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end_date'      :   now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    #Filtro server-side por la suscripción: MP solo devuelve sus pagos.
    #Si la cuenta no soporta el filtro, se reintenta con el barrido general.
    results         =   []
    for params in ({**base_params, **date_params, 'external_reference': str(suscription.id)}, {**base_params, **date_params}):
        mp_result   =   sdk.payment().search(params)
        if mp_result.get('status') != 200:
            continue
        results     =   (mp_result.get('response') or {}).get('results') or []
        if results:
            break
    registered      =   []
    #MP devuelve desc por fecha: se procesan del más viejo al más nuevo para
    #que el ÚLTIMO pago aprobado del lote sea el dueño final del período —
    #en orden desc el puntero quedaba en el pago más viejo y un refund del
    #cargo real (el más reciente) no revocaba nada.
    for mp_payment in reversed(results):
        payment_id  =   mp_payment.get('id')
        if not payment_id or str(mp_payment.get('external_reference')) != str(suscription.id):
            continue
        if Payment.objects.filter(external_reference = str(payment_id)).exists():
            continue
        try:
            registered.append(CreatePaymentQuery({
                'user'          :   suscription.user,
                'suscription'   :   suscription,
                'payment_id'    :   payment_id,
            }, mp_payment = mp_payment))
        except serializers.ValidationError:
            continue
    return registered

#CHECKOUT PREFERENCE QUERY (crea la preferencia de Checkout Pro para la suscripción)
def CreateCheckoutPreferenceQuery(suscription):
    #Cobra el plan pendiente si existe; el plan vigente solo cambia al acreditarse el pago.
    #Con upgrade pendiente (pending_charge) el checkout cobra solo la
    #diferencia prorrateada — el plan cambia al acreditarse sin mover la
    #fecha de facturación (modelo Netflix).
    plan                =   suscription.pending_plan_suscription or suscription.plan_suscription
    charge              =   suscription.pending_charge if suscription.pending_charge is not None else plan.price
    preference_data     =   {
        'items'             :   [{
            'title'         :   f'DAVENT · {plan.name}',
            'quantity'      :   1,
            'unit_price'    :   float(charge),
            'currency_id'   :   'ARS',
        }],
        'external_reference':   str(suscription.id),
        'back_urls'         :   {
            'success'       :   f'{FRONTEND_URL}/dashboard?pay=success',
            'failure'       :   f'{FRONTEND_URL}/dashboard?pay=failure',
            'pending'       :   f'{FRONTEND_URL}/dashboard?pay=pending',
        },
    }
    #MP exige URL pública https para auto_return; en localhost se usa el botón "Volver".
    if FRONTEND_URL.startswith('https://'):
        preference_data['auto_return']  =   'approved'
    #IPN: MP avisa al backend apenas se acredita el pago (requiere URL pública, ej. ngrok en dev).
    if BACKEND_URL:
        preference_data['notification_url'] =   f'{BACKEND_URL.rstrip("/")}/api/payments/webhook/'
    mp_result           =   sdk.preference().create(preference_data)
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo iniciar el pago en Mercado Pago'})
    return mp_result['response']

#=================================
# MERCADO PAGO PREAPPROVAL (débito automático mensual)
#=================================
#GET PREAPPROVAL (estado real de la suscripción en MP)
def GetPreapproval(preapproval_id) -> dict:
    mp_result       =   sdk.preapproval().get(preapproval_id)
    status_code     =   mp_result.get('status')
    if status_code == 404:
        raise MercadoPagoNotFound(f'Preapproval {preapproval_id} no existe en Mercado Pago')
    if status_code != 200:
        #Errores transitorios (5xx, timeout, rate limit) NO son "preapproval
        #inválido": propagarlos como ValidationError hacía que el action
        #subscription recreara el débito y dejara el viejo huérfano —
        #posible doble débito mensual.
        raise serializers.ValidationError({'preapproval_id': 'No se pudo verificar el débito automático en Mercado Pago'})
    return mp_result['response']

#CREATE PREAPPROVAL QUERY (alta del débito: queda pending hasta que el cliente lo autoriza en MP)
def CreatePreapprovalQuery(suscription) -> dict:
    #Cobra el plan pendiente si existe; el vigente si no
    plan                =   suscription.pending_plan_suscription or suscription.plan_suscription
    #Un débito de $0 (plan trial) no tiene sentido en MP ni reemplaza el alta
    #paga: el plan pago se elige antes de autorizar la tarjeta.
    if plan.price <= 0:
        raise serializers.ValidationError({'plan_suscription': 'Elegí un plan pago para activar el débito automático.'})
    #MP exige back_url pública https (obligatoria en preapprovals; rechaza
    #localhost). En dev se usa una URL neutra y el retorno lo cubre /sync/.
    back_url            =   f'{FRONTEND_URL}/dashboard?sub=return' if FRONTEND_URL.startswith('https://') else 'https://www.mercadopago.com.ar'
    preapproval_data    =   {
        'reason'            :   f'DAVENT · {plan.name}',
        'external_reference':   str(suscription.id),
        'payer_email'       :   MP_PAYER_EMAIL or suscription.user.user.email,
        'back_url'          :   back_url,
        'status'            :   'pending',
        'auto_recurring'    :   {
            'frequency'         :   1,
            'frequency_type'    :   'months',
            'transaction_amount':   float(plan.price),
            'currency_id'       :   'ARS',
        },
    }
    #Si el período ya está pago, el primer débito se agenda al vencimiento:
    #evita cobrar dos veces el mismo mes. OJO: en el modelo pending de MP la
    #primera cuota queda generada como pago pendiente y el checkout del
    #init_point la cobra en el acto — start_date solo ancla la recurrencia,
    #no difiere esa cuota. free_trial es el mecanismo que la cubre: MP marca
    #el primer pago como "ya pagado" y el primer cargo real cae al terminar
    #el período abonado. Va en días con ceil para que nunca caiga dentro de
    #la ventana ya paga (el sobrante de horas lo absorbe GRACE_DAYS con el
    #débito ya autorizado).
    if suscription.status == SUSCRIPTION_STATUS_ACTIVE and suscription.end_date and suscription.end_date > timezone.now():
        preapproval_data['auto_recurring']['start_date']    =   suscription.end_date.isoformat()
        days_left   =   math.ceil((suscription.end_date - timezone.now()).total_seconds() / 86400)
        if days_left > 0:
            preapproval_data['auto_recurring']['free_trial']    =   {
                'frequency'     :   days_left,
                'frequency_type':   'days',
            }
    mp_result           =   sdk.preapproval().create(preapproval_data)
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo iniciar el débito automático en Mercado Pago'})
    response                    =   mp_result['response']
    suscription.preapproval_id  =   response.get('id')
    #Un débito nuevo deja sin efecto la baja anterior: cancelled_at viejo
    #habilitaba el early-return de cancel-renewal (no cancelaba ESTE
    #preapproval) y bloqueaba el realineo de monto en checkout/subscription.
    suscription.cancelled_at    =   None
    suscription.cancel_requested_at =   None
    try:
        suscription.save(update_fields = ['preapproval_id', 'cancelled_at', 'cancel_requested_at'])
    except Exception:
        #Compensación (saga mínima): el alta remota ya existe en MP — si la
        #escritura local falla se cancela el preapproval para no dejar un
        #débito huérfano cobrando sin suscripción asociada.
        CancelPreapprovalByIdQuery(response.get('id'))
        raise
    return response

#UPDATE PREAPPROVAL PLAN QUERY (cambio de plan con débito activo: se ajusta el monto del próximo débito)
def UpdatePreapprovalPlanQuery(suscription):
    if not suscription.preapproval_id:
        return
    plan        =   suscription.pending_plan_suscription or suscription.plan_suscription
    mp_result   =   sdk.preapproval().update(suscription.preapproval_id, {
        'reason'        :   f'DAVENT · {plan.name}',
        'auto_recurring':   {
            'frequency'         :   1,
            'frequency_type'    :   'months',
            'transaction_amount':   float(plan.price),
            'currency_id'       :   'ARS',
        },
    })
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo actualizar el débito automático en Mercado Pago'})

#SYNC PREAPPROVAL QUERY (refleja en auto_renew el estado real de MP; fallback cuando el webhook no llega)
def SyncPreapprovalQuery(suscription):
    if not suscription or not suscription.preapproval_id:
        return None
    mp_status       =   GetPreapproval(suscription.preapproval_id).get('status')
    update_fields   =   []
    auto_renew      =   mp_status == 'authorized'
    if suscription.auto_renew != auto_renew:
        suscription.auto_renew  =   auto_renew
        update_fields.append('auto_renew')
    #paused también corta el débito: MP lo reactiva solo si el emisor lo
    #pide, pero localmente no hay débito vivo — sin cancelled_at los call
    #sites (checkout, cupón, assign) seguían tratándolo como activo y el
    #update de plan pegaba 400 contra un preapproval pausado.
    if mp_status in ('cancelled', 'paused') and suscription.cancelled_at is None:
        suscription.cancelled_at    =   timezone.now()
        update_fields.append('cancelled_at')
    if mp_status == 'cancelled' and suscription.cancel_requested_at is not None:
        #La baja solicitada quedó confirmada por MP: la intención se limpia.
        suscription.cancel_requested_at =   None
        update_fields.append('cancel_requested_at')
    elif mp_status == 'authorized' and suscription.cancelled_at is not None:
        #Un débito authorized en MP no tiene baja vigente: limpia un
        #cancelled_at residual (p.ej. escrito por una sync que leyó MP
        #antes de que el alta nueva confirmara).
        suscription.cancelled_at    =   None
        update_fields.append('cancelled_at')
    if update_fields:
        suscription.save(update_fields = update_fields)
    return mp_status

#CANCEL PREAPPROVAL QUERY (baja del débito: el acceso sigue hasta end_date)
def CancelPreapprovalQuery(suscription):
    if not suscription.preapproval_id:
        raise serializers.ValidationError({'suscription': 'No hay débito automático para cancelar'})
    try:
        mp_status   =   SyncPreapprovalQuery(suscription)
    except MercadoPagoNotFound:
        #404 en MP = el débito ya no existe: no puede volver a cobrar. Se
        #consolida la baja local igual que si MP hubiera confirmado.
        mp_status   =   'cancelled'
    if mp_status == 'cancelled':
        suscription.auto_renew          =   False
        suscription.cancelled_at        =   suscription.cancelled_at or timezone.now()
        suscription.cancel_requested_at =   None
        suscription.save(update_fields = ['auto_renew', 'cancelled_at', 'cancel_requested_at'])
        return suscription
    try:
        mp_result   =   sdk.preapproval().update(suscription.preapproval_id, {'status': 'cancelled'})
    except MercadoPagoNotFound:
        mp_result   =   {'status': 404}
    if mp_result.get('status') == 404:
        #Mismo caso: el preapproval desapareció entre el sync y el update.
        suscription.auto_renew          =   False
        suscription.cancelled_at        =   suscription.cancelled_at or timezone.now()
        suscription.cancel_requested_at =   None
        suscription.save(update_fields = ['auto_renew', 'cancelled_at', 'cancel_requested_at'])
        return suscription
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo cancelar el débito automático en Mercado Pago'})
    suscription.auto_renew          =   False
    suscription.cancelled_at        =   timezone.now()
    suscription.cancel_requested_at =   None
    suscription.save(update_fields = ['auto_renew', 'cancelled_at', 'cancel_requested_at'])
    return suscription

#CANCEL PREAPPROVAL BY ID (post-commit del canje de cupón y compensación de
#CreatePreapprovalQuery: cancela el débito en MP por id sin tocar el estado
#local — la suscripción ya fue actualizada cuando esto corre)
def CancelPreapprovalByIdQuery(preapproval_id) -> None:
    try:
        mp_result   =   sdk.preapproval().update(str(preapproval_id), {'status': 'cancelled'})
        if mp_result.get('status') not in (200, 201):
            logger.warning('No se pudo cancelar el preapproval %s en MP (status=%s)', preapproval_id, mp_result.get('status'))
    except Exception:
        logger.exception('Falló la cancelación del preapproval %s en MP', preapproval_id)

#PREAPPROVAL WEBHOOK QUERY (topic subscription_preapproval: alta/pausa/baja del débito)
def PreapprovalWebhookQuery(preapproval_id):
    #Lock de fila: sin él un webhook/sync podía commitear auto_renew=True
    #con el estado MP pre-cancel DESPUÉS del commit de cancel-renewal
    #(re-activaba el débito recién dado de baja).
    with transaction.atomic():
        suscription     =   Suscription.objects.select_for_update(of = ('self',)).filter(preapproval_id = str(preapproval_id)).first()
        if not suscription:
            return None
        return SyncPreapprovalQuery(suscription)

#GET AUTHORIZED PAYMENT (el SDK no cubre /authorized_payments: consulta directa con el access token)
def GetAuthorizedPayment(authorized_payment_id) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', str(authorized_payment_id)):
        raise serializers.ValidationError({'authorized_payment_id': 'Identificador inválido'})
    response    =   requests.get(
        f'https://api.mercadopago.com/authorized_payments/{authorized_payment_id}',
        headers     =   {'Authorization': f'Bearer {config("SECRET_MP_KEY")}'},
        timeout     =   15,
    )
    if response.status_code != 200:
        raise serializers.ValidationError({'authorized_payment_id': 'No se pudo verificar el débito en Mercado Pago'})
    return response.json()

#AUTHORIZED PAYMENT WEBHOOK QUERY (topic subscription_authorized_payment: cada débito mensual)
def AuthorizedPaymentWebhookQuery(authorized_payment_id):
    authorized      =   GetAuthorizedPayment(authorized_payment_id)
    payment_id      =   (authorized.get('payment') or {}).get('id') or authorized.get('payment_id')
    if not payment_id:
        #Débito aún agendado sin payment generado: la gracia cubre hasta que se ejecute.
        return None
    #El payment del débito hereda external_reference = suscription.id: entra por el flujo estándar
    return PaymentWebhookQuery(payment_id)
