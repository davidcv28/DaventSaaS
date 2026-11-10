import logging
import re
import uuid

import boto3
from botocore.config import Config as BotoConfig
from decouple import config
from django.core.cache import cache
from django.db import transaction

from AdminApp.domains.invoices.services.vault import VaultError, decrypt_secret
from StoreApp.domains.stores.models import Store, StoreStorageConfig

from .imaging import normalize_image
from .services import plan_benefits_of

"""

Almacenamiento de archivos en Cloudflare R2 (imágenes del cliente),
via su API compatible con S3 (boto3).

Credenciales en .env:
  S3_API               -> endpoint S3 (https://<account>.r2.cloudflarestorage.com)
  R2_ACCESS_KEY_ID     -> access key del API token de R2 (32 caracteres)
  R2_SECRET_ACCESS_KEY -> secret del API token de R2
  R2_BUCKET            -> nombre del bucket
  R2_PUBLIC_URL        -> URL pública del bucket (dominio r2.dev o custom);
                          si falta, las URLs se sirven firmadas (válidas 7 días)

Los objetos se suben con key 'stores/<store_id>/<tipo>/<uuid>.<ext>' y
esa misma key se guarda en DB para reconstruir la URL o borrar el objeto.

La cuota por tienda sale del beneficio 'limit' max_storage_mb del plan
vigente (SuscriptionApp/benefits). Store.storage_used_bytes acumula los
bytes subidos (logo, carrusel e imágenes de productos).

BYO storage (StoreStorageConfig): si la tienda tiene `enabled` y sus
credenciales descifrables, SUS objetos nuevos van a SU bucket R2; la key
'stores/<store_id>/...' no cambia — el bucket destino se resuelve por la
config ACTUAL de la tienda en cada operación. Si el PUT al bucket del
dueño falla cae al bucket DAVENT (nunca se rompe un upload por una
config rota). OJO: no hay migración — deshabilitar el BYO (o habilitarlo
después de tener objetos en DAVENT) deja las keys viejas apuntando al
bucket equivocado hasta resubirlas. Aceptable en MVP, documentado en la
guía del panel.

"""
logger                  =   logging.getLogger(__name__)
LOGO_MAX_BYTES          =   2 * 1024 * 1024   # 2 MB por archivo de logo
IMAGE_MAX_BYTES         =   4 * 1024 * 1024   # 4 MB por imagen de carrusel/producto
CAROUSEL_MAX_IMAGES     =   5                 # tope de imágenes del carrusel
DECOR_MAX_IMAGES        =   3                 # imágenes ilustrativas de la portada (premium); consumen cupo de galería
PRESIGNED_TTL_SECONDS   =   7 * 24 * 60 * 60  # máximo que permite SigV4

_IMAGE_SIGNATURES       =   {
    'png' :   b'\x89PNG\r\n\x1a\n',
    'jpg' :   b'\xff\xd8\xff',
    'gif' :   b'GIF8',
}
_IMAGE_CONTENT_TYPES    =   {
    'image/png'  : ('png', 'image/png'),
    'image/jpeg' : ('jpg', 'image/jpeg'),
    'image/gif'  : ('gif', 'image/gif'),
    'image/webp' : ('webp', 'image/webp'),
}
#=========================================
# R2 CLIENT / CONFIG
#=========================================
def _endpoint():
    return config('S3_API', default = '')
def _bucket():
    return config('R2_BUCKET', default = '')
def _public_base():
    """URL pública del bucket (r2.dev o dominio custom), sin barra final."""
    return config('R2_PUBLIC_URL', default = '').rstrip('/')
def storage_configured():
    return all([
        _endpoint(),
        config('R2_ACCESS_KEY_ID', default = ''),
        config('R2_SECRET_ACCESS_KEY', default = ''),
        _bucket(),
    ])
def _client(backend = None):
    """
    Cliente boto3 S3. `backend` = dict resuelto por `_byo_backend`
    (credenciales EN CLARO solo para este cliente — jamás se loguean
    ni salen del proceso); None = bucket DAVENT de las env vars.
    """
    if backend is not None:
        return boto3.client(
            's3',
            endpoint_url          =   backend['endpoint'],
            aws_access_key_id     =   backend['access_key'],
            aws_secret_access_key =   backend['secret_key'],
            region_name           =   backend['region'],
            config                =   BotoConfig(signature_version = 's3v4'),
        )
    return boto3.client(
        's3',
        endpoint_url          =   _endpoint(),
        aws_access_key_id     =   config('R2_ACCESS_KEY_ID', default = ''),
        aws_secret_access_key =   config('R2_SECRET_ACCESS_KEY', default = ''),
        region_name           =   'auto',
        config                =   BotoConfig(signature_version = 's3v4'),
    )
