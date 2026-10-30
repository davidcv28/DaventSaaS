from django.core.management import BaseCommand

from AdminApp.domains.suscriptions.models import SuscriptionPlan

from .seeds import dict_suscriptions

"""

Creamos un script para generar los planes por defecto

"""
#=========================================
# LOAD SUSCRIPTIONS
#=========================================
class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.HTTP_INFO('CARGANDO PLANES POR DEFECTO'))
            for suscription_item, value in dict_suscriptions.items():
                plan, created   =   SuscriptionPlan.objects.get_or_create(
                    name        =   value['name'],
                    defaults    =   {'price': value['price'], 'is_trial': value.get('is_trial', False)},
                )
                #El flag trial y el precio forman parte del seed: si el plan
                #ya existía se corrigen acá (bajar/subir precio re-corre el comando)
                is_trial        =   value.get('is_trial', False)
                changed         =   []
                if not created and plan.is_trial != is_trial:
                    plan.is_trial   =   is_trial
                    changed.append('is_trial')
                if not created and plan.price != value['price']:
                    plan.price      =   value['price']
                    changed.append('price')
                if changed:
                    plan.save(update_fields = changed)
            self.stdout.write(self.style.SUCCESS('LOS PLANES SE CARGARON CORRECTAMENTE'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('ALGO SALIO MAL, NO SE LOGRARON CARGAR LOS PLANES'))
            raise Exception(f'Algo salio mal {e}')