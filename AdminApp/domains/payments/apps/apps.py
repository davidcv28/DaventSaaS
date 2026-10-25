from django.apps import AppConfig


class PaymentsAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'AdminApp.domains.payments'
    label               =   'payments'

    def ready(self):
        #Registra los system checks del dominio (MP_WEBHOOK_SECRET obligatorio
        #en deploy, etc.) — corren con `manage.py check --deploy`.
        from AdminApp.domains.payments import checks  # noqa: F401