#=========================================
# BYO STORAGE (bucket R2 propio del dueño)
#=========================================
_STORE_KEY_RE               =   re.compile(r'^stores/(\d+)/')
_STORE_STORAGE_CACHE_TTL    =   300     #segundos — acota la staleness del BYO


def _store_id_from_key(key):
    """store_id embebido en keys 'stores/<id>/...' (None si no aplica — chat, system, etc.)."""
    match   =   _STORE_KEY_RE.match(key or '')
    return int(match.group(1)) if match else None


def _storage_config_row(store_id):
    """
    Fila StoreStorageConfig cacheada (campos crudos, secretos SIGUEN
    cifrados en el payload — se descifran recién en `_byo_backend`).
    Key 'store_storage:<id>' con TTL corto + invalidación explícita al
    guardar/borrar desde el panel (ver invalidate_store_storage): la key
    no puede llevar updated_at porque eso exigiría pegarle a la DB en
    cada object_url — justo lo que el cache evita.
    """
    if not store_id:
        return None
    cache_key   =   f'store_storage:{store_id}'
    row         =   cache.get(cache_key)
    if row is None:
        cfg     =   StoreStorageConfig.objects.filter(store_id = store_id).first()
        row     =   {
            'endpoint'          :   cfg.endpoint,
            'bucket'            :   cfg.bucket,
            'region'            :   cfg.region,
            'access_key_enc'    :   cfg.access_key_enc,
            'secret_key_enc'    :   cfg.secret_key_enc,
            'public_base_url'   :   cfg.public_base_url,
            'enabled'           :   cfg.enabled,
        } if cfg is not None else {}
        cache.set(cache_key, row, _STORE_STORAGE_CACHE_TTL)
    return row or None


def invalidate_store_storage(store_id):
    """Borra el cache BYO de la tienda — llamar tras guardar/borrar su StoreStorageConfig."""
    if store_id:
        cache.delete(f'store_storage:{store_id}')


def _byo_backend(store_id):
    """
    Backend S3 del dueño si su StoreStorageConfig está `enabled` y
    completo (endpoint + bucket + ambas credenciales descifrables).
    `public_base_url` es OPCIONAL: sin ella las URLs públicas salen
    firmadas (presigned) con las credenciales de la tienda.

    Devuelve un dict con credenciales en claro SOLO para construir el
    cliente boto3 — nunca se loguea ni se devuelve. None = la tienda
    usa el bucket DAVENT (sin config, deshabilitada o ilegible).
    """
    if not store_id:
        return None
    row     =   _storage_config_row(store_id)
    if not row or not row.get('enabled'):
        return None
    if not all([
        row.get('endpoint'),
        row.get('bucket'),
        row.get('access_key_enc'),
        row.get('secret_key_enc'),
    ]):
        return None
    try:
        access_key  =   decrypt_secret(row['access_key_enc'], f'{StoreStorageConfig.PURPOSE_ACCESS_KEY}:{store_id}').decode()
        secret_key  =   decrypt_secret(row['secret_key_enc'], f'{StoreStorageConfig.PURPOSE_SECRET_KEY}:{store_id}').decode()
    except (VaultError, UnicodeDecodeError):
        #Blob manipulado o llave rotada: se trata como "sin BYO" y todo
        #cae al bucket DAVENT — nunca romper la tienda por un secreto roto.
        logger.warning('StoreStorageConfig ilegible store_id=%s — se usa el bucket DAVENT', store_id)
        return None
    return {
        'endpoint'          :   row['endpoint'],
        'bucket'            :   row['bucket'],
        'region'            :   row.get('region') or 'auto',
        'access_key'        :   access_key,
        'secret_key'        :   secret_key,
        'public_base_url'   :   (row.get('public_base_url') or '').rstrip('/'),
    }


def _byo_backend_for_key(key):
    """Backend BYO de la tienda dueña de la key 'stores/<id>/...' (None si no aplica)."""
    store_id    =   _store_id_from_key(key)
    return _byo_backend(store_id) if store_id else None


