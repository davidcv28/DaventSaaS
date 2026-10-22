
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
#=============================================

   