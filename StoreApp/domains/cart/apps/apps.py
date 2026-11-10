from django.apps import AppConfig

"""
Carrito de compras por cliente y tienda (e-commerce DAVENT).
"""

#=========================================
# CART APP CONFIG
#=========================================
class CartAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.cart'
    label               =   'cart'
