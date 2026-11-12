"""
Reintenta las bajas de débito automático que quedaron pendientes.

``cancel_renewal`` persiste ``cancel_requested_at`` ANTES de llamar a MP:
si el update remoto falla (timeout, 5xx) la intención sobrevive y este
comando la concreta llamando ``CancelPreapprovalQuery`` de nuevo. Sin él,
una baja fallida era indistinguible de "nunca se pidió" y el preapproval
seguía debitando en silencio.

Uso (cron diario recomendado):
    manage.py reconcile_preapprovals [--dry-run]
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Suscription

logger      =   logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reintenta las bajas de débito automático pendientes de confirmación en Mercado Pago.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action = 'store_true', help = 'Lista candidatos sin llamar a MP ni escribir.')

    def handle(self, *args, **options):
        #Import perezoso: no instanciar el SDK al cargar el comando.
        from AdminApp.domains.payments.services.services import CancelPreapprovalQuery
        candidates   =   (
            Suscription.objects
            .filter(cancel_requested_at__isnull = False)
            .exclude(preapproval_id__isnull = True)
            .exclude(preapproval_id = '')
            .order_by('cancel_requested_at')
        )
        dry_run      =   options['dry_run']
        ok           =   0
        failed       =   0
        for suscription in candidates:
            if dry_run:
                self.stdout.write(
                    f'  suscripción={suscription.pk} preapproval={suscription.preapproval_id} '
                    f'baja pedida={suscription.cancel_requested_at:%Y-%m-%d %H:%M}'
                )
                continue
            try:
                with transaction.atomic():
                    locked  =   Suscription.objects.select_for_update(of = ('self',)).get(pk = suscription.pk)
                    if locked.cancel_requested_at is None:
                        continue
                    CancelPreapprovalQuery(locked)
                ok      +=  1
                logger.info('reconcile_preapprovals: baja confirmada suscripción=%s', suscription.pk)
            except Exception as exc:
                failed  +=  1
                logger.warning('reconcile_preapprovals: reintento falló suscripción=%s: %s', suscription.pk, exc)
        if dry_run:
            self.stdout.write(f'Candidatos a reconciliar: {candidates.count()} (dry-run, sin cambios).')
        else:
            self.stdout.write(f'Bajas reconciliadas: {ok} · pendientes: {failed} · procesadas: {candidates.count()}')
            if failed:
                logger.warning('reconcile_preapprovals: %s bajas siguen pendientes', failed)
