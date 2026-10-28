#=========================================
# MOTOR DE DISEÑO AUTOMÁTICO (sin IA paga, offline y determinista)
#=========================================
#Entrevista corta (todo opcional) + datos reales de la tienda → 2-3
#propuestas de web completa: plantilla, look (site_theme) y qué bloques
#van, en qué orden y con qué variante.
#Cero llamadas de red: las recetas viven en ai_design_recipes y el texto
#sale de ai_design_copy. La variación "aleatoria pero pensada" viene de una
#semilla derivada del store + respuestas + ENGINE_VERSION, así que el mismo
#input devuelve el mismo JSON byte a byte (y la semilla que manda el
#frontend se suma para pedir "otra propuesta").
#Nada de lo que arma el motor se escribe sin pasar por clean_layout_config
#ni por la whitelist de plantillas del plan: los invariantes del editor
#(locked siempre activo, premium fuera sin has_design_advanced, bloque sin
#datos apagado) son los mismos acá que en el Studio.

import copy
import hashlib
import json
import random
import re
import unicodedata
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from StoreApp.domains.stores.layout_blocks  import TEMPLATE_BLOCKS, AI_ICONS, clean_layout_config
from StoreApp.domains.stores.models         import Store, StoreCustomization, StoreGalleryImage, StudioVersion
from StoreApp.domains.stores.site_theme     import clean_site_theme

from . import ai_design_copy
from . import ai_design_recipes as R
from . import imaging, storage
from .services import allowed_templates_of, profile_has_benefit

ENGINE_VERSION              =   R.ENGINE_VERSION
CACHE_TTL                   =   60 * 60

#Datos que el motor mira para saber si puede armar una web completa. El
#orden manda en `missing`: primero lo que más cambia el resultado.
MISSING_ORDER               =   ('about', 'gallery', 'testimonials', 'faqs', 'stats', 'categories', 'brands', 'offers', 'team', 'video', 'products')
MISSING_LABELS              =   {
    'about':        'el texto de "Sobre nosotros"',
    'gallery':      'fotos en la galería',
    'testimonials': 'testimonios de clientes',
    'faqs':         'preguntas frecuentes',
    'stats':        'las cifras del negocio',
    'categories':   'categorías del catálogo (dos o más)',
    'brands':       'marcas cargadas',
    'offers':       'productos con descuento',
    'team':         'los integrantes del equipo',
    'video':        'un video del negocio',
    'products':     'productos en el catálogo',
}
#Cada faltante viaja como objeto {code, label, hint, action}: el frontend
#usa `action` para abrir la sección que lo resuelve. 'images' es el pedido
#de fotos de "Diseñar con IA"; 'empresa' y 'catalog' son secciones del panel.
MISSING_HINTS                =   {
    'about':        'Contá en dos o tres frases qué hacés y para quién.',
    'gallery':      'Subí 3 fotos horizontales de tu local o tus trabajos.',
    'testimonials': 'Una frase real de un cliente alcanza para empezar.',
    'faqs':         'Las tres preguntas que más te hacen por WhatsApp.',
    'stats':        'Años de trayectoria, clientes o trabajos hechos.',
    'categories':   'Agrupá el catálogo en dos o más categorías.',
    'brands':       'Cargá las marcas que trabajás.',
    'offers':       'Poné un precio de oferta en algún producto.',
    'team':         'Sumá a las personas que atienden.',
    'video':        'Pegá el link de YouTube o Vimeo del negocio.',
    'products':     'Cargá tus primeros productos con foto y precio.',
}
MISSING_ACTIONS              =   {
    'about': 'empresa', 'gallery': 'images', 'testimonials': 'empresa',
    'faqs': 'empresa', 'stats': 'empresa', 'categories': 'catalog',
    'brands': 'empresa', 'offers': 'catalog', 'team': 'empresa',
    'video': 'empresa', 'products': 'catalog',
}


class AiDesignError(Exception):
    """Error de contrato del motor (se traduce a 400 en el viewset)."""


#=========================================
# HECHOS DEL NEGOCIO (qué datos reales hay)
#=========================================
def _facts(store, customization):
    """
    Devuelve (facts, stats): `facts` son booleanos que habilitan bloques y
    `stats` los conteos que usan el puntaje y el texto. Una sola pasada de
    consultas: el motor no vuelve a pegarle a la base.
    """
    from StoreApp.domains.catalog.models            import Product, Category, Brand
    from StoreApp.domains.catalog.services.services import running_discounts_of

    products    =   Product.objects.filter(store = store, is_active = True)
    discounts   =   running_discounts_of(store)
    stats       =   {
        'products'      :   products.count(),
        'images'        :   products.exclude(image_key = '').count(),
        'categories'    :   Category.objects.filter(store = store).count(),
        'brands'        :   Brand.objects.filter(store = store).count(),
        'gallery'       :   store.gallery_images.count(),
        'carousel'      :   store.carousel_images.count(),
        'offers'        :   products.exclude(offer_price__isnull = True).count(),
        #Cuánto texto real hay cargado: una web con relato pide una
        #plantilla con más libertad tipográfica (los ai_*).
        'text_chars'    :   len(customization.about_text or '') + len(customization.description or '') + sum(
            len(str(row.get('text') or '')) for row in (customization.services or []) if isinstance(row, dict)
        ),
    }
    #La cuenta regresiva necesita un descuento CON vencimiento: sin fecha no
    #hay nada que contar y el bloque quedaría mintiendo.
    promo       =   any(discount.ends_at for discount in discounts)
    facts       =   {
        'products'      :   stats['products'] > 0,
        'images'        :   stats['images'] >= 3,
        'categories'    :   stats['categories'] >= 2,
        'brands'        :   stats['brands'] >= 2,
        'gallery'       :   stats['gallery'] > 0,
        'carousel'      :   stats['carousel'] > 0,
        'offers'        :   (stats['offers'] > 0 or bool(discounts)) and customization.show_offers,
        'countdown'     :   promo and customization.show_countdown,
        'catalog_dense' :   stats['products'] >= 6,
        'catalog_note'  :   bool(customization.catalog_note),
        'announcements' :   bool(customization.announcements) and customization.show_announcements,
        'highlights'    :   stats['products'] >= 3 or bool(customization.about_specialties),
        'about'         :   bool(customization.about_text or customization.about_specialties or customization.about_years),
        'services'      :   bool(customization.services) and customization.show_services,
        'stats'         :   bool(customization.stats) and customization.show_stats,
        'benefits'      :   bool(customization.benefits) and customization.show_benefits,
        'timeline'      :   bool(customization.timeline) and customization.show_timeline,
        'team'          :   bool(customization.team) and customization.show_team,
        'testimonials'  :   bool(customization.testimonials) and customization.show_testimonials,
        'faqs'          :   bool(customization.faqs) and customization.show_faq,
        'video'         :   bool(customization.video_url) and customization.show_video,
        'steps'         :   bool(customization.service_steps or customization.services),
        'service_form'  :   bool(customization.service_days or customization.service_slots),
        'compare'       :   stats['products'] >= 4,
        'contact'       :   bool(customization.whatsapp or customization.contact_email or customization.show_location),
        'logo'          :   bool(customization.logo_key),
        'cover'         :   bool(customization.cover_key),
    }
    return facts, stats


