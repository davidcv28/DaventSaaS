from datetime import timedelta

from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Suscription

"""

Extiende el plan de prueba de una cuenta (soporte): suma días al end_date
de la suscripción trial, contando desde hoy si ya venció. No cambia el
plan ni la duración estándar (TRIAL_DAYS) — es una excepción por cuenta.

  manage.py extend_trial usuario@mail.com [--days 3]

"""


class Command(BaseCommand):
    help = 'Extiende N días el plan de prueba de una cuenta (por email).'

    def add_arguments(self, parser):
        parser.add_argument('email', help = 'Email de la cuenta (auth user).')
        parser.add_argument('--days', type = int, default = 1, help = 'Días a sumar (default: 1).')

    def handle(self, *args, **options):
        days    =   options['days']
        if days < 1:
            raise CommandError('--days debe ser >= 1.')
        suscription =   Suscription.objects.select_related('user__user', 'plan_suscription').filter(
            user__user__email__iexact   =   options['email'],
            plan_suscription__is_trial  =   True,
        ).first()
        if suscription is None:
            raise CommandError(f'No hay suscripción trial para "{options["email"]}".')
        base                    =   max(suscription.end_date, timezone.now())
        suscription.end_date    =   base + timedelta(days = days)
        suscription.save(update_fields = ['end_date'])
        self.stdout.write(self.style.SUCCESS(
            f'Trial de {options["email"]} extendido hasta {suscription.end_date:%Y-%m-%d %H:%M} UTC (+{days}d).'
        ))
