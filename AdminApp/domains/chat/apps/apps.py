from django.apps import AppConfig


"""
Creamos la app para el dominio chat
"""

#=========================================
# CHAT APP CONFIG
#=========================================
class ChatAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField'
    name                    =   'AdminApp.domains.chat'
    label                   =   'chat'