#=========================================
# RESPUESTAS DE LA ENTREVISTA (todo opcional)
#=========================================
def _fold(text):
    #Sin acentos ni mayúsculas: las pistas de rubro matchean igual.
    text    =   unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def _guess_rubro(store, customization, stats):
    haystack    =   ' '.join([
        customization.display_name or '',
        store.slug or '',
        ' '.join(str(row.get('title') or '') for row in (customization.services or []) if isinstance(row, dict)),
        ' '.join(str(row.get('name') or '') for row in (customization.services or []) if isinstance(row, dict)),
    ])
    haystack    =   _fold(haystack)
    for rubro, words in R.RUBRO_HINTS.items():
        if any(word in haystack for word in words):
            return rubro
    return 'otro'


def _guess_goals(customization, stats):
    #Con catálogo cargado y página de catálogo, la meta natural es vender;
    #con página de servicios, mostrarlos; si no, confianza (web de vidriera).
    templates   =   customization.site_templates or []
    if stats['products'] > 0 and 'catalog' in templates:
        return ['vender_online', 'dar_confianza']
    if 'services' in templates:
        return ['mostrar_servicios', 'conseguir_consultas']
    return ['dar_confianza', 'conseguir_consultas']


#=========================================
# COLOR DE MARCA (paleta derivada con contraste AA)
#=========================================
_HEX6_RE    =   re.compile(r'^#?[0-9a-fA-F]{6}$')
_HEX3_RE    =   re.compile(r'^#?[0-9a-fA-F]{3}$')

def _norm_hex(raw):
    if not isinstance(raw, str):
        return None
    value   =   raw.strip()
    if _HEX6_RE.match(value):
        return '#' + value.lstrip('#').lower()
    if _HEX3_RE.match(value):
        return '#' + ''.join(c * 2 for c in value.lstrip('#').lower())
    return None

def _hex_rgb(value):
    h   =   value.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _rgb_hex(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(round(channel)))) for channel in rgb)

def _luminance(value):
    def channel(raw):
        s   =   raw / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b =   _hex_rgb(value)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def _contrast_ratio(a, b):
    la, lb  =   _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def _mix(a, b, ratio):
    """ratio 0 => a, ratio 1 => b."""
    ra, rb  =   _hex_rgb(a), _hex_rgb(b)
    return _rgb_hex(tuple(x + (y - x) * ratio for x, y in zip(ra, rb)))

def _ensure_contrast(color, base, target = 4.5):
    #Contraste AA garantizado: si el color no alcanza sobre la base, se
    #oscurece (base clara) o se aclara (base oscura) hasta llegar.
    if _contrast_ratio(color, base) >= target:
        return color
    toward  =   '#000000' if _luminance(base) > 0.4 else '#ffffff'
    for step in range(1, 21):
        candidate   =   _mix(color, toward, step / 20)
        if _contrast_ratio(candidate, base) >= target:
            return candidate
    return toward

def _palette_from_brand(accent, palette):
    """
    Paleta derivada del color de marca elegido por el dueño:
    accent = el color (ajustado a AA sobre el fondo), primary = variante
    oscura, secondary = tinta del look, muted/border = mezclas con el fondo.
    """
    bg          =   palette['bg']
    accent      =   _ensure_contrast(accent, bg)
    primary     =   _ensure_contrast(_mix(accent, '#000000', 0.25), bg)
    secondary   =   palette['text']
    muted       =   _ensure_contrast(_mix(accent, bg, 0.55), bg)
    border      =   _mix(accent, bg, 0.75)
    return {**palette, 'accent': accent, 'primary': primary, 'secondary': secondary, 'muted': muted, 'border': border}


def _answers(store, customization, payload, stats):
    """Normaliza la entrevista: lo que no vino (o no es válido) se deduce."""
    payload     =   payload if isinstance(payload, dict) else {}
    rubro       =   str(payload.get('rubro') or '').strip()
    if rubro not in R.RUBROS:
        rubro   =   _guess_rubro(store, customization, stats)
    tone        =   str(payload.get('tone') or '').strip()
    if tone not in R.TONES:
        tone    =   R.DEFAULT_TONE
    goals       =   [goal for goal in (payload.get('goals') or []) if goal in R.GOALS][:2]
    if not goals:
        goals   =   _guess_goals(customization, stats)
    must_have   =   [block for block in (payload.get('must_have') or []) if block in TEMPLATE_BLOCKS['landing']]
    #Color de marca: un valor inválido se ignora (la IA elige), nunca 400.
    brand_color =   _norm_hex(payload.get('brand_color')) or ''
    night_raw   =   payload.get('night_mode') if isinstance(payload.get('night_mode'), dict) else {}
    night_default = night_raw.get('default')
    cover_choice  =   payload.get('cover_choice')
    if cover_choice not in ('foto', 'logo', 'auto'):
        cover_choice    =   'auto'
    use_icons   =   payload.get('use_icons')
    return {
        'rubro'         :   rubro,
        'tone'          :   tone,
        'goals'         :   goals,
        'must_have'     :   must_have,
        'audience'      :   str(payload.get('audience') or '').strip()[:120],
        'brand_color'   :   brand_color,
        'night_mode'    :   {
            'enabled'   :   night_raw.get('enabled') is True,
            'default'   :   night_default if night_default in ('light', 'dark') else '',
        },
        'cover_choice'  :   cover_choice,
        #None = lo deduce el motor (rubro visual => con íconos).
        'use_icons'     :   use_icons if isinstance(use_icons, bool) else None,
    }


