from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from StoreApp.domains.stores.models import AiDesignEvent


class Command(BaseCommand):
    help = 'Poda los eventos de "Diseñar con IA" más viejos que la ventana de retención (default 365 días).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 365, help = 'Días de historial a conservar.')

    def handle(self, *args, **options):
        days    =   max(int(options['days']), 31)
        cutoff  =   timezone.now() - timedelta(days = days)
        deleted, _  =   AiDesignEvent.objects.filter(created_at__lt = cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Eventos podados: {deleted} filas anteriores a {cutoff:%Y-%m-%d}.'))
