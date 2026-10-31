from django.apps import AppConfig


class DesignAppConfig(AppConfig):
    default_auto_field  =   'django.db.models.BigAutoField'
    name                =   'StoreApp.domains.design'
    label               =   'design'

    def ready(self):
        from StoreApp.domains.design import signals  # noqa: F401 — conecta el bump del cache público
