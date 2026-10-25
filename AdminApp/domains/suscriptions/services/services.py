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

    El débito en MP se cancela POST-COMMIT por id (CancelPreapprovalByIdQuery):
    si la transacción rollbackea —cupón inválido, vencido, agotado, ya usado,
    plan vigente— el débito del usuario queda intacto. Cancelarlo ANTES de
    validar dejaba al usuario sin débito y sin plan en cualquier canje fallido.
    Un fallo de la API de MP queda logueado para reconciliar vía /sync/.
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
        preapproval_id                          =   suscription.preapproval_id
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
        if preapproval_id:
            #Import diferido: evita un edge de inicialización entre dominios
            #(payments.services ya importa suscriptions.models).
            from AdminApp.domains.payments.services import CancelPreapprovalByIdQuery
            transaction.on_commit(lambda pid = preapproval_id : CancelPreapprovalByIdQuery(pid))
    logger.info('Cupón canjeado: coupon=%s user=%s', coupon.code, profile.pk)
    return suscription, coupon