def _base_seed(store, answers):
    #sha256(store, respuestas normalizadas, versión del motor): dos tiendas
    #con la misma entrevista no salen iguales y la misma tienda sí.
    raw     =   json.dumps(
        {'store': store.pk, 'answers': answers, 'engine': ENGINE_VERSION},
        sort_keys = True, ensure_ascii = False,
    )
    return int(hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12], 16)


def _request_seed(payload):
    try:
        return max(0, int((payload or {}).get('seed') or 0))
    except (TypeError, ValueError):
        return 0


#=========================================
# PUNTAJE DE PLANTILLAS
#=========================================
def _score_templates(facts, stats, answers, allowed):
    """
    Puntúa las plantillas del plan: afinidad rubro (orden de la receta) y
    tono, objetivo, densidad de datos y volumen de catálogo/imágenes. Los
    dos diseños exclusivos de IA (solo presentes en `allowed` con
    has_ai_design) suman señales de "libertad": fotos propias, textos
    largos, rubro visual y objetivos de mostrar trabajos/confianza.
    Devuelve las permitidas ordenadas de mejor a peor (empate: orden del rubro).
    """
    rubro_order =   list(R.RUBROS[answers['rubro']]['templates'])
    #Los ai_* no viven en las recetas por rubro: se suman al final del pool
    #y la whitelist del plan decide si existen (nunca se hardcodea acá).
    for template in R.AI_TEMPLATES:
        if template not in rubro_order:
            rubro_order.append(template)
    goal        =   answers['goals'][0]
    goal_boost  =   R.TEMPLATE_GOAL_AFFINITY.get(goal, ())
    density     =   sum(1 for key in ('products', 'images', 'gallery', 'testimonials', 'stats', 'team', 'timeline', 'benefits', 'faqs') if facts.get(key))
    #Señales de libertad visual: cuanta más materia real hay, mejor se
    #defiende una plantilla audaz sin quedar vacía.
    freedom     =   0
    if stats['gallery'] >= 3 or stats['images'] >= 6:
        freedom += 2
    if stats['text_chars'] >= 240:
        freedom += 1
    if answers['rubro'] in R.VISUAL_RUBROS:
        freedom += 2
    if goal in ('mostrar_trabajos', 'dar_confianza'):
        freedom += 2
    if answers['tone'] in ('moderno', 'audaz'):
        freedom += 1
    scored      =   []
    for index, template in enumerate(rubro_order):
        if template not in allowed:
            continue
        score   =   (len(rubro_order) - index) * 3
        score   +=  R.TEMPLATE_TONE_AFFINITY.get(template, {}).get(answers['tone'], 0)
        score   +=  3 if template in goal_boost else 0
        score   +=  min(density, 6)
        if template in R.AI_TEMPLATES:
            score   +=  min(freedom, 5)
        #Catálogo grande pide grilla densa; web de vidriera (sin productos)
        #respira mejor con una plantilla editorial.
        if stats['products'] >= 12 and template in ('vitrina', 'duo'):
            score   +=  2
        if stats['products'] == 0 and template in ('calma', 'classic'):
            score   +=  2
        if stats['images'] >= 6 and template in ('cobre', 'minimal'):
            score   +=  1
        scored.append((score, -index, template))
    scored.sort(reverse = True)
    #El plan Básico tiene una sola plantilla: la lista nunca queda vacía
    #(allowed_templates_of siempre devuelve al menos 'classic').
    return [template for _, _, template in scored]


#=========================================
# ARMADO DEL LAYOUT
#=========================================
def _pattern_for(template, answers, shift):
    """
    Patrón "pro" de un diseño de IA: el más afín al objetivo, rotado por la
    propuesta para que dos sugerencias con la misma plantilla no cuenten la
    misma historia. None para las plantillas del plan (usan las recetas).
    """
    patterns    =   R.AI_PATTERNS.get(template)
    if not patterns:
        return None
    goal        =   answers['goals'][0]
    ordered     =   sorted(
        range(len(patterns)),
        key = lambda index: (goal not in patterns[index]['goals'], index),
    )
    return patterns[ordered[shift % len(ordered)]]


def _order_for(surface, answers, pattern = None):
    """Orden de bloques para la superficie: receta del objetivo + prioridad del rubro."""
    rubro       =   R.RUBROS[answers['rubro']]
    base        =   list(rubro['priority'][surface])
    off         =   set()
    if surface == 'landing' and pattern:
        #Los ai_* no usan la receta por objetivo: el patrón ya trae el orden
        #audaz y apaga lo que le rompe el ritmo.
        off     =   set(pattern['off'])
        order   =   [block for block in pattern['order'] if block in TEMPLATE_BLOCKS[surface]]
        order  +=   [block for block in base if block not in order]
    elif surface == 'landing':
        recipe  =   R.GOAL_RECIPES[answers['goals'][0]]
        off     =   set(recipe['off'])
        order   =   [block for block in recipe['order'] if block in TEMPLATE_BLOCKS[surface]]
        order  +=   [block for block in base if block not in order]
    else:
        order   =   base
    #Los bloques con datos que la receta no nombró entran al final del grupo:
    #mejor una sección útil de más que perder contenido real.
    for block in R.BLOCK_FALLBACKS[surface]:
        if block not in order:
            order.append(block)
    return order, off


