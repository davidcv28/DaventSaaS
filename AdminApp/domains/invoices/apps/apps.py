from django.apps import AppConfig


class InvoicesAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'AdminApp.domains.invoices'
    label               =   'invoices'

    def ready(self):
        #Registra los system checks del dominio (secretos fiscales de ARCA
        #en producción) — corren con `manage.py check --deploy`.
        from AdminApp.domains.invoices import checks  # noqa: F401
