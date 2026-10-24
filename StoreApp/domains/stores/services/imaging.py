import io
import os
import tempfile
import threading
import requests
from decouple import config
from PIL import Image, ImageOps, UnidentifiedImageError
"""

Procesado automático de imágenes del cliente (Pillow, server-side).

- normalize_image: corrige orientación EXIF, acota el tamaño, aplana la
  transparencia sobre blanco (productos/portada/carrusel; el logo conserva
  el alfa) y recodifica a WebP optimizado — toda imagen del cliente entra
  a R2 ya comprimida en el formato estándar de la web. La
  galería/decoración además acota la proporción (paisajes/capturas extremas)
  para que siempre encajen en la grilla de la web pública.
- remove_background: quita el fondo de un producto con U²-Net (onnxruntime,
  licencia Apache-2.0) y lo reemplaza por blanco sobre un lienzo cuadrado.
  El modelo se descarga una vez (BG_MODEL_URL) y queda en caché en disco.

"""
Image.MAX_IMAGE_PIXELS  =   40_000_000
WEBP_QUALITY            =   86
MAX_SIDE_GALLERY        =   1600
MAX_SIDE_PRODUCT        =   1200
PRODUCT_CANVAS          =   1000
MAX_SIDE_COVER          =   2200
MAX_SIDE_LOGO           =   800
COVER_MIN_RATIO         =   1.0               # portadas verticales se recortan a cuadrado (el hero es apaisado)
GALLERY_RATIO           =   (3 / 4, 16 / 9)   # (alto máximo relativo, ancho máximo relativo)
BG_MODEL_URL            =   'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx'
BG_MODEL_SIZE           =   320
_bg_lock                =   threading.Lock()
_bg_session             =   None
INVALID_IMAGE           =   'El archivo no es una imagen válida.'
def _open(upload):
    try:
        upload.seek(0)
        image       =   Image.open(upload)
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise ValueError(INVALID_IMAGE)
    return ImageOps.exif_transpose(image)
