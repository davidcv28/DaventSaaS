import logging
from datetime import timedelta

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
        if coupon is None or not coupon.is_active:
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
        suscription.status                      =   Suscription.STATUS_ACTIVE
        suscription.start_date                  =   now
        suscription.end_date                    =   now + timedelta(days = coupon.days)
        suscription.auto_renew                  =   False
        suscription.preapproval_id              =   None
        suscription.cancelled_at                =   None
        suscription.save()
        CouponRedemption.objects.create(coupon = coupon, user = profile, suscription = suscription)
    logger.info('Cupón canjeado: coupon=%s user=%s', coupon.code, profile.pk)
    return suscription, coupon
