import os
import re

from django.conf import settings
from django.core.checks import Error, Tags, register

"""

Guard central de variables de entorno críticas y peligrosas.

Los checks por dominio (users/payments/invoices) validan lo que cada app
necesita; este módulo cubre el eje transversal: NOMBRES que no deben existir
en producción (interruptores de arranque, inyección de runtime) y VALORES
peligrosos (hosts/orígenes comodín, claves placeholder, Redis ausente,
backend de email de consola, etc.). Se expone de dos formas:

  - `manage.py check --deploy` → errores `project.E006…E018`.
  - `manage.py check_env` → tabla nombre→OK/ERROR con valores enmascarados
    y exit != 0 si hay errores (gate del CI y del runbook de deploy).

"""

#Nombres que no deben viajar en el entorno de producción: cambian el
#comportamiento del proceso (seeds, superusuario, inyección de módulos).
DANGEROUS_NAMES = frozenset({
    'PYTHONPATH',
    'PYTHONSTARTUP',
    'LD_PRELOAD',
    'LD_LIBRARY_PATH',
    'DJANGO_SETTINGS_MODULE',
    'AUTO_SEED',
    'DJANGO_SUPERUSER_PASSWORD',
})

#Placeholders que nunca son una clave real (los del .env.example, CI y dev).
SECRET_PLACEHOLDERS = ('change-me', 'django-insecure', 'ci-only', 'changeme', 'secret')

CONSOLE_EMAIL_BACKENDS = (
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
)

LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1', 'db', 'redis')

MASK_LENGTH = 6


def mask(value) -> str:
    """Valor enmascarado para logs/tablas: nunca se imprime un secreto entero."""
    text    =   str(value or '')
    if not text:
        return '<vacío>'
    if len(text) <= MASK_LENGTH:
        return '*' * len(text)
    return f'{text[:MASK_LENGTH]}…({len(text)} chars)'


def _env(name : str, default : str = '') -> str:
    return os.environ.get(name, default)


def _is_true(value) -> bool:
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'on')


def _origins(value) -> list:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    return [item.strip() for item in str(value or '').split(',') if item.strip()]


def _master_keys() -> list:
    return [key.strip() for key in str(getattr(settings, 'SECRETS_MASTER_KEYS', '') or '').split(',') if key.strip()]


def _remote_database_without_ssl() -> bool:
    """La base apunta a un host remoto y la conexión no exige TLS."""
    database    =   (getattr(settings, 'DATABASES', {}) or {}).get('default', {})
    host        =   str(database.get('HOST') or '')
    if not host or host in LOCAL_HOSTS:
        return False
    options     =   database.get('OPTIONS') or {}
    if options.get('sslmode'):
        return False
    url         =   str(getattr(settings, 'DATABASE_URL', '') or _env('DATABASE_URL'))
    return 'sslmode=' not in url


def _error(check_id : str, name : str, message : str, hint : str) -> dict:
    return {'id': check_id, 'name': name, 'message': message, 'hint': hint}


