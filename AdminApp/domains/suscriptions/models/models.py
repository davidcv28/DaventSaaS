from email import message
from os import name

from attr import fields
from django.contrib.postgres import constraints
from django.db import models
from rest_framework import status
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
    name                        =   models.CharField(max_length = 60, null = False, blank = False, unique = True)
    price                       =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0.00, blank = False, null = False, verbose_name = 'Precio suscripción')
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
    user                        =   models.OneToOneField(UserProfile, on_delete = models.CASCADE, related_name = 'suscription')
    plan_suscription            =   models.ForeignKey(SuscriptionPlan, on_delete = models.RESTRICT, verbose_name = 'Suscripción', db_index = False)
    pending_plan_suscription    =   models.ForeignKey(SuscriptionPlan, on_delete = models.SET_NULL, null = True, blank = True, related_name = 'pending_suscriptions', verbose_name = 'Plan pendiente de pago', db_index = False)
    start_date                  =   models.DateTimeField(default = timezone.now, verbose_name = 'Fecha de inicio')
    end_date                    =   models.DateTimeField(verbose_name = 'Fecha de caducidad')
    status                      =   models.CharField(default = 'Suscripción activa', max_length = 30, null = False, blank = False, verbose_name = 'Estado de suscripción')
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
#=============================================

   