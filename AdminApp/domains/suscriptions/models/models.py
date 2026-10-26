
from django.db import models
from AdminApp.domains.users.models import UserProfile
from django.utils import timezone
from datetime import timedelta
"""

Creamos las suscripciones

"""
#=========================================
#SUSCRIPTION PLAN MODEL
#=========================================
class SuscriptionPlan(models.Model):
    #Duración del plan de prueba (is_trial=True): se otorga solo en el registro
    #y al vencer no se puede reactivar (no es seleccionable ni asignable).
    TRIAL_DAYS                  =   1
    name                        =   models.CharField(max_length = 60, null = False, blank = False, unique = True)
    price                       =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0.00, blank = False, null = False, verbose_name = 'Precio suscripción')
    is_trial                    =   models.BooleanField(default = False, verbose_name = 'Plan de prueba')
    class Meta:
        app_label               =   'suscriptions'
        verbose_name            =   'Plan'
        verbose_name_plural     =   'Planes'
    def __str__(self):
        return self.name
    
def _bust_benefits_cache(*profile_ids):
    #Pisa el cache cross-request de beneficios (plan_benefits_of en
    #StoreApp/stores/services — keys 'planben:<profile_id>'): sin esto el
    #gating seguiría viendo el plan anterior hasta que venza el TTL.
    if not profile_ids:
        return
    from django.core.cache import cache
    try:
        cache.delete_many(['planben:%s' % pk for pk in profile_ids])
    except Exception:
        pass
#=========================================
#SUSCRIPTION QUERYSET (bulk update también invalida el cache de beneficios)
#=========================================
class SuscriptionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        #QuerySet.update() bypassa save(): la invalidación corre acá igual
        #para que un downgrade/upgrade por bulk no sirva el plan viejo.
        profiles    =   list(self.values_list('user_id', flat = True))
        updated     =   super().update(**kwargs)
        _bust_benefits_cache(*profiles)
        return updated
#=========================================
#SUSCRIPTION MODEL
#=========================================
class Suscription(models.Model):
    #ESTADOS (texto libre histórico): centralizados acá como fuente de verdad
    STATUS_ACTIVE           =   'Suscripción activa'
    STATUS_PENDING_PAYMENT  =   'Pendiente de pago'
    #Días de gracia tras end_date cuando el débito automático está activo:
    #cubre el reintento de Mercado Pago si el cobro de renovación falla.
    GRACE_DAYS              =   5
    user                        =   models.OneToOneField(UserProfile, on_delete = models.CASCADE, related_name = 'suscription')
    plan_suscription            =   models.ForeignKey(SuscriptionPlan, on_delete = models.RESTRICT, verbose_name = 'Suscripción', db_index = False)
    pending_plan_suscription    =   models.ForeignKey(SuscriptionPlan, on_delete = models.SET_NULL, null = True, blank = True, related_name = 'pending_suscriptions', verbose_name = 'Plan pendiente de pago', db_index = False)
    start_date                  =   models.DateTimeField(default = timezone.now, verbose_name = 'Fecha de inicio')
    end_date                    =   models.DateTimeField(verbose_name = 'Fecha de caducidad')
    status                      =   models.CharField(default = 'Suscripción activa', max_length = 30, null = False, blank = False, verbose_name = 'Estado de suscripción')
    #DÉBITO AUTOMÁTICO (Mercado Pago preapproval): auto_renew queda activo mientras
    #la suscripción de MP esté authorized; cancelled_at marca la baja pedida por el cliente.
    auto_renew                  =   models.BooleanField(default = False, verbose_name = 'Renovación automática')
    preapproval_id              =   models.CharField(max_length = 64, null = True, blank = True, unique = True, verbose_name = 'Suscripción en Mercado Pago')
    cancelled_at                =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de baja de la renovación')
    objects                     =   SuscriptionQuerySet.as_manager()
    class Meta:
        app_label               =   'suscriptions'
        verbose_name            =   'Suscripción'
        verbose_name_plural     =   'Suscripciones'
        indexes                 =   [
            models.Index(fields = ['plan_suscription'], name = 'idx_suscription_plan'),
            models.Index(fields = ['pending_plan_suscription'], name = 'idx_suscription_pending_plan'),
        ]
        constraints             =   [
            models.UniqueConstraint(
                fields          =   ['user', 'plan_suscription'],
                name            =   'UniqueUserSuscriptionConstraint',
            )
        ]
    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date   =   self.start_date + timedelta(days = 30)
        super().save(*args, **kwargs)
        _bust_benefits_cache(self.user_id)
    #=========================================
    # ACCESS UNTIL (fin real del acceso, con gracia si hay débito automático)
    #=========================================
    def access_until(self):
        grace   =   timedelta(days = self.GRACE_DAYS) if self.auto_renew else timedelta(0)
        return (self.end_date or self.start_date) + grace
    #=========================================
    # GRANTS ACCESS (única fuente de verdad para el gating de beneficios)
    #=========================================
    def grants_access(self):
        return self.status == self.STATUS_ACTIVE and bool(self.end_date) and timezone.now() <= self.access_until()

from django.db.models.signals import post_delete
post_delete.connect(lambda sender, instance, **kwargs: _bust_benefits_cache(instance.user_id), sender = Suscription)
#=========================================
#COUPON MODEL
#=========================================
class Coupon(models.Model):
    #Código promocional canjeable: otorga `days` días del `plan` indicado.
    #max_uses=None = canjes ilimitados; expires_at=None = sin vencimiento.
    code                        =   models.CharField(max_length = 40, unique = True, verbose_name = 'Código')
    plan                        =   models.ForeignKey(SuscriptionPlan, on_delete = models.RESTRICT, verbose_name = 'Plan otorgado', db_index = False)
    days                        =   models.PositiveIntegerField(verbose_name = 'Días de acceso')
    max_uses                    =   models.PositiveIntegerField(null = True, blank = True, verbose_name = 'Máximo de canjes')
    expires_at                  =   models.DateTimeField(null = True, blank = True, verbose_name = 'Vencimiento')
    is_active                   =   models.BooleanField(default = True, verbose_name = 'Activo')
    created_at                  =   models.DateTimeField(auto_now_add = True, verbose_name = 'Fecha de creación')
    class Meta:
        app_label               =   'suscriptions'
        verbose_name            =   'Cupón'
        verbose_name_plural     =   'Cupones'
    def __str__(self):
        return self.code
#=========================================
#COUPON REDEMPTION MODEL (auditoría + un canje por usuario y cupón)
#=========================================
class CouponRedemption(models.Model):
    coupon                      =   models.ForeignKey(Coupon, on_delete = models.CASCADE, related_name = 'redemptions', verbose_name = 'Cupón')
    user                        =   models.ForeignKey(UserProfile, on_delete = models.CASCADE, related_name = 'coupon_redemptions', verbose_name = 'Usuario')
    suscription                 =   models.ForeignKey(Suscription, on_delete = models.SET_NULL, null = True, blank = True, related_name = 'coupon_redemptions', verbose_name = 'Suscripción')
    redeemed_at                 =   models.DateTimeField(auto_now_add = True, verbose_name = 'Fecha de canje')
    class Meta:
        app_label               =   'suscriptions'
        verbose_name            =   'Canje de cupón'
        verbose_name_plural     =   'Canjes de cupones'
        constraints             =   [
            models.UniqueConstraint(
                fields          =   ['coupon', 'user'],
                name            =   'UniqueCouponRedemptionConstraint',
            )
        ]
#=============================================