def _variant_for(surface, block_id, answers, rng, shift, pattern = None):
    """Variante del bloque: la preferida del rubro (y del objetivo para el hero)."""
    spec        =   TEMPLATE_BLOCKS[surface].get(block_id) or {}
    variants    =   spec.get('variants')
    if not variants:
        return None
    if pattern and surface == 'landing':
        #El patrón de IA manda: fija la variante que sostiene su lenguaje.
        chosen  =   pattern['variants'].get(block_id)
        if chosen in variants:
            return chosen
    pool        =   [variant for variant in R.RUBROS[answers['rubro']]['variants'].get(block_id, ()) if variant in variants]
    if surface == 'landing' and block_id == 'hero':
        goal_variant    =   R.GOAL_RECIPES[answers['goals'][0]]['hero_variant']
        if goal_variant in variants:
            pool    =   [goal_variant] + [variant for variant in pool if variant != goal_variant]
    if not pool:
        return None
    #La primera propuesta respeta el orden preferido; las siguientes rotan
    #para que "otra propuesta" se sienta otra cosa sin salir del catálogo.
    if shift == 0 or len(pool) == 1:
        return pool[0]
    return pool[rng.randrange(len(pool))]


def _build_surface(surface, facts, answers, rng, shift, pattern = None):
    order, off      =   _order_for(surface, answers, pattern)
    blocks          =   []
    for block_id in order:
        spec    =   TEMPLATE_BLOCKS[surface].get(block_id)
        if spec is None or block_id in off:
            continue
        gate    =   R.BLOCK_GATES[surface].get(block_id)
        #Bloque sin datos reales => apagado (queda en el borrador para que el
        #dueño lo vea y lo active cuando cargue el dato).
        enabled =   True if gate is None else bool(facts.get(gate))
        block   =   {'id': block_id, 'enabled': enabled}
        variant =   _variant_for(surface, block_id, answers, rng, shift, pattern)
        if variant:
            block['variant']    =   variant
        blocks.append(block)
    #Variación "aleatoria pero pensada": en las propuestas alternativas el
    #grupo del medio se reordena con la semilla (la portada, el cierre y el
    #contacto quedan fijos por las reglas de jerarquía).
    if surface == 'landing' and shift > 0:
        fixed   =   {'hero', 'cta', 'contact'}
        middle  =   [block for block in blocks if block['id'] not in fixed]
        rest    =   [block for block in blocks if block['id'] in fixed]
        rng.shuffle(middle)
        blocks  =   middle + rest
    #Lo que el dueño pidió explícitamente sube al frente (después del hero).
    must    =   [block for block in answers['must_have'] if block in {item['id'] for item in blocks}]
    if surface == 'landing' and must:
        head    =   [item for item in blocks if item['id'] == 'hero']
        middle  =   [item for item in blocks if item['id'] not in {'hero', 'cta', 'contact'} and item['id'] in must]
        rest    =   [item for item in blocks if item not in head + middle]
        blocks  =   head + middle + rest
    if surface == 'landing':
        blocks  =   _enforce_hierarchy(blocks)
    for index, block in enumerate(blocks):
        block['order']  =   index
    return {'blocks': blocks}


def _enforce_hierarchy(blocks):
    """
    Reglas de jerarquía de ai_design_recipes.HIERARCHY_RULES que no salen
    solas del orden: hero primero, prueba social antes del CTA y contacto
    al cierre.
    """
    by_id   =   {block['id']: block for block in blocks}
    head    =   [by_id.pop('hero')] if 'hero' in by_id else []
    tail    =   [by_id.pop('contact')] if 'contact' in by_id else []
    cta     =   [by_id.pop('cta')] if 'cta' in by_id else []
    social  =   [by_id.pop(block_id) for block_id in ('testimonials', 'brands') if block_id in by_id]
    middle  =   [block for block in blocks if block['id'] in by_id]
    return head + middle + social + cta + tail


def _layout(store, facts, answers, rng, shift, pattern = None):
    layout  =   {}
    for surface in ('landing', 'catalog', 'services'):
        layout[surface] =   _build_surface(surface, facts, answers, rng, shift, pattern)
    return layout


#=========================================
# ELEMENTOS SOLO-IA (bloques nuevos según la entrevista)
#=========================================
_ELEMENT_ICONS  =   ('sparkles', 'star', 'heart', 'shield-check', 'clock', 'award')


def _element_props(block_id, customization, facts, use_icons):
    """Contenido real para los bloques nuevos (nunca inventa datos)."""
    if block_id == 'aiquote':
        row =   next((item for item in (customization.testimonials or []) if isinstance(item, dict) and str(item.get('text') or '').strip()), None)
        if row is None:
            return {}
        return {
            'text'      :   str(row.get('text')).strip()[:160],
            'author'    :   str(row.get('name') or row.get('author') or '').strip()[:40],
        }
    if block_id == 'aigrid':
        items   =   []
        for index, row in enumerate((customization.services or [])[:6]):
            if not isinstance(row, dict):
                continue
            title   =   str(row.get('title') or row.get('name') or '').strip()[:40]
            text    =   str(row.get('text') or row.get('desc') or '').strip()[:90]
            if not (title or text):
                continue
            item    =   {'title': title} if title else {}
            if use_icons:
                icon        =   str(row.get('icon') or '')
                item['icon'] =   icon if icon in AI_ICONS else _ELEMENT_ICONS[index % len(_ELEMENT_ICONS)]
            if text:
                item['text']    =   text
            items.append(item)
        return {'title': 'Lo que hacemos', 'items': items} if items else {}
    if block_id == 'aicheck':
        items   =   []
        for row in (customization.benefits or [])[:6]:
            if not isinstance(row, dict):
                continue
            text    =   str(row.get('text') or row.get('title') or row.get('name') or '').strip()[:90]
            if text:
                items.append({'text': text})
        return {'title': 'Lo que nos diferencia', 'items': items} if items else {}
    if block_id == 'aiband' and facts.get('offers'):
        return {'title': 'Ofertas vigentes', 'text': 'Aprovechá los precios de esta semana.', 'label': 'Ver ofertas'}
    if block_id == 'aistrip':
        items   =   []
        if customization.whatsapp:
            items.append({'icon': 'phone', 'label': 'Escribinos por WhatsApp'})
        if customization.show_location:
            items.append({'icon': 'map-pin', 'label': 'Estamos cerca'})
        if customization.service_days or customization.service_slots:
            items.append({'icon': 'clock', 'label': 'Con turno previo'})
        return {'items': items} if len(items) >= 2 else {}
    return {}


