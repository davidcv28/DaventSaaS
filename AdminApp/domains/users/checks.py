from django.conf import settings
from django.core.checks import Error, Tags, register

"""

System checks del dominio Users: fallan el `manage.py check --deploy`
cuando la configuración de producción queda insegura por omisión.

"""


@register(Tags.security, deploy = True)
def check_admin_url(app_configs, **kwargs):
    #El login del admin no pasa por los throttles de DRF (lo acota el
    #AdminLoginRateLimitMiddleware, pero la ofuscación es la primera capa):
    #con el default 'admin/' cualquier bot lo encuentra y prueba credenciales.
    #En dev el default está bien — el check solo muerde en --deploy.
    if settings.DEBUG:
        return []
    if settings.ADMIN_URL.strip('/') in ('', 'admin'):
        return [
            Error(
                "ADMIN_URL usa el path predecible 'admin/': el login del panel de "
                "Django queda expuesto a los bots que escanean rutas conocidas.",
                hint = "Definir ADMIN_URL con un path no obvio en el .env (ej. 'gestion-x7k2/').",
                id = 'users.E001',
            )
        ]
    return []
