#=========================================
# TEMPLATE BLOCKS — catálogo cerrado del editor de layout
#=========================================
#`layout_config` de StoreCustomization guarda, por superficie de la web
#pública, la lista de bloques que el dueño activó/ordenó:
#    { surface: { blocks: [{id, enabled, order, variant?, props?}] } }
#Las superficies son 'landing', 'catalog' y 'services'. Cada id de bloque,
#variante y prop pertenece a este catálogo: lo que no esté declarado se
#descarta (nunca CSS/HTML libre del usuario — mismo criterio que el resto
#de la personalización).
#Los layouts por defecto de cada plantilla viven en el frontend
#(frontend/src/templates/<id>/index.js): acá solo se valida la forma. Si
#la config falta o es inválida, la web pública cae al layout default de la
#plantilla — nunca rompe.
#`premium`: el bloque se descarta sin el beneficio has_design_advanced.
#`locked`: bloque estructural, no se puede apagar desde el editor (la
#validación lo fuerza a enabled=True si llega desactivado).
#`variants`: catálogo cerrado de variantes del bloque; una variante
#desconocida se descarta y el bloque queda en su variante default (la
#primera declarada).
#`props`: campos de texto propios del bloque (hoy solo 'title', override
#del título de la sección); se sanitizan a texto plano acotado.

import json
import re

from django.utils.html     import strip_tags
from rest_framework        import serializers

LAYOUT_SURFACES             =   ('landing', 'catalog', 'services')
LAYOUT_MAX_BYTES            =   8192
LAYOUT_MAX_BLOCKS           =   24
LAYOUT_MAX_PROPS            =   4
LAYOUT_PROP_MAX             =   80

_TITLE_PROPS                =   {'title': LAYOUT_PROP_MAX}

TEMPLATE_BLOCKS             =   {
    'landing': {
        'hero':            {'label': 'Portada',                'variants': ('full', 'compact', 'centered', 'split', 'cinema', 'editorial', 'search', 'slides')},
        'announcements':   {'label': 'Cinta de anuncios',      'variants': ('marquee', 'static')},
        'highlights':      {'label': 'Etiquetas destacadas'},
        'categories':      {'label': 'Departamentos',          'variants': ('row', 'rail'), 'props': _TITLE_PROPS},
        'featured':        {'label': 'Vitrina de productos',   'variants': ('grid', 'cols2', 'cols3', 'cols4', 'masonry', 'rail', 'lead', 'cats', 'quick'), 'props': _TITLE_PROPS},
        'about':           {'label': 'Sobre nosotros',         'props': _TITLE_PROPS},
        'services':        {'label': 'Qué ofrecemos',          'props': _TITLE_PROPS},
        'stats':           {'label': 'Cifras del negocio',     'variants': ('band', 'cards'), 'props': _TITLE_PROPS},
        'benefits':        {'label': 'Garantías',              'variants': ('cards', 'bento'), 'props': _TITLE_PROPS},
        'offers':          {'label': 'Ofertas',                'variants': ('grid', 'rail', 'quick'), 'props': _TITLE_PROPS},
        'brands':          {'label': 'Marcas',                 'variants': ('marquee', 'logos'), 'props': _TITLE_PROPS},
        'countdown':       {'label': 'Cuenta regresiva',       'variants': ('card', 'band')},
        'timeline':        {'label': 'Trayectoria',            'props': _TITLE_PROPS},
        'team':            {'label': 'Equipo',                 'props': _TITLE_PROPS},
        'gallery':         {'label': 'Galería',                'variants': ('grid', 'masonry', 'rail'), 'props': _TITLE_PROPS},
        'testimonials':    {'label': 'Testimonios',            'variants': ('cards', 'carousel', 'masonry'), 'props': _TITLE_PROPS},
        'faq':             {'label': 'Preguntas frecuentes',   'variants': ('accordion', 'cols', 'list'), 'props': _TITLE_PROPS},
        'video':           {'label': 'Video',                  'props': _TITLE_PROPS},
        'steps':           {'label': 'Cómo funciona',          'props': _TITLE_PROPS},
        'compare':         {'label': 'Comparativa'},
        'cta':             {'label': 'Llamado a la acción',    'variants': ('card', 'band'), 'props': {'title': 120}},
        'contact':         {'label': 'Contacto',               'variants': ('card', 'map'), 'props': _TITLE_PROPS},
    },
    'catalog': {
        'note':            {'label': 'Aviso del catálogo'},
        'banner':          {'label': 'Carrusel de portada',    'premium': True},
        'promo':           {'label': 'Promociones vigentes'},
        'filters':         {'label': 'Filtros',                'variants': ('panel', 'chips')},
        'sort':            {'label': 'Ordenamiento'},
        'grid':            {'label': 'Grilla de productos',    'variants': ('auto', 'cols2', 'cols3', 'cols4', 'masonry', 'list', 'lead', 'quick'), 'locked': True},
    },
    'services': {
        'hero':            {'label': 'Portada'},
        'band':            {'label': 'Cinta de servicios'},
        'picker':          {'label': 'Selector y presupuesto', 'locked': True},
        'steps':           {'label': 'Cómo funciona'},
        'form':            {'label': 'Formulario de pedido'},
        'faq':             {'label': 'Preguntas frecuentes'},
    },
}

