from django.conf import settings
from django.core.checks import Error, Tags, register

"""
System checks de despliegue a nivel proyecto.

Los defaults de settings.py atan las cabeceras de seguridad a DEBUG, pero un
`.env` puede apagarlas explícitamente (SECURE_SSL_REDIRECT=False, etc.). Este
check hace que `manage.py check --deploy` falle en producción si alguna quedó
apagada — un env incompleto o mal copiado no puede degradar el transporte en
silencio.
"""

#Nombre de setting -> id del check
_REQUIRED_TRUE = {
    'SECURE_SSL_REDIRECT'   :   'project.E001',
    'SESSION_COOKIE_SECURE' :   'project.E002',
    'CSRF_COOKIE_SECURE'    :   'project.E003',
}


@register(Tags.security, deploy = True)
def check_production_transport_security(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    errors      =   []
    for name, check_id in _REQUIRED_TRUE.items():
        if not getattr(settings, name, False):
            errors.append(Error(
                f'{name} está apagado con DEBUG=False: el tráfico viaja sin HTTPS forzado.',
                hint = f'Quitar {name}=False del .env de producción (el default ya es True).',
                id = check_id,
            ))
    if getattr(settings, 'SECURE_HSTS_SECONDS', 0) <= 0:
        errors.append(Error(
            'SECURE_HSTS_SECONDS es 0 con DEBUG=False: el navegador no recuerda exigir HTTPS.',
            hint = 'Dejar el default de producción (31536000) o definir un valor > 0.',
            id = 'project.E004',
        ))
    if not getattr(settings, 'SECURE_PROXY_SSL_HEADER', None):
        errors.append(Error(
            'SECURE_PROXY_SSL_HEADER no está configurado con DEBUG=False: detrás de '
            'nginx/Cloudflare request.is_secure() ve http y el redirect entra en loop.',
            hint = 'Dejar SECURE_SSL_REDIRECT=True o definir SECURE_PROXY_SSL=True.',
            id = 'project.E005',
        ))
    return errors
