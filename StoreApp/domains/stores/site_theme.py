import json
import re

from rest_framework import serializers

"""

Tema visual del Studio (`site_theme` de StoreCustomization) — espejo del
contrato único del Studio (frontend/src/studio/contract.js): las
secciones/claves/enums están cerrados en catálogo (STUDIO_ENUMS) y el
backend RECHAZA lo desconocido o inválido (el frontend aplica sus propios
defaults para el render: una tienda sin site_theme se ve idéntica a hoy).

Reglas:
- Secciones permitidas: palette, containers, typography, buttons,
  background, motion, mobile, blocks, layout, skin — cualquier otra clave de
  primer nivel o de sección se rechaza (nada de HTML/CSS libre).
- v2 del tema (motor "Diseñar con IA" 4): typography.roles (13 roles
  cerrados con font/size/weight/tracking/leading/case), layout (density,
  grid, hero, gutter, measure, radiusScale) y skin {id, family} del
  catálogo de 18 familias. `skin` fuera del catálogo se DESCARTA en
  silencio (igual que los bloques desconocidos); un rol/enum/peso
  inválido es 400.
- palette: hex #RGB/#RRGGBB, se normaliza a #rrggbb minúsculas.
- enums: coincidencia exacta del catálogo; numéricos con rango;
  booleans estrictos.
- typography.heading/body: slug del catálogo de fuentes o stack CSS
  acotado — solo letras, espacios, comas, puntos y guiones (sin comillas
  ni funciones: el valor termina dentro de un font-family CSS).
- background.value: hex, URL de una imagen PROPIA de la tienda (logo,
  portada, carrusel, galería) o un token CSS seguro de fondo (colores y
  degradados — sin url(), expression, @import ni caracteres que cierren
  la declaración).
- Tamaño máximo del JSON: SITE_THEME_MAX_BYTES (contado sobre el payload
  recibido, como layout_config).

Gating por plan (mismo criterio que `accent` — descarte silencioso, no
400): todo el tema exige has_design_advanced salvo el subconjunto básico
SITE_THEME_PLUS_KEYS (radius/density de containers) que alcanza con
has_design_plus. El plan Básico (has_style, derivado de has_customization)
solo persiste SITE_THEME_STYLE_KEYS: el estilo elegido (style.id, si su
plantilla entra en el plan) y su juego de colores de fuentes/contenedores
en claro y oscuro (styleColors, hex + AA). Sin beneficios de diseño el
viewset ya saca el campo del payload; clean_site_theme además filtra las
claves que sobran para el plan y el serializer mergea el resultado sobre lo
guardado, así los valores premium almacenados sobreviven una baja de plan
(reaparecen al volver).

"""
SITE_THEME_MAX_BYTES    =   12288   #+2 KB por `blocks` (12 bloques) y +6 KB por la v2:
                                    #typography.roles (13 roles x 6 claves), layout (6 claves) y skin
_BG_VALUE_MAX           =   600
_FONT_MAX               =   120
_TRACKING_MAX           =   16
_SITE_THEME_MAX_BLOCKS  =   12

