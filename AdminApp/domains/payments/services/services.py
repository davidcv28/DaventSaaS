import mercadopago
import requests
from decimal import Decimal
from datetime import timedelta
from decouple import config
from django.db import transaction, IntegrityError
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from AdminApp.domains.payments.models import Payment, DailyRevenue, MonthlyRevenue
from AdminApp.domains.suscriptions.models import Suscription
from AdminApp.domains.invoices.services import IssueInvoiceQuery

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
}
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
        if payment_exists.status == Payment.Status.APPROVED:
            ApplyPendingPlanQuery(payment_exists.suscription)
        return payment_exists
    if mp_payment is None:
        mp_payment      =   GetMercadoPagoPayment(payment_id)
    #OWNERSHIP DEL COBRO: la preferencia se crea con external_reference = id de
    #la suscripción. Sin este chequeo, un payment_id ajeno (el monto solo se
    #compara con el precio del plan) podía registrarse en la suscripción de
    #otro usuario — misma regla que aplica PaymentWebhookQuery.
    if str(mp_payment.get('external_reference') or '') != str(suscription.id):
        raise serializers.ValidationError({'payment_id': 'El pago no corresponde a esta suscripción.'})
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
                ApplyPendingPlanQuery(suscription, renew = True)
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
        #renew solo si el pago entra a approved ahora: un webhook repetido no vuelve a extender
        if new_status == Payment.Status.APPROVED:
            ApplyPendingPlanQuery(payment.suscription, renew = old_status != Payment.Status.APPROVED)
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
def ApplyPendingPlanQuery(suscription, renew = False):
    pending_plan        =   suscription.pending_plan_suscription
    is_pending_payment  =   suscription.status == SUSCRIPTION_STATUS_PENDING_PAYMENT
    if not pending_plan and not is_pending_payment and not renew:
        return suscription
    now                 =   timezone.now()
    update_fields       =   ['status', 'start_date', 'end_date']
    if pending_plan:
        suscription.plan_suscription            =   pending_plan
        suscription.pending_plan_suscription    =   None
        update_fields                          +=   ['plan_suscription', 'pending_plan_suscription']
    #Todo cobro aprobado reinicia el período: 30 días desde el cobro (máx. 30).
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

#=================================
# MERCADO PAGO PREAPPROVAL (débito automático mensual)
#=================================
#GET PREAPPROVAL (estado real de la suscripción en MP)
def GetPreapproval(preapproval_id) -> dict:
    mp_result       =   sdk.preapproval().get(preapproval_id)
    if mp_result.get('status') != 200:
        raise serializers.ValidationError({'preapproval_id': 'No se pudo verificar el débito automático en Mercado Pago'})
    return mp_result['response']

#CREATE PREAPPROVAL QUERY (alta del débito: queda pending hasta que el cliente lo autoriza en MP)
def CreatePreapprovalQuery(suscription) -> dict:
    #Cobra el plan pendiente si existe; el vigente si no
    plan                =   suscription.pending_plan_suscription or suscription.plan_suscription
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
    #evita cobrar dos veces el mismo mes.
    if suscription.status == SUSCRIPTION_STATUS_ACTIVE and suscription.end_date and suscription.end_date > timezone.now():
        preapproval_data['auto_recurring']['start_date']    =   suscription.end_date.isoformat()
    mp_result           =   sdk.preapproval().create(preapproval_data)
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo iniciar el débito automático en Mercado Pago'})
    response                    =   mp_result['response']
    suscription.preapproval_id  =   response.get('id')
    suscription.save(update_fields = ['preapproval_id'])
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
    if mp_status == 'cancelled' and suscription.cancelled_at is None:
        suscription.cancelled_at    =   timezone.now()
        update_fields.append('cancelled_at')
    if update_fields:
        suscription.save(update_fields = update_fields)
    return mp_status

#CANCEL PREAPPROVAL QUERY (baja del débito: el acceso sigue hasta end_date)
def CancelPreapprovalQuery(suscription):
    if not suscription.preapproval_id:
        raise serializers.ValidationError({'suscription': 'No hay débito automático para cancelar'})
    if SyncPreapprovalQuery(suscription) == 'cancelled':
        return suscription
    mp_result   =   sdk.preapproval().update(suscription.preapproval_id, {'status': 'cancelled'})
    if mp_result.get('status') not in (200, 201):
        raise serializers.ValidationError({'suscription': 'No se pudo cancelar el débito automático en Mercado Pago'})
    suscription.auto_renew      =   False
    suscription.cancelled_at    =   timezone.now()
    suscription.save(update_fields = ['auto_renew', 'cancelled_at'])
    return suscription

#PREAPPROVAL WEBHOOK QUERY (topic subscription_preapproval: alta/pausa/baja del débito)
def PreapprovalWebhookQuery(preapproval_id):
    suscription     =   Suscription.objects.filter(preapproval_id = str(preapproval_id)).first()
    if not suscription:
        return None
    return SyncPreapprovalQuery(suscription)

#GET AUTHORIZED PAYMENT (el SDK no cubre /authorized_payments: consulta directa con el access token)
def GetAuthorizedPayment(authorized_payment_id) -> dict:
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