def _add_elements(layout, customization, facts, answers, use_icons, has_ai):
    """
    Reglas de elementos (documentadas en ai_design_recipes.AI_ELEMENT_ORDER):
    dar_confianza => aiquote; must_have precios/garantías => aicheck;
    mostrar_servicios => aigrid; vender_online con ofertas => aiband; 2+
    datos de contacto en must_have => aistrip. Máximo 3, nunca duplica ids
    ni pisa un bloque existente. Sin íconos (use_icons=False) no se suman
    aigrid/aistrip.
    """
    if not has_ai:
        return layout
    goal    =   answers['goals'][0]
    must    =   set(answers['must_have'])
    picked  =   []
    if goal == 'dar_confianza':
        picked.append('aiquote')
    if must & {'offers', 'benefits'}:
        picked.append('aicheck')
    if goal == 'mostrar_servicios':
        picked.append('aigrid')
    if goal == 'vender_online' and facts.get('offers'):
        picked.append('aiband')
    if len(must & {'contact', 'faq', 'stats'}) >= 2:
        picked.append('aistrip')
    if not use_icons:
        picked  =   [block_id for block_id in picked if block_id not in ('aigrid', 'aistrip')]
    picked  =   [block_id for block_id in R.AI_ELEMENT_ORDER if block_id in picked][:R.AI_ELEMENT_MAX]
    landing =   layout['landing']['blocks']
    for block_id in picked:
        if block_id in {block['id'] for block in landing}:
            continue
        block   =   {'id': block_id, 'enabled': True, 'variant': TEMPLATE_BLOCKS['landing'][block_id]['variants'][0]}
        props   =   _element_props(block_id, customization, facts, use_icons)
        if props:
            block['props']  =   props
        anchor  =   R.AI_ELEMENT_ANCHORS.get(block_id)
        ids     =   [item['id'] for item in landing]
        if anchor in ids:
            index   =   ids.index(anchor) if block_id == 'aiquote' else ids.index(anchor) + 1
        else:
            index   =   len(landing)
            for tail in ('cta', 'contact'):
                if tail in ids:
                    index   =   min(index, ids.index(tail))
        landing.insert(index, block)
    landing =   _enforce_hierarchy(landing)
    for index, block in enumerate(landing):
        block['order']  =   index
    layout['landing']['blocks'] =   landing
    return layout


#=========================================
# LOOK (site_theme parcial)
#=========================================
def _theme(answers, rng, shift, template = None):
    #Los diseños exclusivos de IA traen su propio look (vidrio/luz vs.
    #tipografía XL); el resto usa el look del rubro.
    look_id =   R.AI_LOOKS.get(template) or R.RUBROS[answers['rubro']]['look']
    theme   =   copy.deepcopy(R.LOOKS[look_id])
    #El tono ajusta energía (curvas, aire, movimiento), no la identidad.
    for section, values in R.TONE_TWEAKS[answers['tone']].items():
        theme.setdefault(section, {}).update(values)
    if answers.get('brand_color'):
        #El color del dueño manda: la paleta se deriva de él y la propuesta
        #lo declara como elección del usuario.
        theme['palette']    =   _palette_from_brand(answers['brand_color'], theme['palette'])
        choice              =   {'source': 'user', 'accent': theme['palette']['accent']}
    else:
        accents =   R.ACCENTS.get(look_id) or (theme['palette']['accent'],)
        accent  =   accents[(shift + rng.randrange(len(accents))) % len(accents)]
        theme['palette']['accent']  =   accent
        theme['palette']['primary'] =   accent
        choice              =   {'source': 'ai', 'accent': accent}
    return theme, choice


def _resolve_night(answers, theme, template):
    """
    Modo noche: con enabled=True la web arranca en el default elegido y
    muestra el interruptor (theme_toggle=True); sin la respuesta el
    interruptor queda apagado y `theme` sigue el look (oscuro si el fondo
    de la paleta es oscuro). Devuelve (night_mode, theme, theme_toggle).
    """
    look_default    =   'dark' if _luminance(theme['palette']['bg']) < 0.4 else 'light'
    raw             =   answers.get('night_mode') or {}
    default         =   raw.get('default') or look_default
    if raw.get('enabled'):
        return {'enabled': True, 'default': default}, default, True
    return {'enabled': False, 'default': default}, look_default, False


def _cover_for(answers, facts):
    """Logo o foto de portada: el pedido explícito manda; en 'auto' el
    logo reemplaza a la portada solo si no hay foto cargada."""
    has_logo    =   bool(facts.get('logo'))
    choice      =   answers.get('cover_choice')
    if choice == 'logo' and has_logo:
        return {'mode': 'logo', 'reason': 'Tu logo ya es tu mejor portada: la web abre con la marca, sin foto.'}
    if choice == 'auto' and has_logo and not facts.get('cover'):
        return {'mode': 'logo', 'reason': 'No hay foto de portada y sí logo: la marca abre la web.'}
    return {'mode': 'photo', 'reason': 'La portada va con foto para mostrar el local o el trabajo.'}


def _block_styles(template, theme, layout):
    """
    Overrides "pro" por contenedor del diseño de IA: solo bloques que están
    en el layout y solo claves del catálogo. `accent` se resuelve con la
    paleta final (las recetas lo dejan en None).
    """
    styles  =   R.AI_BLOCK_STYLES.get(template) or {}
    present =   {block['id'] for block in layout['landing']['blocks'] if block.get('enabled')}
    out     =   {}
    for block_id, values in styles.items():
        if block_id not in present:
            continue
        clean   =   {}
        for key, value in values.items():
            if value is None and key == 'accent':
                value   =   theme['palette']['accent']
            if value is not None:
                clean[key]  =   value
        if clean:
            out[block_id]   =   clean
    return out


#=========================================
# NOTAS Y "POR QUÉ"
#=========================================
def _why(answers, template, index, pattern = None):
    if pattern:
        #El patrón de IA ya explica su propia apuesta visual.
        return pattern['why'][:160]
    goal    =   answers['goals'][0]
    base    =   R.GOAL_RECIPES[goal]['why']
    if index == 0:
        return base[:160]
    #Las variantes explican en qué se diferencian, no repiten el argumento.
    return f"Variante {R.TEMPLATE_LABELS.get(template, template)}: mismo contenido, otro ritmo de lectura y otro cierre."[:160]