#=========================================
# CATÁLOGO CERRADO (espejo de STUDIO_ENUMS del contrato)
#=========================================
_PALETTE_KEYS   =   ('primary', 'secondary', 'accent', 'bg', 'surface', 'text', 'muted', 'border', 'success', 'danger')
_RADIUS         =   ('none', 'sm', 'md', 'lg', 'xl', 'pill')
_SHADOW         =   ('none', 'soft', 'medium', 'deep')
_BORDER         =   ('none', 'thin', 'bold')
_DENSITY        =   ('compact', 'comfortable', 'spacious')
_SURFACE        =   ('flat', 'glass', 'elevated', 'outlined')
_TYPE_SCALE     =   ('compact', 'balanced', 'editorial')
_BTN_SHAPE      =   ('square', 'rounded', 'pill')
_BTN_STYLE      =   ('solid', 'outline', 'ghost', 'gradient')
_BTN_SIZE       =   ('sm', 'md', 'lg')
_BG_TYPE        =   ('solid', 'gradient', 'mesh', 'pattern', 'image')
_OVERLAY        =   ('none', 'soft', 'strong')
_REVEAL         =   ('none', 'fade', 'rise', 'stagger')
_HOVER          =   ('none', 'lift', 'glow')
_INTENSITY      =   ('subtle', 'medium', 'bold')
_NAV            =   ('top', 'bottom', 'drawer')
_CARD_STYLE     =   ('standard', 'compact', 'overlay')
_HERO_HEIGHT    =   ('compact', 'tall')
_BLOCK_ALIGN    =   ('left', 'center', 'right')
#v2 del tema: layout cerrado (mismas claves/enums que el contrato del
#frontend) y catálogo de pieles. `_DENSITY` se comparte con containers.
_GRID           =   ('12', 'asym', 'split', 'bento', 'editorial')
_HERO_LAYOUT    =   ('centered', 'split', 'cinema', 'logo', 'editorial')
_GUTTER         =   ('sm', 'md', 'lg')
_MEASURE        =   ('narrow', 'normal', 'wide')
_RADIUS_SCALE   =   ('none', 'sm', 'md', 'lg', 'xl')
#Espejo de ai_design_typography (catálogo cerrado de 13 roles y 24
#familias). Se importa acá para validar `typography.roles` y `skin`.
from .services.ai_design_typography import (  # noqa: E402
    FONT_SLUGS as _TYPE_FONT_SLUGS,
)
from .services.ai_design_typography import (
    TYPE_CASES as _TYPE_CASE,
)
from .services.ai_design_typography import (
    TYPE_LEADING as _TYPE_LEADING,
)
from .services.ai_design_typography import (
    TYPE_SIZES as _TYPE_SIZE,
)
from .services.ai_design_typography import (
    TYPE_TRACKING as _TYPE_TRACKING,
)
from .services.ai_design_typography import (
    TYPOGRAPHY_ROLES as _TYPE_ROLES,
)


#El catálogo de pieles se resuelve por función; `ai_design_skins` es la
#fuente única de ids, familias y presets del Studio.
def _skin_ids():
    from .services.ai_design_skins import SKIN_IDS
    return SKIN_IDS


def _skin_families():
    from .services.ai_design_skins import SKIN_FAMILY_SET
    return SKIN_FAMILY_SET


def _skin_family_of():
    from .services.ai_design_skins import SKIN_FAMILY_OF
    return SKIN_FAMILY_OF


def _style_preset_templates():
    from .services.ai_design_skins import STYLE_PRESET_TEMPLATES
    return STYLE_PRESET_TEMPLATES
#Sección `blocks`: overrides de estilo por contenedor (id de bloque de la
#superficie landing). Las claves de bloque se validan contra
#TEMPLATE_BLOCKS['landing']; lo desconocido se descarta en silencio.
_BLOCK_STYLE_KEYS       =   ('radius', 'shadow', 'border', 'density', 'surface', 'align', 'accent')
_BLOCK_STYLE_SPEC       =   {
    'radius'    :   ('enum', _RADIUS),
    'shadow'    :   ('enum', _SHADOW),
    'border'    :   ('enum', _BORDER),
    'density'   :   ('enum', _DENSITY),
    'surface'   :   ('enum', _SURFACE),
    'align'     :   ('enum', _BLOCK_ALIGN),
    'accent'    :   ('hex',),
}
#Estilos del selector: el catálogo cerrado completo de STUDIO_PRESETS
#(frontend/src/studio/presets/catalog.js). El id solo se guarda si la
#plantilla del preset entra en el nivel del plan.
#La tabla vive en el catálogo de pieles (fuente única compartida con el
#motor de IA): los ids válidos se derivan de ahí, nunca de una copia que
#pueda quedar desactualizada cuando se suma un preset.
_STYLE_IDS      =   tuple(_style_preset_templates())
_STYLE_MODES            =   ('light', 'dark')
_STYLE_PALETTES         =   ('original', 'warm', 'cool', 'contrast')
_STYLE_FONT_KEYS        =   ('heading', 'body', 'muted', 'link')
_STYLE_CONTAINER_KEYS   =   ('bg', 'surface', 'border', 'onSurface')

