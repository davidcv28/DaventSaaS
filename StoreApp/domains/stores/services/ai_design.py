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
from . import ai_design_skins as SKIN
from . import ai_design_typography as TYPE
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
    Paleta derivada del color de marca elegido por el dueño.
    El color del dueño manda en ACENTO y botones; el TEXTO se queda neutro:
    una tinta gris derivada del fondo, no del acento (mezclar el azul de
    marca con el fondo producía grises verdosos/lilas que se leen mal).
    """
    bg          =   palette['bg']
    accent      =   _ensure_contrast(accent, bg)
    primary     =   _ensure_contrast(_mix(accent, '#000000', 0.25), bg)
    text        =   _calm_text(palette.get('text') or _neutral_ink(bg), bg, 7.0)
    muted       =   _calm_text(_mix(text, bg, 0.45), bg, 4.5)
    border      =   _mix(text, bg, 0.82)
    return {**palette, 'accent': accent, 'primary': primary, 'secondary': text,
            'text': text, 'muted': muted, 'border': border}


#=========================================
# TINTA NEUTRA (colores de fuente legibles)
#=========================================
def _neutral_ink(bg):
    """Tinta base según el fondo: casi negro sobre claro, casi blanco sobre oscuro."""
    return '#12141a' if _luminance(bg) > 0.4 else '#f5f6f8'


def _desaturate(value, amount):
    """Acerca el color al gris de su misma luminancia (conserva el brillo)."""
    r, g, b     =   _hex_rgb(value)
    gray        =   0.2126 * r + 0.7152 * g + 0.0722 * b
    return _rgb_hex(tuple(channel + (gray - channel) * amount for channel in (r, g, b)))


def _calm_text(value, bg, target = 4.5):
    """
    Texto/muted legibles: se desatura (un gris con un dejo del tono, no un
    color de marca) y se fuerza el contraste mínimo sobre el fondo.
    """
    return _ensure_contrast(_desaturate(value, 0.7), bg, target)


def _calm_palette(palette):
    """
    Invariante de legibilidad de la paleta final (piel × acento × tono):
    text/muted son tintas neutras con AA garantizado y border es un gris
    tenue derivado de la tinta. El acento sigue libre para botones y detalles.
    """
    bg      =   palette['bg']
    text    =   _calm_text(palette.get('text') or _neutral_ink(bg), bg, 7.0)
    muted   =   _calm_text(palette.get('muted') or _mix(text, bg, 0.45), bg, 4.5)
    border  =   _mix(text, bg, 0.82)
    return {**palette, 'text': text, 'muted': muted, 'border': border}


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
    #Estilos pedidos (opcional): se priorizan, nunca se imponen — si el plan
    #no permite la plantilla del estilo, el motor cae al siguiente.
    styles      =   []
    for style in (payload.get('styles') or []):
        if style in SKIN.STYLE_FAMILIES and style not in styles:
            styles.append(style)
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
        'styles'        :   styles[:3],
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
# ELECCIÓN DE ESTILO (plantilla + piel + par tipográfico)
#=========================================
#Un par tipográfico con un font fuera del catálogo (un stack) no puede
#viajar en typography.heading: se cae a Inter, que sí es un slug válido.
_FALLBACK_FONT  =   'inter'

#El motor v4 no puntúa plantillas sueltas: puntúa ESTILOS, la terna
#(plantilla, piel, par tipográfico). Las plantillas compiten por afinidad
#con rubro/tono/objetivo y por señales de datos — los ai_* ya NO tienen un
#bonus ciego de "libertad": si ganan es porque la matriz del rubro, el
#tono o las fotos los favorecen.
_DATA_SIGNALS   =   {
    #fotos/texto largo/catálogo amplio: qué estilos se defienden mejor
    'photos'    :   ('cobre', 'minimal', 'ai_lumen', 'lookbook', 'atelier', 'arena', 'perspective', 'aurora', 'signature'),
    'text'      :   ('minimal', 'calma', 'classic', 'ai_lumen', 'proceso', 'terra', 'carta', 'lab', 'studio'),
    'catalog'   :   ('vitrina', 'duo', 'promo', 'shop', 'street', 'mercado', 'ai_pulse'),
    'empty'     :   ('classic', 'calma', 'minimal', 'studio', 'boutique', 'carta'),
}


def _data_signal(template, stats, facts):
    """Señales de datos reales: una plantilla audaz sin materia queda vacía."""
    score   =   0
    if (stats['gallery'] >= 3 or stats['images'] >= 6) and template in _DATA_SIGNALS['photos']:
        score   +=  3
    if stats['text_chars'] >= 240 and template in _DATA_SIGNALS['text']:
        score   +=  2
    if stats['products'] >= 12 and template in _DATA_SIGNALS['catalog']:
        score   +=  3
    if stats['products'] == 0 and template in _DATA_SIGNALS['empty']:
        score   +=  2
    return score


def _skin_pool(answers, seed):
    """
    Pieles ordenadas por afinidad al rubro y al tono, rotadas por la
    semilla: regenerar con seed+1 cambia de familia visual, no solo de
    variantes. Nunca deja de ser el catálogo cerrado.
    """
    rubro   =   answers['rubro']
    tone    =   answers['tone']
    both    =   [skin for skin in SKIN.SKIN_IDS if rubro in SKIN.SKINS[skin]['rubros'] and tone in SKIN.SKINS[skin]['tones']]
    by_rubro =  [skin for skin in SKIN.SKIN_IDS if rubro in SKIN.SKINS[skin]['rubros'] and skin not in both]
    by_tone  =  [skin for skin in SKIN.SKIN_IDS if tone in SKIN.SKINS[skin]['tones'] and skin not in both and skin not in by_rubro]
    rest     =  [skin for skin in SKIN.SKIN_IDS if skin not in both + by_rubro + by_tone]
    pool     =  both + by_rubro + by_tone + rest
    offset   =  seed % max(1, len(pool))
    return pool[offset:] + pool[:offset]


#=========================================
# ESTILOS DE DISEÑO (motor v5)
#=========================================
#Cada piel declara un `style` (STYLE_FAMILIES). La selección ordena las
#pieles afines por estilo y hace rotar la semilla DENTRO del estilo: la
#propuesta base de un rubro cae en un estilo distinto con seed+1, y las
#propuestas de una misma generación salen de estilos diferentes.
def _style_pool(style, rubro, tone):
    """Pieles de un estilo: match total, después rubro, después tono."""
    skins   =   [skin for skin in SKIN.SKIN_IDS if SKIN.SKINS[skin]['style'] == style]
    both    =   [skin for skin in skins if rubro in SKIN.SKINS[skin]['rubros'] and tone in SKIN.SKINS[skin]['tones']]
    rest    =   [skin for skin in skins if skin not in both]
    return both + rest


def _style_order(answers, seed):
    """
    Estilos ordenados: primero los afines al rubro y al tono, después el
    resto del entrenamiento, rotados por la semilla. Siempre devuelve los 8:
    ningún estilo queda inalcanzable.
    """
    rubro   =   answers['rubro']
    tone    =   answers['tone']
    scores  =   {}
    for style in (answers.get('styles') or []):
        if style in SKIN.STYLE_FAMILIES:
            scores[style]   =   scores.get(style, 0) + 12
    for style in SKIN.STYLE_FAMILIES:
        skins   =   [SKIN.SKINS[skin] for skin in SKIN.SKIN_IDS if SKIN.SKINS[skin]['style'] == style]
        if any(rubro in skin['rubros'] for skin in skins):
            scores[style]   =   scores.get(style, 0) + 6
        if any(tone in skin['tones'] for skin in skins):
            scores[style]   =   scores.get(style, 0) + 3
    ordered =   sorted(SKIN.STYLE_FAMILIES, key = lambda style: (-scores.get(style, 0), SKIN.STYLE_FAMILIES.index(style)))
    offset  =   seed % len(ordered)
    #La semilla rota SOLO el bloque de estilos sin afinidad: el estilo del
    #rubro no se pierde por regenerar, pero "otra propuesta" cambia de estilo.
    head    =   ordered[:2]
    tail    =   ordered[2:]
    if tail:
        cut     =   offset % len(tail)
        tail    =   tail[cut:] + tail[:cut]
    return head + tail


def _style_candidates(facts, stats, answers, allowed, seed):
    """
    Candidatos de estilo ordenados de mejor a peor. Primero la matriz
    "firma" del rubro (3 combinaciones, con piso de diversidad), después
    las plantillas permitidas que la matriz no nombró (con piel afín
    rotada por la semilla).
    """
    allowed_set =   set(allowed)
    tone        =   answers['tone']
    goal        =   answers['goals'][0]
    density     =   sum(1 for key in ('products', 'images', 'gallery', 'testimonials', 'stats', 'team', 'timeline', 'benefits', 'faqs') if facts.get(key))
    skins       =   _skin_pool(answers, seed)
    pairs       =   list(TYPE.TYPE_PAIRS)
    styles      =   _style_order(answers, seed)
    #Estilos que el dueño pidió: se priorizan en el puntaje (nunca se imponen).
    requested   =   set(answers.get('styles') or ())
    chosen_styles = {style: set() for style in styles}
    seen        =   set()
    #Plantillas ya tomadas por los bloques 1 y 2: la cobertura de estilos
    #puede reusarlas (la diversidad la resuelve `_select_styles`).
    reusing     =   set()
    candidates  =   []

    def add(template, skin_id, pair, base, strict = False):
        """`strict` (cobertura de estilos) permite reusar una plantilla con
        otra piel: la diversidad de plantilla se aplica en `_select_styles`,
        que descarta las repetidas si hay de sobra."""
        if template not in allowed_set:
            return
        if (template, skin_id) in seen or (not strict and template in reusing):
            return
        skin    =   SKIN.SKINS.get(skin_id)
        if skin is None or pair not in TYPE.TYPE_PAIRS:
            return
        seen.add((template, skin_id))
        chosen_styles[skin['style']].add(pair)
        reusing.add(template)
        score   =   base
        #Estilo pedido: se prioriza de verdad (nunca por encima de una
        #candidata imposible, porque `allowed` filtra antes). +70 lo pone por
        #delante de cualquier afinidad perdida del rubro sin inventar peso.
        score   +=  70 if skin['style'] in requested else 0
        score   +=  R.TEMPLATE_TONE_AFFINITY.get(template, {}).get(tone, 0) * 2
        score   +=  4 if template in R.TEMPLATE_GOAL_AFFINITY.get(goal, ()) else 0
        score   +=  3 if tone in skin['tones'] else 0
        score   +=  2 if answers['rubro'] in skin['rubros'] else 0
        score   +=  min(density, 6)
        score   +=  _data_signal(template, stats, facts)
        candidates.append({
            'template'  :   template,
            'skin'      :   skin_id,
            'pair'      :   pair,
            'style'     :   skin['style'],
            'source'    :   R.style_source_of(template),
            'score'     :   score,
        })

    def alt_pair(style, index):
        """Par tipográfico alternativo DENTRO del estilo: si esa piel no
        admite el de la matriz, se busca el del puerto."""
        available   =   [pair_id for pair_id in TYPE.TYPE_PAIRS if pair_id not in chosen_styles[style]]
        return available[index % len(available)] if available else None

    #1) matriz "firma" del rubro: piso de diversidad (plan + legacy + ai).
    for index, signature in enumerate(R.RUBRO_STYLES.get(answers['rubro'], ())):
        add(signature['template'], signature['skin'], signature['pair'], 40 - index * 5)
    #2) el resto de las plantillas permitidas, con piel rotada.
    order       =   list(R.RUBROS[answers['rubro']]['templates']) + list(R.AI_TEMPLATES) + list(R.LEGACY_TEMPLATES)
    order      +=  [template for template in allowed if template not in order]
    #Cada plantilla entra UNA vez al bloque general: la rotación de piel ya se
    #encarga de que la familia cambie con la semilla.
    for index, template in enumerate(order):
        if template in seen_templates(candidates):
            continue
        add(template, skins[(index * 3 + seed) % len(skins)], pairs[(index * 5 + seed) % len(pairs)], 8)
    #3) cobertura de ESTILOS: cada estilo con pieles entra a competir, así una
    #generación puede ofrecer "minimal" vs "editorial" vs "lujo" y no tres
    #variantes del mismo aire. Base baja: solo gana si el puntaje lo acompaña
    #(los estilos PEDIDOS por el dueño arrancan con la base de la matriz).
    covered_templates   =   set()
    for style_index, style in enumerate(styles):
        pool    =   _style_pool(style, answers['rubro'], tone)
        if not pool:
            continue
        #Cada estilo de la cobertura estrena plantilla propia: si dos estilos
        #cayeran sobre la misma, `_select_styles` (que exige plantilla nueva)
        #no podría mostrar dos estilos distintos en una generación.
        used    =   False
        for template_index, template in enumerate(order):
            if template in covered_templates or template in reusing:
                continue
            pair    =   pairs[(style_index * 3 + template_index) % len(pairs)]
            before  =   len(candidates)
            base    =   40 if style in requested else 6
            add(template, pool[(template_index + style_index + seed) % len(pool)], pair, base, strict = True)
            if len(candidates) > before:
                covered_templates.add(template)
                used = True
                break
        if not used and pool:
            #Ninguna plantilla libre para ese estilo: se clona la mejor
            #candidata del estilo (o la primera) con OTRA plantilla del plan
            #que todavía no compita. La plantilla importa: `_select_styles`
            #nunca elige dos propuestas con la misma.
            taken   =   seen_templates(candidates)
            free    =   [template for template in order if template in allowed_set and template not in taken]
            if not free:
                continue
            first   =   min((item for item in candidates if item['style'] == style),
                            key = lambda item: item['score'], default = None)
            if first is None:
                first   =   candidates[0] if candidates else None
            if first is None:
                continue
            candidates.append({**first,
                               'template': free[(style_index + seed) % len(free)],
                               'skin': pool[style_index % len(pool)],
                               'style': style,
                               'score': 34 if style in requested else 5})
    #Los mejores compiten; entre los tres estilos "firma" del rubro la
    #semilla decide el orden (así "otra propuesta" cambia de familia
    #visual, no de variante).
    candidates.sort(key = lambda item: (-item['score'], item['template'], item['skin']))
    #La rotación de la semilla juega SOLO entre los estilos "firma" del
    #rubro: los estilos que el dueño pidió quedan clavados al frente (si no,
    #"otra propuesta" se los comía y el pedido no se notaba).
    head    =   min(3, len(candidates))
    locked  =   [index for index, item in enumerate(candidates[:head]) if item['style'] in requested]
    if head > 1 and not locked:
        rotate      =   seed % head
        candidates  =   candidates[rotate:head] + candidates[:rotate] + candidates[head:]
    return candidates


def seen_templates(candidates):
    return {item['template'] for item in candidates}


def _select_styles(candidates, count):
    """
    Diversidad OBLIGATORIA: dentro de una generación las propuestas
    difieren en ESTILO, plantilla, piel y par tipográfico (v5). Se elige en
    tres pases que van relajando en este orden: primero estilo (dos
    sugerencias no son el mismo aire contado dos veces), después piel y
    par, y al final solo la plantilla queda como condición — la plantilla
    NUNCA se repite: dos propuestas con la misma plantilla no son dos.
    """
    chosen      =   []
    templates   =   set()
    skins       =   set()
    pairs       =   set()
    styles      =   set()

    def take(item):
        chosen.append(item)
        templates.add(item['template'])
        skins.add(item['skin'])
        pairs.add(item['pair'])
        styles.add(item['style'])

    #1) ESTILO primero: la generación cubre estilos distintos (con 2
    #propuestas = 2 estilos) aunque eso implique relajar piel o par. Es el
    #invariante más visible del v5: dos sugerencias no pueden ser el mismo
    #aire visual contado dos veces.
    for item in candidates:
        if len(chosen) >= count:
            break
        if item['template'] in templates or item['style'] in styles:
            continue
        take(item)
    #2) Estricto: plantilla + piel + par nuevos (la calidad del resto).
    for item in candidates:
        if len(chosen) >= count:
            break
        if item in chosen or item['template'] in templates or item['skin'] in skins or item['pair'] in pairs:
            continue
        take(item)
    #3) Relajado: solo exige plantilla nueva (la plantilla nunca se repite).
    for item in candidates:
        if len(chosen) >= count:
            break
        if item in chosen or item['template'] in templates:
            continue
        take(item)
    return chosen[:count]


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


#El layout de la piel se traduce a variantes REALES del catálogo (nunca
#CSS): es lo que hace que "rediseñar" cambie la estructura, no solo el
#color. Los ids de variante existen en TEMPLATE_BLOCKS.
#Familias cuya segunda variante es la versión nocturna (claro ↔ oscuro):
#abren con el default oscuro y el interruptor de tema encendido.
_TWO_FACE_FAMILIES  =   frozenset({'aurora', 'prestige'})
_NIGHT_FAMILIES     =   frozenset({'glass', 'tech', 'neon', 'gradient', 'cinematic', 'aurora', 'prestige'})
_HERO_BY_LAYOUT     =   {
    'centered': 'centered', 'split': 'split', 'cinema': 'cinema',
    'editorial': 'editorial', 'logo': 'logo',
}
_GRID_BY_LAYOUT     =   {
    '12':        ('grid', 'auto'),
    'asym':      ('cols3', 'cols3'),
    'split':     ('cols2', 'cols2'),
    'bento':     ('masonry', 'masonry'),
    'editorial': ('lead', 'lead'),
}


def _apply_skin_layout(layout, skin, facts):
    """
    Rediseño completo: la portada, la vitrina y la grilla del catálogo
    toman la variante que pide el layout de la piel. Con logo de portada
    el hero 'logo' solo se usa si hay logo real.
    """
    config      =   skin['layout']
    hero        =   _HERO_BY_LAYOUT.get(config.get('hero'))
    if hero == 'logo' and not facts.get('logo'):
        hero    =   'full'
    featured, catalog_grid  =   _GRID_BY_LAYOUT.get(config.get('grid'), ('grid', 'auto'))
    for surface, section in layout.items():
        for block in section.get('blocks', []):
            if surface == 'landing' and block['id'] == 'hero' and hero:
                block['variant']    =   hero
            elif surface == 'landing' and block['id'] == 'featured':
                block['variant']    =   featured
            elif surface == 'catalog' and block['id'] == 'grid':
                block['variant']    =   catalog_grid
    return layout


#=========================================
# ELEMENTOS SOLO-IA (bloques nuevos según la entrevista)
#=========================================
_ELEMENT_ICONS  =   ('sparkles', 'star', 'heart', 'shield-check', 'clock', 'award')
#Bloques v4: se suman SOLO con datos reales (sin props no hay bloque).
_V4_ELEMENTS    =   ('aiprocess', 'aipricing', 'aimosaic')


def _money(value):
    """Precio corto en formato es-AR ($1.500). Sin valor, cadena vacía."""
    try:
        return '$' + f'{int(round(float(value))):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return ''


def _pricing_items(customization):
    """2-4 filas de precio con datos REALES del catálogo (nunca inventa)."""
    from StoreApp.domains.catalog.models import Product
    rows    =   Product.objects.filter(store = customization.store, is_active = True)[:4]
    items   =   []
    for product in rows:
        price   =   product.offer_price if product.offer_price is not None else product.price
        money   =   _money(price)
        name    =   str(product.name or '').strip()[:40]
        if name and money:
            items.append({'name': name, 'price': money})
    return items


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
    if block_id == 'aiprocess':
        items   =   []
        for row in (customization.service_steps or [])[:5]:
            if not isinstance(row, dict):
                continue
            title   =   str(row.get('title') or row.get('name') or '').strip()[:60]
            text    =   str(row.get('text') or row.get('desc') or '').strip()[:160]
            if title:
                items.append({'title': title, **({'text': text} if text else {})})
        return {'title': 'Cómo trabajamos', 'items': items} if len(items) >= 3 else {}
    if block_id == 'aipricing':
        items   =   _pricing_items(customization)
        return {'title': 'Precios', 'items': items} if len(items) >= 2 else {}
    if block_id == 'aimosaic':
        title   =   str(customization.headline or customization.display_name or '').strip()[:80]
        caption =   str(customization.about_text or customization.description or '').strip()[:120]
        if not (title or caption):
            return {}
        return {**({'title': title} if title else {}), **({'caption': caption} if caption else {})}
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


def _add_elements(layout, customization, facts, stats, answers, use_icons, has_ai):
    """
    Reglas de elementos (ai_design_recipes.AI_ELEMENT_ORDER): dar_confianza
    => aiquote; must_have precios/garantías => aicheck; mostrar_servicios =>
    aigrid; vender_online con ofertas => aiband; 2+ datos de contacto =>
    aistrip; pasos cargados => aiprocess; 2+ productos => aipricing; galería
    grande => aimosaic. Máximo 4 en total, nunca duplica ids ni pisa un
    bloque existente. Sin íconos (use_icons=False) no se suman aigrid ni
    aistrip.
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
    #v4: rediseño de contenido, no solo de piel.
    if facts.get('steps') and goal in ('mostrar_servicios', 'conseguir_consultas'):
        picked.append('aiprocess')
    if stats.get('products', 0) >= 2 and goal in ('vender_online', 'mostrar_servicios'):
        picked.append('aipricing')
    if stats.get('gallery', 0) >= 4 or stats.get('images', 0) >= 6:
        picked.append('aimosaic')
    if not use_icons:
        picked  =   [block_id for block_id in picked if block_id not in ('aigrid', 'aistrip')]
    picked  =   [block_id for block_id in R.AI_ELEMENT_ORDER if block_id in picked][:R.AI_ELEMENT_MAX]
    landing =   layout['landing']['blocks']
    for block_id in picked:
        if block_id in {block['id'] for block in landing}:
            continue
        props   =   _element_props(block_id, customization, facts, use_icons)
        if not props and block_id in _V4_ELEMENTS:
            #Los bloques v4 (precios/pasos/mosaico) solo se suman con datos
            #reales: no inventamos precios, pasos ni fotos.
            continue
        block   =   {'id': block_id, 'enabled': True, 'variant': TEMPLATE_BLOCKS['landing'][block_id]['variants'][0]}
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
def _theme(skin, pair, answers, rng, shift, template = None):
    """
    site_theme parcial v2 compuesto por la piel: paleta + contenedores +
    botones + fondo + movimiento + layout + skin, con la tipografía
    expandida a los 13 roles del par elegido. El tono ajusta energía
    (curvas, aire, movimiento), no la identidad.
    """
    theme   =   {
        'palette'       :   copy.deepcopy(skin['palette']),
        'containers'    :   copy.deepcopy(skin['containers']),
        'buttons'       :   copy.deepcopy(skin['buttons']),
        'background'    :   copy.deepcopy(skin['background']),
        'motion'        :   copy.deepcopy(skin['motion']),
        'layout'        :   copy.deepcopy(skin['layout']),
        'skin'          :   {'id': skin['id'], 'family': skin['family']},
    }
    for section, values in R.TONE_TWEAKS[answers['tone']].items():
        theme.setdefault(section, {}).update(values)
    #El layout responde al tono sin salirse de los enums del contrato.
    if answers['tone'] == 'audaz':
        theme['layout']['density']  =   'compact'
    elif answers['tone'] == 'calido':
        theme['layout']['gutter']   =   'lg'
    #Tipografía por rol: el par fija las familias, la piel y el tono los
    #pesos/tamaños. Nunca dos familias distintas para roles de cuerpo.
    roles       =   TYPE.roles_for(pair, answers['tone'], skin['family'])
    pair_data   =   TYPE.TYPE_PAIRS.get(pair) or TYPE.TYPE_PAIRS['grotesk-clean']
    #El heading es un slug del catálogo STORE_FONTS (una familia con coma es
    #un stack CSS: site_theme lo descarta y la tienda pierde la tipografía).
    heading     =   pair_data['display'] if pair_data['display'] in TYPE.FONT_SLUGS else _FALLBACK_FONT
    theme['typography'] =   {
        'heading'       :   heading,
        'body'          :   pair_data['body'],
        'scale'         :   skin['typography'].get('scale', 'balanced'),
        'weightHeading' :   roles['h1']['weight'],
        'letterSpacing' :   '-0.02em',
        'roles'         :   roles,
    }
    if answers.get('brand_color'):
        #El color del dueño manda: la paleta se deriva de él y la propuesta
        #lo declara como elección del usuario.
        theme['palette']    =   _palette_from_brand(answers['brand_color'], theme['palette'])
        choice              =   {'source': 'user', 'accent': theme['palette']['accent']}
    else:
        accents =   skin['accents'] or (theme['palette']['accent'],)
        accent  =   accents[(shift + rng.randrange(len(accents))) % len(accents)]
        #AA no negociable: el acento es el color de marca de los botones y
        #tiene que leerse sobre el fondo de la página (piel × rubro).
        accent  =   _ensure_contrast(accent, theme['palette']['bg'], 4.5)
        theme['palette']['accent']  =   accent
        theme['palette']['primary'] =   accent
        choice              =   {'source': 'ai', 'accent': accent}
    #Legibilidad no negociable: la tinta y el muted se normalizan siempre
    #(una piel con texto tintado o un acento de marca no pueden ensuciar
    #los colores de fuente).
    theme['palette']    =   _calm_palette(theme['palette'])
    if choice['source'] == 'ai':
        choice['accent']    =   theme['palette']['accent']
    return theme, choice


