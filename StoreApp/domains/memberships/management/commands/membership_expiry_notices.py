"""
Aviso de membresía de tienda por vencer (e-commerce DAVENT — track F).

Lista las StoreSubscription 'active' con `vigente_hasta` dentro de los
próximos `--days` días (default 3), claimed por fila y encola el mail
al cliente por Celery (`send_membership_expiry_notice` →
services/mails.py). Pensado para cron diario en el host:

  30 8 * * *  cd /opt/davent && docker compose exec -T api python manage.py membership_expiry_notices

Idempotencia: `expiry_notified_until` guarda el `vigente_hasta` ya
avisado — el claim es un UPDATE condicional (solo una corrida gana la
fila), así dos corridas simultáneas o repetidas no duplican mails; si
la suscripción se renueva (vigente_hasta cambia) vuelve a avisar.

  --days N      ventana de aviso en días (default 3, mínimo 1).
  --dry-run     lista los candidatos sin marcar ni encolar nada.
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from StoreApp.domains.customers.models import StoreMembership
from StoreApp.domains.memberships.models import StoreSubscription

logger  =   logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Avisa por email a los clientes cuya membresía de tienda vence en los próximos N días (idempotente por vigencia).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 3,
                            help = 'Días de anticipación del aviso (default 3).')
        parser.add_argument('--dry-run', action = 'store_true',
                            help = 'Lista los candidatos sin marcar ni enviar mails.')

    def handle(self, *args, **options):
        dry_run     =   options['dry_run']
        days        =   max(1, int(options['days']))
        now         =   timezone.now()
        window_end  =   now + timedelta(days = days)
        candidates  =   (
            StoreSubscription.objects
            .filter(
                status              =   StoreSubscription.STATUS_ACTIVE,
                vigente_hasta__gt   =   now,
                vigente_hasta__lte  =   window_end,
                #Una membresía suspendida o una cuenta inactiva no reciben
                #avisos (los beneficios ya están cortados para ellos).
                membership__status      =   StoreMembership.STATUS_ACTIVE,
                membership__customer__is_active = True,
            )
            .exclude(vigente_hasta__isnull = True)
            .select_related('plan', 'membership__customer', 'membership__store')
            .order_by('vigente_hasta', 'pk')
        )
        sent    =   0
        skipped =   0
        listed  =   []
        for sub in candidates.iterator():
            email   =   (getattr(getattr(sub.membership, 'customer', None), 'email', '') or '').strip()
            if not email:
                skipped  +=  1
                continue
            #Ya avisado por ESTA vigencia → no es candidato (el dry-run
            #refleja lo que realmente se enviaría, no la ventana entera).
            if sub.expiry_notified_until is not None and sub.expiry_notified_until == sub.vigente_hasta:
                skipped  +=  1
                continue
            if dry_run:
                listed.append((sub.pk, email, sub.vigente_hasta))
                continue
            #Claim atómico por fila: solo el UPDATE que efectivamente
            #cambia expiry_notified_until encola el mail — una segunda
            #corrida (o un retry del cron) no duplica el envío.
            claimed =   (
                StoreSubscription.objects
                .filter(pk = sub.pk)
                .filter(Q(expiry_notified_until__isnull = True) | ~Q(expiry_notified_until = sub.vigente_hasta))
                .update(expiry_notified_until = sub.vigente_hasta, updated_at = now)
            )
            if not claimed:
                skipped  +=  1
                continue
            try:
                self._enqueue(sub.pk)
            except Exception:                                   # noqa: BLE001 — el claim se revierte para reintentar mañana
                logger.exception('membership_expiry_notices: encolado falló (subscription=%s)', sub.pk)
                StoreSubscription.objects.filter(pk = sub.pk).update(expiry_notified_until = None)
                continue
            sent    +=  1
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY-RUN: {len(listed)} suscripción(es) por avisar en {days} día(s)'
            ))
            for pk, email, until in listed:
                self.stdout.write(f'  subscription={pk} vence={until:%Y-%m-%d %H:%M} {email}')
            return
        self.stdout.write(self.style.SUCCESS(
            f'Avisos de membresía encolados: {sent} (saltados: {skipped})'
        ))

    def _enqueue(self, subscription_id):
        """Encola la task Celery (import perezoso — celery solo si hace falta)."""
        from StoreApp.domains.memberships.tasks import send_membership_expiry_notice
        send_membership_expiry_notice.delay(subscription_id)