#spec por sección: clave -> (kind, extra). kinds: hex|enum|font|int|bool|css|bg.
_SECTION_SPECS  =   {
    'palette'       :   {key: ('hex',) for key in _PALETTE_KEYS},
    'containers'    :   {
        'radius'    :   ('enum', _RADIUS),
        'shadow'    :   ('enum', _SHADOW),
        'border'    :   ('enum', _BORDER),
        'density'   :   ('enum', _DENSITY),
        'surface'   :   ('enum', _SURFACE),
    },
    'typography'    :   {
        'heading'       :   ('font',),
        'body'          :   ('font',),
        'scale'         :   ('enum', _TYPE_SCALE),
        'weightHeading' :   ('int', 100, 900),
        'letterSpacing' :   ('tracking',),
        #v2: presupuesto tipográfico por rol (13 roles cerrados).
        'roles'         :   ('roles',),
    },
    'buttons'       :   {
        'shape'     :   ('enum', _BTN_SHAPE),
        'style'     :   ('enum', _BTN_STYLE),
        'size'      :   ('enum', _BTN_SIZE),
    },
    'background'    :   {
        'type'      :   ('enum', _BG_TYPE),
        'value'     :   ('bg',),
        'overlay'   :   ('enum', _OVERLAY),
    },
    'motion'        :   {
        'reveal'    :   ('enum', _REVEAL),
        'hover'     :   ('enum', _HOVER),
        'intensity' :   ('enum', _INTENSITY),
    },
    'mobile'        :   {
        'nav'       :   ('enum', _NAV),
        'gridCols'  :   ('int', 1, 2),
        'cardStyle' :   ('enum', _CARD_STYLE),
        'stickyCta' :   ('bool',),
        'heroHeight':   ('enum', _HERO_HEIGHT),
    },
    'style'         :   {
        'id'        :   ('enum', _STYLE_IDS),
        'palette'   :   ('enum', _STYLE_PALETTES),
    },
    'styleColors'   :   {mode: ('styleSet',) for mode in _STYLE_MODES},
    'blocks'        :   {},
    #v2: layout propio de la web (no solo paleta/radio) y piel del catálogo.
    'layout'        :   {
        'density'       :   ('enum', _DENSITY),
        'grid'          :   ('enum', _GRID),
        'hero'          :   ('enum', _HERO_LAYOUT),
        'gutter'        :   ('enum', _GUTTER),
        'measure'       :   ('enum', _MEASURE),
        'radiusScale'   :   ('enum', _RADIUS_SCALE),
    },
    'skin'          :   {
        'id'            :   ('skin',),
        'family'        :   ('enum', tuple(sorted(_skin_families()))),
    },
}
#Subconjunto básico del tema que admite has_design_plus (Estándar): el
#resto de las secciones/claves exige has_design_advanced (Premium).
SITE_THEME_PLUS_KEYS    =   frozenset({
    ('containers', 'radius'),
    ('containers', 'density'),
})
#Piso del plan Básico (has_customization): el estilo elegido + su juego de
#colores de fuentes y contenedores en claro/oscuro. Nada de tipografía,
#fondo, movimiento ni paleta libres.
SITE_THEME_STYLE_KEYS   =   frozenset({
    ('style', 'id'),
    ('style', 'palette'),
    ('styleColors', 'light'),
    ('styleColors', 'dark'),
    #v6: la piel elegida por el motor (o por el Studio) viaja hasta en
    #Básico: una web diseñada no puede quedar con la piel base al publicar.
    ('skin', 'id'),
    ('skin', 'family'),
})
#=========================================
# VALIDADORES DE VALOR
#=========================================
_HEX6_RE    =   re.compile(r'^#?[0-9a-fA-F]{6}$')
_HEX3_RE    =   re.compile(r'^#?[0-9a-fA-F]{3}$')
#Stack tipográfico: familias con espacios, comas, puntos y guiones. Sin
#comillas ni funciones — el texto termina inline en un font-family CSS y
#una comilla podría cerrar el atributo.
_FONT_RE        =   re.compile(r'^[\w ,.\-]{1,%d}$' % _FONT_MAX)
_TRACKING_RE    =   re.compile(r'^-?\d+(\.\d+)?(px|em|rem|%)?$|^normal$')
#Token CSS de fondo: colores hex/nombrados, rgb(a)/hsl(a) y degradados.
#El charset ya descarta : ; { } < > ' " / \ @ = — sin ellos no hay
#url() externa, comentarios ni cierre de declaración; igual se rechazan
#los nombres de función peligrosos por las dudas.
_BG_CSS_RE      =   re.compile(r'^[A-Za-z0-9 #(),.%%\-]{1,%d}$' % _BG_VALUE_MAX)
_BG_CSS_BANNED  =   ('url', 'expression', 'import', 'javascript', 'data:', 'file:')