def store_storage_configured(store):
    """
    True si la tienda tiene backend de storage disponible: el R2 de
    DAVENT (env) O su propio bucket BYO enabled+configurado. Los uploads
    lo usan como gate — con BYO activo no hace falta que DAVENT tenga
    credenciales propias.
    """
    store_id    =   getattr(store, 'pk', None) or getattr(store, 'id', None)
    return storage_configured() or _byo_backend(store_id) is not None
#=========================================
# OBJECT URL (delivery pública)
#=========================================
def object_url(key, private = False, expires = None):
    """
    URL servible del objeto. Si el bucket tiene URL pública configurada
    la usa; si no, devuelve una URL firmada de lectura (válida
    PRESIGNED_TTL_SECONDS). Devuelve None sin key o sin backend.

    BYO: si la key es 'stores/<id>/...' y ESA tienda tiene storage
    propio activo, la URL sale de SU public_base_url o se firma con SUS
    credenciales. OJO: la URL se resuelve por la config ACTUAL — un
    objeto subido al bucket DAVENT antes de activar el BYO (o durante
    un fallback) no existe en el bucket del dueño y su URL nueva da 404
    (limitación MVP documentada, sin migración de objetos).

    ``private=True`` ignora la URL pública y fuerza la firmada: para objetos
    que no son contenido público de tienda (adjuntos del chat de soporte,
    comprobantes de pago, etiquetas de campaña). ``expires`` acota la
    vigencia de la firma (segundos).
    """
    if not key:
        return None
    backend     =   _byo_backend_for_key(key)
    if backend is None and not storage_configured():
        return None
    base        =   None
    if not private:
        #BYO: dominio público del dueño (si no tiene, cae a presigned
        #con SUS credenciales). Sin BYO: R2_PUBLIC_URL de DAVENT.
        base    =   backend['public_base_url'] if backend is not None else _public_base()
        base    =   base or None
    if base:
        return f'{base}/{key}'
    try:
        if backend is not None:
            return _client(backend).generate_presigned_url(
                'get_object',
                Params      =   {'Bucket': backend['bucket'], 'Key': key},
                ExpiresIn   =   expires or PRESIGNED_TTL_SECONDS,
            )
        return _client().generate_presigned_url(
            'get_object',
            Params      =   {'Bucket': _bucket(), 'Key': key},
            ExpiresIn   =   expires or PRESIGNED_TTL_SECONDS,
        )
    except Exception:
        return None
def _delete_object(key):
    """
    Borrado best-effort: intenta el bucket donde el objeto probablemente
    vive (BYO de la tienda dueña de la key, si la hay) y, si esa llamada
    falla, el bucket DAVENT — cubre objetos que cayeron por fallback de
    upload. Los errores se tragan como siempre: el objeto huérfano no
    bloquea el flujo y la cuota ya se liberó en DB.
    """
    if not key:
        return
    backend =   _byo_backend_for_key(key)
    if backend is not None:
        try:
            _client(backend).delete_object(Bucket = backend['bucket'], Key = key)
            return
        except Exception:
            pass
    if not storage_configured():
        return
    try:
        _client().delete_object(Bucket = _bucket(), Key = key)
    except Exception:
        # El objeto huérfano no bloquea el flujo; la cuota ya se liberó en DB.
        pass
def put_object(key, body, content_type):
    """
    Sube bytes arbitrarios bajo una key explícita. Si la key es de una
    tienda con BYO activo va a SU bucket; si esa subida falla cae al
    bucket DAVENT (un upload nunca se rompe por una config rota del
    dueño). Para objetos sin tienda (chat de soporte, 'system/...') va
    siempre a DAVENT. Lanza ValueError si ninguna subida funciona.
    """
    backend =   _byo_backend_for_key(key)
    if backend is not None:
        try:
            _client(backend).put_object(
                Bucket          =   backend['bucket'],
                Key             =   key,
                Body            =   body,
                ContentType     =   content_type,
                CacheControl    =   'private, max-age=0',
            )
            return key
        except Exception:
            logger.warning('BYO storage falló store_id=%s — fallback al bucket DAVENT', _store_id_from_key(key))
    try:
        _client().put_object(
            Bucket          =   _bucket(),
            Key             =   key,
            Body            =   body,
            ContentType     =   content_type,
            CacheControl    =   'private, max-age=0',
        )
    except Exception:
        raise ValueError('No pudimos subir la imagen. Reintentá en unos minutos.')
    return key
