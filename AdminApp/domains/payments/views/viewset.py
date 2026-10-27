import hashlib
import hmac
import logging
import re
from decimal import Decimal
from decouple import config
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
from django.utils import timezone
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.users.services import BillingMissingFieldsQuery
from AdminApp.domains.payments.models import Payment
from AdminApp.domains.invoices.services import IssueInvoiceQuery
from AdminApp.domains.payments.services import (
    PaymentWebhookQuery,
    CreateCheckoutPreferenceQuery,
    ApplyPendingPlanQuery,
    SyncSuscriptionPaymentsQuery,
    UpdateRevenueRollupsQuery,
    CreatePreapprovalQuery,
    GetPreapproval,
    UpdatePreapprovalPlanQuery,
    SyncPreapprovalQuery,
    CancelPreapprovalQuery,
    PreapprovalWebhookQuery,
    AuthorizedPaymentWebhookQuery,
    SUSCRIPTION_STATUS_PENDING_PAYMENT,
    SUSCRIPTION_STATUS_ACTIVE
)
from .viewset_base      import  PaymentBaseViewSet
from .viewset_config    import  PaymentConfigs, DailyRevenueConfigs, MonthlyRevenueConfigs
"""

Creamos los viewsets correspondientes al dominio payments

"""
logger              =   logging.getLogger(__name__)
#Ventana mínima entre barridos reales contra la API de Mercado Pago en
#/payments/sync/ (ver el action sync): el payment_id puntual nunca se acota.
SYNC_SWEEP_SECONDS      =   15
#TTL del dedup de entregas de webhook (ver el action webhook): cubre la
#ventana de frescura de la firma — un replay más viejo ya cae por el ts.
WEBHOOK_DEDUP_SECONDS   =   600
WEBHOOK_ID_RE           =   re.compile(r'[A-Za-z0-9_-]{1,64}')
#=========================================
# WEBHOOK SIGNATURE (HMAC-SHA256 según doc oficial de Mercado Pago)
#=========================================
def _verify_mp_signature(request, resource_id) -> bool:
    """
    Valida x-signature + x-request-id: el manifest es
    'id:<data.id>;request-id:<x-request-id>;ts:<ts>;' firmado con HMAC-SHA256
    y MP_WEBHOOK_SECRET -> debe matchear el v1= del header (compare_digest).
    Sin secret el evento se procesa igual SOLO en dev con opt-in explícito:
    exige DEBUG=True y MP_WEBHOOK_ALLOW_UNSIGNED=True en el .env — así un
    DEBUG=True accidental en producción no deja el webhook sin verificar
    (un webhook sin firma permite forjar acreditaciones de pago).
    """
    secret          =   config('MP_WEBHOOK_SECRET', default = '')
    if not secret:
        allow_unsigned  =   settings.DEBUG and config('MP_WEBHOOK_ALLOW_UNSIGNED', default = False, cast = bool)
        if allow_unsigned:
            logger.warning('MP_WEBHOOK_SECRET no configurado: webhook de MP procesado sin verificar firma (MP_WEBHOOK_ALLOW_UNSIGNED)')
            return True
        logger.error('MP_WEBHOOK_SECRET no configurado: webhook de MP rechazado')
        return False
    x_signature     =   request.headers.get('x-signature', '')
    x_request_id    =   request.headers.get('x-request-id', '')
    parts           =   {}
    for pair in x_signature.split(','):
        if '=' in pair:
            key, value  =   pair.split('=', 1)
            parts[key.strip()]  =   value.strip()
    ts              =   parts.get('ts')
    v1              =   parts.get('v1')
    if not ts or not v1 or not x_request_id or not resource_id:
        return False
    #Ventana de frescura: sin ella, una firma válida capturada (logs, proxy)
    #rejugaba el mismo evento para siempre. La doc de MP muestra ts en
    #segundos, pero hay despliegues en milisegundos: se aceptan ambos.
    try:
        ts_value    =   int(ts)
    except (TypeError, ValueError):
        return False
    if ts_value > 100_000_000_000:          # > año 5138 en segundos -> ms
        ts_value    =   ts_value / 1000
    if abs(timezone.now().timestamp() - ts_value) > 600:
        return False
    manifest        =   f'id:{resource_id};request-id:{x_request_id};ts:{ts};'
    expected        =   hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)

