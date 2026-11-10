from django.apps import AppConfig

"""
Panel del dueño: métricas de ventas/ganancias, clientes, exportaciones
y agregados cross-dominio del e-commerce.
"""

#=========================================
# STORE ADMIN APP CONFIG
#=========================================
class StoreAdminAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.storeadmin'
    label               =   'storeadmin'