def _put_object(store, folder, upload, processed = None):
    """
    Sube un archivo ya validado al bucket de la tienda (BYO si está
    activo, si no DAVENT) y devuelve la key persistible.
    `processed` = (bytes, ext, content_type) si la imagen se recodificó.
    Si el PUT al bucket del dueño falla cae al DAVENT — la key guardada
    es la misma y la URL se resuelve por la config ACTUAL de la tienda.
    Lanza ValueError si ninguna subida funciona.
    """
    if processed is None:
        ext, content_type   =   _IMAGE_CONTENT_TYPES[upload.content_type]
        body                =   upload.read()
    else:
        body, ext, content_type =   processed
    key                 =   f'stores/{store.id}/{folder}/{uuid.uuid4().hex}.{ext}'
    backend             =   _byo_backend(store.id)
    if backend is not None:
        try:
            _client(backend).put_object(
                Bucket          =   backend['bucket'],
                Key             =   key,
                Body            =   body,
                ContentType     =   content_type,
                CacheControl    =   'public, max-age=31536000, immutable',
            )
            return key
        except Exception:
            logger.warning('BYO storage falló store_id=%s — fallback al bucket DAVENT', store.id)
    try:
        _client().put_object(
            Bucket          =   _bucket(),
            Key             =   key,
            Body            =   body,
            ContentType     =   content_type,
            CacheControl    =   'public, max-age=31536000, immutable',
        )
    except Exception:
        raise ValueError('No pudimos subir la imagen. Reintentá en unos minutos.')
    return key
#=========================================
# STORAGE LIMIT / QUOTA
#=========================================
def storage_limit_bytes(profile):
    """Tope en bytes del plan vigente (max_storage_mb). None = ilimitado, 0 = sin cuota."""
    benefits        =   plan_benefits_of(profile)
    if 'max_storage_mb' not in benefits:
        return 0
    max_mb          =   benefits['max_storage_mb']
    return None if max_mb is None else max_mb * 1024 * 1024
def image_limit(profile):
    """Tope de imágenes del plan vigente (max_images). None = ilimitado, 0 = sin cuota."""
    benefits        =   plan_benefits_of(profile)
    if 'max_images' not in benefits:
        return 0
    return benefits['max_images']
def gallery_limit(profile):
    """Tope de la galería del plan vigente (max_gallery_images). None = ilimitado, 0 = sin galería."""
    benefits        =   plan_benefits_of(profile)
    if 'max_gallery_images' not in benefits:
        return 0
    return benefits['max_gallery_images']
def image_count(store):
    """Cantidad de imágenes que ocupan cuota: logo + portada + carrusel + galería + productos + marcas."""
    #_n_product_images/_n_brand_images vienen anotados en el queryset del
    #listado y los count() de carrusel/galería usan el prefetch: sin eso
    #sumaban queries extra por tienda.
    products    =   getattr(store, '_n_product_images', None)
    if products is None:
        products    =   store.products.exclude(image_key = '').count()
    brands      =   getattr(store, '_n_brand_images', None)
    if brands is None:
        brands      =   store.brands.exclude(image_key = '').count()
    count           =   store.carousel_images.count() + store.gallery_images.count() + products + brands
    customization   =   getattr(store, 'customization', None)
    if customization and customization.logo_key:
        count       +=  1
    if customization and customization.cover_key:
        count       +=  1
    return count
def _check_image_slot(store, is_new):
    """
    Verifica el tope max_images del plan al subir una imagen nueva
    (reemplazar una existente no suma al contador). Lanza ValueError es-AR.
    """
    if not is_new:
        return
    limit       =   image_limit(store.user)
    if limit is not None and image_count(store) >= limit:
        raise ValueError(f'Tu plan admite hasta {limit} imágenes. Borrá alguna o pasá a un plan superior.')
def storage_payload(store, profile):
    """Resumen de cuota para respuestas de la API ({used_bytes, max_mb, images, max_images})."""
    limit           =   storage_limit_bytes(profile)
    return {
        'used_bytes'    :   store.storage_used_bytes,
        'max_mb'        :   None if limit is None else limit // (1024 * 1024),
        'images'        :   image_count(store),
        'max_images'    :   image_limit(profile),
    }
