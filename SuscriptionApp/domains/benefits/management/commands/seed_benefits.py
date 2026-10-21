from django.core.management import BaseCommand
from .seeds import dict_benefits, dict_plan_benefits
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit, PlanPresentation
from AdminApp.domains.suscriptions.models import SuscriptionPlan

"""

Carga el catálogo de beneficios y los asigna a cada plan.
Idempotente: re-correrlo actualiza valores y presentaciones.

"""
#=========================================
# LOAD BENEFITS
#=========================================
class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.HTTP_INFO('CARGANDO BENEFICIOS POR DEFECTO'))
            benefits        =   {}
            for code, data in dict_benefits.items():
                benefit, _          =   Benefit.objects.update_or_create(code = code, defaults = data)
                benefits[code]      =   benefit
            for plan_name, config in dict_plan_benefits.items():
                plan                =   SuscriptionPlan.objects.filter(name = plan_name).first()
                if not plan:
                    self.stdout.write(self.style.WARNING(f'PLAN "{plan_name}" NO EXISTE, SE OMITE (correr manage.py suscriptions primero)'))
                    continue
                PlanPresentation.objects.update_or_create(plan = plan, defaults = config['presentation'])
                for code, val in config['benefits'].items():
                    benefit         =   benefits[code]
                    defaults        =   {'value': val, 'enabled': True} if benefit.kind == Benefit.LIMIT else {'enabled': bool(val), 'value': None}
                    PlanBenefit.objects.update_or_create(plan = plan, benefit = benefit, defaults = defaults)
            self.stdout.write(self.style.SUCCESS('LOS BENEFICIOS SE CARGARON CORRECTAMENTE'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('ALGO SALIO MAL, NO SE LOGRARON CARGAR LOS BENEFICIOS'))
            raise Exception(f'Algo salio mal {e}')
