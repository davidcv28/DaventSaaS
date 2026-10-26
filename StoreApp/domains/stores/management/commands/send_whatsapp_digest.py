from django.core.management import BaseCommand
from StoreApp.domains.stores.services import send_daily_digests
"""

Envía el resumen diario de WhatsApp a los perfiles con opt-in y beneficio.
Idempotente (sent_at <20h = ya enviado) — safe correrlo desde celery beat,
el cron de Render o a mano:

    manage.py send_whatsapp_digest
    manage.py send_whatsapp_digest --dry-run   # qué enviaría, sin mandar

"""
#=========================================
# SEND WHATSAPP DIGEST (job diario)
#=========================================
class Command(BaseCommand):
    help    =   'Envía el resumen diario de la tienda por WhatsApp (opt-in + plan premium)'
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action = 'store_true', help = 'Reporta sin enviar ni marcar sent_at')
    def handle(self, *args, **options):
        if options['dry_run']:
            #dry-run sin tocar Meta ni la DB: cuenta elegibles con la misma regla
            from datetime import timedelta
            from django.utils import timezone
            from AdminApp.domains.users.models import UserProfile
            from StoreApp.domains.stores.services import profile_has_benefit
            now         =   timezone.now()
            eligible    =   [
                            p for p in UserProfile.objects
                                .filter(whatsapp_digest = True)
                                .exclude(phone__isnull = True).exclude(phone = '')
                                .select_related('store', 'suscription__plan_suscription')
                            if (not p.whatsapp_digest_sent_at or now - p.whatsapp_digest_sent_at >= timedelta(hours = 20))
                               and profile_has_benefit(p, 'has_whatsapp_digest')
                               and getattr(p, 'store', None) is not None
                            ]
            self.stdout.write(f'{len(eligible)} resumen(es) por enviar')
            for p in eligible:
                self.stdout.write(f'  -> {p.user.email} ({p.phone})')
            return
        stats   =   send_daily_digests()
        self.stdout.write(self.style.SUCCESS(f"WhatsApp digest: {stats['sent']} enviados, {stats['skipped']} saltados, {stats['failed']} fallidos"))
