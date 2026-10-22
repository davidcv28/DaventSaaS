"""
Servicios / queries del dominio Invoices.
La factura se emite al acreditarse el pago (APPROVED), dentro de la misma
transacción: el cobro se registra completo con su comprobante, o no se registra.
Al emitirse se envía al correo de la cuenta del cliente (post-commit: el mail
solo sale si el cobro quedó registrado; un fallo de mail no rompe la acreditación).
"""
import logging
from decimal import Decimal

from decouple import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.html import escape
from rest_framework import serializers

from AdminApp.domains.invoices.models import Invoice, TypeInvoice
from AdminApp.domains.payments.models import Payment

logger          =   logging.getLogger(__name__)
FRONTEND_URL    =   config('FRONTEND_URL', default = 'http://localhost:5173')

#=================================
# INVOICE HELPERS
#=================================
def DeriveInvoiceTypeQuery(tax_condition : str, issuer_condition : str = None) -> str:
    #El tipo depende de la condición fiscal del EMISOR (settings.INVOICE_ISSUER):
    #monotributo -> siempre Factura C; responsable inscripto -> A si el
    #comprador es RI, B en el resto de los casos.
    issuer  =   (issuer_condition or settings.INVOICE_ISSUER['tax_condition']).upper()
    if issuer == 'RI':
        return TypeInvoice.A if tax_condition == 'RI' else TypeInvoice.B
    return TypeInvoice.C

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
                invoice         =   Invoice.objects.create(
                    user            =   payment.user,
                    payment         =   payment,
                    type            =   invoice_type,
                    pos             =   pos,
                    number          =   number,
                    total           =   payment.amount,
                    issued_at       =   timezone.localdate(),
                )
                #EMAIL: se agenda post-commit — nunca se envía dentro de la
                #transacción (un rollback no debe haber notificado igual)
                transaction.on_commit(lambda : SendInvoiceEmailQuery(invoice))
                return invoice
        except IntegrityError:
            #CARRERA: si otro proceso emitió para este pago, se devuelve la existente;
            #si fue colisión de número (type, pos), se recalcula en el próximo intento
            existing            =   Invoice.objects.filter(payment = payment).first()
            if existing:
                return existing
            if attempt == 2:
                raise serializers.ValidationError({'invoice': 'Error al emitir la factura.'})

#=================================
# INVOICE EMAIL
#=================================
def _format_ars(value) -> str:
    #12,345.67 -> 12.345,67 (formato es-AR)
    return  f'${Decimal(value):,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')

#SEND INVOICE EMAIL QUERY (comprobante con presentación DAVENT al correo de la cuenta)
def SendInvoiceEmailQuery(invoice : Invoice) -> None:
    recipient       =   (invoice.user.user.email or '').strip()
    if not recipient:
        return
    issuer          =   settings.INVOICE_ISSUER
    comprobante     =   f'{invoice.pos:04d}-{invoice.number:08d}'
    type_label      =   invoice.get_type_display()
    plan_name       =   invoice.payment.suscription.plan_suscription.name
    customer        =   invoice.user.business_name or f'{invoice.user.first_name} {invoice.user.last_name}'.strip() or recipient
    total           =   _format_ars(invoice.total)
    issued          =   invoice.issued_at.strftime('%d/%m/%Y')
    invoice_url     =   f'{FRONTEND_URL}/facturas/{invoice.pk}'
    subject         =   f'Tu factura de DAVENT — {type_label} {comprobante}'
    body            =   (
        f'Hola {customer},\n\n'
        f'Ya emitimos el comprobante de tu último pago acreditado en DAVENT.\n\n'
        f'Comprobante     : {type_label} {comprobante}\n'
        f'Fecha de emisión: {issued}\n'
        f'Plan            : {plan_name}\n'
        f'Total           : {total}\n\n'
        f'Ver o imprimir tu factura: {invoice_url}\n'
        f'También está disponible en tu panel, sección Facturas.\n\n'
        f'{issuer["name"]} — {issuer["tagline"]}'
    )
    issuer_line     =   ' · '.join(filter(None, [
        escape(issuer['name']),
        f'CUIT {escape(issuer["cuit"])}' if issuer['cuit'] else '',
        escape(issuer['address']),
        escape(issuer['email']),
    ]))
    html            =   f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
        <tr>
          <td style="background:#4f46e5;padding:24px 32px;">
            <span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:.08em;">DAVENT</span><br />
            <span style="color:#c7d2fe;font-size:12px;">Plataforma de catálogos digitales</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h1 style="margin:0 0 8px;font-size:20px;line-height:1.3;">Tu factura ya está disponible</h1>
            <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#475569;">
              Hola {escape(customer)}, emitimos el comprobante de tu último pago acreditado.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:12px;font-size:14px;margin-bottom:24px;">
              <tr>
                <td style="padding:12px 16px;color:#64748b;border-bottom:1px solid #e2e8f0;">Comprobante</td>
                <td align="right" style="padding:12px 16px;font-weight:700;border-bottom:1px solid #e2e8f0;">{escape(type_label)} {comprobante}</td>
              </tr>
              <tr>
                <td style="padding:12px 16px;color:#64748b;border-bottom:1px solid #e2e8f0;">Fecha de emisión</td>
                <td align="right" style="padding:12px 16px;border-bottom:1px solid #e2e8f0;">{issued}</td>
              </tr>
              <tr>
                <td style="padding:12px 16px;color:#64748b;border-bottom:1px solid #e2e8f0;">Plan</td>
                <td align="right" style="padding:12px 16px;border-bottom:1px solid #e2e8f0;">{escape(plan_name)}</td>
              </tr>
              <tr>
                <td style="padding:12px 16px;color:#64748b;">Total</td>
                <td align="right" style="padding:12px 16px;font-size:17px;font-weight:700;color:#4f46e5;">{total}</td>
              </tr>
            </table>
            <p style="margin:0 0 20px;text-align:center;">
              <a href="{invoice_url}" style="display:inline-block;background:#4f46e5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:12px 28px;border-radius:10px;">Ver mi factura</a>
            </p>
            <p style="margin:0;font-size:12.5px;line-height:1.6;color:#64748b;">
              También podés verla e imprimirla desde tu panel, en la sección <strong>Facturas</strong>.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11.5px;line-height:1.6;color:#94a3b8;">
            {issuer_line}<br />
            Este correo se generó automáticamente; no respondas a esta dirección.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    try:
        mail            =   EmailMultiAlternatives(
            subject         =   subject,
            body            =   body,
            from_email      =   settings.DEFAULT_FROM_EMAIL,
            to              =   [recipient],
        )
        mail.attach_alternative(html, 'text/html')
        mail.send(fail_silently = False)
    except Exception:
        #La factura ya quedó emitida: un fallo de correo no rompe la acreditación
        logger.exception('No se pudo enviar por correo la factura %s', invoice.pk)
    
