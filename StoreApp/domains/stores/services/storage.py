import uuid
import boto3
from botocore.config import Config as BotoConfig
from decouple import config
from django.db import transaction
from StoreApp.domains.stores.models import Store
from .services import plan_benefits_of
from .imaging  import normalize_image
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

"""
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
def _client():
    return boto3.client(
        's3',
        endpoint_url          =   _endpoint(),
        aws_access_key_id     =   config('R2_ACCESS_KEY_ID', default = ''),
        aws_secret_access_key =   config('R2_SECRET_ACCESS_KEY', default = ''),
        region_name           =   'auto',
        config                =   BotoConfig(signature_version = 's3v4'),
    )
#=========================================
# OBJECT URL (delivery pública)
#=========================================
def object_url(key):
    """
    URL servible del objeto. Si el bucket tiene URL pública configurada
    (R2_PUBLIC_URL) la usa; si no, devuelve una URL firmada de lectura
    (válida PRESIGNED_TTL_SECONDS). Devuelve None sin key o sin config.
    """
    if not key or not storage_configured():
        return None
    base        =   _public_base()
    if base:
        return f'{base}/{key}'
    try:
        return _client().generate_presigned_url(
            'get_object',
            Params      =   {'Bucket': _bucket(), 'Key': key},
            ExpiresIn   =   PRESIGNED_TTL_SECONDS,
        )
    except Exception:
        return None
def _delete_object(key):
    if not key or not storage_configured():
        return
    try:
        _client().delete_object(Bucket = _bucket(), Key = key)
    except Exception:
        # El objeto huérfano no bloquea el flujo; la cuota ya se liberó en DB.
        pass
def put_object(key, body, content_type):
    """
    Sube bytes arbitrarios al bucket bajo una key explícita (adjuntos que
    no pertenecen a una tienda — p.ej. imágenes del chat de soporte, sin
    cupo por tienda). Lanza ValueError si la subida falla.
    """
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
    Sube un archivo ya validado a R2 y devuelve la key persistible.
    `processed` = (bytes, ext, content_type) si la imagen se recodificó.
    Lanza ValueError si la subida falla.
    """
    if processed is None:
        ext, content_type   =   _IMAGE_CONTENT_TYPES[upload.content_type]
        body                =   upload.read()
    else:
        body, ext, content_type =   processed
    key                 =   f'stores/{store.id}/{folder}/{uuid.uuid4().hex}.{ext}'
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
    """Cantidad de imágenes que ocupan cuota: logo + carrusel + galería + productos."""
    #_n_product_images viene anotado en el queryset del listado y los count()
    #de carrusel/galería usan el prefetch: sin eso sumaban 3 queries por tienda.
    products    =   getattr(store, '_n_product_images', None)
    if products is None:
        products    =   store.products.exclude(image_key = '').count()
    count           =   store.carousel_images.count() + store.gallery_images.count() + products
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
    if not storage_configured():
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_logo_file(upload)
    if error:
        raise ValueError(error)
    store       =   customization.store
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
    if not storage_configured():
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    store       =   customization.store
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
    if not storage_configured():
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
    if not storage_configured():
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
    if not storage_configured():
        raise ValueError('El almacenamiento de imágenes no está configurado. Avisale a soporte.')
    error       =   validate_image_file(upload, IMAGE_MAX_BYTES)
    if error:
        raise ValueError(error)
    store       =   product.store
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