def _check_quota(store, incoming_bytes, replacing_bytes = 0):
    """
    Verifica que entrar incoming_bytes (menos replacing_bytes que se liberan)
    no supere la cuota del plan. Lanza ValueError con mensaje es-AR.
    """
    limit       =   storage_limit_bytes(store.user)
    new_used    =   store.storage_used_bytes - replacing_bytes + incoming_bytes
    if limit is not None and new_used > limit:
        restante    =   max(0, limit - (store.storage_used_bytes - replacing_bytes)) // (1024 * 1024)
        raise ValueError(f'Tu plan no tiene espacio suficiente ({restante} MB disponibles).')
    return new_used
def _consume_quota(store, new_used):
    """
    Persiste storage_used_bytes. Debe llamarse sobre la instancia BLOQUEADA
    (select_for_update) dentro del atomic del upload/delete: los cupos se
    recalculan sobre el valor real de la fila y los commits quedan
    serializados por tienda — dos requests concurrentes ya no pueden
    leer el mismo storage_used_bytes y pisarse el update.
    """
    store.storage_used_bytes    =   max(0, new_used)
    store.save(update_fields = ['storage_used_bytes'])
#=========================================
# IMAGE VALIDATION
#=========================================
def validate_image_file(upload, max_bytes = IMAGE_MAX_BYTES):
    """Devuelve '' si es válido o el mensaje de error (es-AR)."""
    if upload.size > max_bytes:
        mb          =   max_bytes // (1024 * 1024)
        return f'La imagen no puede pesar más de {mb} MB.'
    ext         =   (_IMAGE_CONTENT_TYPES.get(getattr(upload, 'content_type', '') or '') or ('',))[0]
    if not ext:
        return 'Formato no admitido: usá una imagen PNG, JPG, WebP o GIF.'
    head        =   upload.read(16)
    upload.seek(0)
    if ext == 'webp':
        if not (head.startswith(b'RIFF') and head[8:12] == b'WEBP'):
            return 'El archivo no es una imagen válida.'
    elif not head.startswith(_IMAGE_SIGNATURES[ext]):
        return 'El archivo no es una imagen válida.'
    return ''
def validate_logo_file(upload):
    return validate_image_file(upload, LOGO_MAX_BYTES)
#=========================================
# LOGO UPLOAD / DELETE
#=========================================
def upload_logo(customization, upload):
    """
    Sube el logo a R2 (normalizado a WebP, conserva la transparencia),
    libera el anterior y descuenta/actualiza la cuota de la tienda.
    Lanza ValueError con mensaje para el cliente si falla la cuota o el
    storage no está configurado.
    """
    store       =   customization.store
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_logo_file(upload)
    if error:
        raise ValueError(error)
    processed   =   normalize_image(upload, 'logo')
    size        =   len(processed[0])
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_image_slot(store, is_new = not customization.logo_key)
    _check_quota(store, size, replacing_bytes = customization.logo_size)
    key         =   _put_object(store, 'logo', upload, processed)
    try:
        with transaction.atomic():
            #Los cupos se rechequean bajo lock de la fila de la tienda:
            #cierra la carrera check->put->consume entre uploads concurrentes.
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            locked_cust =   locked.customization
            _check_image_slot(locked, is_new = not locked_cust.logo_key)
            new_used    =   _check_quota(locked, size, replacing_bytes = locked_cust.logo_size)
            old_key     =   locked_cust.logo_key
            locked_cust.logo_key      =   key
            locked_cust.logo_size     =   size
            locked_cust.save(update_fields = ['logo_key', 'logo_size', 'updated_at'])
            _consume_quota(locked, new_used)
    except ValueError:
        #El objeto ya subido quedaría huérfano: se borra antes de propagar.
        _delete_object(key)
        raise
    customization.logo_key          =   key
    customization.logo_size         =   size
    store.storage_used_bytes        =   locked.storage_used_bytes
    if old_key:
        _delete_object(old_key)
    return customization
