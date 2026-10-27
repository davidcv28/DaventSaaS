"""
Campos cifrados del modelo UserProfile.

`EncryptedCharField` guarda en la columna AES-256-GCM (formato del vault
`enc:v1:<kid>:<payload>`) y devuelve el texto en claro al leer, así los
serializers, `_build_det` (AFIP) y `BillingMissingFieldsQuery` consumen el
valor normal sin tocar crypto.

Cada campo fija `aad`/`purpose` propio (context binding): el ciphertext de una
columna no descifra si se copia a otra — vault.decrypt_secret exige el mismo
purpose. `max_length` valida el TEXTO EN CLARO; la columna es TEXT porque el
ciphertext (enc:v1: + nonce + tag) supera cualquier largo de origen.

Igualdad/unicidad no pueden resolverse sobre ciphertext (cada cifrado usa un
nonce distinto): `digest_for` deriva una huella HMAC-SHA256 estable por campo,
guardada en las columnas `<name>_hash` (document_hash, phone_hash) que mantienen
`UserProfile.save()`. La llave de la huella es `SECRETS_HASH_KEY` — distinta de
la keyring de cifrado — para que un leak de una no habilite ataques sobre la
otra.
"""
import hashlib
import hmac

from django.conf import settings
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _


def _vault():
    #Lazy: invoices.services carga a su vez modelos que dependen de
    #users.models — importar el vault acá arriba armaría un ciclo.
    from AdminApp.domains.invoices.services import vault
    return vault


def hash_key() -> bytes:
    """Llave del HMAC de búsquedas. En producción es obligatoria SECRETS_HASH_KEY
    (nunca la de cifrado); sin env se deriva de SECRET_KEY solo para dev/test."""
    raw = (getattr(settings, 'SECRETS_HASH_KEY', '') or '').strip()
    if raw:
        return raw.encode('utf-8')
    return hashlib.sha256(f'davent-field-hash:{settings.SECRET_KEY}'.encode('utf-8')).digest()


def digest_for(field_name: str, value) -> str:
    """Huella estable para igualdad sobre el valor en claro (casefold: equivale
    al __iexact que usaban los validadores sobre document/phone)."""
    normalized = str(value).strip().casefold()
    return hmac.new(hash_key(), f'{field_name}:{normalized}'.encode('utf-8'), hashlib.sha256).hexdigest()


class EncryptedCharField(models.TextField):
    description = _('CharField cifrado en reposo con AES-256-GCM (vault).')

    def __init__(self, *args, aad: str = None, max_length: int = None, **kwargs):
        #`aad` fija el purpose aunque se renombre la app/modelo: el ciphertext
        #existente sigue descifrando mientras el string no cambie.
        self.aad = aad
        self.max_length = max_length
        kwargs.setdefault('null', True)
        super().__init__(*args, **kwargs)
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(max_length))

    @property
    def purpose(self) -> str:
        return self.aad or f'{self.model._meta.label}.{self.name}'

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.aad is not None:
            kwargs['aad'] = self.aad
        if self.max_length is not None:
            kwargs['max_length'] = self.max_length
        kwargs.pop('null', None)
        return name, path, args, kwargs

    def _decrypt(self, value):
        return _vault().decrypt_secret(value, self.purpose).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        if _vault().is_encrypted(value):
            return self._decrypt(value)
        #Tolerancia a filas aún en claro (estado intermedio de migración):
        #la primera save() las vuelve a cifrar.
        return value

    def to_python(self, value):
        if isinstance(value, str) and _vault().is_encrypted(value):
            return self._decrypt(value)
        return super().to_python(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ''):
            return value
        value = str(value)
        if _vault().is_encrypted(value):
            #Idempotencia: re-saves/updates no doble-cifran un token válido.
            return value
        return _vault().encrypt_secret(value.encode('utf-8'), self.purpose)

    def get_db_prep_value(self, value, connection, prepared = False):
        if prepared:
            #Lookup (filter/exclude/exact/iexact/contains...): el ciphertext es
            #aleatorio por nonce — jamás matchea. Fallar en voz alta en vez de
            #devolver resultados vacíos silenciosos: usar <field>_hash.
            raise TypeError(
                f'No se puede filtrar por "{self.name}" cifrado; '
                f'usá la huella estable "{self.name}_hash" (digest_for).'
            )
        return super().get_db_prep_value(value, connection, prepared)

    def formfield(self, **kwargs):
        if self.max_length is not None:
            kwargs.setdefault('max_length', self.max_length)
        return super().formfield(**kwargs)
