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
#`props`: campos propios del bloque. Un entero es un texto plano con ese
#tope; una tupla ('icon_list'|'text_list'|'icon_cards', max) es una lista
#tipada de items (también texto plano, iconos de AI_ICONS). Todo se
#sanitiza y se recorta: nunca HTML ni CSS libre.
#`ai_only`: bloque exclusivo de "Diseñar con IA" — se descarta sin el
#beneficio has_ai_design (mismo patrón fail-closed que `premium`).

import json
import re

from django.utils.html     import strip_tags
from rest_framework        import serializers

LAYOUT_SURFACES             =   ('landing', 'catalog', 'services')
LAYOUT_MAX_BYTES            =   8192
LAYOUT_MAX_BLOCKS           =   24
LAYOUT_MAX_PROPS            =   4
LAYOUT_PROP_MAX             =   80
LAYOUT_ITEM_TITLE_MAX       =   40
LAYOUT_ITEM_TEXT_MAX        =   90
LAYOUT_ITEM_LABEL_MAX       =   40
#Bloques v4: precios (aipricing), pasos (aiprocess) y mosaico (aimosaic).
LAYOUT_PRICE_MAX            =   20
LAYOUT_PRICE_NOTE_MAX       =   80
LAYOUT_PRICE_ITEM_MAX       =   60
LAYOUT_PROCESS_TITLE_MAX    =   60
LAYOUT_PROCESS_TEXT_MAX     =   160
LAYOUT_CAPTION_MAX          =   120

#Catálogo cerrado de iconos de los bloques solo-IA (Lucide, ISC). La lista
#está CONGELADA contra lo que bundlea el frontend (frontend/src/assets/
#icons/lucide): un nombre que no exista ahí se descarta. Además se aceptan
#los GENERADOS ("gen:<slug>": el frontend dibuja un glifo geométrico
#determinístico desde el hash del slug cuando el concepto no existe).
AI_ICONS                    =   frozenset({
    'activity', 'anchor', 'apple', 'archive', 'award', 'baby',
    'badge-check', 'beer', 'bike', 'bone', 'book-open', 'box',
    'briefcase', 'brush', 'building-2', 'bus', 'cake', 'calculator',
    'calendar', 'camera', 'car', 'carrot', 'cat', 'chart-line',
    'check-circle', 'chef-hat', 'clock', 'code', 'coffee', 'compass',
    'cpu', 'credit-card', 'cup-soda', 'database', 'dog', 'droplet',
    'dumbbell', 'factory', 'file-text', 'film', 'filter', 'flag',
    'flame', 'flower', 'folder', 'fuel', 'gamepad', 'gift',
    'globe', 'graduation-cap', 'grid', 'hammer', 'handshake', 'headphones',
    'heart', 'home', 'hotel', 'id-card', 'images', 'key',
    'laptop', 'layers', 'leaf', 'lock', 'mail', 'map-pin',
    'medal', 'message-circle', 'mic', 'monitor', 'moon', 'mountain',
    'music', 'package', 'palette', 'parking', 'paw-print', 'pen-tool',
    'percent', 'phone', 'pill', 'pizza', 'plane', 'printer',
    'puzzle', 'qr-code', 'quote', 'radio', 'receipt', 'route',
    'ruler', 'scan-line', 'scissors', 'search', 'server', 'settings',
    'shield-check', 'shirt', 'shopping-bag', 'shopping-cart', 'sliders', 'smartphone',
    'snowflake', 'sparkles', 'speaker', 'star', 'stethoscope', 'store',
    'sun', 'sun-medium', 'syringe', 'tag', 'target', 'terminal',
    'thermometer', 'ticket', 'train', 'tree', 'trending-up', 'trophy',
    'truck', 'tv', 'users', 'utensils', 'video', 'wallet',
    'warehouse', 'wifi', 'wind', 'wine', 'wrench', 'zap',
})
AI_GENERATED_ICON_RE        =   re.compile(r'^gen:[a-z0-9-]{1,24}$')

