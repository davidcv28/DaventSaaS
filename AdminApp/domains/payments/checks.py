from decouple import config
from django.conf import settings
from django.core.checks import Error, Tags, register

"""

System checks del dominio Payments: fallan el `manage.py check --deploy`
cuando falta configuración crítica — el fallback de dev del webhook
(_verify_mp_signature procesa sin firma si DEBUG=True) nunca debe colarse a
producción por una variable ausente.

"""


@register(Tags.security, deploy = True)
def check_mp_webhook_secret(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if not config('MP_WEBHOOK_SECRET', default = ''):
        return [
            Error(
                'MP_WEBHOOK_SECRET no está configurado en producción: los webhooks '
                'de Mercado Pago serían rechazados (401) y los pagos no se acreditarían.',
                hint = 'Copiar el secret del panel de webhooks de Mercado Pago al .env.',
                id = 'payments.E001',
            )
        ]
    return []


@register(Tags.security, deploy = True)
def check_mp_secret_key(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if not config('SECRET_MP_KEY', default = ''):
        return [
            Error(
                'SECRET_MP_KEY (access token de Mercado Pago) no está configurado.',
                hint = 'Access token de producción de MP en el .env del deploy.',
                id = 'payments.E002',
            )
        ]
    return []


@register(Tags.security, deploy = True)
def check_mp_webhook_allow_unsigned(app_configs, **kwargs):
    #El flag es un bypass solo-dev (además exige DEBUG=True en runtime): si se
    #cuela en el .env de producción queda inerte, pero su presencia marca un
    #env copiado de dev — y bastaría un DEBUG=True accidental para abrir el
    #webhook sin firma.
    if settings.DEBUG:
        return []
    if config('MP_WEBHOOK_ALLOW_UNSIGNED', default = False, cast = bool):
        return [
            Error(
                'MP_WEBHOOK_ALLOW_UNSIGNED está habilitado en un entorno de deploy: '
                'si DEBUG se activa, los webhooks de MP se procesarían sin firma.',
                hint = 'Quitar MP_WEBHOOK_ALLOW_UNSIGNED del .env (es un bypass solo para dev local).',
                id = 'payments.E003',
            )
        ]
    return []