def _norm_hex(raw):
    if not isinstance(raw, str):
        return None
    value   =   raw.strip()
    if _HEX6_RE.match(value):
        return '#' + value.lstrip('#').lower()
    if _HEX3_RE.match(value):
        return '#' + ''.join(c * 2 for c in value.lstrip('#').lower())
    return None

def _v_enum(raw, options, label):
    if not isinstance(raw, str) or raw not in options:
        raise serializers.ValidationError(f'"{label}": elegí una opción válida ({" | ".join(options)}).')
    return raw

def _v_int(raw, lo, hi, label):
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise serializers.ValidationError(f'"{label}" debe ser un número entero entre {lo} y {hi}.')
    value   =   int(round(raw))
    if value < lo or value > hi:
        raise serializers.ValidationError(f'"{label}" debe ser un número entre {lo} y {hi}.')
    return value

def _v_bool(raw, label):
    if not isinstance(raw, bool):
        raise serializers.ValidationError(f'"{label}" admite solo verdadero o falso.')
    return raw

def _v_font(raw):
    if not isinstance(raw, str) or not _FONT_RE.match(raw.strip()):
        raise serializers.ValidationError('La fuente admite solo letras, números, espacios, comas, puntos y guiones.')
    return raw.strip()

def _v_tracking(raw):
    value   =   raw.strip() if isinstance(raw, str) else ''
    if len(value) > _TRACKING_MAX or not _TRACKING_RE.match(value):
        raise serializers.ValidationError('El interletraje debe ser una medida CSS corta (por ejemplo -0.02em).')
    return value

def _v_css(raw):
    value   =   raw.strip() if isinstance(raw, str) else ''
    if not _BG_CSS_RE.match(value):
        raise serializers.ValidationError('El fondo admite solo colores y degradados CSS.')
    lowered =   value.lower()
    if any(bad in lowered for bad in _BG_CSS_BANNED):
        raise serializers.ValidationError('El fondo no admite URLs ni funciones externas.')
    return value

def _contrast_ratio(a, b):
    """WCAG 2.1 (misma fórmula que contrastRatio del contrato)."""
    def channel(value):
        s   =   value / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    def lum(hex_value):
        h   =   hex_value.lstrip('#')
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    la, lb  =   lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def _v_style_set(raw, mode):
    """Juego de colores de un modo: fuentes y contenedores con hex normalizado
    y AA (4.5) de cada color de texto sobre surface y bg."""
    if not isinstance(raw, dict):
        raise serializers.ValidationError(f'El set "{mode}" debe ser un objeto con fuentes y contenedores.')
    unknown =   [key for key in raw if key not in ('fonts', 'containers')]
    if unknown:
        raise serializers.ValidationError(f'Clave desconocida en "{mode}": "{unknown[0]}".')
    fonts       =   raw.get('fonts') or {}
    containers  =   raw.get('containers') or {}
    if not isinstance(fonts, dict) or not isinstance(containers, dict):
        raise serializers.ValidationError(f'Las fuentes y contenedores de "{mode}" deben ser objetos.')
    for key in fonts:
        if key not in _STYLE_FONT_KEYS:
            raise serializers.ValidationError(f'Color de fuente desconocido en "{mode}": "{key}".')
    for key in containers:
        if key not in _STYLE_CONTAINER_KEYS:
            raise serializers.ValidationError(f'Color de contenedor desconocido en "{mode}": "{key}".')
    out =   {'fonts': {}, 'containers': {}}
    for key, value in fonts.items():
        color   =   _norm_hex(value)
        if color is None:
            raise serializers.ValidationError(f'"{key}": ingresá un color válido (hex #RRGGBB).')
        out['fonts'][key]   =   color
    for key, value in containers.items():
        color   =   _norm_hex(value)
        if color is None:
            raise serializers.ValidationError(f'"{key}": ingresá un color válido (hex #RRGGBB).')
        out['containers'][key]  =   color
    bases   =   [out['containers'][key] for key in ('surface', 'bg') if key in out['containers']]
    for key, color in out['fonts'].items():
        #`link` es el acento: vive en enlaces sobre el fondo de la página
        #(no sobre los cards). Contrahacerlo oscurecería la marca.
        checked  =   [out['containers']['bg']] if key == 'link' and 'bg' in out['containers'] else bases
        for base in checked:
            if _contrast_ratio(color, base) < 4.5:
                raise serializers.ValidationError(
                    f'El color de fuente "{key}" no alcanza contraste AA sobre el contenedor.'
                )
    on_surface  =   out['containers'].get('onSurface')
    for base in bases:
        if on_surface and _contrast_ratio(on_surface, base) < 4.5:
            raise serializers.ValidationError('El texto sobre superficie no alcanza contraste AA.')
    return out

