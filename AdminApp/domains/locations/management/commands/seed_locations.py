#===== IMPORTACIONES =====
from django.core.management import BaseCommand

from AdminApp.domains.locations.models import City, Province, ZipCode

from .seeds import list_cities, list_province, list_zipcode

"""
GENERAMOS AUTOMATICAMENTE LAS PROVINCIAS, CIUDADES Y CODIGOS POSTALES
Comando de Django management que carga datos semilla de ubicaciones geográficas.
"""

#=====================================
# PROVINCES AND CITIES LOAD
#=====================================
class Command(BaseCommand):
    help = 'Carga las provincias, códigos postales y ciudades en la base de datos'
    def handle(self, *args, **options):
        if not Province.objects.exists():
            try:
                #=====================================
                # LOAD PROVINCES
                #=====================================
                bulk_provinces  =   []
                for province_item in list_province:
                    new_province    =   Province(name_province = province_item)
                    bulk_provinces.append(new_province)
                Province.objects.bulk_create(bulk_provinces, ignore_conflicts = True )

                #=====================================
                # LOAD ZIPCODE
                #=====================================
                bulk_zipcode = []
                for zipcode_item in list_zipcode:
                    new_zipcode     =    ZipCode(zipcode = zipcode_item)
                    bulk_zipcode.append(new_zipcode)
                ZipCode.objects.bulk_create(bulk_zipcode, ignore_conflicts = True)

                #=====================================
                # LOAD CITIES
                #=====================================
                provinces           =   list(Province.objects.all())
                zipcodes            =   list(ZipCode.objects.all())
                zipcodes_dict       =    {z.zipcode: z for z in zipcodes}    
                provinces_dict      =    {p.name_province: p for p in provinces}
                bulk_cities         =    []
                for province_key, cities in list_cities.items():
                    province_obj    =   provinces_dict[province_key]
                    for city_data in cities:
                        city_zip    =   zipcodes_dict[city_data['zipcode']]
                        new_city    =   City(name_city = city_data['city'], province = province_obj, zipcode = city_zip)
                        bulk_cities.append(new_city)
                City.objects.bulk_create(bulk_cities, ignore_conflicts = True)

                #===== MENSAJE DE ÉXITO =====
                self.stdout.write(self.style.SUCCESS('LAS PROVINCIAS Y CIUDADES FUERON AGREGADAS SATISFACTORIAMENTE'))
                        
            except:
                raise
        else:
            #===== MENSAJE DE ADVERTENCIA (DATOS YA EXISTENTES) =====
            self.stdout.write(self.style.WARNING('LAS PROVINCIAS Y CIUDADES YA SE ENCUENTRAN CARGADAS'))
            
        