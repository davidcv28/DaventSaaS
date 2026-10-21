from django.core.management import BaseCommand
from .seeds import dict_suscriptions
from AdminApp.domains.suscriptions.models import SuscriptionPlan

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
            bulk_suscriptions   =   []
            for suscription_item, value in dict_suscriptions.items():
                new_suscription =   SuscriptionPlan(name = value['name'], price = value['price'])
                bulk_suscriptions.append(new_suscription)
            SuscriptionPlan.objects.bulk_create(bulk_suscriptions, ignore_conflicts = True)
            self.stdout.write(self.style.SUCCESS('LOS PLANES SE CARGARON CORRECTAMENTE'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('ALGO SALIO MAL, NO SE LOGRARON CARGAR LOS PLANES'))
            raise Exception(f'Algo salio mal {e}')