"""
Cifrado en reposo de secretos fiscales (clave privada / certificado ARCA).

AES-256-GCM con keyring rotativo:
- SECRETS_MASTER_KEYS (env) = "kid1:<b64url 32 bytes>,kid2:<b64url 32 bytes>".
  La PRIMERA es la activa (cifra); todas descifran -> rotación sin downtime:
  se antepone la nueva, se re-cifra (`manage.py encrypt_secret --rotate`) y
  luego se retira la vieja.
- Formato: enc:v1:<kid>:<b64url(nonce[12] || ciphertext || tag)>.
- El `purpose` viaja como AAD: un blob cifrado para AFIP_KEY no puede
  reutilizarse como AFIP_CERT (ni moverse a otro campo) sin fallar el tag.
"""
import base64
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

PREFIX      =   'enc:v1:'
_KID_RE     =   re.compile(r'^[A-Za-z0-9_.-]{1,32}$')


class VaultError(Exception):
    """Falla de cifrado/descifrado. El mensaje nunca incluye material secreto."""


def _b64d(value : str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _keyring() -> dict:
    ring    =   {}
    for item in (getattr(settings, 'SECRETS_MASTER_KEYS', '') or '').split(','):
        item    =   item.strip()
        if not item:
            continue
        kid, _, raw     =   item.partition(':')
        if not _KID_RE.match(kid) or not raw:
            raise VaultError('SECRETS_MASTER_KEYS mal formado (se espera kid:base64url)')
        try:
            key     =   _b64d(raw)
        except Exception:
            raise VaultError(f'La llave maestra "{kid}" no es base64 válido')
        if len(key) != 32:
            raise VaultError(f'La llave maestra "{kid}" debe ser de 32 bytes (AES-256)')
        ring[kid]   =   key
    return ring


def generate_master_key(kid : str) -> str:
    return f'{kid}:{base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")}'


def is_encrypted(value : str) -> bool:
    return (value or '').strip().startswith(PREFIX)


def encrypt_secret(plaintext : bytes, purpose : str) -> str:
    ring    =   _keyring()
    if not ring:
        raise VaultError('SECRETS_MASTER_KEYS no está configurada')
    kid     =   next(iter(ring))
    nonce   =   os.urandom(12)
    blob    =   AESGCM(ring[kid]).encrypt(nonce, plaintext, purpose.encode())
    return  f'{PREFIX}{kid}:{base64.urlsafe_b64encode(nonce + blob).decode().rstrip("=")}'


def decrypt_secret(token : str, purpose : str) -> bytes:
    token   =   (token or '').strip()
    if not token.startswith(PREFIX):
        raise VaultError('Valor no cifrado')
    kid, _, payload     =   token[len(PREFIX):].partition(':')
    key     =   _keyring().get(kid)
    if key is None:
        raise VaultError(f'No hay llave maestra "{kid}" en SECRETS_MASTER_KEYS')
    try:
        raw     =   _b64d(payload)
        return  AESGCM(key).decrypt(raw[:12], raw[12:], purpose.encode())
    except (InvalidTag, ValueError):
        #Manipulado, llave equivocada o purpose distinto: indistinguibles a propósito.
        raise VaultError('No se pudo descifrar el secreto (llave, contexto o datos inválidos)')


def rotate_secret(token : str, purpose : str) -> str:
    return encrypt_secret(decrypt_secret(token, purpose), purpose)
