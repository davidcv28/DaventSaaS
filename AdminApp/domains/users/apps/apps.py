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

    def ready(self):
        #Registra los system checks del dominio (ADMIN_URL no predecible en
        #deploy, etc.) — corren con `manage.py check --deploy`.
        from AdminApp.domains.users import checks  # noqa: F401
