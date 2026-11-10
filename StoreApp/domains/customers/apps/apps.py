from django.apps import AppConfig

"""
Cuentas de compradores de las webs de tiendas (e-commerce DAVENT).
"""

#=========================================
# CUSTOMERS APP CONFIG
#=========================================
class CustomersAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.customers'
    label               =   'customers'
