from django.apps import AppConfig

"""
Soporte comprador <-> dueño de tienda (hilos por tienda, opcionalmente
anclados a un pedido).
"""

#=========================================
# SUPPORT APP CONFIG
#=========================================
class SupportAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.support'
    label               =   'support'
