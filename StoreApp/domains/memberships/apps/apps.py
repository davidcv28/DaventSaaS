from django.apps import AppConfig

"""
Planes de suscripción que cada dueño ofrece a SUS clientes y sus
beneficios (tarjeta digital, descuentos/envío gratis, exclusivos).
"""

#=========================================
# MEMBERSHIPS APP CONFIG
#=========================================
class MembershipsAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.memberships'
    label               =   'memberships'