def _notes(facts, stats, answers, template, has_advanced):
    notes       =   []
    if stats['products']:
        notes.append(f"Tu catálogo tiene {stats['products']} productos: vitrina destacada y grilla en 3 columnas.")
    if stats['gallery'] or stats['images']:
        notes.append('La galería va cerca de la portada: las fotos venden antes que el texto.')
    missing     =   [key for key in MISSING_ORDER if not facts.get(key)][:2]
    if missing:
        notes.append('Falta ' + ' y '.join(MISSING_LABELS.get(key, key) for key in missing) + ': ese bloque queda apagado hasta que lo cargues.')
    if not has_advanced:
        notes.append('Tu plan no incluye los bloques premium: no los sumamos para que nada quede vacío.')
    if answers['must_have']:
        notes.append('Respetamos lo que pediste: ' + ', '.join(answers['must_have']) + '.')
    return notes[:4]


#=========================================
# PEDIDO DE IMÁGENES (qué fotos faltan para que la web se vea profesional)
#=========================================
def _image_requests(stats, layout):
    """
    0 a 2 pedidos de fotos. Solo cuando la tienda no tiene imágenes propias
    (galería ni productos) y algún bloque de imagen quedó apagado: pedir
    fotos que no van a cambiar nada es ruido. `unlocks` lista los bloques y
    la variante de portada que se encenderían con esas fotos.
    """
    if stats['gallery'] or stats['images']:
        return []
    landing     =   {block['id']: block for block in layout['landing']['blocks']}
    hero        =   landing.get('hero') or {}
    hero_unlock =   f"hero:{hero.get('variant')}" if hero.get('variant') else 'hero'
    requests    =   [{
        'id'            :   'local',
        'purpose'       :   'portada',
        'label'         :   'Fotos de tu local o tus trabajos',
        'hint'          :   '3 fotos horizontales, con luz natural y el local ordenado.',
        'target'        :   'cover',
        'min_count'     :   3,
        'aspect'        :   '16:9',
        'unlocks'       :   ['gallery', hero_unlock],
    }]
    #Segundo pedido solo si hay catálogo: la vitrina sin fotos de producto
    #es la sección que más pierde.
    if stats['products'] > 0 and 'featured' in landing:
        requests.append({
            'id'            :   'productos',
            'purpose'       :   'catálogo',
            'label'         :   'Fotos de tus productos',
            'hint'          :   '2 o 3 fotos por producto, fondo liso y buena luz.',
            'target'        :   'gallery',
            'min_count'     :   2,
            'aspect'        :   '1:1',
            'unlocks'       :   ['featured'],
        })
    return requests[:2]


#=========================================
# GENERACIÓN DE PROPUESTAS
#=========================================
def _proposal_count(allowed, facts):
    #Nunca una sola: con dos plantillas permitidas ya hay dos historias
    #distintas. Una tercera solo si el plan y los datos la justifican.
    if len(allowed) >= 3 and sum(1 for value in facts.values() if value) >= 6:
        return 3
    return 2


def _build(store, customization, answers, seed, has_advanced, allowed, facts, stats, has_ai = False):
    templates       =   _score_templates(facts, stats, answers, allowed)
    if not templates:
        templates   =   [StoreCustomization.TEMPLATE_CLASSIC]
    rng             =   random.Random(seed)
    count           =   _proposal_count(allowed, facts)
    use_icons       =   answers.get('use_icons')
    if use_icons is None:
        #Sin respuesta, el rubro decide: las webs de vidriera llevan íconos.
        use_icons   =   answers['rubro'] in R.VISUAL_RUBROS
    has_plus        =   profile_has_benefit(store.user, 'has_design_plus')
    has_style       =   profile_has_benefit(store.user, 'has_customization')
    #Con los ai_* habilitados, al menos una propuesta los usa: si el puntaje
    #no los dejó arriba, la segunda propuesta pasa a ser la mejor de IA
    #(siempre dentro de la whitelist del plan).
    ai_allowed      =   [template for template in templates if template in R.AI_TEMPLATES]
    if ai_allowed and count >= 2 and not any(template in R.AI_TEMPLATES for template in templates[:count]):
        templates[1]    =   ai_allowed[0]
    proposals       =   []
    signatures      =   set()
    for index in range(count):
        #La propuesta 0 va con la mejor plantilla; las demás rotan para que
        #nunca haya dos iguales (misma plantilla => otro orden/variantes).
        shift       =   0 if index == 0 else index
        template    =   templates[index % len(templates)]
        pattern     =   _pattern_for(template, answers, shift)
        for attempt in range(4):
            layout  =   _layout(store, facts, answers, rng, shift + attempt, pattern)
            layout  =   _add_elements(layout, customization, facts, answers, use_icons, has_ai)
            signature = (template, tuple(block['id'] for block in layout['landing']['blocks']))
            if signature not in signatures:
                break
        signatures.add(signature)
        cover   =   _cover_for(answers, facts)
        if cover['mode'] == 'logo':
            for block in layout['landing']['blocks']:
                if block['id'] == 'hero':
                    block['variant']    =   'logo'
        theme, choice   =   _theme(answers, rng, shift + attempt, template)
        if cover['mode'] == 'logo':
            #Con el logo de portada el fondo nunca apunta a una imagen: el
            #hero se resuelve con color sólido.
            background  =   dict(theme.get('background') or {})
            background['type']  =   'solid'
            background.pop('value', None)
            theme['background'] =   background
        block_styles    =   _block_styles(template, theme, layout)
        if block_styles:
            theme['blocks'] =   block_styles
        night, theme_mode, theme_toggle =   _resolve_night(answers, theme, template)
        text    =   ai_design_copy.build(store, customization, answers['rubro'], answers['tone'], facts, stats, rng)
        proposals.append({
            'id'            :   f'p{index + 1}',
            'label'         :   (pattern['label'] if pattern else R.GOAL_RECIPES[answers['goals'][0]]['labels'][index % 3])[:32],
            'why'           :   _why(answers, template, index, pattern),
            'template'      :   template,
            'site_theme'    :   clean_site_theme(
                theme,
                has_plus        =   has_plus,
                has_advanced    =   has_advanced,
                has_style       =   has_style,
                store           =   store,
            ),
            'layout_config' :   clean_layout_config(layout, has_advanced, has_ai),
            'theme_choice'  :   choice,
            'night_mode'    :   night,
            'cover'         :   cover,
            'theme'         :   theme_mode,
            'theme_toggle'  :   theme_toggle,
            'copy'          :   text,
            'notes'         :   _notes(facts, stats, answers, template, has_advanced),
            'copy_draft'    :   ai_design_copy.draft_business_fields(store, customization, answers['rubro'], answers['tone'], facts, stats, rng),
            'image_requests':   _image_requests(stats, layout),
        })
    return {
        'engine'    :   ENGINE_VERSION,
        'seed'      :   seed,
        'missing'   :   [
            {
                'code'      :   key,
                'label'     :   MISSING_LABELS.get(key, key),
                'hint'      :   MISSING_HINTS.get(key, ''),
                'action'    :   MISSING_ACTIONS.get(key, 'empresa'),
            }
            for key in MISSING_ORDER if not facts.get(key)
        ][:6],
        'proposals' :   proposals,
    }


