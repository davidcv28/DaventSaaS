import os

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

from AdminApp.domains.invoices.services import vault

"""
System checks del dominio Invoices: con AFIP_ENABLED en producción la
configuración de secretos fiscales debe estar completa — un deploy sin
keyring o con la clave privada en claro dejaría el CAE caído (facturas sin
validez fiscal) o el PEM legible por cualquier proceso del host.
"""


def _insecure_permissions(path : str) -> bool:
    """True si el archivo PEM es legible/escribible por 'group' u 'others'.
    Solo POSIX: en Windows st_mode no refleja los ACL reales."""
    if os.name != 'posix':
        return False
    return bool(os.stat(path).st_mode & 0o077)


@register(Tags.security, deploy = True)
def check_afip_secrets(app_configs, **kwargs):
    if settings.DEBUG or not settings.AFIP.get('enabled'):
        return []
    errors  =   []
    if not getattr(settings, 'SECRETS_MASTER_KEYS', '').strip():
        errors.append(
            Error(
                'AFIP_ENABLED=True sin SECRETS_MASTER_KEYS: los secretos fiscales '
                'no podrían descifrarse (la llave derivada de dev no sirve en prod).',
                hint = 'Generar el keyring con manage.py encrypt_secret --gen-master-key k1.',
                id = 'invoices.E001',
            )
        )
    key     =   (settings.AFIP.get('key') or '').strip()
    is_path =   bool(key) and os.path.isfile(key)
    if key and not (vault.is_encrypted(key) or is_path):
        errors.append(
            Error(
                'AFIP_KEY no está cifrada (enc:v1:) ni es una ruta a archivo: '
                'la clave privada no puede viajar en claro en el entorno.',
                hint = 'Cifrarla con manage.py encrypt_secret --purpose AFIP_KEY o montarla como archivo.',
                id = 'invoices.E002',
            )
        )
    elif is_path and _insecure_permissions(key):
        errors.append(
            Warning(
                f'El archivo de clave privada {key!r} es legible por group/others '
                '(mode & 0o077 != 0): cualquier proceso del host puede leerla.',
                hint = 'chmod 600 el archivo PEM y revisar su ownership.',
                id = 'invoices.W001',
            )
        )
    return errors
