import copy
import re
import unicodedata

from django.core.cache import cache
from rest_framework import serializers

from . import ai_design_recipes as R
from .ai_design import (
    CACHE_TTL,
    AiDesignError,
    _ensure_contrast,
    _luminance,
    _norm_hex,
    apply_design_overlay,
    generate,
)

"""
Proxy del wizard "Diseño asistido" hacia el MCP de estilos.

El frontend manda el pedido del cliente como ESTRUCTURA DE DATO (una clave
por pregunta del wizard) y el MCP decide qué PATRÓN DE DISEÑO aplicar,
tomado de las fuentes de repos cargadas en `DesignModelMcp`
(`html_componentes` + `tokens_diseno.source_repo`), NO de los presets
curados del sistema:

  1. `prompt` -> respuestas del motor (`ai_design.generate`): rubro,
     objetivos, tono, audiencia, imprescindibles y notas libres.
  2. `select_styles` consulta el catálogo del MCP (`search_design_styles` /
     `list_design_styles`) y se queda SOLO con las entradas que vienen de un
     repo (`tokens_diseno.source_repo`), priorizando las que traen una
     página completa (`hero` en `html_componentes`).
  3. `pattern_from_components` lee los bloques HTML del repo y deriva el
     patrón: qué secciones usa y en qué orden, y la variante de portada y
     de vitrina (split/centered/full, cols3/cols4…).
  4. Cada propuesta del motor recibe un patrón DISTINTO: el orden y las
     variantes se aplican al `layout_config` (saneado con
     `clean_layout_config`) y los `tokens_diseno` del repo se traducen a
     `site_theme` (saneado con `clean_site_theme`). Lo que se ve en la
     tarjeta es lo que se publica.
  5. El overlay queda en caché por (tienda, semilla): `apply` y `refine` lo
     reaplican sobre el recálculo del motor, por eso publicar no pierde el
     patrón elegido por el MCP.

El token del MCP y cualquier credencial quedan del lado del servidor: el
navegador nunca ve nada más que este endpoint.
"""

MAX_MESSAGE     =   4000
MAX_TURNS       =   20
MAX_STYLES      =   6

#Claves del mensaje (texto libre, compatibilidad) -> campo del motor.
_BLOCK_KEYS     =   {
    'rubro'             :   'rubro',
    'categoria'         :   'rubro',
    'tipo de negocio'   :   'rubro',
    'objetivo'          :   'goals',
    'objetivos'         :   'goals',
    'que busco'         :   'goals',
    'tono'              :   'tone',
    'estilo'            :   'tone',
    'audiencia'         :   'audience',
    'publico'           :   'audience',
    'a quien le hablo'  :   'audience',
    'imprescindible'    :   'must_have',
    'no puede faltar'   :   'must_have',
    'notas'             :   'content_hint',
    'descripcion'       :   'content_hint',
    'nombre'            :   'content_hint',
}

#Palabras -> id de rubro del motor (R.RUBROS). El orden importa: gana la
#primera que aparece en el texto.
_RUBRO_WORDS    =   (
    ('gastronomia', ('gastronomia', 'comida', 'resto', 'restaurant', 'bar', 'panaderia', 'cafeteria', 'delivery', 'heladeria')),
    ('indumentaria', ('indumentaria', 'moda', 'ropa', 'calzado', 'accesorio')),
    ('belleza', ('belleza', 'estetica', 'peluqueria', 'unas', 'maquillaje', 'spa')),
    ('salud', ('salud', 'bienestar', 'consultorio', 'terapia', 'clinica', 'gym', 'gimnasio')),
    ('construccion', ('construccion', 'obra', 'plomeria', 'electricidad', 'arreglo', 'oficio', 'pintura', 'carpinteria')),
    ('seguridad', ('seguridad', 'bombero', 'epp', 'industrial')),
    ('tecnologia', ('tecnologia', 'software', 'equipo', 'reparacion', 'informatica')),
    ('educacion', ('educacion', 'clase', 'curso', 'taller', 'escuela')),
    ('turismo', ('turismo', 'viaje', 'hotel', 'alojamiento', 'excursion')),
    ('mascotas', ('mascota', 'veterinaria', 'pet')),
    ('arte', ('arte', 'diseno', 'deco', 'mueble', 'regalo', 'manualidad')),
    ('servicios_profesionales', ('profesional', 'estudio', 'consultoria', 'contador', 'abogado')),
    ('comercio', ('comercio', 'tienda', 'local', 'kiosco', 'almacen', 'mayorista', 'distribuidor')),
)