def _v_roles(raw):
    """
    typography.roles: los 13 roles cerrados, cada uno con {font, size,
    weight, tracking, leading, case}. Todo fuera del catálogo es 400 (la
    tipografía no se descarta en silencio: un rol inválido rompería la
    escala completa).
    """
    if not isinstance(raw, dict):
        raise serializers.ValidationError('"roles" debe ser un objeto {rol: valores}.')
    unknown =   [role for role in raw if role not in _TYPE_ROLES]
    if unknown:
        raise serializers.ValidationError(f'Rol tipográfico desconocido: "{unknown[0]}".')
    out     =   {}
    for role, value in raw.items():
        if not isinstance(value, dict):
            raise serializers.ValidationError(f'Los valores de "{role}" deben ser un objeto.')
        extra   =   [key for key in value if key not in ('font', 'size', 'weight', 'tracking', 'leading', 'case')]
        if extra:
            raise serializers.ValidationError(f'Clave desconocida en "{role}": "{extra[0]}".')
        font    =   value.get('font')
        if not isinstance(font, str) or font not in _TYPE_FONT_SLUGS:
            raise serializers.ValidationError(f'"{role}.font": elegí una fuente del catálogo.')
        weight  =   value.get('weight')
        if isinstance(weight, bool) or not isinstance(weight, int) or weight % 100 or not 300 <= weight <= 900:
            raise serializers.ValidationError(f'"{role}.weight" debe ser 300, 400, 500, 600, 700, 800 o 900.')
        out[role]   =   {
            'font'      :   font,
            'size'      :   _v_enum(value.get('size'), _TYPE_SIZE, f'{role}.size'),
            'weight'    :   weight,
            'tracking'  :   _v_enum(value.get('tracking'), _TYPE_TRACKING, f'{role}.tracking'),
            'leading'   :   _v_enum(value.get('leading'), _TYPE_LEADING, f'{role}.leading'),
            'case'      :   _v_enum(value.get('case'), _TYPE_CASE, f'{role}.case'),
        }
    return out


def _clean_skin(raw):
    """
    skin: {id, family} del catálogo. Un id fuera del catálogo se DESCARTA
    en silencio (None) — igual que un bloque desconocido: la web sigue
    viéndose bien con el resto del tema. La family se corrige desde el id
    cuando no coincide.
    """
    if not isinstance(raw, dict):
        return None
    skin_id =   raw.get('id')
    if not isinstance(skin_id, str) or skin_id not in _skin_ids():
        return None
    family  =   _skin_family_of().get(skin_id)
    return {'id': skin_id, 'family': family}


def _store_image_urls(store):
    """URLs servibles de las imágenes propias de la tienda (logo, portada,
    carrusel, galería/decoración) — único origen válido de un fondo image."""
    from .services.storage import object_url
    if store is None:
        return set()
    keys        =   []
    cust        =   getattr(store, 'customization', None)
    if cust is not None:
        keys   +=   [cust.logo_key, cust.cover_key]
    keys       +=   store.carousel_images.values_list('image_key', flat = True)
    keys       +=   store.gallery_images.values_list('image_key', flat = True)
    return {url for url in (object_url(key) for key in keys if key) if url}
