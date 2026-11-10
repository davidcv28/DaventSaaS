from django.apps import AppConfig

"""
Cobros de las tiendas: Mercado Pago del vendedor (preferencias,
webhook, reembolsos) y métodos manuales de pago.
"""

#=========================================
# STORE PAYMENTS APP CONFIG
#=========================================
class StorePaymentsAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.storepayments'
    label               =   'storepayments'