def delete_logo(customization):
    """Borra el logo de R2 y libera la cuota."""
    store       =   customization.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_cust =   locked.customization
        #La key se toma de la fila bloqueada (no del objeto del caller):
        #un reemplazo concurrente no puede hacernos borrar el logo nuevo.
        old_key     =   locked_cust.logo_key
        freed       =   locked_cust.logo_size
        locked_cust.logo_key      =   ''
        locked_cust.logo_size     =   0
        locked_cust.save(update_fields = ['logo_key', 'logo_size', 'updated_at'])
        _consume_quota(locked, locked.storage_used_bytes - freed)
    if old_key:
        _delete_object(old_key)
    customization.logo_key          =   ''
    customization.logo_size         =   0
    store.storage_used_bytes        =   locked.storage_used_bytes
    return customization
#=========================================
# COVER UPLOAD / DELETE (imagen de portada de la web pública, premium)
#=========================================
def upload_cover(customization, upload):
    """
    Sube la portada (normalizada a WebP) a R2, libera la anterior y ajusta la
    cuota. Lanza ValueError con mensaje es-AR si falla storage, archivo o cuota.
    """
    store       =   customization.store
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    processed   =   normalize_image(upload, 'cover')
    size        =   len(processed[0])
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_image_slot(store, is_new = not customization.cover_key)
    _check_quota(store, size, replacing_bytes = customization.cover_size)
    key         =   _put_object(store, 'cover', upload, processed)
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            locked_cust =   locked.customization
            _check_image_slot(locked, is_new = not locked_cust.cover_key)
            new_used    =   _check_quota(locked, size, replacing_bytes = locked_cust.cover_size)
            old_key     =   locked_cust.cover_key
            locked_cust.cover_key     =   key
            locked_cust.cover_size    =   size
            locked_cust.save(update_fields = ['cover_key', 'cover_size', 'updated_at'])
            _consume_quota(locked, new_used)
    except ValueError:
        _delete_object(key)
        raise
    customization.cover_key         =   key
    customization.cover_size        =   size
    store.storage_used_bytes        =   locked.storage_used_bytes
    if old_key:
        _delete_object(old_key)
    return customization
def delete_cover(customization):
    """Borra la portada de R2 y libera la cuota."""
    store       =   customization.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_cust =   locked.customization
        old_key     =   locked_cust.cover_key
        freed       =   locked_cust.cover_size
        locked_cust.cover_key     =   ''
        locked_cust.cover_size    =   0
        locked_cust.save(update_fields = ['cover_key', 'cover_size', 'updated_at'])
        _consume_quota(locked, locked.storage_used_bytes - freed)
    if old_key:
        _delete_object(old_key)
    customization.cover_key         =   ''
    customization.cover_size        =   0
    store.storage_used_bytes        =   locked.storage_used_bytes
    return customization
#=========================================
# CAROUSEL UPLOAD / DELETE (banners de la web pública)
#=========================================
def carousel_usage(store):
    """(cantidad, bytes) que el carrusel ocupa dentro de la cuota."""
    images      =   store.carousel_images.all()
    return images.count(), sum(image.image_size for image in images)
def upload_carousel_image(store, upload):
    """
    Sube una imagen del carrusel a R2 (normalizada a WebP como la portada)
    y crea el StoreCarouselImage al final del orden. Lanza ValueError si
    el storage no está configurado, el archivo es inválido, se llegó al
    tope o no hay cuota.
    """
    from StoreApp.domains.stores.models import StoreCarouselImage
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    if store.carousel_images.count() >= CAROUSEL_MAX_IMAGES:
        raise ValueError(f'El carrusel admite hasta {CAROUSEL_MAX_IMAGES} imágenes.')
    processed   =   normalize_image(upload, 'carousel')
    size        =   len(processed[0])
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_image_slot(store, is_new = True)
    _check_quota(store, size)
    key         =   _put_object(store, 'carousel', upload, processed)
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            if locked.carousel_images.count() >= CAROUSEL_MAX_IMAGES:
                raise ValueError(f'El carrusel admite hasta {CAROUSEL_MAX_IMAGES} imágenes.')
            _check_image_slot(locked, is_new = True)
            new_used    =   _check_quota(locked, size)
            last        =   locked.carousel_images.order_by('-position').first()
            image       =   StoreCarouselImage.objects.create(
                store       =   locked,
                image_key   =   key,
                image_size  =   size,
                position    =   (last.position + 1) if last else 0,
            )
            _consume_quota(locked, new_used)
    except ValueError:
        _delete_object(key)
        raise
    store.storage_used_bytes        =   locked.storage_used_bytes
    return image