#=========================================
# CLEAN / FILTER / MERGE
#=========================================
def _clean_block_styles(content):
    """
    Sección `blocks`: {block_id: {radius|shadow|border|density|surface|
    align|accent}}. Máximo 12 bloques; los ids fuera del catálogo de
    landing se descartan en silencio; una clave o un valor inválido dentro
    de un bloque válido se rechaza (400), igual que el resto del tema.
    """
    if not isinstance(content, dict):
        raise serializers.ValidationError('La sección "blocks" debe ser un objeto {bloque: estilos}.')
    if len(content) > _SITE_THEME_MAX_BLOCKS:
        raise serializers.ValidationError(f'Podés personalizar hasta {_SITE_THEME_MAX_BLOCKS} bloques.')
    from .layout_blocks import TEMPLATE_BLOCKS
    known   =   TEMPLATE_BLOCKS['landing']
    out     =   {}
    for block_id, styles in content.items():
        if block_id not in known:
            continue
        if not isinstance(styles, dict):
            raise serializers.ValidationError(f'Los estilos de "{block_id}" deben ser un objeto.')
        unknown =   [key for key in styles if key not in _BLOCK_STYLE_KEYS]
        if unknown:
            raise serializers.ValidationError(f'Estilo desconocido en "{block_id}": "{unknown[0]}".')
        clean   =   {}
        for key, raw in styles.items():
            kind    =   _BLOCK_STYLE_SPEC[key][0]
            if kind == 'hex':
                color   =   _norm_hex(raw)
                if color is None:
                    raise serializers.ValidationError(f'"{block_id}.{key}": ingresá un color válido (hex #RRGGBB).')
                clean[key]  =   color
            else:
                clean[key]  =   _v_enum(raw, _BLOCK_STYLE_SPEC[key][1], f'{block_id}.{key}')
        if clean:
            out[block_id]   =   clean
    return out

def clean_site_theme(value, *, has_plus = False, has_advanced = False, has_style = False, store = None):
    """
    Valida y sanea el site_theme recibido según el contrato del Studio.
    Devuelve un dict PARCIAL (solo lo enviado, ya normalizado): el merge
    con los defaults corre del lado del frontend (resolveSiteTheme) y el
    merge sobre lo guardado corre en el serializer. Las secciones/claves
    por encima del plan se descartan en silencio (como `accent`).
    """
    if not isinstance(value, dict):
        raise serializers.ValidationError('El tema del sitio debe ser un objeto de secciones.')
    try:
        if len(json.dumps(value)) > SITE_THEME_MAX_BYTES:
            raise serializers.ValidationError('El tema del sitio es demasiado grande.')
    except (TypeError, ValueError):
        raise serializers.ValidationError('El tema del sitio no es un JSON válido.')
    unknown     =   [key for key in value if key not in _SECTION_SPECS]
    if unknown:
        raise serializers.ValidationError(f'Sección desconocida: "{unknown[0]}".')
    clean       =   {}
    for section, content in value.items():
        if section == 'blocks':
            #Overrides por contenedor: toda la sección exige Premium (no
            #está en SITE_THEME_PLUS_KEYS); sin el flag se descarta entera.
            if not has_advanced:
                continue
            blocks  =   _clean_block_styles(content)
            if blocks:
                clean['blocks'] =   blocks
            continue
        spec    =   _SECTION_SPECS[section]
        #Los tres pisos del plan suman: Premium todo, Estándar = básico +
        #Estándar (radius/density), Básico = estilo + colores + piel. Así
        #subir de plan nunca pierde lo que el plan anterior ya guardaba.
        if has_advanced:
            allowed =   set(spec)
        elif has_plus:
            allowed =   {key for key in spec if (section, key) in SITE_THEME_PLUS_KEYS or (section, key) in SITE_THEME_STYLE_KEYS}
        elif has_style:
            allowed =   {key for key in spec if (section, key) in SITE_THEME_STYLE_KEYS}
        else:
            allowed =   set()
        if not allowed:
            continue    #sección entera reservada a otro plan: descarte silencioso
        if not isinstance(content, dict):
            raise serializers.ValidationError(f'La sección "{section}" debe ser un objeto.')
        unknown_keys    =   [key for key in content if key not in spec]
        if unknown_keys:
            raise serializers.ValidationError(f'Clave desconocida en "{section}": "{unknown_keys[0]}".')
        out     =   {}
        for key, raw in content.items():
            if key not in allowed:
                continue    #clave reservada a otro plan: descarte silencioso
            kind        =   spec[key][0]
            if kind == 'hex':
                color   =   _norm_hex(raw)
                if color is None:
                    raise serializers.ValidationError(f'"{key}": ingresá un color válido (hex #RRGGBB).')
                out[key]    =   color
            elif kind == 'enum':
                out[key]    =   _v_enum(raw, spec[key][1], key)
            elif kind == 'int':
                out[key]    =   _v_int(raw, spec[key][1], spec[key][2], key)
            elif kind == 'bool':
                out[key]    =   _v_bool(raw, key)
            elif kind == 'font':
                out[key]    =   _v_font(raw)
            elif kind == 'tracking':
                out[key]    =   _v_tracking(raw)
            elif kind == 'bg':
                out[key]    =   _clean_bg_value(raw, store)
            elif kind == 'styleSet':
                out[key]    =   _v_style_set(raw, key)
            elif kind == 'roles':
                out[key]    =   _v_roles(raw)
            elif kind == 'skin':
                cleaned     =   _clean_skin({'id': raw})
                if cleaned is None:
                    continue    #piel fuera del catálogo: descarte silencioso
                out[key]    =   cleaned['id']
        #La family de la piel nunca se guarda suelta: se deriva del id y,
        #sin id válido, la sección entera se descarta.
        if section == 'skin':
            if out.get('id'):
                out['family']   =   _skin_family_of()[out['id']]
            else:
                out.clear()
        if out:
            clean[section]  =   out
    #El id del estilo solo viaja si su plantilla entra en el nivel del plan
    #(Básico: classic/duo; Estándar suma calma/vitrina; Premium, todo).
    style   =   clean.get('style')
    if style and 'id' in style:
        template    =   _style_preset_templates().get(style['id'])
        try:
            from .services.services import allowed_templates_of
            allowed_tpls    =   allowed_templates_of(store.user) if store is not None else ()
        except Exception:
            allowed_tpls    =   ()
        if not template or template not in allowed_tpls:
            style.pop('id', None)
            style.pop('palette', None)
        if not style:
            clean.pop('style', None)
    return clean

