from django.core.management import BaseCommand

from AdminApp.domains.suscriptions.services import SendSubscriptionNoticesQuery

"""

Mails automáticos de estado de cuenta: avisa cuando el acceso está por
vencer (<=3 días) y cuando acaba de vencer, una sola vez por período.
Pensado para cron diario en el host:

  30 8 * * *  cd /opt/davent && docker compose exec -T api python manage.py subscription_notices

  --dry-run lista los candidatos sin enviar ni registrar el aviso.

"""


class Command(BaseCommand):
    help = 'Envía los avisos de vencimiento/vencido de suscripción (idempotente por período).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action = 'store_true',
                            help = 'Muestra quién recibiría aviso sin enviar mails ni registrarlos.')

    def handle(self, *args, **options):
        result  =   SendSubscriptionNoticesQuery(dry_run = options['dry_run'])
        sent    =   result['sent']
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN: {sent['ending']} por vencer, {sent['expired']} vencidos"
            ))
            for pk, kind, email in result['candidates']:
                self.stdout.write(f'  suscription={pk} {kind:<7} {email}')
            return
        self.stdout.write(self.style.SUCCESS(
            f"Avisos enviados: {sent['ending']} por vencer, {sent['expired']} vencidos"
        ))
