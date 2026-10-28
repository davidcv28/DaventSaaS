"""
Detecta cobros huérfanos de Mercado Pago (residual W-5).

Un cobro huérfano es un pago ``approved`` en MP que no tiene fila local en
``Payment`` — típicamente el débito que MP ejecutó en la ventana entre el
canje de un cupón y la baja efectiva del preapproval. El comando SOLO lista
y loguea: no acredita, no crea ``Payment`` ni toca suscripciones. La
reconciliación es manual (panel de MP + decisión del operador).

Uso:
    manage.py audit_orphan_payments [--days 30] [--include-test] [--json]
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.utils import timezone

from AdminApp.domains.payments.models import Payment
from AdminApp.domains.suscriptions.models import Suscription

logger      =   logging.getLogger(__name__)
PAGE_SIZE   =   50
MAX_PAGES   =   40


class Command(BaseCommand):
    help = 'Lista cobros approved de Mercado Pago sin registro local (solo lectura, no acredita).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 30, help = 'Ventana hacia atrás en días (default 30).')
        parser.add_argument('--include-test', action = 'store_true', help = 'Incluye pagos con live_mode=False.')
        parser.add_argument('--json', action = 'store_true', help = 'Salida JSON (para alertas).')

    def handle(self, *args, **options):
        #Import perezoso: no instanciar el SDK al cargar el comando (help,
        #autocomplete) — sin SECRET_MP_KEY el import explotaría.
        from AdminApp.domains.payments.services.services import sdk
        days        =   max(1, min(options['days'], 365))
        now         =   timezone.now()
        base        =   {
            'sort'          :   'date_created',
            'criteria'      :   'desc',
            'limit'         :   PAGE_SIZE,
            'status'        :   'approved',
            'begin_date'    :   (now - timedelta(days = days)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end_date'      :   now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        orphans     =   []
        seen        =   0
        for page in range(MAX_PAGES):
            result  =   sdk.payment().search({**base, 'offset': page * PAGE_SIZE})
            if result.get('status') != 200:
                self.stderr.write(f'Mercado Pago respondió {result.get("status")}: se corta la auditoría.')
                logger.error('audit_orphan_payments: MP status=%s', result.get('status'))
                break
            results =   (result.get('response') or {}).get('results') or []
            seen    +=  len(results)
            for mp_payment in results:
                if mp_payment.get('live_mode') is False and not options['include_test']:
                    continue
                orphan =   self._classify(mp_payment)
                if orphan:
                    orphans.append(orphan)
            if len(results) < PAGE_SIZE:
                break
        payload =   {'days': days, 'scanned': seen, 'orphans': orphans}
        if options['json']:
            self.stdout.write(json.dumps(payload, ensure_ascii = False))
        else:
            self.stdout.write(f'Pagos aprobados revisados: {seen} · huérfanos: {len(orphans)}')
            for item in orphans:
                self.stdout.write(
                    f'  MP #{item["payment_id"]} · {item["amount"]} {item["currency"]} · '
                    f'fecha {item["date"]} · suscripción {item["suscription_id"]} · {item["reason"]}'
                )
        if orphans:
            logger.warning('audit_orphan_payments: %s cobros sin registro local (ventana %sd)', len(orphans), days)
        return None

    def _classify(self, mp_payment):
        """Devuelve el dict del huérfano o None si el pago está registrado."""
        payment_id  =   str(mp_payment.get('id') or '')
        if not payment_id:
            return None
        if Payment.objects.filter(external_reference = payment_id).exists():
            return None
        suscription_id  =   str(mp_payment.get('external_reference') or '')
        suscription     =   Suscription.objects.filter(pk = suscription_id).first() if suscription_id.isdigit() else None
        if suscription is None:
            reason  =   'external_reference no corresponde a ninguna suscripción local'
        else:
            reason  =   f'monto/plan no acreditado localmente (suscripción #{suscription_id})'
        try:
            amount  =   str(Decimal(str(mp_payment.get('transaction_amount') or 0)).quantize(Decimal('0.01')))
        except (InvalidOperation, ValueError):
            amount  =   str(mp_payment.get('transaction_amount') or '')
        return {
            'payment_id'        :   payment_id,
            'amount'            :   amount,
            'currency'          :   mp_payment.get('currency_id') or '',
            'date'              :   str(mp_payment.get('date_approved') or mp_payment.get('date_created') or '')[:19],
            'suscription_id'    :   suscription_id or None,
            'live_mode'         :   mp_payment.get('live_mode'),
            'reason'            :   reason,
        }