def _resolve_night(answers, theme, template):
    """
    Modo noche: con enabled=True la web arranca en el default elegido y
    muestra el interruptor (theme_toggle=True); sin la respuesta el
    interruptor queda apagado y `theme` sigue el look (oscuro si el fondo
    de la paleta es oscuro). Devuelve (night_mode, theme, theme_toggle).
    """
    family          =   (theme.get('skin') or {}).get('family')
    #Las pieles de nocturno (v5: aurora/prestige) y las oscuras de siempre
    #abren con el interruptor arriba: la variante oscura queda a un clic.
    look_default    =   'dark' if (_luminance(theme['palette']['bg']) < 0.4 or family in _NIGHT_FAMILIES) else 'light'
    raw             =   answers.get('night_mode') or {}
    default         =   raw.get('default') or look_default
    if raw.get('enabled') or _needs_night_toggle(family):
        return {'enabled': True, 'default': default}, default, True
    return {'enabled': False, 'default': default}, look_default, False


def _needs_night_toggle(family):
    """Piel con dos caras (clara/oscura): sin interruptor la segunda sería
    inalcanzable. Solo las familias nuevas lo fuerzan."""
    return family in _TWO_FACE_FAMILIES


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


_SKIN_BLOCK_STYLES  =   {
    #Firma por contenedor de cada piel (claves del catálogo de site_theme).
    'brutal':       {'hero': {'radius': 'none', 'border': 'bold'}, 'cta': {'radius': 'none', 'border': 'bold'}},
    'editorial':    {'hero': {'align': 'left'}, 'aiquote': {'align': 'center'}},
    'luxury':       {'hero': {'density': 'spacious'}, 'cta': {'border': 'thin'}},
    'glass':        {'hero': {'surface': 'glass'}, 'stats': {'surface': 'glass'}},
    'kinetic':      {'hero': {'density': 'compact'}, 'aiband': {'accent': None}},
    'minimal':      {'hero': {'surface': 'flat'}},
    'mono':         {'hero': {'radius': 'none'}},
    'neon':         {'hero': {'surface': 'glass'}, 'aiband': {'accent': None}},
    'corporate':    {'hero': {'surface': 'elevated'}},
    'soft':         {'hero': {'radius': 'xl'}},
    'organic':      {'hero': {'radius': 'xl'}},
    'retro':        {'hero': {'border': 'bold'}},
    'paper':        {'hero': {'surface': 'flat'}},
    'tech':         {'hero': {'surface': 'outlined'}},
    'playful':      {'hero': {'radius': 'xl'}},
    'gradient':     {'hero': {'surface': 'glass'}},
    'cinematic':    {'hero': {'align': 'center'}},
    'warm':         {'hero': {'radius': 'lg'}},
    #v5: la firma de cada estilo nuevo en el hero (claves del catálogo de
    #layout_blocks; una clave que no exista se descarta igual).
    'swiss':        {'hero': {'radius': 'none', 'border': 'thin', 'align': 'left'}},
    'magazine':     {'hero': {'align': 'left'}, 'aiquote': {'align': 'center'}},
    'pop':          {'hero': {'radius': 'none', 'border': 'bold'}, 'cta': {'radius': 'none', 'border': 'bold'}},
    'craft':        {'hero': {'radius': 'lg', 'surface': 'outlined'}},
    'nostalgia':    {'hero': {'radius': 'md', 'border': 'thin'}},
    'prestige':     {'hero': {'density': 'spacious', 'align': 'center'}, 'cta': {'border': 'thin'}},
    'showcase':     {'hero': {'density': 'compact', 'align': 'center'}, 'gallery': {'density': 'compact'}},
    'aurora':       {'hero': {'surface': 'glass'}, 'stats': {'surface': 'glass'}, 'aiband': {'accent': None}},
}