#=========================================
# PAYMENT VIEWSET
#=========================================
class PaymentViewSet(PaymentBaseViewSet):
    viewset_config  =   PaymentConfigs
    #=========================================
    # APPROVE ACTION (solo admin - sella status y paid_at)
    #=========================================
    @action(detail = True, methods = ['post'])
    def approve(self, request, pk = None):
        #ATOMICIDAD: la acreditación se sella junto con el plan, los rollups y la factura
        with transaction.atomic():
            instance        =   self.get_object()
            was_approved    =   instance.status == Payment.Status.APPROVED
            instance.approve()
            ApplyPendingPlanQuery(instance.suscription, renew = not was_approved)
            if not was_approved:
                UpdateRevenueRollupsQuery(instance)
                IssueInvoiceQuery(instance)
                logger.info('Pago aprobado manualmente: payment=%s admin=%s', instance.pk, request.user.pk)
        serializer  =   self.get_serializer(instance)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # WEBHOOK ACTION (notificaciones IPN de Mercado Pago)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'webhook')
    def webhook(self, request):
        topic       =   request.data.get('type') or request.query_params.get('topic')
        #'data' puede llegar no-dict en requests malformados -> evitar 500.
        data        =   request.data.get('data')
        resource_id =   data.get('id') if isinstance(data, dict) else None
        resource_id =   resource_id or request.query_params.get('id')
        #El id se interpola en paths de la API de MP: solo alfanumérico corto
        #(un '../' o '?' permitiría redirigir la consulta autenticada con el token).
        resource_id =   str(resource_id) if resource_id is not None else None
        if resource_id and not WEBHOOK_ID_RE.fullmatch(resource_id):
            logger.warning('Webhook de MP rechazado: id con formato inválido (topic=%s)', topic)
            return Response({'detail': 'Identificador inválido'}, status = status.HTTP_400_BAD_REQUEST)
        #Firma HMAC: sin ella cualquiera podría forjar acreditaciones de pago.
        if not _verify_mp_signature(request, resource_id):
            logger.warning('Webhook de MP rechazado: firma inválida (topic=%s id=%s)', topic, resource_id)
            return Response({'detail': 'Firma de webhook inválida'}, status = status.HTTP_401_UNAUTHORIZED)
        #Dedup de entregas: MP reintenta el mismo evento y un replay dentro de
        #la ventana de frescura reenvía las mismas cabeceras. cache.add es
        #atómico — el primer delivery clama el request-id y los demás (aun
        #concurrentes entre workers) se absorben sin volver a pegarle a la
        #API de MP. Fail-open si el cache cae: la idempotencia real está en
        #las queries; si el procesamiento explota se libera la marca para
        #que el retry de MP con el mismo request-id pueda reintentarlo.
        dedup_key       =   None
        x_request_id    =   request.headers.get('x-request-id', '')
        if x_request_id:
            dedup_key   =   f'mp-webhook:{topic}:{resource_id}:{x_request_id}'
            try:
                if not cache.add(dedup_key, 1, WEBHOOK_DEDUP_SECONDS):
                    return Response({'Exito': 'Notificación ya procesada'}, status = status.HTTP_200_OK)
            except Exception:
                dedup_key   =   None
        try:
            if topic == 'payment' and resource_id:
                PaymentWebhookQuery(resource_id)
            elif topic == 'subscription_preapproval' and resource_id:
                PreapprovalWebhookQuery(resource_id)
            elif topic == 'subscription_authorized_payment' and resource_id:
                AuthorizedPaymentWebhookQuery(resource_id)
        except Exception:
            if dedup_key:
                try:
                    cache.delete(dedup_key)
                except Exception:
                    pass
            raise
        return Response({'Exito': 'Notificación procesada'}, status = status.HTTP_200_OK)
    #=========================================
    # RESOLVE SUSCRIPTION (resuelve/crea la suscripción y deja el plan elegido pendiente)
    #=========================================
    def _resolve_suscription(self, request):
        suscription_id  =   request.data.get('suscription')
        plan_id         =   request.data.get('plan_suscription')
        if suscription_id:
            #ids no numéricos devolvían ValueError -> 500: se parsean defensivo.
            try:
                suscription =   Suscription.objects.select_related('plan_suscription', 'user__user').get(pk = int(suscription_id))
            except (Suscription.DoesNotExist, TypeError, ValueError):
                raise serializers.ValidationError({'suscription': 'La suscripción ingresada no existe'})
            if suscription.user.user_id != request.user.id:
                raise serializers.ValidationError({'suscription': 'La suscripción seleccionada no pertenece a tu usuario.'})
        else:
            suscription =   Suscription.objects.select_related('plan_suscription', 'user__user').filter(user__user = request.user).first()
        target_plan     =   None
        if plan_id:
            #Los planes de prueba (is_trial) no son pagables: solo se otorgan en el registro
            try:
                target_plan =   SuscriptionPlan.objects.get(pk = int(plan_id), is_trial = False)
            except (SuscriptionPlan.DoesNotExist, TypeError, ValueError):
                raise serializers.ValidationError({'plan_suscription': 'El plan seleccionado no está disponible'})
        if not suscription:
            if not target_plan:
                raise serializers.ValidationError({'plan_suscription': 'Elegí un plan para iniciar el pago'})
            profile     =   UserProfile.objects.filter(user = request.user).first()
            if not profile:
                raise serializers.ValidationError({'suscription': 'Tu usuario aún no tiene perfil comercial.'})
            #La suscripción queda pendiente hasta que se acredite el pago
            suscription =   Suscription.objects.create(
                user                =   profile,
                plan_suscription    =   target_plan,
                status              =   SUSCRIPTION_STATUS_PENDING_PAYMENT,
                start_date          =   timezone.now(),
                end_date            =   timezone.now(),
            )
        elif target_plan and suscription.status == SUSCRIPTION_STATUS_PENDING_PAYMENT:
            #Reintento de checkout: solo se corrige el plan elegido, sigue pendiente
            suscription.plan_suscription    =   target_plan
            suscription.save(update_fields = ['plan_suscription'])
        elif target_plan and target_plan.id != suscription.plan_suscription_id:
            #El plan se aplica recién cuando el pago se acredita
            suscription.pending_plan_suscription    =   target_plan
            suscription.save(update_fields = ['pending_plan_suscription'])
        #DATOS FISCALES: el alta ya no los pide — se exigen recién al iniciar
        #un cobro porque la factura se emite sobre este perfil (ARCA + PDF).
        #El frontend usa 'billing_required' para abrir el form de facturación.
        missing =   BillingMissingFieldsQuery(suscription.user)
        if missing:
            raise serializers.ValidationError({
                'billing_required'  :   missing,
                'detail'            :   'Completá tus datos de facturación para poder contratar un plan.',
            })
        return suscription
    #=========================================
    # CHECKOUT ACTION (crea preferencia MP y devuelve init_point)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'checkout')
    def checkout(self, request):
        suscription     =   self._resolve_suscription(request)
        #Cambio de plan vía checkout con débito vivo: el próximo cobro
        #automático también debe cargar el plan pendiente o el plan nuevo de
        #una suscripción impaga (misma regla que el action subscription).
        #Si no se actualiza la preapproval, MP cargaría el monto viejo y el
        #webhook lo rechazaría por el chequeo de monto — cobro huérfano.
        #Un débito ya cancelado (cancelled_at) queda fuera: MP rechazaría
        #el update y arrastraría un 400 al checkout.
        if suscription.preapproval_id and not suscription.cancelled_at and (
            suscription.pending_plan_suscription_id or suscription.status == SUSCRIPTION_STATUS_PENDING_PAYMENT):
            UpdatePreapprovalPlanQuery(suscription)
        preference      =   CreateCheckoutPreferenceQuery(suscription)
        #Con credenciales TEST se usa el checkout sandbox; en prod el init_point real.
        is_sandbox      =   str(config('SECRET_MP_KEY', default = '')).startswith('TEST-')
        checkout_url    =   preference.get('sandbox_init_point') if is_sandbox else preference.get('init_point')
        return Response(
            {
                'checkout_url'      :   checkout_url or preference.get('init_point'),
                'init_point'        :   preference.get('init_point'),
                'sandbox_init_point':   preference.get('sandbox_init_point'),
                'preference_id'     :   preference.get('id'),
            }, status = status.HTTP_200_OK)
    #=========================================
    # SUBSCRIPTION ACTION (débito automático MP: alta, retoma init_point o cambia el plan del débito)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'subscription')
    def subscription(self, request):
        suscription     =   self._resolve_suscription(request)
        try:
            mp_status   =   SyncPreapprovalQuery(suscription)
        except serializers.ValidationError:
            #Preapproval_id viejo/inválido en MP: se descarta y se crea uno nuevo
            mp_status   =   None
        #Ya autorizado: si hay plan pendiente nuevo, se actualiza el monto del próximo débito
        if mp_status == 'authorized':
            if suscription.pending_plan_suscription_id:
                UpdatePreapprovalPlanQuery(suscription)
            return Response(
                {
                    'status'        :   'authorized',
                    'auto_renew'    :   True,
                    'preapproval_id':   suscription.preapproval_id,
                }, status = status.HTTP_200_OK)
        if mp_status == 'pending':
            #Autorización en curso: se retoma el mismo init_point con el monto al día
            UpdatePreapprovalPlanQuery(suscription)
            preapproval     =   GetPreapproval(suscription.preapproval_id)
        else:
            #Sin débito o cancelado/pausado: se crea uno nuevo
            preapproval     =   CreatePreapprovalQuery(suscription)
        is_sandbox      =   str(config('SECRET_MP_KEY', default = '')).startswith('TEST-')
        #En preapprovals MP no devuelve sandbox_init_point: el init_point es uno solo.
        return Response(
            {
                'status'            :   preapproval.get('status'),
                'checkout_url'      :   (preapproval.get('sandbox_init_point') or preapproval.get('init_point')) if is_sandbox else preapproval.get('init_point'),
                'init_point'        :   preapproval.get('init_point'),
                'sandbox_init_point':   preapproval.get('sandbox_init_point'),
                'preapproval_id'    :   suscription.preapproval_id,
            }, status = status.HTTP_200_OK)
    #=========================================
    # CANCEL RENEWAL ACTION (baja del débito automático: el acceso sigue hasta end_date)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'cancel-renewal')
    def cancel_renewal(self, request):
        suscription =   Suscription.objects.filter(user__user = request.user).first()
        if not suscription:
            raise serializers.ValidationError({'suscription': 'No tenés una suscripción para dar de baja'})
        if not suscription.auto_renew and suscription.cancelled_at:
            return Response({'Exito': 'La renovación automática ya estaba desactivada', 'auto_renew': False}, status = status.HTTP_200_OK)
        CancelPreapprovalQuery(suscription)
        return Response(
            {
                'Exito'     :   'Renovación automática desactivada. Tu plan sigue vigente hasta el fin del período ya pago.',
                'auto_renew':   False,
                'end_date'  :   suscription.end_date,
            }, status = status.HTTP_200_OK)
    #=========================================
    # SYNC ACTION (registra pagos ya acreditados en MP sin depender del redirect)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'sync')
    def sync(self, request):
        suscription =   Suscription.objects.select_related('user', 'plan_suscription', 'pending_plan_suscription').filter(user__user = request.user).first()
        raw_id      =   request.data.get('payment_id') or request.query_params.get('payment_id')
        try:
            payment_id = int(str(raw_id).strip()) if raw_id not in (None, '') else None
        except (TypeError, ValueError):
            payment_id = None
        #El barrido completo contra la API de MP (search + preapproval) tarda
        #~1s por request y el frontend lo llama al montar el panel y cada 5s
        #en los watchers de checkout/débito: con cache.add se acota a un
        #barrido real cada SYNC_SWEEP_SECONDS por usuario. El payment_id
        #puntual (retorno del checkout) nunca se acota — es la vía instantánea.
        if payment_id is None and not cache.add(f'payments:sync-sweep:{request.user.pk}', 1, SYNC_SWEEP_SECONDS):
            return Response(
                {
                    'Exito'             :   'Pagos sincronizados',
                    'synced'            :   0,
                    'auto_renew'        :   bool(suscription and suscription.auto_renew),
                    'preapproval_status':   None,
                    'throttled'         :   True,
                }, status = status.HTTP_200_OK)
        payments    =   SyncSuscriptionPaymentsQuery(suscription, payment_id = payment_id) if suscription else []
        #El débito automático también se sincroniza acá: cubre los casos en que
        #el webhook de MP no puede llegar (localhost, red privada).
        mp_status   =   SyncPreapprovalQuery(suscription)
        return Response(
            {
                'Exito'             :   'Pagos sincronizados',
                'synced'            :   len(payments),
                'auto_renew'        :   bool(suscription and suscription.auto_renew),
                'preapproval_status':   mp_status,
            }, status = status.HTTP_200_OK)
    #=========================================
    # ADMIN SUMMARY ACTION (KPIs del panel admin, calculado en vivo desde Payment)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'admin-summary')
    def admin_summary(self, request):
        today           =   timezone.localdate()
        first_of_month  =   today.replace(day = 1)
        approved_qs     =   Payment.objects.filter(status = Payment.Status.APPROVED).annotate(
            effective   =   Coalesce('paid_at', 'created_at')
        )
        totals          =   approved_qs.aggregate(
            total       =   Coalesce(Sum('amount'), Decimal('0')),
            month_total =   Coalesce(Sum('amount', filter = Q(effective__date__gte = first_of_month)), Decimal('0')),
            today_total =   Coalesce(Sum('amount', filter = Q(effective__date = today)), Decimal('0')),
        )
        #CONTEOS POR ESTADO DE PAGO
        status_counts   =   {s: 0 for s in Payment.Status.values}
        for row in Payment.objects.values('status').annotate(n = Count('id')):
            status_counts[row['status']]    =   row['n']
        #CONTEOS DE SUSCRIPCIONES (status es texto libre en el modelo)
        subs_rows       =   list(Suscription.objects.values('status').annotate(n = Count('id')))
        subs_active     =   sum(r['n'] for r in subs_rows if r['status'] == SUSCRIPTION_STATUS_ACTIVE)
        subs_pending    =   sum(r['n'] for r in subs_rows if r['status'] == SUSCRIPTION_STATUS_PENDING_PAYMENT)
        #INGRESOS AGRUPADOS (ventanas recientes para los gráficos del panel)
        revenue_by_day  =   list(
            approved_qs.annotate(day = TruncDate('effective'))
                .values('day').annotate(total_amount = Sum('amount'), payments_count = Count('id'))
                .order_by('-day')[:31]
        )
        revenue_by_month    =   list(
            approved_qs.annotate(month = TruncMonth('effective'))
                .values('month').annotate(total_amount = Sum('amount'), payments_count = Count('id'))
                .order_by('-month')[:12]
        )
        #DISTRIBUCIÓN POR PLAN: ingresos aprobados + suscripciones vigentes
        subs_per_plan   =   {
            r['plan_suscription__name']: r['n']
            for r in Suscription.objects.values('plan_suscription__name').annotate(n = Count('id'))
        }
        by_plan         =   [
            {
                'plan'          :   row['suscription__plan_suscription__name'],
                'revenue'       :   row['revenue'],
                'payments'      :   row['payments'],
                'suscriptions'  :   subs_per_plan.get(row['suscription__plan_suscription__name'], 0),
            }
            for row in approved_qs.values('suscription__plan_suscription__name')
                .annotate(revenue = Sum('amount'), payments = Count('id'))
                .order_by('-revenue')
        ]
        #Planes con suscripciones pero aún sin pagos aprobados
        for name, n in subs_per_plan.items():
            if name and all(p['plan'] != name for p in by_plan):
                by_plan.append({'plan': name, 'revenue': Decimal('0'), 'payments': 0, 'suscriptions': n})
        return Response(
            {
                'total_revenue'         :   totals['total'],
                'revenue_month'         :   totals['month_total'],
                'revenue_today'         :   totals['today_total'],
                'payments_total'        :   sum(status_counts.values()),
                'payments_approved'     :   status_counts.get(Payment.Status.APPROVED, 0),
                'payments_pending'      :   status_counts.get(Payment.Status.PENDING, 0),
                'payments_rejected'     :   status_counts.get(Payment.Status.REJECTED, 0),
                'payments_refunded'     :   status_counts.get(Payment.Status.REFUNDED, 0),
                'suscriptions_total'    :   sum(r['n'] for r in subs_rows),
                'suscriptions_active'   :   subs_active,
                'suscriptions_pending'  :   subs_pending,
                'customers'             :   UserProfile.objects.count(),
                'revenue_by_day'        :   [
                    {'date': r['day'], 'total_amount': r['total_amount'], 'payments_count': r['payments_count']}
                    for r in revenue_by_day
                ],
                'revenue_by_month'      :   [
                    {'year': r['month'].year, 'month': r['month'].month, 'total_amount': r['total_amount'], 'payments_count': r['payments_count']}
                    for r in revenue_by_month
                ],
                'by_plan'               :   by_plan,
            }, status = status.HTTP_200_OK)

#=========================================
# DAILY REVENUE VIEWSET (solo lectura)
#=========================================
class DailyRevenueViewSet(PaymentBaseViewSet):
    viewset_config  =   DailyRevenueConfigs

#=========================================
# MONTHLY REVENUE VIEWSET (solo lectura)
#=========================================
class MonthlyRevenueViewSet(PaymentBaseViewSet):
    viewset_config  =   MonthlyRevenueConfigs
