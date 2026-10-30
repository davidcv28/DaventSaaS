from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from StoreApp.domains.stores.models import StoreDailyVisit


class Command(BaseCommand):
    help = 'Poda las visitas diarias más viejas que la ventana de retención (default 730 días).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 730, help = 'Días de historial a conservar.')

    def handle(self, *args, **options):
        days    =   max(int(options['days']), 31)
        cutoff  =   timezone.localdate() - timedelta(days = days)
        deleted, _  =   StoreDailyVisit.objects.filter(date__lt = cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Visitas podadas: {deleted} filas anteriores a {cutoff}.'))