def _flatten_white(image):
    """RGB sobre fondo blanco (descarta el canal alfa sin dejar bordes negros)."""
    image           =   image.convert('RGBA')
    canvas          =   Image.new('RGBA', image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    return canvas.convert('RGB')
def _clamp_ratio(image):
    width, height   =   image.size
    ratio           =   width / height
    low, high       =   GALLERY_RATIO
    if ratio > high:
        return ImageOps.fit(image, (int(height * high), height), method = Image.LANCZOS, centering = (0.5, 0.5))
    if ratio < low:
        return ImageOps.fit(image, (width, int(width / low)), method = Image.LANCZOS, centering = (0.5, 0.35))
    return image
def _encode(image):
    buffer          =   io.BytesIO()
    # method=6: máximo esfuerzo de compresión (más lento, archivos menores).
    image.save(buffer, format = 'WEBP', quality = WEBP_QUALITY, method = 6)
    return buffer.getvalue()
def normalize_image(upload, kind = 'gallery'):
    """
    Devuelve (bytes, 'webp', 'image/webp') listo para subir a R2.
    kind: 'gallery' | 'decor' (acota proporción, conserva color), 'logo'
    (conserva la transparencia) o 'product' | 'cover' | 'carousel'
    (aplana sobre blanco). Lanza ValueError si no es una imagen legible.
    """
    image           =   _open(upload)
    if kind == 'product':
        image       =   _flatten_white(image)
        max_side    =   MAX_SIDE_PRODUCT
    elif kind == 'logo':
        # Los logos suelen venir en PNG transparente: el alfa viaja al WebP.
        image       =   image.convert('RGBA') if 'A' in image.getbands() else image.convert('RGB')
        max_side    =   MAX_SIDE_LOGO
    elif kind in ('cover', 'carousel'):
        image       =   _flatten_white(image)
        width, height   =   image.size
        if width / height < COVER_MIN_RATIO:
            image   =   ImageOps.fit(image, (width, int(width / COVER_MIN_RATIO)), method = Image.LANCZOS, centering = (0.5, 0.4))
        max_side    =   MAX_SIDE_COVER
    else:
        image       =   image.convert('RGBA') if 'A' in image.getbands() else image.convert('RGB')
        image       =   _clamp_ratio(image)
        max_side    =   MAX_SIDE_GALLERY
    image.thumbnail((max_side, max_side), Image.LANCZOS)
    return _encode(image), 'webp', 'image/webp'
#=========================================
# BACKGROUND REMOVAL (U²-Net / onnxruntime)
#=========================================
def _model_path():
    return os.path.join(tempfile.gettempdir(), 'davent_bg_model.onnx')
def _session():
    global _bg_session
    if _bg_session is not None:
        return _bg_session
    with _bg_lock:
        if _bg_session is not None:
            return _bg_session
        try:
            import onnxruntime
            path    =   _model_path()
            if not os.path.exists(path):
                response    =   requests.get(config('BG_MODEL_URL', default = BG_MODEL_URL), timeout = 120)
                response.raise_for_status()
                with open(path + '.tmp', 'wb') as handle:
                    handle.write(response.content)
                os.replace(path + '.tmp', path)
            _bg_session =   onnxruntime.InferenceSession(path, providers = ['CPUExecutionProvider'])
        except Exception:
            raise ValueError('El editor de fondo no está disponible en este momento. Probá más tarde.')
    return _bg_session
def _subject_mask(image):
    import numpy as np
    session         =   _session()
    small           =   image.convert('RGB').resize((BG_MODEL_SIZE, BG_MODEL_SIZE), Image.LANCZOS)
    array           =   np.asarray(small, dtype = np.float32)
    array           =   array / max(float(array.max()), 1e-6)
    array           =   (array - np.array([0.485, 0.456, 0.406], dtype = np.float32)) / np.array([0.229, 0.224, 0.225], dtype = np.float32)
    tensor          =   array.transpose(2, 0, 1)[None].astype(np.float32)
    output          =   session.run(None, {session.get_inputs()[0].name: tensor})[0][0, 0]
    low, high       =   float(output.min()), float(output.max())
    output          =   (output - low) / max(high - low, 1e-6)
    mask            =   Image.fromarray((output * 255).astype('uint8'), mode = 'L')
    return mask.resize(image.size, Image.LANCZOS)
def remove_background(upload):
    """
    Quita el fondo y centra el producto sobre un lienzo blanco cuadrado.
    Devuelve (bytes PNG, 'png', 'image/png'). ValueError es-AR si no se
    detecta un objeto o el modelo no está disponible.
    """
    image           =   _flatten_white(_open(upload))
    image.thumbnail((MAX_SIDE_PRODUCT, MAX_SIDE_PRODUCT), Image.LANCZOS)
    mask            =   _subject_mask(image).point(lambda v: 0 if v < 40 else (255 if v > 215 else int((v - 40) * 255 / 175)))
    box             =   mask.point(lambda v: 255 if v > 128 else 0).getbbox()
    if not box or (box[2] - box[0]) * (box[3] - box[1]) < 0.02 * image.size[0] * image.size[1]:
        raise ValueError('No pudimos detectar el producto en la imagen. Probá con una foto con el objeto más a la vista.')
    cutout          =   image.convert('RGBA')
    cutout.putalpha(mask)
    cutout          =   cutout.crop(box)
    target          =   int(PRODUCT_CANVAS * 0.88)
    cutout.thumbnail((target, target), Image.LANCZOS)
    canvas          =   Image.new('RGBA', (PRODUCT_CANVAS, PRODUCT_CANVAS), (255, 255, 255, 255))
    canvas.alpha_composite(cutout, ((PRODUCT_CANVAS - cutout.width) // 2, (PRODUCT_CANVAS - cutout.height) // 2))
    buffer          =   io.BytesIO()
    canvas.convert('RGB').save(buffer, format = 'PNG', optimize = True)
    return buffer.getvalue(), 'png', 'image/png'