def _prepare(store, payload):
    """Contexto común de generate/apply: tienda, borrador, respuestas y plan."""
    customization   =   StoreCustomization.objects.get_or_create(store = store)[0]
    facts, stats    =   _facts(store, customization)
    answers         =   _answers(store, customization, payload, stats)
    allowed         =   allowed_templates_of(store.user)
    has_advanced    =   profile_has_benefit(store.user, 'has_design_advanced')
    has_ai          =   profile_has_benefit(store.user, 'has_ai_design')
    return customization, answers, allowed, has_advanced, has_ai


def generate(store, payload):
    """2-3 propuestas de web completa para la entrevista del dueño."""
    customization, answers, allowed, has_advanced, has_ai =   _prepare(store, payload)
    facts, stats =   _facts(store, customization)
    seed    =   _base_seed(store, answers) + _request_seed(payload)
    result  =   _build(store, customization, answers, seed, has_advanced, allowed, facts, stats, has_ai)
    #Guardamos las respuestas con la semilla: apply recalcula con el MISMO
    #motor y las mismas respuestas (nunca confía en un layout del cliente).
    cache.set(_cache_key(store, seed), answers, CACHE_TTL)
    return result


def _cache_key(store, seed):
    return f'ai_design:{store.pk}:{int(seed)}'


def _apply_titles(layout, rubro):
    """
    props.title de bloques: solo donde el catálogo lo permite y el dueño no
    puso uno. El resto del layout queda tal como salió del motor.
    """
    for surface, config in layout.items():
        for block in config.get('blocks', []):
            if not block.get('enabled'):
                continue
            spec    =   TEMPLATE_BLOCKS[surface].get(block['id']) or {}
            if not (spec.get('props') or {}).get('title'):
                continue
            props   =   block.setdefault('props', {})
            if props.get('title'):
                continue
            title   =   ai_design_copy.title_for(block['id'], rubro)
            if title:
                props['title'] = title
    return layout


#=========================================
# AUTOFILL DE DATOS DE NEGOCIO (copy_draft -> campos vacíos)
#=========================================
#Iconos por defecto al convertir el borrador en filas del modelo: el
#catálogo de iconos es cerrado y el copy_draft no los elige (es texto).
_DRAFT_ICONS                =   {'services': 'package', 'steps': 'check', 'announcements': 'megaphone'}


def _draft_rows(key, rows):
    """
    copy_draft usa nombres pensados para la UI ({name, desc} en servicios,
    {title, desc} en pasos); el modelo guarda {icon, title, text} (y
    {icon, text} en anuncios). Se mapea acá y se recorta otra vez a los
    topes del modelo.
    """
    clean   =   []
    for row in rows or []:
        if key == 'faqs':
            question    =   str(row.get('q') or '').strip()[:StoreCustomization.FAQ_Q_MAX]
            answer      =   str(row.get('a') or '').strip()[:StoreCustomization.FAQ_A_MAX]
            if question and answer:
                clean.append({'q': question, 'a': answer})
            continue
        if key == 'announcements':
            text        =   str(row.get('text') or '').strip()[:StoreCustomization.ANNOUNCEMENT_TEXT_MAX]
            if text:
                clean.append({'icon': _DRAFT_ICONS[key], 'text': text})
            continue
        if key == 'services':
            title       =   str(row.get('name') or '').strip()[:StoreCustomization.SERVICE_TITLE_MAX]
            text        =   str(row.get('desc') or '').strip()[:StoreCustomization.SERVICE_TEXT_MAX]
        else:
            title       =   str(row.get('title') or '').strip()[:StoreCustomization.SERVICE_STEP_TITLE_MAX]
            text        =   str(row.get('desc') or '').strip()[:StoreCustomization.SERVICE_STEP_TEXT_MAX]
        if title and text:
            clean.append({'icon': _DRAFT_ICONS[key], 'title': title, 'text': text})
    return clean


#Clave del copy_draft -> campo del modelo (los pasos y los anuncios no se
#llaman igual en la API que en StoreCustomization).
_DRAFT_FIELDS               =   {
    'about_text': 'about_text', 'about_mission': 'about_mission',
    'faqs': 'faqs', 'services': 'services', 'steps': 'service_steps',
    'announcements': 'announcements',
}


def _apply_draft(customization, draft):
    """
    Escribe el copy_draft SOLO en los campos que siguen vacíos. Nunca toca
    testimonios, cifras, precios, contacto, redes ni horarios — el motor no
    inventa datos del negocio (ni los pisa si el dueño ya los cargó).
    Devuelve la lista de campos escritos.
    """
    written =   []
    for key, field in _DRAFT_FIELDS.items():
        value   =   (draft or {}).get(key)
        if not value or getattr(customization, field):
            continue
        setattr(customization, field, _draft_rows(key, value) if isinstance(value, list) else value)
        written.append(field)
    return written


