"""
Adjuntos de imagen del chat de soporte.

El archivo NUNCA se guarda como blob en la base: se sube al bucket (R2)
o, en entornos sin storage configurado, al disco bajo MEDIA_ROOT — en la
DB solo viaja ``ChatMessage.image_key``. Cada parte del chat tiene el
archivo en su PC: el emisor lo adjunta desde su disco y el receptor lo
descarga del URL. Reutiliza la capa de storage e imágenes del dominio de
tiendas: el adjunto sale normalizado a WebP, con la orientación EXIF
corregida y sin metadatos de ubicación.
"""
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from StoreApp.domains.stores.services import imaging, storage

def upload_chat_image(thread, upload):
    """
    Valida, normaliza y sube el adjunto. Devuelve la key a persistir en
    ``ChatMessage.image_key`` — nunca el archivo en sí. Lanza ValueError
    con el motivo si la imagen no es válida o la subida falla.
    """
    error       =   storage.validate_image_file(upload)
    if error:
        raise ValueError(error)
    body, ext, content_type =   imaging.normalize_image(upload, 'chat')
    key         =   f'chat/{thread.id}/{uuid4().hex}.{ext}'
    if storage.storage_configured():
        storage.put_object(key, body, content_type)
    else:
        # Sin R2 (dev local / VPS sin bucket): el archivo va al disco del
        # servidor bajo MEDIA_ROOT — jamás a la base de datos.
        key     =   default_storage.save(key, ContentFile(body))
    return key


def chat_image_url(request, message):
    """
    Resuelve el URL visible del adjunto: público o firmado del bucket, o
    el path de MEDIA local en dev. '' cuando el mensaje no tiene imagen.
    """
    if not message.image_key:
        return ''
    url         =   storage.object_url(message.image_key)
    if url:
        return url
    media       =   f'/{settings.MEDIA_URL}{message.image_key}'
    return request.build_absolute_uri(media) if request else media
