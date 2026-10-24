"""
Modelos del dominio invoices.
Invoice es el comprobante fiscal de un Payment aprobado (un cobro = una factura).
"""
from django.db import models

from AdminApp.domains.payments.models import Payment
from AdminApp.domains.users.models    import UserProfile

#=========================================
# INVOICE TYPE
#=========================================
class TypeInvoice(models.TextChoices):
    A   =   'A', 'Factura A'
    B   =   'B', 'Factura B'
    C   =   'C', 'Factura C'

#=========================================
# INVOICE MODEL
#=========================================
class Invoice(models.Model):
    class AfipStatus(models.TextChoices):
        #DISABLED: emitida con la integración apagada (o pre-AFIP) — nunca va a
        #tener CAE. PENDING: a la espera del request post-commit. PROCESSING:
        #claim optimista contra dobles pedidos. OK: CAE otorgado. ERROR:
        #rechazo/caída de ARCA — reintentable por /invoices-admin/<id>/retry-cae/.
        DISABLED    =   'disabled', 'Sin integración ARCA'
        PENDING     =   'pending', 'CAE pendiente'
        PROCESSING  =   'processing', 'Solicitando CAE'
        OK          =   'ok', 'CAE otorgado'
        ERROR       =   'error', 'Error ARCA'

    user        =   models.ForeignKey(UserProfile, on_delete = models.PROTECT, related_name = 'invoices', db_index = False)
    payment     =   models.OneToOneField(Payment, on_delete = models.PROTECT, related_name = 'invoice')
    type        =   models.CharField(max_length = 1, choices = TypeInvoice.choices, verbose_name = 'Tipo de factura')
    pos         =   models.PositiveSmallIntegerField(default = 1, verbose_name = 'Punto de venta')
    number      =   models.PositiveIntegerField(verbose_name = 'Número de comprobante')
    total       =   models.DecimalField(max_digits = 12, decimal_places = 2, verbose_name = 'Total')
    issued_at   =   models.DateField(verbose_name = 'Fecha de emisión')
    #ARCA (ex-AFIP): fiscal_number es el CbteDesde que otorga WSFE — puede
    #diferir del interno `number` cuando una factura se emite con ARCA caído
    #y pide el CAE después (el correlativo fiscal no admite huecos).
    fiscal_number   =   models.PositiveIntegerField(null = True, blank = True, verbose_name = 'Número fiscal ARCA')
    cae             =   models.CharField(max_length = 20, blank = True, default = '', verbose_name = 'CAE')
    cae_due         =   models.DateField(null = True, blank = True, verbose_name = 'Vencimiento del CAE')
    afip_status     =   models.CharField(max_length = 12, choices = AfipStatus.choices, default = AfipStatus.DISABLED, verbose_name = 'Estado ARCA')
    afip_error      =   models.CharField(max_length = 500, blank = True, default = '', verbose_name = 'Último error de ARCA')
    created_at  =   models.DateTimeField(auto_now_add = True)
    updated_at  =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'invoices'
        verbose_name        =   'Factura'
        verbose_name_plural =   'Facturas'
        ordering            =   ['-created_at']
        indexes             =   [
            models.Index(fields = ['user', 'created_at'], name = 'idx_invoice_user_created'),
        ]
        constraints         =   [
            models.UniqueConstraint(
                fields      =   ['type', 'pos', 'number'],
                name        =   'unique_invoice_type_pos_number',
            ),
        ]

    def __str__(self):
        return f'{self.type} {self.pos:04d}-{self.number:08d} - {self.user}'