def _clean_bg_value(raw, store):
    """background.value: null, hex, URL de imagen propia o token CSS seguro
    (degradado/patrón). Cualquier otra cosa (HTML, CSS libre, URL ajena)
    se rechaza."""
    if raw is None or raw == '':
        return None
    if not isinstance(raw, str):
        raise serializers.ValidationError('El valor del fondo debe ser un color, una imagen propia o un degradado CSS.')
    value   =   raw.strip()
    if not value or len(value) > _BG_VALUE_MAX:
        raise serializers.ValidationError('El valor del fondo es demasiado largo.')
    color   =   _norm_hex(value)
    if color is not None:
        return color
    if value in _store_image_urls(store):
        return value
    return _v_css(value)

def filter_site_theme(theme, *, has_plus = False, has_advanced = False, has_style = False):
    """
    site_theme EFECTIVO para la web pública según el plan vigente — espejo
    del descarte del PATCH: con has_design_advanced pasa todo lo guardado;
    con has_design_plus el subconjunto básico (radius/density) + el estilo;
    con solo has_style (Básico) el estilo y su juego de colores; sin
    beneficios de diseño, {} (los defaults del contrato replican el look
    actual). Lo guardado no se toca: reaparece si el plan vuelve.
    """
    if not isinstance(theme, dict):
        return {}
    if has_advanced:
        return dict(theme)
    #La piel es presupuesto visual básico (el motor la elige con cualquier
    #plan con diseño): sin flags de diseño no hay piel que publicar.
    if not has_plus and not has_style:
        return {}
    keep_set    =   SITE_THEME_PLUS_KEYS | SITE_THEME_STYLE_KEYS if has_plus else SITE_THEME_STYLE_KEYS
    out     =   {}
    for section, content in theme.items():
        if not isinstance(content, dict):
            continue
        keep    =   {key: val for key, val in content.items() if (section, key) in keep_set}
        if keep:
            out[section]    =   keep
    return out

def merge_theme(stored, patch):
    """
    Merge por sección del PATCH saneado sobre lo guardado: las claves que
    vienen pisan, las ausentes se conservan (los valores premium
    almacenados sobreviven una baja de plan y los PATCH parciales no pisan
    secciones ajenas).
    """
    merged  =   dict(stored) if isinstance(stored, dict) else {}
    for section, content in (patch or {}).items():
        base            =   merged.get(section)
        merged[section] =   {**(base if isinstance(base, dict) else {}), **content}
    return merged
