from django.apps import AppConfig

"""
App del dominio notifications: avisos del sistema para el panel del
usuario (opiniones, mensajes del staff, estado de la suscripción y
novedades del changelog) — separados del chat de soporte.
"""

#=========================================
# NOTIFICATIONS APP CONFIG
#=========================================
class NotificationsAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField'
    name                    =   'AdminApp.domains.notifications'
    label                   =   'notifications'
