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


@register(Tags.security, deploy = True)
def check_secrets_keyring(app_configs, **kwargs):
    #PII de UserProfile (documento, nombres, domicilio, celular, razón social)
    #va cifrada AES-256-GCM. Sin keyring real el vault deriva una llave del
    #SECRET_KEY: funciona pero queda acoplada a esa llave (rotarla rompería
    #todo el ciphertext). En producción el keyring dedicado es obligatorio.
    if settings.DEBUG:
        return []
    if not getattr(settings, 'SECRETS_MASTER_KEYS', '').strip():
        return [
            Error(
                "SECRETS_MASTER_KEYS vacía en producción: los campos cifrados de "
                "UserProfile caerían a la llave derivada del SECRET_KEY.",
                hint = "Generar una con 'manage.py encrypt_secret --gen-master-key k1' y definirla en el entorno.",
                id = 'users.E002',
            )
        ]
    if not getattr(settings, 'SECRETS_HASH_KEY', '').strip():
        return [
            Error(
                "SECRETS_HASH_KEY vacía en producción: las huellas de búsqueda "
                "de los campos cifrados quedan derivadas del SECRET_KEY (si rota, "
                "la unicidad/búsqueda de documento y celular se rompe en silencio).",
                hint = "Definir SECRETS_HASH_KEY con un valor aleatorio distinto a la keyring de cifrado.",
                id = 'users.E003',
            )
        ]
    return []
