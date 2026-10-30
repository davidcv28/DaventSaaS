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
        #Checks de despliegue a nivel proyecto (cabeceras de transporte en
        #producción): se registran acá porque es la primera app instalada.
        from DaventProject import checks as project_checks  # noqa: F401
        #Guard central de env vars (project.E006…E018).
        from DaventProject import envguard  # noqa: F401
