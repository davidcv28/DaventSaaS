"""
Servicios / queries del dominio Invoices.
La factura se emite al acreditarse el pago (APPROVED), dentro de la misma
transacción: el cobro se registra completo con su comprobante, o no se registra.
"""

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import serializers

from AdminApp.domains.invoices.models import Invoice, TypeInvoice
from AdminApp.domains.payments.models import Payment

#=================================
# INVOICE HELPERS
#=================================
def DeriveInvoiceTypeQuery(tax_condition : str) -> str:
    return TypeInvoice.A if tax_condition == 'RI' else TypeInvoice.B

#=================================
# INVOICE MODEL QUERYS
#=================================

#ISSUE INVOICE QUERY (emite la factura de un pago aprobado; idempotente)
def IssueInvoiceQuery(payment, pos : int = 1) -> Invoice:
    if payment.status != Payment.Status.APPROVED:
        raise serializers.ValidationError({'payment': 'Solo se pueden emitir facturas para pagos aprobados.'})
    existing            =   Invoice.objects.filter(payment = payment).first()
    if existing:
        return existing
    invoice_type        =   DeriveInvoiceTypeQuery(payment.user.tax_condition)
    for attempt in range(3):
        try:
            with transaction.atomic():
                last_invoice    =   Invoice.objects.select_for_update().filter(type = invoice_type, pos = pos).order_by('-number').first()
                number          =   last_invoice.number + 1 if last_invoice else 1
                return Invoice.objects.create(
                    user            =   payment.user,
                    payment         =   payment,
                    type            =   invoice_type,
                    pos             =   pos,
                    number          =   number,
                    total           =   payment.amount,
                    issued_at       =   timezone.localdate(),
                )
        except IntegrityError:
            #CARRERA: si otro proceso emitió para este pago, se devuelve la existente;
            #si fue colisión de número (type, pos), se recalcula en el próximo intento
            existing            =   Invoice.objects.filter(payment = payment).first()
            if existing:
                return existing
            if attempt == 2:
                raise serializers.ValidationError({'invoice': 'Error al emitir la factura.'})
    
