from django.apps import AppConfig

"""
Páginas legales por tienda (términos, privacidad, devoluciones) y el
flujo de arrepentimiento del comprador.
"""

#=========================================
# LEGAL PAGES APP CONFIG
#=========================================
class LegalPagesAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.legalpages'
    label               =   'legalpages'