def _block_styles(template, theme, layout, skin = None):
    """
    Overrides "pro" por contenedor: la firma de la plantilla (ai_*) y la de
    la piel, solo bloques que están en el layout y solo claves del
    catálogo. `accent` se resuelve con la paleta final.
    """
    styles  =   {}
    for block_id, values in (R.AI_BLOCK_STYLES.get(template) or {}).items():
        styles.setdefault(block_id, {}).update(values)
    if skin is not None:
        for block_id, values in _SKIN_BLOCK_STYLES.get(skin['family'], {}).items():
            styles.setdefault(block_id, {}).update(values)
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
    """
    2-3 propuestas de web completa. Cada una es una TERNA de estilo
    (plantilla + piel + par tipográfico) con diversidad garantizada, un
    layout de landing/catálogo/servicios rediseñado por la piel y el
    site_theme v2 (roles tipográficos incluidos).
    """
    styles          =   _style_candidates(facts, stats, answers, allowed, seed)
    if not styles:
        fallback    =   StoreCustomization.TEMPLATE_CLASSIC if StoreCustomization.TEMPLATE_CLASSIC in allowed else list(allowed)[0]
        styles      =   [{'template': fallback, 'skin': SKIN.SKIN_IDS[seed % len(SKIN.SKIN_IDS)],
                          'pair': 'grotesk-clean', 'source': R.style_source_of(fallback), 'score': 0}]
    count           =   _proposal_count(allowed, facts)
    chosen          =   _select_styles(styles, count)
    rng             =   random.Random(seed)
    use_icons       =   answers.get('use_icons')
    if use_icons is None:
        #Sin respuesta, el rubro decide: las webs de vidriera llevan íconos.
        use_icons   =   answers['rubro'] in R.VISUAL_RUBROS
    has_plus        =   profile_has_benefit(store.user, 'has_design_plus')
    has_style       =   profile_has_benefit(store.user, 'has_customization')
    proposals       =   []
    signatures      =   set()
    for index, style in enumerate(chosen):
        #La propuesta 0 va con el mejor estilo; las demás ya vienen con
        #plantilla/piel/par distintos (diversidad obligatoria).
        shift       =   0 if index == 0 else index
        template    =   style['template']
        skin        =   SKIN.SKINS[style['skin']]
        pair        =   style['pair']
        pattern     =   _pattern_for(template, answers, shift)
        attempt     =   0
        for attempt in range(4):
            layout  =   _layout(store, facts, answers, rng, shift + attempt, pattern)
            layout  =   _apply_skin_layout(layout, skin, facts)
            layout  =   _add_elements(layout, customization, facts, stats, answers, use_icons, has_ai)
            signature = (template, tuple(block['id'] for block in layout['landing']['blocks']))
            if signature not in signatures:
                break
        signatures.add(signature)
        cover   =   _cover_for(answers, facts)
        if cover['mode'] == 'logo':
            for block in layout['landing']['blocks']:
                if block['id'] == 'hero':
                    block['variant']    =   'logo'
        theme, choice   =   _theme(skin, pair, answers, rng, shift + attempt, template)
        if cover['mode'] == 'logo':
            #Con el logo de portada el fondo nunca apunta a una imagen: el
            #hero se resuelve con color sólido.
            background  =   dict(theme.get('background') or {})
            background['type']  =   'solid'
            background.pop('value', None)
            theme['background'] =   background
        block_styles    =   _block_styles(template, theme, layout, skin)
        if block_styles:
            theme['blocks'] =   block_styles
        night, theme_mode, theme_toggle =   _resolve_night(answers, theme, template)
        text    =   ai_design_copy.build(store, customization, answers['rubro'], answers['tone'], facts, stats, rng)
        clean_theme     =   clean_site_theme(
            theme,
            has_plus        =   has_plus,
            has_advanced    =   has_advanced,
            has_style       =   has_style,
            store           =   store,
        )
        proposals.append({
            'id'            :   f'p{index + 1}',
            'label'         :   (pattern['label'] if pattern else R.GOAL_RECIPES[answers['goals'][0]]['labels'][index % 3])[:32],
            'why'           :   _why(answers, template, index, pattern),
            'template'      :   template,
            'style_source'  :   style['source'],
            'skin'          :   {'id': skin['id'], 'family': skin['family'], 'label': skin['label']},
            'site_theme'    :   clean_theme,
            'typography_roles': (clean_theme.get('typography') or {}).get('roles') or theme['typography']['roles'],
            'layout'        :   clean_theme.get('layout') or theme['layout'],
            'variety'       :   {
                'family'        :   skin['family'],
                #v5: el estilo de diseño (grupo del entrenamiento) que la
                #propuesta representa; la UI lo muestra como etiqueta.
                'style'         :   skin['style'],
                'style_label'   :   SKIN.STYLE_LABELS.get(skin['style'], ''),
                'differs_by'    :   ['template', 'skin', 'type-pair'],
            },
            'redesign'      :   {
                'surfaces'      :   ['landing', 'catalog', 'services'],
                'changed'       :   bool(clean_theme.get('layout') or clean_theme.get('skin')),
            },
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
