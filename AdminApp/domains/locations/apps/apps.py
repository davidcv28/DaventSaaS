from django.apps import AppConfig

"""
Creamos la app para el dominio locations
"""

#=========================================
# LOCATIONS APP CONFIG
#=========================================
class LocationsAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField' 
    name                    =   'AdminApp.domains.locations'
    label                   =   'locations'