def _publish(customization, store):
    """
    Publica el borrador en el mismo paso (misma lógica que
    customization/publish del Studio): snapshot en StudioVersion y
    poda del historial a MAX_PER_STORE.
    """
    customization.layout_config    =   copy.deepcopy(customization.layout_config_draft) or {}
    customization.site_theme       =   copy.deepcopy(customization.site_theme_draft) or {}
    if customization.template_draft in allowed_templates_of(store.user):
        customization.template     =   customization.template_draft
    customization.template_draft   =   customization.template
    customization.save(update_fields = ['layout_config', 'site_theme', 'template', 'template_draft', 'updated_at'])
    StudioVersion.objects.create(
        store       =   store,
        snapshot    =   {
            'template'      :   customization.template,
            'layout_config' :   customization.layout_config,
            'site_theme'    :   customization.site_theme,
        },
        note        =   'Diseño con IA',
    )
    stale   =   list(StudioVersion.objects.filter(store = store).values_list('pk', flat = True)[StudioVersion.MAX_PER_STORE:])
    if stale:
        StudioVersion.objects.filter(pk__in = stale).delete()


def apply(store, seed, proposal_id, autofill = False):
    """
    Recalcula la propuesta con el mismo motor, la escribe en el BORRADOR
    (layout_config_draft, site_theme_draft, template_draft, theme,
    theme_toggle) y PUBLICA en el mismo paso. El copy solo rellena campos
    VACÍOS — nunca pisa datos de negocio que ya cargó el dueño. Con
    autofill=True suma el copy_draft a los campos vacíos (about, misión,
    FAQs, servicios, pasos, anuncios), también sin pisar nada.
    """
    try:
        seed    =   int(seed)
    except (TypeError, ValueError):
        raise AiDesignError('Falta la semilla de la propuesta: generá las propuestas de nuevo.')
    customization, answers, allowed, has_advanced, has_ai =   _prepare(store, cache.get(_cache_key(store, seed)) or {})
    facts, stats =   _facts(store, customization)
    built       =   _build(store, customization, answers, seed, has_advanced, allowed, facts, stats, has_ai)
    proposal    =   next((item for item in built['proposals'] if item['id'] == proposal_id), None)
    if proposal is None:
        raise AiDesignError('La propuesta no existe o venció: generá las propuestas de nuevo.')

    layout      =   _apply_titles(copy.deepcopy(proposal['layout_config']), answers['rubro'])
    #La plantilla del borrador nunca sale de la whitelist del plan.
    template    =   proposal['template'] if proposal['template'] in allowed else customization.template

    updated     =   ['layout_config_draft', 'site_theme_draft', 'template_draft', 'theme', 'theme_toggle', 'updated_at']
    customization.layout_config_draft   =   clean_layout_config(layout, has_advanced, has_ai)
    customization.site_theme_draft      =   copy.deepcopy(proposal['site_theme'])
    customization.template_draft        =   template
    customization.theme                 =   proposal.get('theme') or customization.theme
    customization.theme_toggle          =   bool(proposal.get('theme_toggle'))
    for field, value in proposal['copy'].items():
        #El copy solo rellena lo vacío: lo que el dueño ya escribió manda.
        if value and not getattr(customization, field):
            setattr(customization, field, value)
            updated.append(field)
    if autofill:
        updated.extend(_apply_draft(customization, proposal.get('copy_draft') or {}))
    customization.save(update_fields = list(dict.fromkeys(updated)))
    _publish(customization, store)
    return customization


#=========================================
# PEDIDO DE IMÁGENES (upload de las fotos que pide la propuesta)
#=========================================
def upload_design_image(store, upload):
    """
    Valida, normaliza (WebP 78, 1600px, sin recorte) y guarda una foto del
    pedido de imágenes como StoreGalleryImage(kind='gallery') al final del
    orden, consumiendo la misma cuota del plan que la galería. En R2 si hay
    bucket; si no (dev), en MEDIA_ROOT — el archivo nunca va a la base.
    Lanza ValueError con mensaje es-AR si el archivo, el cupo o la cuota
    no dan.
    """
    error   =   storage.validate_image_file(upload)
    if error:
        raise ValueError(error)
    body, ext, content_type =   imaging.normalize_image(upload, 'ai_gallery')
    size    =   len(body)
    #Fast path antes de subir: cupo de galería/imágenes y cuota del plan.
    storage._check_gallery_slot(store, StoreGalleryImage.KIND_GALLERY)
    storage._check_image_slot(store, is_new = True)
    storage._check_quota(store, size)
    key     =   f'stores/{store.pk}/gallery/{uuid4().hex}.{ext}'
    if storage.storage_configured():
        storage.put_object(key, body, content_type)
    else:
        key     =   default_storage.save(key, ContentFile(body))
    try:
        with transaction.atomic():
            #Los cupos se rechequean bajo lock de la fila de la tienda.
            locked      =   Store.objects.select_for_update().get(pk = store.pk)
            storage._check_gallery_slot(locked, StoreGalleryImage.KIND_GALLERY)
            storage._check_image_slot(locked, is_new = True)
            new_used    =   storage._check_quota(locked, size)
            last        =   locked.gallery_images.filter(kind = StoreGalleryImage.KIND_GALLERY).order_by('-position').first()
            image       =   StoreGalleryImage.objects.create(
                store       =   locked,
                kind        =   StoreGalleryImage.KIND_GALLERY,
                image_key   =   key,
                image_size  =   size,
                position    =   (last.position + 1) if last else 0,
            )
            storage._consume_quota(locked, new_used)
    except ValueError:
        if storage.storage_configured():
            storage._delete_object(key)
        else:
            default_storage.delete(key)
        raise
    store.storage_used_bytes    =   locked.storage_used_bytes
    return image


def design_image_url(image):
    """URL visible de una imagen del pedido: bucket público o /media en dev."""
    url     =   storage.object_url(image.image_key)
    if url:
        return url
    media   =   f'{settings.MEDIA_URL}{image.image_key}'
    return media if media.startswith('/') else f'/{media}'
