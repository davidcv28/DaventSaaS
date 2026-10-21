from django.db import models
from AdminApp.domains.suscriptions.models import SuscriptionPlan
"""

Beneficios de los planes de suscripción.
El catálogo de beneficios (Benefit) se asigna a cada plan con un valor
concreto (PlanBenefit). PlanPresentation guarda el copy de marketing
que muestran las tarjetas del frontend.

"""
#=========================================
# BENEFIT MODEL (catálogo de beneficios)
#=========================================
class Benefit(models.Model):
    LIMIT                       =   'limit'
    FLAG                        =   'flag'
    KIND_CHOICES                =   [
        (LIMIT, 'Límite numérico'),
        (FLAG,  'Característica'),
    ]
    code                        =   models.CharField(max_length = 40, unique = True)
    label                       =   models.CharField(max_length = 120)
    kind                        =   models.CharField(max_length = 10, choices = KIND_CHOICES, default = FLAG)
    class Meta:
        app_label               =   'benefits'
        verbose_name            =   'Beneficio'
        verbose_name_plural     =   'Beneficios'
    def __str__(self):
        return self.code
#=========================================
# PLAN BENEFIT MODEL (valor del beneficio por plan)
#=========================================
class PlanBenefit(models.Model):
    plan                        =   models.ForeignKey(SuscriptionPlan, on_delete = models.CASCADE, related_name = 'benefits', verbose_name = 'Plan', db_index = False)
    benefit                     =   models.ForeignKey(Benefit, on_delete = models.CASCADE, related_name = 'plan_values', verbose_name = 'Beneficio', db_index = False)
    value                       =   models.IntegerField(null = True, blank = True, verbose_name = 'Valor')
    enabled                     =   models.BooleanField(default = False, verbose_name = 'Habilitado')
    class Meta:
        app_label               =   'benefits'
        verbose_name            =   'Beneficio de plan'
        verbose_name_plural     =   'Beneficios de planes'
        indexes                 =   [
            models.Index(fields = ['benefit'], name = 'idx_planbenefit_benefit'),
        ]
        constraints             =   [
            models.UniqueConstraint(
                fields          =   ['plan', 'benefit'],
                name            =   'UniquePlanBenefitConstraint',
            )
        ]
    def __str__(self):
        return f'{self.plan.name} - {self.benefit.code}'
#=========================================
# PLAN PRESENTATION MODEL (copy de marketing)
#=========================================
class PlanPresentation(models.Model):
    plan                        =   models.OneToOneField(SuscriptionPlan, on_delete = models.CASCADE, related_name = 'presentation', verbose_name = 'Plan')
    slug                        =   models.SlugField(max_length = 60, unique = True)
    tagline                     =   models.CharField(max_length = 120, blank = True, verbose_name = 'Tagline')
    cta_label                   =   models.CharField(max_length = 60, blank = True, verbose_name = 'Texto del botón')
    bullets                     =   models.JSONField(default = list, blank = True, verbose_name = 'Ventajas visibles')
    featured                    =   models.BooleanField(default = False, verbose_name = 'Destacado')
    display_order               =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden de muestra')
    class Meta:
        app_label               =   'benefits'
        verbose_name            =   'Presentación de plan'
        verbose_name_plural     =   'Presentaciones de planes'
    def __str__(self):
        return f'{self.plan.name} ({self.slug})'