def delete_carousel_image(image):
    """Borra la imagen del carrusel en R2, libera cuota y la elimina."""
    store       =   image.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_img  =   locked.carousel_images.filter(pk = image.pk).first()
        if locked_img is None:
            return
        key         =   locked_img.image_key
        size        =   locked_img.image_size
        locked_img.delete()
        _consume_quota(locked, locked.storage_used_bytes - size)
    _delete_object(key)
    store.storage_used_bytes        =   locked.storage_used_bytes
#=========================================
# GALLERY UPLOAD / DELETE (sección Galería de la web pública)
#=========================================
def upload_gallery_image(store, upload, kind = 'gallery'):
    """
    Sube una imagen de la galería (kind 'gallery') o una decoración de la
    portada (kind 'decor', solo premium, hasta DECOR_MAX_IMAGES) a R2. La
    imagen se normaliza automáticamente (orientación, tamaño, proporción,
    WebP). El tope lo fija el beneficio max_gallery_images del plan
    (0 = sin galería; None = ilimitado) y las decoraciones consumen ese
    mismo cupo. Lanza ValueError si el storage no está configurado, el
    archivo es inválido o no hay cupo/cuota.
    """
    from StoreApp.domains.stores.models import StoreGalleryImage
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    if kind not in StoreGalleryImage.KINDS:
        raise ValueError('Tipo de imagen no válido.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_gallery_slot(store, kind)
    processed   =   normalize_image(upload, 'decor' if kind == StoreGalleryImage.KIND_DECOR else 'gallery')
    size        =   len(processed[0])
    _check_image_slot(store, is_new = True)
    _check_quota(store, size)
    key         =   _put_object(store, 'decor' if kind == StoreGalleryImage.KIND_DECOR else 'gallery', upload, processed)
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            _check_gallery_slot(locked, kind)
            _check_image_slot(locked, is_new = True)
            new_used    =   _check_quota(locked, size)
            last        =   locked.gallery_images.filter(kind = kind).order_by('-position').first()
            image       =   StoreGalleryImage.objects.create(
                store       =   locked,
                kind        =   kind,
                image_key   =   key,
                image_size  =   size,
                position    =   (last.position + 1) if last else 0,
            )
            _consume_quota(locked, new_used)
    except ValueError:
        _delete_object(key)
        raise
    store.storage_used_bytes        =   locked.storage_used_bytes
    return image
def _check_gallery_slot(store, kind):
    """
    Cupo de la galería/decoración bajo el plan vigente (beneficio
    max_gallery_images + flag has_design_advanced para 'decor'). Se usa
    como fast path antes de subir el objeto y otra vez bajo lock de la
    fila — dos requests concurrentes no pueden pasar el tope.
    """
    from StoreApp.domains.stores.models import StoreGalleryImage
    limit       =   gallery_limit(store.user)
    if limit == 0:
        raise ValueError('La galería de imágenes está disponible desde el Plan estándar.')
    if kind == StoreGalleryImage.KIND_DECOR:
        if not plan_benefits_of(store.user).get('has_design_advanced'):
            raise ValueError('Las imágenes decorativas están disponibles en el Plan premium.')
        if store.gallery_images.filter(kind = kind).count() >= DECOR_MAX_IMAGES:
            raise ValueError(f'Podés cargar hasta {DECOR_MAX_IMAGES} imágenes decorativas.')
    if limit is not None and store.gallery_images.count() >= limit:
        raise ValueError(f'Tu plan admite hasta {limit} imágenes entre galería y decoración. Pasá a un plan superior para sumar más.')
def delete_gallery_image(image):
    """Borra la imagen de la galería en R2, libera cuota y la elimina."""
    store       =   image.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_img  =   locked.gallery_images.filter(pk = image.pk).first()
        if locked_img is None:
            return
        key         =   locked_img.image_key
        size        =   locked_img.image_size
        locked_img.delete()
        _consume_quota(locked, locked.storage_used_bytes - size)
    _delete_object(key)
    store.storage_used_bytes        =   locked.storage_used_bytes
#=========================================
# PRODUCT IMAGE UPLOAD / DELETE (catálogo)
#=========================================
def upload_product_image(product, upload):
    """
    Sube/reemplaza la imagen de un producto y ajusta la cuota de la tienda.
    Lanza ValueError con mensaje para el cliente.
    """
    store       =   product.store
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    processed   =   normalize_image(upload, 'product')
    size        =   len(processed[0])
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_image_slot(store, is_new = not product.image_key)
    _check_quota(store, size, replacing_bytes = product.image_size)
    key         =   _put_object(store, 'products', upload, processed)
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            locked_prod =   locked.products.filter(pk = product.pk).first()
            if locked_prod is None:
                raise ValueError('El producto ya no existe.')
            _check_image_slot(locked, is_new = not locked_prod.image_key)
            new_used    =   _check_quota(locked, size, replacing_bytes = locked_prod.image_size)
            old_key     =   locked_prod.image_key
            locked_prod.image_key   =   key
            locked_prod.image_size  =   size
            locked_prod.save(update_fields = ['image_key', 'image_size'])
            _consume_quota(locked, new_used)
    except ValueError:
        _delete_object(key)
        raise
    product.image_key               =   key
    product.image_size              =   size
    store.storage_used_bytes        =   locked.storage_used_bytes
    if old_key:
        _delete_object(old_key)
    return product
def delete_product_image(product):
    """Borra la imagen del producto en R2 y libera la cuota."""
    store       =   product.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_prod =   locked.products.filter(pk = product.pk).first()
        if locked_prod is None:
            return
        old_key     =   locked_prod.image_key
        freed       =   locked_prod.image_size
        locked_prod.image_key   =   ''
        locked_prod.image_size  =   0
        locked_prod.save(update_fields = ['image_key', 'image_size'])
        _consume_quota(locked, locked.storage_used_bytes - freed)
    if old_key:
        _delete_object(old_key)
    product.image_key               =   ''
    product.image_size              =   0
    store.storage_used_bytes        =   locked.storage_used_bytes
    return product
#=========================================
# BRAND IMAGE UPLOAD / DELETE (catálogo)
#=========================================
def upload_brand_image(brand, upload):
    """
    Sube/reemplaza el logo de una marca y ajusta la cuota de la tienda.
    Se normaliza como logo: WebP con transparencia conservada y tamaño
    acotado, así llega a la web con fondo invisible. Lanza ValueError.
    """
    store       =   brand.store
    if not store_storage_configured(store):
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_logo_file(upload)
    if error:
        raise ValueError(error)
    processed   =   normalize_image(upload, 'logo')
    size        =   len(processed[0])
    #Fast path: evita subir el objeto cuando el cupo claramente no da.
    _check_image_slot(store, is_new = not brand.image_key)
    _check_quota(store, size, replacing_bytes = brand.image_size)
    key         =   _put_object(store, 'brands', upload, processed)
    try:
        with transaction.atomic():
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            locked_brand=   locked.brands.filter(pk = brand.pk).first()
            if locked_brand is None:
                raise ValueError('La marca ya no existe.')
            _check_image_slot(locked, is_new = not locked_brand.image_key)
            new_used    =   _check_quota(locked, size, replacing_bytes = locked_brand.image_size)
            old_key     =   locked_brand.image_key
            locked_brand.image_key     =   key
            locked_brand.image_size    =   size
            locked_brand.save(update_fields = ['image_key', 'image_size'])
            _consume_quota(locked, new_used)
    except ValueError:
        _delete_object(key)
        raise
    brand.image_key                 =   key
    brand.image_size                =   size
    store.storage_used_bytes        =   locked.storage_used_bytes
    if old_key:
        _delete_object(old_key)
    return brand
def delete_brand_image(brand):
    """Borra la imagen de la marca en R2 y libera la cuota."""
    store       =   brand.store
    with transaction.atomic():
        locked      =   Store.objects.select_for_update().get(pk = store.pk)
        locked_brand=   locked.brands.filter(pk = brand.pk).first()
        if locked_brand is None:
            return
        old_key     =   locked_brand.image_key
        freed       =   locked_brand.image_size
        locked_brand.image_key     =   ''
        locked_brand.image_size    =   0
        locked_brand.save(update_fields = ['image_key', 'image_size'])
        _consume_quota(locked, locked.storage_used_bytes - freed)
    if old_key:
        _delete_object(old_key)
    brand.image_key                 =   ''
    brand.image_size                =   0
    store.storage_used_bytes        =   locked.storage_used_bytes
    return brand
