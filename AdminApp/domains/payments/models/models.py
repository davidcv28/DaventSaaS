"""
Modelos del dominio payments.
Payment registra cada cobro individual (fuente de verdad del dinero entrante).
DailyRevenue / MonthlyRevenue son rollups materializados para dashboards.
"""

from django.db import models
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Suscription
from AdminApp.domains.users.models import UserProfile

#=========================================
# PAYMENT MODEL
#=========================================
class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING                     =   'pending', 'Pendiente'
        APPROVED                    =   'approved', 'Aprobado'
        REJECTED                    =   'rejected', 'Rechazado'
        REFUNDED                    =   'refunded', 'Reembolsado'

    user                        =   models.ForeignKey(UserProfile, on_delete = models.PROTECT, related_name = 'payments', db_index = False)
    suscription                 =   models.ForeignKey(Suscription, on_delete = models.PROTECT, related_name = 'payments', db_index = False)
    amount                      =   models.DecimalField(max_digits = 12, decimal_places = 2, verbose_name = 'Monto')
    currency                    =   models.CharField(max_length = 3, default = 'ARS', verbose_name = 'Moneda')
    status                      =   models.CharField(max_length = 20, choices = Status.choices, default = Status.PENDING, verbose_name = 'Estado')
    external_reference          =   models.CharField(max_length = 255, unique = True, blank = True, null = True, verbose_name = 'Referencia externa (Mercado Pago)')
    #Trazabilidad del origen del cobro: live_mode=False marca un pago hecho
    #con credenciales TEST de MP — en producción se rechaza antes de acreditar.
    live_mode                   =   models.BooleanField(null = True, blank = True, verbose_name = 'Cobro real (live) de Mercado Pago')
    mp_status_detail            =   models.CharField(max_length = 255, blank = True, default = '', verbose_name = 'Detalle de estado de Mercado Pago')
    paid_at                     =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de pago')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    updated_at                  =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label               =   'payments'
        verbose_name            =   'Pago'
        verbose_name_plural     =   'Pagos'
        indexes                 =   [
            models.Index(fields = ['status', 'paid_at'], name = 'idx_payment_status_paidat'),
            models.Index(fields = ['user'], name = 'idx_payment_user'),
            models.Index(fields = ['suscription'], name = 'idx_payment_suscription'),
        ]
        constraints             =   [
            models.CheckConstraint(
                condition       =   models.Q(amount__gte = 0),
                name            =   'payment_amount_non_negative',
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.amount} - {self.status}'

    def approve(self):
        """Marca el pago como aprobado y sella la fecha efectiva de cobro."""
        self.status             =   self.Status.APPROVED
        self.paid_at            =   timezone.now()
        self.save(update_fields = ['status', 'paid_at', 'updated_at'])

#=========================================
# DAILY REVENUE MODEL
#=========================================
class DailyRevenue(models.Model):
    date                        =   models.DateField(unique = True, verbose_name = 'Fecha')
    total_amount                =   models.DecimalField(max_digits = 14, decimal_places = 2, default = 0, verbose_name = 'Monto total del día')
    payments_count              =   models.PositiveIntegerField(default = 0, verbose_name = 'Cantidad de pagos')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    updated_at                  =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label               =   'payments'
        verbose_name            =   'Ingreso diario'
        verbose_name_plural     =   'Ingresos diarios'
        ordering                =   ['-date']

    def __str__(self):
        return f'{self.date} - {self.total_amount}'

#=========================================
# MONTHLY REVENUE MODEL
#=========================================
class MonthlyRevenue(models.Model):
    year                        =   models.PositiveIntegerField(verbose_name = 'Año')
    month                       =   models.PositiveSmallIntegerField(verbose_name = 'Mes')
    total_amount                =   models.DecimalField(max_digits = 14, decimal_places = 2, default = 0, verbose_name = 'Monto total del mes')
    payments_count              =   models.PositiveIntegerField(default = 0, verbose_name = 'Cantidad de pagos')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    updated_at                  =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label               =   'payments'
        verbose_name            =   'Ingreso mensual'
        verbose_name_plural     =   'Ingresos mensuales'
        ordering                =   ['-year', '-month']
        constraints             =   [
            models.UniqueConstraint(
                fields          =   ['year', 'month'],
                name            =   'UniqueYearMonthRevenueConstraint',
            ),
            models.CheckConstraint(
                condition       =   models.Q(month__gte = 1, month__lte = 12),
                name            =   'monthly_revenue_month_range',
            ),
        ]

    def __str__(self):
        return f'{self.year}-{self.month:02d} - {self.total_amount}'