_WS_RUN                     =   re.compile(r'\s+')

def _clean_text(raw, max_len):
    #Texto de un prop: etiquetas fuera, espacios colapsados, corte al tope.
    text                    =   strip_tags(str(raw or ''))
    return _WS_RUN.sub(' ', text).strip()[:max_len]

def _clean_props(raw, allowed):
    if not isinstance(raw, dict):
        return None
    clean                   =   {}
    for key, value in raw.items():
        if key not in allowed or len(clean) >= LAYOUT_MAX_PROPS:
            continue
        text                =   _clean_text(value, allowed[key])
        if text:
            clean[key]      =   text
    return clean or None

def _order_key(pair):
    #El orden declarado en 'order' (int) ordena la lista; los que llegan
    #sin order válido quedan al final en su posición relativa (sort
    #estable). 'order' bool cuenta como ausente (True es int en Python).
    idx, item               =   pair
    order                   =   item.get('order')
    if isinstance(order, bool) or not isinstance(order, int):
        return (1, 0, idx)
    return (0, order, idx)

def _clean_blocks(raw_blocks, surface, has_advanced):
    if not isinstance(raw_blocks, list):
        return []
    indexed                 =   [(i, item) for i, item in enumerate(raw_blocks[:LAYOUT_MAX_BLOCKS]) if isinstance(item, dict)]
    indexed.sort(key        =   _order_key)
    seen, clean             =   set(), []
    for _, item in indexed:
        block_id            =   str(item.get('id') or '').strip()
        spec                =   TEMPLATE_BLOCKS[surface].get(block_id)
        #IDs desconocidos y repetidos se descartan; premium sin el
        #beneficio también (fail-closed al plan vigente).
        if spec is None or block_id in seen:
            continue
        if spec.get('premium') and not has_advanced:
            continue
        seen.add(block_id)
        block               =   {'id': block_id, 'enabled': bool(item.get('enabled', True)) or spec.get('locked', False), 'order': len(clean)}
        variants            =   spec.get('variants')
        variant             =   str(item.get('variant') or '').strip()
        if variants and variant and variant != variants[0]:
            if variant in variants[1:]:
                block['variant']    =   variant
            #variante desconocida: se descarta, queda la default.
        props               =   _clean_props(item.get('props'), spec.get('props') or {})
        if props:
            block['props']  =   props
        clean.append(block)
    return clean

def clean_layout_config(value, has_design_advanced):
    """
    Normaliza `layout_config` contra TEMPLATE_BLOCKS.
    Devuelve {surface: {'blocks': [...]}} solo con superficies válidas;
    una config vacía o irreconocible queda en {} y la web pública cae al
    layout por defecto de la plantilla (fail-safe, nunca rompe).
    """
    if not isinstance(value, dict):
        raise serializers.ValidationError('Debe ser un objeto {superficie: {blocks: [...]}}.')
    try:
        if len(json.dumps(value)) > LAYOUT_MAX_BYTES:
            raise serializers.ValidationError('La configuración de bloques es demasiado grande.')
    except (TypeError, ValueError):
        raise serializers.ValidationError('La configuración de bloques no es JSON válido.')
    clean                   =   {}
    for surface in LAYOUT_SURFACES:
        raw                 =   value.get(surface)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            continue
        blocks              =   _clean_blocks(raw.get('blocks'), surface, has_design_advanced)
        if blocks:
            clean[surface]  =   {'blocks': blocks}
    return clean
