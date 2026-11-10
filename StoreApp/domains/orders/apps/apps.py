from django.apps import AppConfig

"""
Pedidos, items, bitácora de estados y comprobantes no fiscales
(e-commerce DAVENT).
"""

#=========================================
# ORDERS APP CONFIG
#=========================================
class OrdersAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.orders'
    label               =   'orders'
