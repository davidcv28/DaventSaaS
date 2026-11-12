import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from AdminApp.domains.suscriptions.models import Coupon, CouponRedemption, Suscription

logger          =   logging.getLogger(__name__)

"""

Queries del dominio Suscriptions.

"""

#=================================
# REDEEM COUPON QUERY
#=================================
def RedeemCouponQuery(profile, code : str) -> tuple:
    """
    Canjea un código promocional: pisa la suscripción OneToOne con el plan del
    cupón por coupon.days días y limpia restos de débito MP (pending_plan /
    auto_renew / preapproval_id / cancelled_at).

    Un débito MP aún vivo (preapproval sin baja confirmada) rechaza el canje:
    un cobro en vuelo de MP entraría con el plan ya pisado por el cupón.
    cancelled_at certifica que MP procesó la baja — ahí solo se limpian los
    restos locales sin volver a llamar a la API.
    """
    code    =   (code or '').strip()
    if not code:
        raise serializers.ValidationError({'code': 'Ingresá un código.'})
    #select_for_update + unique(coupon, user) serializan canjes concurrentes
    #para que max_uses no se supere en una carrera.
    with transaction.atomic():
        coupon      =   Coupon.objects.select_for_update().filter(code__iexact = code).first()
        if coupon is None or not coupon.is_active or coupon.plan.is_trial:
            raise serializers.ValidationError({'code': 'El cupón no es válido.'})
        now         =   timezone.now()
        if coupon.expires_at and coupon.expires_at <= now:
            raise serializers.ValidationError({'code': 'El cupón venció.'})
        if coupon.max_uses is not None and coupon.redemptions.count() >= coupon.max_uses:
            raise serializers.ValidationError({'code': 'El cupón llegó a su límite de usos.'})
        if coupon.redemptions.filter(user = profile).exists():
            raise serializers.ValidationError({'code': 'Ya usaste este cupón.'})
        suscription =   Suscription.objects.select_for_update().filter(user = profile).first() or Suscription(user = profile)
        if suscription.pk and suscription.grants_access() and not suscription.plan_suscription.is_trial:
            raise serializers.ValidationError({'detail': 'Ya tenés un plan vigente.'})
        #Un débito MP aún vivo (preapproval sin baja confirmada) puede cobrar
        #en vuelo tras el canje: ese cobro entraría con el plan ya pisado por
        #el cupón. Se exige darlo de baja primero — cancelled_at certifica
        #que MP ya procesó la cancelación.
        if suscription.pk and suscription.preapproval_id and not suscription.cancelled_at:
            raise serializers.ValidationError({'detail': 'Primero tenés que dar de baja el débito automático para canjear un cupón.'})
        suscription.plan_suscription            =   coupon.plan
        suscription.pending_plan_suscription    =   None
        suscription.pending_charge              =   None
        suscription.status                      =   Suscription.STATUS_ACTIVE
        suscription.start_date                  =   now
        suscription.end_date                    =   now + timedelta(days = coupon.days)
        suscription.auto_renew                  =   False
        suscription.preapproval_id              =   None
        suscription.cancelled_at                =   None
        suscription.cancel_requested_at         =   None
        #El cupón abre un período sin cobro: ningún Payment puede revocarlo.
        suscription.period_payment_id           =   None
        suscription.period_end_before           =   None
        suscription.save()
        CouponRedemption.objects.create(coupon = coupon, user = profile, suscription = suscription)
    logger.info('Cupón canjeado: coupon=%s user=%s', coupon.code, profile.pk)
    return suscription, coupon

#=================================
# PLAN CHANGE QUERY (modelo Netflix)
#=================================
def _upgrade_charge(suscription, target_plan):
    """
    Cargo prorrateado de un upgrade: (plan_nuevo - plan_vigente) ×
    días_restantes / días_del_período. Solo aplica con suscripción paga
    vigente — un plan trial ($0) o un período vencido no prorratea: el
    cambio se cobra a precio completo y reinicia el período al acreditarse.
    """
    current         =   suscription.plan_suscription
    now             =   timezone.now()
    if (
        suscription.status != Suscription.STATUS_ACTIVE
        or not current or current.is_trial or current.price <= 0
        or target_plan.price <= current.price
        or not suscription.end_date or suscription.end_date <= now
        or not suscription.start_date or suscription.start_date >= suscription.end_date
    ):
        return None
    period_s        =   Decimal(str((suscription.end_date - suscription.start_date).total_seconds()))
    remain_s        =   Decimal(str((suscription.end_date - now).total_seconds()))
    charge          =   (target_plan.price - current.price) * remain_s / period_s
    charge          =   charge.quantize(Decimal('0.01'), rounding = ROUND_HALF_UP)
    return max(charge, Decimal('0.01'))

def RequestPlanChangeQuery(suscription, target_plan):
    """
    Cambio de plan del cliente (modelo Netflix):

    - UPGRADE (plan más caro): queda pendiente con `pending_charge`
      prorrateado — el checkout cobra solo la diferencia por los días
      restantes y al acreditarse el plan cambia SIN reiniciar el período
      (la fecha de facturación se mantiene y el próximo débito sale al
      precio nuevo).
    - DOWNGRADE (plan más barato) o lateral: queda `pending_plan` sin
      cargo — en la próxima facturación se cobra el precio nuevo y recién
      ahí se aplica el plan (el usuario conserva el plan actual hasta
      end_date).
    - Mismo plan: cancela el cambio pendiente.

    Con débito MP vivo se realinea el monto del próximo débito al plan
    objetivo (best-effort: si MP falla no se bloquea el cambio local — el
    checkout/subscription lo reintenta).
    """
    #Lock de fila + recarga: dos cambios concurrentes (o uno contra
    #ApplyPendingPlanQuery) leían plan/pending stale y commiteaban
    #pending_charge calculado sobre el plan equivocado.
    with transaction.atomic():
        suscription =   Suscription.objects.select_for_update(of = ('self',)).select_related(
            'plan_suscription', 'pending_plan_suscription').get(pk = suscription.pk)
        if target_plan.id == suscription.plan_suscription_id:
            suscription.pending_plan_suscription    =   None
            suscription.pending_charge              =   None
            suscription.save(update_fields = ['pending_plan_suscription', 'pending_charge'])
            return suscription
        is_upgrade      =   target_plan.price > (suscription.plan_suscription.price or Decimal('0'))
        suscription.pending_plan_suscription    =   target_plan
        suscription.pending_charge              =   _upgrade_charge(suscription, target_plan) if is_upgrade else None
        suscription.save(update_fields = ['pending_plan_suscription', 'pending_charge'])
        if suscription.preapproval_id and not suscription.cancelled_at:
            try:
                from AdminApp.domains.payments.services import UpdatePreapprovalPlanQuery
                UpdatePreapprovalPlanQuery(suscription)
            except Exception:
                logger.warning('No se pudo realinear el débito MP del plan pendiente (suscription=%s)', suscription.pk)
        return suscription
