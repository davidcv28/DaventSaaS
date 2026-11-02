from datetime import timedelta

from decouple import config
from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Suscription

"""

Leads de conversión: lista las cuentas cuyo plan de prueba venció hace
poco (o está por vencer), con email y fecha — el trial no es reactivable,
así que la única vía de retener al usuario es el contacto/winback.

  manage.py trial_leads                 # vencidos en los últimos 30 días
  manage.py trial_leads --days 7
  manage.py trial_leads --pending       # trial aún vigente
  manage.py trial_leads --notify        # manda el mail de winback a cada uno

"""

WINBACK_SUBJECT =   'Tu web de DAVENT te está esperando'
WINBACK_BODY    =   (
    'Hola{first_name},\n\n'
    'Tu período de prueba en DAVENT terminó, pero tu web sigue guardada.\n'
    'Elegí un plan y volvé a publicarla en minutos: {site_url}\n\n'
    'Cualquier duda respondé este correo.\n\n'
    '— El equipo de DAVENT'
)


class Command(BaseCommand):
    help = 'Lista cuentas con plan de prueba vencido (leads de winback).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type = int, default = 30,
                            help = 'Ventana en días hacia atrás (default: 30).')
        parser.add_argument('--pending', action = 'store_true',
                            help = 'Listar trials aún vigentes en vez de vencidos.')
        parser.add_argument('--notify', action = 'store_true',
                            help = 'Enviar el mail de winback a cada cuenta listada.')

    def handle(self, *args, **options):
        now     =   timezone.now()
        qs      =   Suscription.objects.select_related('user__user', 'plan_suscription').filter(
            plan_suscription__is_trial = True,
        ).order_by('-end_date')
        if options['pending']:
            qs  =   qs.filter(end_date__gt = now)
        else:
            qs  =   qs.filter(end_date__lte = now, end_date__gte = now - timedelta(days = options['days']))
        site_url    =   config('PLATFORM_URL', default = 'https://davent.app').rstrip('/')
        sent        =   0
        for suscription in qs:
            user    =   suscription.user
            email   =   getattr(user.user, 'email', '') or ''
            state   =   'vigente' if suscription.end_date > now else 'vencido'
            self.stdout.write(
                f'{email:<40} {state:<9} {suscription.end_date:%Y-%m-%d} '
                f'(alta {suscription.start_date:%Y-%m-%d})'
            )
            if options['notify'] and email:
                send_mail(
                    WINBACK_SUBJECT,
                    WINBACK_BODY.format(
                        first_name  =   f' {user.first_name}' if user.first_name else '',
                        site_url    =   site_url,
                    ),
                    None,
                    [email],
                    fail_silently = False,
                )
                sent    +=  1
        total   =   qs.count()
        self.stdout.write(self.style.SUCCESS(f'{total} trial(s) listados' + (f', {sent} mail(s) enviados' if options['notify'] else '')))
