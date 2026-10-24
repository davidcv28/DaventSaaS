from datetime import datetime, timedelta

from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Coupon, SuscriptionPlan

"""

Creamos un script para generar/actualizar cupones promocionales

Uso:
    manage.py create_coupon --code FLYER7 --plan "Plan premium" --days 7
    manage.py create_coupon --code FLYER7 --plan "Plan premium" --days 7 --max-uses 10 --expires 2026-12-31
    manage.py create_coupon --code FLYER7 --deactivate

"""
#=========================================
# CREATE COUPON
#=========================================
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--code', required = True, help = 'Código canjeable (case-insensitive)')
        parser.add_argument('--plan', help = 'Nombre exacto del plan a otorgar')
        parser.add_argument('--days', type = int, default = 7, help = 'Días de acceso otorgados (default 7)')
        parser.add_argument('--max-uses', type = int, default = None, help = 'Máximo de canjes (default ilimitado)')
        parser.add_argument('--expires', help = 'Vencimiento ISO YYYY-MM-DD (default sin vencimiento)')
        parser.add_argument('--deactivate', action = 'store_true', help = 'Marca el cupón como inactivo')
    def handle(self, *args, **options):
        code            =   options['code'].strip().upper()
        coupon          =   Coupon.objects.filter(code__iexact = code).first()
        if options['deactivate']:
            if coupon is None:
                raise CommandError(f'El cupón {code} no existe.')
            coupon.is_active = False
            coupon.save(update_fields = ['is_active'])
            self.stdout.write(self.style.SUCCESS(f'CUPÓN {code} DESACTIVADO'))
            return
        if not options['plan']:
            raise CommandError('Indicá --plan (o usá --deactivate para darlo de baja).')
        plan            =   SuscriptionPlan.objects.filter(name = options['plan']).first()
        if plan is None:
            raise CommandError(f'No existe el plan "{options["plan"]}". Corré manage.py suscriptions para cargarlos.')
        if plan.is_trial:
            raise CommandError('El plan de prueba no se puede usar en cupones.')
        expires_at      =   None
        if options['expires']:
            try:
                expires_at  =   timezone.make_aware(
                    datetime.strptime(options['expires'], '%Y-%m-%d') + timedelta(days = 1)
                )
            except ValueError:
                raise CommandError('Fecha inválida: usá el formato YYYY-MM-DD.')
        coupon, created =   Coupon.objects.update_or_create(
            code            =   code,
            defaults        =   {
                'plan'          :   plan,
                'days'          :   options['days'],
                'max_uses'      :   options['max_uses'],
                'expires_at'    :   expires_at,
                'is_active'     :   True,
            },
        )
        uses_label      =   options['max_uses'] if options['max_uses'] is not None else 'ilimitados'
        expires_label   =   expires_at.date().isoformat() if expires_at else 'sin vencimiento'
        verb            =   'CREADO' if created else 'ACTUALIZADO'
        self.stdout.write(self.style.SUCCESS(
            f'CUPÓN {code} {verb}: {plan.name} x {options["days"]} días, {uses_label} canjes, {expires_label}'
        ))
