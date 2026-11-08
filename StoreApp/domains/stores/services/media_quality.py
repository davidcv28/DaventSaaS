"""
Calidad mínima de las fotos por slot de la web pública (aviso, nunca rechazo).

- inspect(upload, slot): lee solo la cabecera de la imagen (sin decodificar
  píxeles), corrige la orientación EXIF y devuelve {width, height, ratio,
  soft, ratio_ok, ...}. `soft` = el lado útil para el slot queda por debajo
  de 1.5× el tamaño de render (los umbrales de SLOT_SPECS ya vienen con ese
  factor aplicado: son el lado fuente mínimo recomendado, no el de render).
- quality(upload, kind): mismo veredicto empaquetado como
  {ok, soft, hint} para viajar en la respuesta del upload. `ok` es False solo
  como aviso — el archivo se acepta igual (regla del repo: nunca rechazar
  por calidad, solo avisar).

El "lado útil" es el ancho que sobrevive al recorte `object-fit: cover` del
slot: min(ancho, alto × aspecto_del_slot). Para slots cuadrados equivale a
min(ancho, alto); para la portada (apaisada) una panorámica conserva más
largo útil que su lado menor.

Nada de esto bloquea la subida: es feedback para que el dueño suba una foto
mejor antes de que la web se vea amateur.
"""
import contextlib

from PIL import Image, UnidentifiedImageError

from .imaging import INVALID_IMAGE
#=========================================
# SLOTS (tabla única de umbrales)
#=========================================
# min_side : lado fuente mínimo recomendado (= 1.5 × lado largo de render).
# aspect   : proporción w/h aproximada del lugar donde se muestra la imagen
#            (object-fit: cover en tarjetas/portada; ≈1 en encuadres cuadrados).
# ratio    : rango (min, max) de w/h tolerado antes de sugerir recorte.
SLOT_SPECS = {
    'cover'   : {
        'label'     :   'la portada',
        'min_side'  :   2200,
        'aspect'    :   16 / 9,
        'ratio'     :   (1.0, 2.5),
        'crop_hint' :   'conviene recortar la imagen a formato horizontal, tipo 3:2 o 16:9',
    },
    'product' : {
        'label'     :   'la foto del producto',
        'min_side'  :   1200,
        'aspect'    :   1.0,
        'ratio'     :   (0.75, 1.5),
        'crop_hint' :   'conviene recortar la imagen a formato casi cuadrado, como se ve en las tarjetas',
    },
    'logo'    : {
        'label'     :   'el logo',
        'min_side'  :   800,
        'aspect'    :   1.0,
        'ratio'     :   (0.5, 2.5),
        'crop_hint' :   'conviene recortar el logo a formato cuadrado o horizontal no muy alargado',
    },
    'gallery' : {
        'label'     :   'la foto de la galería',
        'min_side'  :   1600,
        'aspect'    :   1.0,
        'ratio'     :   (0.75, 16 / 9),
        'crop_hint' :   'la grilla la recorta sola; si podés, encuadrala entre 3:4 y 16:9',
    },
}
# kind de normalize_image -> slot de calidad. 'chat' (adjuntos de soporte)
# y cualquier kind desconocido no tienen slot: quality() devuelve ok neutro.
KIND_TO_SLOT = {
    'cover'      :   'cover',
    'carousel'   :   'cover',
    'product'    :   'product',
    'logo'       :   'logo',
    'gallery'    :   'gallery',
    'decor'      :   'gallery',
    'ai_gallery' :   'gallery',
}
_EXIF_ORIENTATION  =   0x0112
_TRANSPOSED        =   {5, 6, 7, 8}   # orientaciones que invierten ancho/alto
#=========================================
# INSPECCIÓN (solo cabecera: no decodifica la imagen)
#=========================================
def _open_size(upload):
    """
    (ancho, alto) ya corregidos por orientación EXIF, sin load() completo.
    Lanza ValueError(INVALID_IMAGE) si el archivo no es una imagen legible.
    """
    try:
        upload.seek(0)
        image           =   Image.open(upload)
        width, height   =   image.size
        try:
            orientation  =   image.getexif().get(_EXIF_ORIENTATION) or 1
        except Exception:
            orientation  =   1
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise ValueError(INVALID_IMAGE)
    finally:
        with contextlib.suppress(Exception):
            upload.seek(0)
    if orientation in _TRANSPOSED:
        width, height   =   height, width
    return width, height
def inspect(upload, slot = 'gallery'):
    """
    Devuelve {slot, width, height, ratio, usable, min_side, soft, ratio_ok}
    para el slot pedido. No modifica el upload (seek(0) al entrar y al salir).
    """
    spec            =   SLOT_SPECS.get(slot)
    if spec is None:
        raise ValueError(f'Slot de imagen desconocido: {slot}')
    width, height   =   _open_size(upload)
    ratio           =   round(width / height, 3)
    usable          =   min(width, height * spec['aspect'])
    lo, hi          =   spec['ratio']
    return {
        'slot'      :   slot,
        'width'     :   width,
        'height'    :   height,
        'ratio'     :   ratio,
        'usable'    :   int(usable),
        'min_side'  :   spec['min_side'],
        'soft'      :   usable < spec['min_side'],
        'ratio_ok'  :   lo <= ratio <= hi,
    }
def _hint(info, spec):
    parts           =   []
    if info['soft']:
        parts.append(f'Se va a ver borrosa en pantalla grande: usá una foto de al menos {spec["min_side"]} px de lado útil para {spec["label"]}.')
    if not info['ratio_ok']:
        parts.append(f'Para que encuadre mejor en {spec["label"]}, {spec["crop_hint"]}.')
    return ' '.join(parts)
def quality(upload, kind = 'gallery'):
    """
    Veredicto para la respuesta del upload: {ok, soft, hint}.
    `ok` es False solo como aviso (imagen chica o fuera de proporción);
    NUNCA rechaza el archivo — la subida sigue su curso igual.
    Kinds sin slot ('chat', desconocidos) devuelven ok neutro.
    """
    slot            =   KIND_TO_SLOT.get(kind)
    if slot is None:
        return {'ok': True, 'soft': False, 'hint': ''}
    info            =   inspect(upload, slot)
    spec            =   SLOT_SPECS[slot]
    return {
        'ok'        :   not info['soft'] and info['ratio_ok'],
        'soft'      :   info['soft'],
        'hint'      :   _hint(info, spec),
    }