_TITLE_PROPS                =   {'title': LAYOUT_PROP_MAX}

TEMPLATE_BLOCKS             =   {
    'landing': {
        'hero':            {'label': 'Portada',                'variants': ('full', 'compact', 'centered', 'split', 'cinema', 'editorial', 'search', 'slides', 'logo')},
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
        #Bloques exclusivos de "Diseñar con IA" (has_ai_design): suman
        #elementos de contenido que el editor manual no ofrece.
        'aiquote':         {'label': 'Cita destacada',         'variants': ('centered', 'split'), 'props': {'text': 160, 'author': 40}, 'ai_only': True},
        'aistrip':         {'label': 'Datos rápidos',          'variants': ('band', 'cards'), 'props': {'items': ('icon_list', 4)}, 'ai_only': True},
        'aicheck':         {'label': 'Lista de verificación',  'variants': ('cards', 'list'), 'props': {'title': LAYOUT_PROP_MAX, 'items': ('text_list', 6)}, 'ai_only': True},
        'aigrid':          {'label': 'Grilla de servicios',    'variants': ('grid2', 'grid3', 'grid4'), 'props': {'title': LAYOUT_PROP_MAX, 'items': ('icon_cards', 6)}, 'ai_only': True},
        'aiband':          {'label': 'Banda destacada',        'variants': ('band', 'card'), 'props': {'title': LAYOUT_PROP_MAX, 'text': 160, 'label': 40}, 'ai_only': True},
        'aipricing':       {'label': 'Precios y planes',       'variants': ('cards', 'table'), 'props': {'title': LAYOUT_PROP_MAX, 'items': ('pricing_list', 4)}, 'ai_only': True},
        'aiprocess':       {'label': 'Cómo trabajamos',        'variants': ('steps', 'rail'), 'props': {'title': LAYOUT_PROP_MAX, 'items': ('process_list', 5)}, 'ai_only': True},
        'aimosaic':        {'label': 'Mosaico de fotos',       'variants': ('mosaic', 'rail'), 'props': {'title': LAYOUT_PROP_MAX, 'caption': LAYOUT_CAPTION_MAX}, 'ai_only': True},
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

def _clean_icon(raw):
    #Icono del catálogo o generado ("gen:<slug>"); lo demás se descarta.
    icon                    =   str(raw or '').strip().lower()
    if icon in AI_ICONS or AI_GENERATED_ICON_RE.match(icon):
        return icon
    return None

def _clean_icon_list(raw, max_items):
    #aistrip: [{icon?, label}] — el item sin label no aporta nada y se va.
    if not isinstance(raw, list):
        return None
    items                   =   []
    for entry in raw[:max_items]:
        if not isinstance(entry, dict):
            continue
        label               =   _clean_text(entry.get('label'), LAYOUT_ITEM_LABEL_MAX)
        if not label:
            continue
        icon                =   _clean_icon(entry.get('icon'))
        items.append({'label': label, **({'icon': icon} if icon else {})})
    return items or None

def _clean_text_list(raw, max_items):
    #aicheck: [{text}] — solo texto plano, sin iconos.
    if not isinstance(raw, list):
        return None
    items                   =   []
    for entry in raw[:max_items]:
        if not isinstance(entry, dict):
            continue
        text                =   _clean_text(entry.get('text'), LAYOUT_ITEM_TEXT_MAX)
        if text:
            items.append({'text': text})
    return items or None

def _clean_icon_cards(raw, max_items):
    #aigrid: [{icon?, title, text?}] — título o texto, icono opcional.
    if not isinstance(raw, list):
        return None
    items                   =   []
    for entry in raw[:max_items]:
        if not isinstance(entry, dict):
            continue
        title               =   _clean_text(entry.get('title'), LAYOUT_ITEM_TITLE_MAX)
        text                =   _clean_text(entry.get('text'), LAYOUT_ITEM_TEXT_MAX)
        if not (title or text):
            continue
        item                =   {'title': title} if title else {}
        icon                =   _clean_icon(entry.get('icon'))
        if icon:
            item['icon']    =   icon
        if text:
            item['text']    =   text
        items.append(item)
    return items or None

def _clean_price_list(raw, max_items):
    #aipricing: [{name, price, note?, items?[text]}] — 2 a 4 filas con
    #nombre y precio; sin precio la fila no aporta y se va.
    if not isinstance(raw, list):
        return None
    items                   =   []
    for entry in raw[:max_items]:
        if not isinstance(entry, dict):
            continue
        name                =   _clean_text(entry.get('name'), LAYOUT_ITEM_TITLE_MAX)
        price               =   _clean_text(entry.get('price'), LAYOUT_PRICE_MAX)
        if not (name and price):
            continue
        item                =   {'name': name, 'price': price}
        note                =   _clean_text(entry.get('note'), LAYOUT_PRICE_NOTE_MAX)
        if note:
            item['note']    =   note
        features            =   []
        for feature in (entry.get('items') or [])[:5] if isinstance(entry.get('items'), list) else []:
            text            =   _clean_text(feature, LAYOUT_PRICE_ITEM_MAX)
            if text:
                features.append(text)
        if features:
            item['items']   =   features
        items.append(item)
    return items if len(items) >= 2 else None


def _clean_process_list(raw, max_items):
    #aiprocess: [{title, text?}] — 3 a 5 pasos con título.
    if not isinstance(raw, list):
        return None
    items                   =   []
    for entry in raw[:max_items]:
        if not isinstance(entry, dict):
            continue
        title               =   _clean_text(entry.get('title'), LAYOUT_PROCESS_TITLE_MAX)
        if not title:
            continue
        text                =   _clean_text(entry.get('text'), LAYOUT_PROCESS_TEXT_MAX)
        items.append({'title': title, **({'text': text} if text else {})})
    return items if len(items) >= 3 else None


_LIST_CLEANERS              =   {
    'icon_list'     :   _clean_icon_list,
    'text_list'     :   _clean_text_list,
    'icon_cards'    :   _clean_icon_cards,
    'pricing_list'  :   _clean_price_list,
    'process_list'  :   _clean_process_list,
}

def _clean_props(raw, allowed):
    if not isinstance(raw, dict):
        return None
    clean                   =   {}
    for key, value in raw.items():
        if key not in allowed or len(clean) >= LAYOUT_MAX_PROPS:
            continue
        spec                =   allowed[key]
        if isinstance(spec, tuple):
            items           =   _LIST_CLEANERS[spec[0]](value, spec[1])
            if items:
                clean[key]  =   items
            continue
        text                =   _clean_text(value, spec)
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

def _clean_blocks(raw_blocks, surface, has_advanced, has_ai = False):
    if not isinstance(raw_blocks, list):
        return []
    indexed                 =   [(i, item) for i, item in enumerate(raw_blocks[:LAYOUT_MAX_BLOCKS]) if isinstance(item, dict)]
    indexed.sort(key        =   _order_key)
    seen, clean             =   set(), []
    for _, item in indexed:
        block_id            =   str(item.get('id') or '').strip()
        spec                =   TEMPLATE_BLOCKS[surface].get(block_id)
        #IDs desconocidos y repetidos se descartan; premium sin el
        #beneficio también (fail-closed al plan vigente), igual que los
        #bloques solo-IA sin has_ai_design.
        if spec is None or block_id in seen:
            continue
        if spec.get('premium') and not has_advanced:
            continue
        if spec.get('ai_only') and not has_ai:
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

def clean_layout_config(value, has_design_advanced, has_ai_design = False):
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
        blocks              =   _clean_blocks(raw.get('blocks'), surface, has_design_advanced, has_ai_design)
        if blocks:
            clean[surface]  =   {'blocks': blocks}
    return clean
