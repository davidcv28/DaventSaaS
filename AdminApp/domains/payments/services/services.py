import mercadopago
from decimal import Decimal
from datetime import timedelta
from decouple import config
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from AdminApp.domains.invoices.models import Invoice
from AdminApp.domains.payments.models import Payment, DailyRevenue, MonthlyRevenue
from AdminApp.domains.suscriptions.models import Suscription
from AdminApp.domains.invoices.services import IssueInvoiceQuery

sdk             =   mercadopago.SDK(config('SECRET_MP_KEY'))
FRONTEND_URL    =   config('FRONTEND_URL', default = 'http://localhost:5173')
BACKEND_URL     =   config('BACKEND_URL', default = '')

MP_STATUS_MAP   =   {
    'approved'      :   Payment.Status.APPROVED,
    'rejected'      :   Payment.Status.REJECTED,
    'refunded'      :   Payment.Status.REFUNDED,
    'charged_back'  :   Payment.Status.REFUNDED,
}
#ESTADOS DE SUSCRIPCIÓN
SUSCRIPTION_STATUS_ACTIVE           =   'Suscripción activa'
SUSCRIPTION_STATUS_PENDING_PAYMENT  =   'Pendiente de pago'
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

#PAYMENT CREATE QUERY (verificación MP + idempotencia + atomicidad)
def CreatePaymentQuery(validated_data : dict, mp_payment : dict = None) -> Payment:
    data                =   validated_data.copy()
    payment_id          =   data.pop('payment_id')
    suscription         =   data['suscription']
    #IDEMPOTENCIA: el id de pago de Mercado Pago es único
    payment_exists      =   Payment.objects.select_related('suscription__pending_plan_suscription').filter(external_reference = str(payment_id)).first()
    if payment_exists:
        if payment_exists.status == Payment.Status.APPROVED:
            ApplyPendingPlanQuery(payment_exists.suscription)
        return payment_exists
    if mp_payment is None:
        mp_payment      =   GetMercadoPagoPayment(payment_id)
    #VERIFICACIÓN DE MONTO: debe coincidir con el precio del plan (pendiente si existe)
    amount              =   Decimal(str(mp_payment.get('transaction_amount', '0')))
    plan_price          =   (suscription.pending_plan_suscription or suscription.plan_suscription).price
    if amount != plan_price:
        raise serializers.ValidationError({
            'payment_id':   f'El monto del pago (${amount}) no coincide con el precio del plan (${plan_price})'
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
                paid_at             =   paid_at
            )
            #PLAN PENDIENTE: se establece la suscripción cuando el pago se acredita
            if status == Payment.Status.APPROVED:
                ApplyPendingPlanQuery(suscription)
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
    old_status          =   payment.status
    new_status          =   MP_STATUS_MAP.get(mp_payment.get('status'), payment.status)
    paid_at             =   parse_datetime(mp_payment['date_approved']) if mp_payment.get('date_approved') else payment.paid_at
    with transaction.atomic():
        payment.status      =   new_status
        payment.paid_at     =   paid_at
        payment.save(update_fields = ['status', 'paid_at', 'updated_at'])
        #PLAN PENDIENTE: se establece la suscripción cuando el pago se acredita
        if new_status == Payment.Status.APPROVED:
            ApplyPendingPlanQuery(payment.suscription)
        #ROLLUPS: solo se suma cuando el pago entra en approved; se descuenta si sale de approved
        if new_status == Payment.Status.APPROVED and old_status != Payment.Status.APPROVED:
            UpdateRevenueRollupsQuery(payment, sign = 1)
            #FACTURA: se emite dentro de la misma transacción que el cobro
            IssueInvoiceQuery(payment)
        elif old_status == Payment.Status.APPROVED and new_status != Payment.Status.APPROVED:
            UpdateRevenueRollupsQuery(payment, sign = -1)
    return payment

#REVENUE ROLLUPS QUERY (mantiene DailyRevenue / MonthlyRevenue materializados para dashboards)
def UpdateRevenueRollupsQuery(payment, sign = 1):
    """Suma (sign=1) o descuenta (sign=-1) el pago en los rollups diario y mensual.
    Se llama únicamente cuando un pago entra o sale del estado APPROVED."""
    effective           =   payment.paid_at or payment.created_at or timezone.now()
    day                 =   timezone.localtime(effective).date() if timezone.is_aware(effective) else effective.date()
    amount              =   payment.amount * sign
    daily, _            =   DailyRevenue.objects.get_or_create(date = day)
    daily.total_amount      =   (daily.total_amount or 0) + amount
    daily.payments_count    =   max(0, (daily.payments_count or 0) + sign)
    daily.save(update_fields = ['total_amount', 'payments_count', 'updated_at'])
    monthly, _          =   MonthlyRevenue.objects.get_or_create(year = day.year, month = day.month)
    monthly.total_amount    =   (monthly.total_amount or 0) + amount
    monthly.payments_count  =   max(0, (monthly.payments_count or 0) + sign)
    monthly.save(update_fields = ['total_amount', 'payments_count', 'updated_at'])

#APPLY PENDING PLAN QUERY (establece el plan una vez acreditado el pago)
def ApplyPendingPlanQuery(suscription):
    pending_plan        =   suscription.pending_plan_suscription
    is_pending_payment  =   suscription.status == SUSCRIPTION_STATUS_PENDING_PAYMENT
    if not pending_plan and not is_pending_payment:
        return suscription
    now                 =   timezone.now()
    update_fields       =   ['status', 'start_date', 'end_date']
    if pending_plan:
        suscription.plan_suscription            =   pending_plan
        suscription.pending_plan_suscription    =   None
        update_fields                          +=   ['plan_suscription', 'pending_plan_suscription']
    suscription.status      =   SUSCRIPTION_STATUS_ACTIVE
    suscription.start_date  =   now
    suscription.end_date    =   now + timedelta(days = 30)
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
    for mp_payment in results:
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
    #Cobra el plan pendiente si existe; el plan vigente solo cambia al acreditarse el pago
    plan                =   suscription.pending_plan_suscription or suscription.plan_suscription
    preference_data     =   {
        'items'             :   [{
            'title'         :   f'DAVENT · {plan.name}',
            'quantity'      :   1,
            'unit_price'    :   float(plan.price),
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
