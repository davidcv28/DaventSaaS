from django.apps import AppConfig

"""
POS federado ("DAVENT Mostrador"): catálogo de apps, dispositivos
vinculados y licenciamiento offline-first (PLAN_POS).
"""

#=========================================
# POS APP CONFIG
#=========================================
class PosAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.pos'
    label               =   'pos'
