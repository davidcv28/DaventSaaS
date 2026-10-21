from django.apps import AppConfig


"""
Creamos la app para el dominio users
"""

#=========================================
# USERS APP CONFIG
#=========================================
class UsersAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField' 
    name                    =   'AdminApp.domains.users'
    label                   =   'users'