#Palabras -> objetivo del motor (R.GOALS).
_GOAL_WORDS     =   (
    ('vender_online', ('vender', 'venta', 'online', 'comprar', 'ecommerce', 'carrito')),
    ('conseguir_consultas', ('consulta', 'contacto', 'escriban', 'llamen', 'presupuesto', 'whatsapp')),
    ('dar_confianza', ('confianza', 'confiable', 'serio', 'trayectoria', 'seriedad')),
    ('mostrar_trabajos', ('trabajo', 'galeria', 'portfolio', 'obra', 'foto')),
    ('mostrar_servicios', ('servicio', 'ofrezco', 'que hago', 'catalogo de servicios')),
)

#Palabras -> tono del motor (R.TONES).
_TONE_WORDS     =   (
    ('audaz', ('audaz', 'personalidad', 'energia', 'atrevid', 'fuerte')),
    ('calido', ('calido', 'cercano', 'amable', 'familiar')),
    ('serio', ('serio', 'confiable', 'sobrio', 'formal', 'elegante')),
    ('moderno', ('moderno', 'simple', 'limpio', 'actual', 'minimal')),
)

#Palabras -> "no puede faltar" (ids de R.MUST_HAVE_BLOCKS).
_MUST_WORDS     =   (
    ('whatsapp', ('whatsapp', 'wsp')),
    ('hours', ('horario', 'abierto', 'atencion')),
    ('map', ('mapa', 'direccion', 'ubicacion', 'llegar')),
    ('prices', ('precio', 'cuanto sale', 'tarifa', 'lista de precios')),
    ('testimonials', ('opinion', 'testimonio', 'resena', 'clientes dicen')),
    ('faqs', ('pregunta', 'faq', 'duda')),
)

#Rubro del motor -> categorías del catálogo del MCP (DesignModelMcp.categoria).
#La primera que tenga estilos gana; vacío = buscar sin filtro.
_RUBRO_CATEGORIES   =   {
    'comercio'                  :   ('general', 'moda'),
    'gastronomia'               :   ('alimentos', 'cafeteria'),
    'indumentaria'              :   ('moda',),
    'servicios_profesionales'   :   ('servicios', 'general'),
    'salud'                     :   ('salud',),
    'belleza'                   :   ('joyeria', 'moda'),
    'construccion'              :   ('servicios', 'automotriz'),
    'tecnologia'                :   ('tecnologia',),
    'educacion'                 :   ('general', 'infantil'),
    'turismo'                   :   ('turismo',),
    'mascotas'                  :   ('infantil', 'general'),
    'arte'                      :   ('arte', 'fotografia'),
    'seguridad'                 :   ('tecnologia', 'general'),
    'otro'                      :   ('general',),
}

#Tono del motor -> palabras que empujan el ranking de estilos del MCP.
_TONE_HINTS     =   {
    'calido'    :   ('calido', 'artesanal', 'acogedor', 'suave', 'natural'),
    'serio'     :   ('elegante', 'clasico', 'confianza', 'premium', 'limpio'),
    'moderno'   :   ('moderno', 'limpio', 'minimal', 'producto', 'claro'),
    'audaz'     :   ('bold', 'contraste', 'energia', 'urbano', 'colorido'),
}

_LINE           =   re.compile(r'^\s*([^:]{3,32}?)\s*:\s*(.+?)\s*$')
_SLUG_RE        =   re.compile(r'[^a-z0-9]+')

#Radio del token (px) -> enum cerrado de `containers.radius`.
_RADIUS_STEPS   =   ((0, 'none'), (6, 'sm'), (12, 'md'), (18, 'lg'), (999, 'xl'))
#Nombres de fuente que NO están en el catálogo: se elige una del mismo aire.
_SERIF_HINTS    =   ('serif', 'garamond', 'playfair', 'lora', 'fraunces', 'baskerville', 'cinzel', 'georgia', 'times')
_DISPLAY_HINTS  =   ('black', 'anton', 'bebas', 'oswald', 'impact', 'archivo', 'barlow condensed', 'orbitron')
_MONO_HINTS     =   ('mono', 'courier', 'vt323', 'press start')
_SANS_HINTS     =   ('inter', 'manrope', 'figtree', 'jakarta', 'sora', 'work sans', 'outfit', 'nunito', 'raleway', 'poppins', 'karla', 'lato', 'roboto', 'barlow', 'archivo', 'quicksand', 'baloo', 'fredoka', 'space grotesk')


