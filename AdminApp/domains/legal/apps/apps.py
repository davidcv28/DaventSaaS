from django.apps import AppConfig

"""
Creamos la app para el dominio legal
"""

#=========================================
# LEGAL APP CONFIG
#=========================================
class LegalAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField'
    name                    =   'AdminApp.domains.legal'
    label                   =   'legal'