def collect_errors() -> list:
    """
    Lista de errores (dicts) con la config actual. Vacía = entorno sano.
    Cada regla mira el NOMBRE y el VALOR, y no depende de DEBUG salvo donde
    se indica (las reglas de producción solo aplican con DEBUG=False).
    """
    errors  =   []
    prod    =   not settings.DEBUG

    # ---- Nombres peligrosos ----
    for name in sorted(DANGEROUS_NAMES):
        if name not in os.environ:
            continue
        #manage.py setea DJANGO_SETTINGS_MODULE con el módulo del proyecto:
        #solo es peligroso si apunta a otro (override de settings).
        if name == 'DJANGO_SETTINGS_MODULE' and os.environ[name] == 'DaventProject.settings':
            continue
        errors.append(_error(
            'project.E006', name,
            f'{name} está definida en el entorno: cambia el comportamiento del proceso.',
            f'Quitar {name} del entorno de producción.',
        ))
    if _is_true(_env('MP_WEBHOOK_ALLOW_UNSIGNED')):
        errors.append(_error(
            'project.E007', 'MP_WEBHOOK_ALLOW_UNSIGNED',
            'MP_WEBHOOK_ALLOW_UNSIGNED está activo: los webhooks de pago se aceptan sin firma.',
            'Dejarlo en False/0 (solo dev local sin ngrok).',
        ))
    if _env('DEPLOY_CHECK_STRICT', '1').strip() == '0':
        errors.append(_error(
            'project.E008', 'DEPLOY_CHECK_STRICT',
            'DEPLOY_CHECK_STRICT=0: el arranque no aborta con configuración incompleta.',
            'Dejarlo en 1 en VPS/compose (Render lo documenta en 0 a propósito).',
        ))

    # ---- Valores peligrosos ----
    allowed_hosts   =   _origins(getattr(settings, 'ALLOWED_HOSTS', []))
    if '*' in allowed_hosts:
        errors.append(_error(
            'project.E009', 'ALLOWED_HOSTS',
            'ALLOWED_HOSTS contiene "*": se acepta cualquier Host header.',
            'Listar los dominios reales (.dominio cubre apex + subdominios).',
        ))

    for name, setting_name in (('CORS_ALLOWED_ORIGINS', 'CORS_ALLOWED_ORIGINS'), ('CSRF_TRUSTED_ORIGINS', 'CSRF_TRUSTED_ORIGINS')):
        origins =   _origins(getattr(settings, setting_name, []))
        if '*' in origins or any(origin == '*' or '://*' in origin for origin in origins):
            errors.append(_error(
                'project.E010', name,
                f'{name} contiene un comodín "*".',
                'Listar los orígenes exactos (https://www.dominio, https://*.dominio).',
            ))
        insecure    =   [
            origin for origin in origins
            if origin.startswith('http://') and 'localhost' not in origin and '127.0.0.1' not in origin
        ]
        if prod and insecure:
            errors.append(_error(
                'project.E018', name,
                f'{name} incluye un origen http:// en producción.',
                'Usar https:// en todos los orígenes.',
            ))

    secret_key  =   str(getattr(settings, 'SECRET_KEY', '') or '')
    lowered     =   secret_key.lower()
    if (not secret_key or len(secret_key) < 50
            or any(token in lowered for token in SECRET_PLACEHOLDERS)):
        errors.append(_error(
            'project.E011', 'SECRET_KEY',
            'SECRET_KEY vacía, corta (<50 chars) o con un placeholder conocido.',
            'Generar con secrets.token_urlsafe(64) y rotarla por el runbook.',
        ))

    redis_url   =   str(getattr(settings, 'REDIS_URL', '') or _env('REDIS_URL'))
    if prod and not redis_url:
        errors.append(_error(
            'project.E012', 'REDIS_URL',
            'REDIS_URL vacía con DEBUG=False: throttles, dedup y cache caen a locmem por proceso.',
            'Definir REDIS_URL (compose la deriva de REDIS_PASSWORD).',
        ))

    if prod and str(getattr(settings, 'EMAIL_BACKEND', '') or '') in CONSOLE_EMAIL_BACKENDS:
        errors.append(_error(
            'project.E013', 'EMAIL_BACKEND',
            'EMAIL_BACKEND de consola/locmem/dummy en producción: los correos se descartan.',
            'Configurar el backend SMTP real.',
        ))

    if prod and _env('MP_PAYER_EMAIL'):
        errors.append(_error(
            'project.E014', 'MP_PAYER_EMAIL',
            'MP_PAYER_EMAIL está seteada en producción (es un payer de pruebas de MP).',
            'Dejarla vacía en producción.',
        ))

    hash_key    =   str(getattr(settings, 'SECRETS_HASH_KEY', '') or '')
    if hash_key and hash_key in _master_keys():
        errors.append(_error(
            'project.E015', 'SECRETS_HASH_KEY',
            'SECRETS_HASH_KEY es igual a una master key del keyring de PII.',
            'Generar una llave HMAC distinta (nunca reutilizar la de cifrado).',
        ))

    if prod and _remote_database_without_ssl():
        errors.append(_error(
            'project.E016', 'DATABASE_URL',
            'DATABASE_URL apunta a un host remoto sin sslmode: la conexión viaja en claro.',
            'Agregar ?sslmode=require (o verify-full) a la URL.',
        ))

    debug_raw   =   _env('DEBUG')
    if debug_raw and debug_raw.strip().lower() not in ('0', '1', 'true', 'false', 'yes', 'no', 'on', 'off'):
        errors.append(_error(
            'project.E017', 'DEBUG',
            f'DEBUG="{debug_raw}" no es un booleano reconocible.',
            'Usar True/False (0/1 también se acepta).',
        ))

    return errors


@register(Tags.security, deploy = True)
def check_env_guard(app_configs, **kwargs):
    return [
        Error(item['message'], hint = item['hint'], id = item['id'])
        for item in collect_errors()
    ]