def _fold(value):
    raw =   unicodedata.normalize('NFD', str(value or ''))
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').lower().strip()


def _slugify(value):
    return _SLUG_RE.sub('-', _fold(value)).strip('-')


def _match(text, table):
    low =   _fold(text)
    for item_id, words in table:
        if any(word in low for word in words):
            return item_id
    return ''


def _matches(text, table):
    low     =   _fold(text)
    found   =   []
    for item_id, words in table:
        if any(word in low for word in words) and item_id not in found:
            found.append(item_id)
    return found


def normalize_history(raw):
    rows    =   []
    for item in (raw if isinstance(raw, list) else []):
        if not isinstance(item, dict):
            continue
        role    =   str(item.get('role') or '').strip()
        content = str(item.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            rows.append({'role': role, 'content': content[:MAX_MESSAGE]})
    return rows[-MAX_TURNS:]


#=========================================
# PROMPT -> RESPUESTAS DEL MOTOR
#=========================================
def parse_message(message):
    """
    Compatibilidad: traduce un mensaje de texto ("Rubro: … / Tono: …") a la
    estructura del pedido. Tolerante a propósito: una coma de más nunca es
    400.
    """
    prompt  =   {}
    notes   =   []
    for line in str(message or '').splitlines():
        match   =   _LINE.match(line)
        if not match:
            if line.strip():
                notes.append(line.strip())
            continue
        key     =   _BLOCK_KEYS.get(_fold(match.group(1)))
        value   =   match.group(2).strip()
        if not key:
            notes.append(f'{match.group(1).strip()}: {value}')
            continue
        if key == 'rubro':
            prompt['rubro'] = _match(value, _RUBRO_WORDS) or prompt.get('rubro', '')
        elif key == 'tone':
            prompt['tone'] = _match(value, _TONE_WORDS) or prompt.get('tone', '')
        elif key == 'goals':
            goals = [goal for goal in _matches(value, _GOAL_WORDS) if goal in R.GOALS]
            prompt['goals'] = (goals or prompt.get('goals') or [])[:2]
        elif key == 'must_have':
            must = [item for item in _matches(value, _MUST_WORDS) if item in R.MUST_HAVE_BLOCKS]
            prompt['must_have'] = (must or prompt.get('must_have') or [])
        elif key == 'audience':
            prompt['audience'] = value[:120]
        elif key == 'content_hint':
            prompt['notes'] = value[:160]
    if notes and 'notes' not in prompt:
        prompt['notes'] = ' '.join(notes)[:160]
    return prompt


def normalize_prompt(prompt, fallback = None):
    """
    Sanea la estructura del pedido: ids canónicos del motor, textos cortos y
    sin claves de más. Es la fuente única de verdad del wizard.
    """
    data    =   prompt if isinstance(prompt, dict) else {}
    if not data and isinstance(fallback, dict):
        data    =   fallback
    rubro       =   str(data.get('rubro') or '').strip()
    if rubro not in R.RUBROS:
        rubro   =   _match(rubro, _RUBRO_WORDS) if rubro else ''
    tone        =   str(data.get('tone') or '').strip()
    if tone not in R.TONES:
        tone    =   _match(tone, _TONE_WORDS) if tone else ''
    goals       =   []
    for goal in (data.get('goals') or []):
        goal    =   str(goal or '').strip()
        if goal not in R.GOALS:
            goal    =   _match(goal, _GOAL_WORDS)
        if goal and goal in R.GOALS and goal not in goals:
            goals.append(goal)
    must        =   []
    for item in (data.get('must_have') or []):
        item    =   str(item or '').strip()
        if item not in R.MUST_HAVE_BLOCKS:
            item    =   _match(item, _MUST_WORDS)
        if item and item in R.MUST_HAVE_BLOCKS and item not in must:
            must.append(item)
    audience    =   str(data.get('audience') or '').strip()[:120]
    notes       =   str(data.get('notes') or data.get('content_hint') or '').strip()[:160]
    return {
        'rubro'     :   rubro,
        'goals'     :   goals[:2],
        'tone'      :   tone,
        'audience'  :   audience,
        'must_have' :   must,
        'notes'     :   notes,
    }


def _engine_payload(prompt):
    #El motor ignora las claves vacías: cada respuesta que falta se deduce
    #de los datos reales de la tienda.
    payload =   {}
    if prompt.get('rubro'):
        payload['rubro']    =   prompt['rubro']
    if prompt.get('goals'):
        payload['goals']    =   list(prompt['goals'])
    if prompt.get('tone'):
        payload['tone']     =   prompt['tone']
    if prompt.get('audience'):
        payload['audience'] =   prompt['audience']
    if prompt.get('must_have'):
        payload['must_have'] =  list(prompt['must_have'])
    if prompt.get('notes'):
        payload['content_hint'] =   prompt['notes']
    return payload


#=========================================
# ELECCIÓN DEL SKILL (MCP)
#=========================================
def _style_query(prompt):
    """Query para el MCP: rubro + tono + objetivos + imprescindibles."""
    words   =   []
    rubro   =   R.RUBROS.get(prompt.get('rubro') or '') or {}
    if rubro.get('label'):
        words.append(rubro['label'])
    if prompt.get('tone'):
        words.append(prompt['tone'])
        words.extend(_TONE_HINTS.get(prompt['tone'], ()))
    for goal in prompt.get('goals') or []:
        label =   (R.GOAL_RECIPES.get(goal) or {}).get('label')
        if label:
            words.append(label)
    words.extend(R.MUST_HAVE_LABELS.get(item, '') for item in prompt.get('must_have') or [])
    if prompt.get('notes'):
        words.append(prompt['notes'][:60])
    return ' '.join(word for word in words if word).strip()


def _score(style, terms):
    haystack    =   ' '.join([style.slug, style.nombre, style.categoria, ' '.join(style.tags or [])]).lower()
    strong      =   (style.slug + ' ' + style.nombre).lower()
    return sum((3 if term in strong else 1) for term in terms if term and term in haystack)


def select_styles(prompt, limit = MAX_STYLES):
    """
    Skills del MCP para este pedido. Cadena de respaldo: búsqueda por
    categoría del rubro -> búsqueda libre -> catálogo por categoría ->
    catálogo completo. Sin catálogo cargado devuelve [] y el wizard sigue
    con el diseño del motor (nunca rompe por un catálogo vacío).
    """
    from McpApp.domains.skills.services.services import (
        design_payload,
        list_design_styles,
        search_design_styles,
    )

    query   =   _style_query(prompt)
    terms   =   [term for term in _fold(query).replace(',', ' ').split() if len(term) > 2]
    rows    =   []
    for categoria in (_RUBRO_CATEGORIES.get(prompt.get('rubro') or '', ()) or ('',)):
        if categoria:
            rows = search_design_styles(query = query, categoria = categoria, limit = limit * 3)
            if rows:
                break
    if not rows and query:
        rows    =   search_design_styles(query = query, limit = limit * 3)
    if not rows:
        for categoria in (_RUBRO_CATEGORIES.get(prompt.get('rubro') or '', ()) or ('',)):
            if categoria:
                rows = list_design_styles(categoria = categoria, limit = limit * 3)
                if rows:
                    break
    if not rows:
        rows    =   list_design_styles(limit = limit * 3)
    #Solo fuentes de repo: el patrón de diseño sale de `html_componentes`
    #real, no de los presets curados del sistema.
    repo_rows   =   [style for style in rows if _is_repo_style(style)]
    if repo_rows:
        rows    =   repo_rows
    else:
        #Catálogo sin fuentes de repo cargadas: el wizard sigue con el motor.
        rows    =   []
    #Ranking estable: afinidad de tags y, a igualdad, id (determinista).
    rows.sort(key = lambda style: (-_score(style, terms), style.id))
    return [design_payload(style, full = True) for style in rows[:limit]]


def _is_repo_style(style):
    """Una fuente de repo: tokens con `source_repo` y bloques HTML."""
    tokens      =   getattr(style, 'tokens_diseno', None) or {}
    components  =   getattr(style, 'html_componentes', None) or {}
    if not isinstance(tokens, dict) or not isinstance(components, dict):
        return False
    return bool(tokens.get('source_repo')) and bool(components)


#=========================================
# PATRÓN DE DISEÑO DESDE LOS COMPONENTES DEL REPO
#=========================================
#Componente del repo -> bloque de la landing del Studio. Los que no son de
#landing (header/footer, checkout, cuenta) quedan afuera del patrón.
_COMPONENT_BLOCKS   =   {
    'hero'          :   'hero',
    'features'      :   'benefits',
    'benefits'      :   'benefits',
    'products'      :   'featured',
    'featured'      :   'featured',
    'grid'          :   'featured',
    'related'       :   'featured',
    'categories'    :   'categories',
    'testimonials'  :   'testimonials',
    'about'         :   'about',
    'gallery'       :   'gallery',
    'metrics'       :   'stats',
    'contact'       :   'contact',
}


def pattern_from_components(components):
    """
    Deriva el patrón de diseño de los bloques HTML del repo: qué secciones
    usa, en qué orden, y la variante de portada/vitrina que sugiere el
    markup (grillas de 2/3/4 columnas, hero partido, centrado, etc.).
    """
    components  =   components if isinstance(components, dict) else {}
    order       =   []
    variants    =   {}
    for name, html in components.items():
        block   =   _COMPONENT_BLOCKS.get(str(name))
        if not block or block in order:
            continue
        order.append(block)
        markup  =   str(html or '')
        if block == 'hero':
            if 'md:grid-cols-2' in markup or 'lg:grid-cols-2' in markup:
                variants['hero']    =   'split'
            elif 'text-center' in markup or 'items-center text-center' in markup:
                variants['hero']    =   'centered'
            else:
                variants['hero']    =   'full'
        elif block == 'featured':
            if 'lg:grid-cols-4' in markup or 'xl:grid-cols-4' in markup:
                variants['featured']    =   'cols4'
            elif 'lg:grid-cols-3' in markup or 'md:grid-cols-3' in markup:
                variants['featured']    =   'cols3'
            elif 'lg:grid-cols-2' in markup or 'md:grid-cols-2' in markup:
                variants['featured']    =   'cols2'
            else:
                variants['featured']    =   'grid'
        elif block == 'benefits' and 'md:grid-cols-3' in markup:
            variants['benefits']    =   'cards'
    return {'order': order, 'variants': variants}


def apply_pattern(layout, pattern):
    """
    Aplica el patrón del repo sobre el `layout_config` del motor: ordena los
    bloques activos como en el repo y fija las variantes derivadas. Los
    bloques que el motor armó y el repo no trae se conservan al final (nunca
    se pierde contenido), y los desactivados no se tocan.
    """
    pattern =   pattern if isinstance(pattern, dict) else {}
    order   =   pattern.get('order') or []
    if not order or not isinstance(layout, dict):
        return layout
    surface =   layout.get('landing')
    if not isinstance(surface, dict):
        return layout
    blocks  =   surface.get('blocks')
    if not isinstance(blocks, list) or not blocks:
        return layout
    index   =   {block_id: position for position, block_id in enumerate(order)}
    variants =  pattern.get('variants') or {}
    enabled =   []
    disabled =  []
    for position, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        block.setdefault('order', position)
        if block.get('enabled') is False:
            disabled.append(block)
            continue
        enabled.append((position, block))
    enabled.sort(key = lambda pair: (index.get(pair[1].get('id'), len(index)), pair[0]))
    ordered =   []
    for position, block in enumerate(block for _, block in enabled):
        variant =   variants.get(block.get('id'))
        if variant:
            block['variant']    =   variant
        block['order']          =   position
        ordered.append(block)
    surface['blocks']   =   ordered + disabled
    layout['landing']   =   surface
    return layout


#=========================================
# TOKENS DEL SKILL -> site_theme
#=========================================
def _radius_bucket(raw):
    try:
        px  =   int(re.sub(r'[^0-9]', '', str(raw or '')) or 0)
    except ValueError:
        px  =   0
    for limit, value in _RADIUS_STEPS:
        if px <= limit:
            return value
    return 'xl'


def _shadow_bucket(raw):
    value   =   str(raw or '').strip().lower()
    if not value or value == 'none':
        return 'none'
    #Sombra dura (offset sin desenfoque) = medium; el resto, soft.
    if 'rgba' not in value and 'rgb(' not in value:
        return 'medium'
    return 'soft'


def _font_slug(name, fallback):
    from .ai_design_typography import FONT_SLUGS

    slug    =   _slugify(name)
    if slug in FONT_SLUGS:
        return slug
    low =   _fold(name)
    if any(hint in low for hint in _MONO_HINTS):
        return 'space-mono'
    if any(hint in low for hint in _SERIF_HINTS):
        return 'playfair-display'
    if any(hint in low for hint in _DISPLAY_HINTS):
        return 'archivo-black'
    if any(hint in low for hint in _SANS_HINTS):
        return fallback
    return fallback


def theme_from_tokens(tokens, base_theme):
    """
    Traduce `tokens_diseno` del MCP a las secciones cerradas de `site_theme`.
    Lo que el catálogo no puede expresar (sombras con blur, fuentes que no
    están en el catálogo) se resuelve al escalón más cercano.
    """
    tokens  =   tokens if isinstance(tokens, dict) else {}
    theme   =   copy.deepcopy(base_theme or {})

    palette =   dict(theme.get('palette') or {})
    bg      =   _norm_hex(tokens.get('background')) or palette.get('bg') or '#ffffff'
    text    =   _norm_hex(tokens.get('text'))
    surface =   _norm_hex(tokens.get('surface'))
    muted   =   _norm_hex(tokens.get('muted'))
    border  =   _norm_hex(tokens.get('border'))
    primary =   _norm_hex(tokens.get('primary'))
    second  =   _norm_hex(tokens.get('secondary'))
    palette['bg'] =   bg
    if surface:
        palette['surface'] = surface
    if primary:
        #El acento tiene que leerse sobre el fondo: el motor ya resuelve el
        #contraste de la misma forma que sus propias paletas.
        palette['accent']   =   _ensure_contrast(primary, bg, 3.0)
        palette['primary']  =   palette['accent']
    if second:
        palette['secondary'] = _ensure_contrast(second, bg, 3.0)
    if text:
        palette['text'] =   _ensure_contrast(text, bg)
    if muted:
        palette['muted'] =  _ensure_contrast(muted, bg, 3.0)
    if border:
        palette['border'] = border
    theme['palette'] =  palette

    containers  =   dict(theme.get('containers') or {})
    containers['radius']    =   _radius_bucket(tokens.get('radius'))
    containers['shadow']    =   _shadow_bucket(tokens.get('shadow'))
    theme['containers'] =   containers

    typography  =   dict(theme.get('typography') or {})
    typography['heading']   =   _font_slug(tokens.get('heading_font'), typography.get('heading') or 'space-grotesk')
    typography['body']      =   _font_slug(tokens.get('font'), typography.get('body') or 'inter')
    theme['typography'] =   typography
    return theme


def _theme_mode(theme):
    bg  =   ((theme or {}).get('palette') or {}).get('bg') or '#ffffff'
    return 'dark' if _luminance(bg) < 0.35 else 'light'


def apply_overlay(proposal, overlay):
    """Alias del overlay del motor (`apply_design_overlay`)."""
    return apply_design_overlay(proposal, overlay)


#=========================================
# OVERLAY EN CACHÉ (lo reusan apply y refine)
#=========================================
def _overlay_key(store, seed):
    return f'ai_design_mcp:{store.pk}:{int(seed)}'


def save_overlays(store, seed, overlays):
    cache.set(_overlay_key(store, seed), overlays, CACHE_TTL)


def overlay_of(store, seed, proposal_id = None):
    try:
        seed    =   int(seed)
    except (TypeError, ValueError):
        return None
    overlays    =   cache.get(_overlay_key(store, seed))
    if not isinstance(overlays, dict):
        return None
    if proposal_id is None:
        return overlays
    return overlays.get(str(proposal_id))


#=========================================
# FLUJO
#=========================================
def _decorate(store, seed, result, styles, prompt):
    """Aplica a cada propuesta un patrón de diseño distinto del MCP."""
    proposals   =   result.get('proposals') or []
    overlays    =   {}
    chosen      =   []
    has_plus    =   _benefit(store, 'has_design_plus')
    has_advanced =  _benefit(store, 'has_design_advanced')
    has_style   =   _benefit(store, 'has_customization')
    has_ai      =   _benefit(store, 'has_ai_design')
    for index, proposal in enumerate(proposals):
        if not styles:
            break
        style   =   styles[index % len(styles)]
        tokens  =   style.get('tokens_diseno') or {}
        if not tokens:
            continue
        pattern =   pattern_from_components(style.get('html_componentes') or {})
        layout  =   apply_pattern(copy.deepcopy(proposal.get('layout_config') or {}), pattern)
        try:
            from StoreApp.domains.stores.layout_blocks import clean_layout_config
            from StoreApp.domains.stores.site_theme import clean_site_theme

            theme   =   clean_site_theme(
                theme_from_tokens(tokens, proposal.get('site_theme') or {}),
                has_plus        =   has_plus,
                has_advanced    =   has_advanced,
                has_style       =   has_style,
                store           =   store,
            )
            if pattern.get('order'):
                layout  =   clean_layout_config(layout, has_advanced, has_ai)
        except serializers.ValidationError:
            #Un token fuera de contrato nunca tumba la propuesta: se queda
            #el patrón del motor.
            continue
        mcp_style   =   {
            'slug'          :   style.get('slug'),
            'nombre'        :   style.get('nombre'),
            'categoria'     :   style.get('categoria'),
            'tags'          :   list(style.get('tags') or [])[:6],
            #Trazabilidad del patrón aplicado: de qué repo sale y qué
            #secciones ordenó.
            'source_repo'   :   tokens.get('source_repo') or '',
            'pattern'       :   list(pattern.get('order') or []),
        }
        overlay =   {
            'site_theme'    :   theme,
            'layout_config' :   layout if pattern.get('order') else None,
            'theme'         :   _theme_mode(theme),
            'theme_toggle'  :   True,
            'accent'        :   (theme.get('palette') or {}).get('accent') or '',
            'mcp_style'     :   mcp_style,
        }
        apply_design_overlay(proposal, overlay)
        overlays[str(proposal.get('id'))]    =   overlay
        chosen.append(mcp_style)
    if overlays:
        save_overlays(store, seed, overlays)
    return {
        'query'     :   _style_query(prompt),
        'styles'    :   chosen,
        'available' :   len(styles),
    }


def _benefit(store, code):
    from .services import profile_has_benefit

    return profile_has_benefit(store.user, code)


def generate_from_prompt(store, prompt = None, history = None, seed = None, message = ''):
    """Pedido estructurado (o texto) -> propuestas con el skill que elige el MCP."""
    data    =   prompt if isinstance(prompt, dict) else {}
    if not data and message:
        data    =   parse_message(message)
    if not data:
        raise AiDesignError('Contanos lo mínimo de tu negocio para armar la propuesta.')
    if message and len(str(message)) > MAX_MESSAGE:
        raise AiDesignError(f'El pedido admite hasta {MAX_MESSAGE} caracteres.')
    turns   =   normalize_history(history)
    #El historial solo aporta notas de contexto: la estructura del turno
    #actual manda sobre cualquier respuesta vieja.
    if turns and not data.get('notes'):
        data    =   {**data, 'notes': ' '.join(row['content'] for row in turns if row['role'] == 'user')[-160:]}
    clean_prompt =  normalize_prompt(data)
    payload      =  _engine_payload(clean_prompt)
    if seed:
        try:
            payload['seed'] = max(0, int(seed))
        except (TypeError, ValueError):
            pass
    result  =   generate(store, payload)
    styles  =   select_styles(clean_prompt)
    mcp     =   _decorate(store, result.get('seed'), result, styles, clean_prompt)
    return {
        'proposals' :   result.get('proposals') or [],
        'seed'      :   result.get('seed'),
        'missing'   :   result.get('missing') or [],
        'checks'    :   result.get('checks') or [],
        'prompt'    :   clean_prompt,
        'mcp'       :   mcp,
    }


def generate_from_message(store, message, history = None, seed = None):
    """Compatibilidad con el contrato de texto anterior."""
    return generate_from_prompt(store, parse_message(message), history, seed, message = str(message or ''))
