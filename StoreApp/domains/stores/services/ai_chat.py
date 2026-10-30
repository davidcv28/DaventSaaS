import re
import unicodedata

from StoreApp.domains.stores.layout_blocks import clean_layout_config
from StoreApp.domains.stores.site_theme import clean_site_theme

from .ai_design import AiDesignError, generate
from .services import profile_has_benefit

"""
Chat de diseño ("Diseñar con IA", beneficio has_ai_chat).

El usuario describe en lenguaje natural qué quiere y el service interpreta
la intención, la traduce a las respuestas que entiende el motor de diseño
existente (`ai_design.generate`) y devuelve un PATCH ya saneado sobre
site_theme / layout_config / template.

El patch NUNCA se aplica acá: el frontend lo confirma y lo manda al PATCH
/api/stores/customization/ (borrador). El motor es el mismo de siempre y
todo lo que sale pasa otra vez por clean_site_theme/clean_layout_config,
así que no hay HTML/CSS libre ni ids fuera de catálogo.
"""

MAX_MESSAGE     =   1000
MAX_TURNS       =   20
HISTORY_USER    =   6

#Colores nombrados (es-AR) -> hex de marca. Se acepta también #RRGGBB.
_COLORS =   {
    'rojo'      :   '#dc2626',
    'bordo'     :   '#7f1d1d',
    'naranja'   :   '#ea580c',
    'amarillo'  :   '#eab308',
    'verde'     :   '#16a34a',
    'oliva'     :   '#4d7c0f',
    'turquesa'  :   '#0d9488',
    'celeste'   :   '#0ea5e9',
    'azul'      :   '#2563eb',
    'marino'    :   '#1e3a8a',
    'violeta'   :   '#7c3aed',
    'lila'      :   '#a855f7',
    'rosa'      :   '#db2777',
    'fucsia'    :   '#c026d3',
    'dorado'    :   '#b45309',
    'marron'    :   '#78350f',
    'beige'     :   '#d6c7a1',
    'negro'     :   '#111827',
    'gris'      :   '#4b5563',
    'blanco'    :   '#f8fafc',
}

#Palabras -> estilo del motor (STYLE_FAMILIES).
_STYLE_WORDS =   (
    ('minimal',     'minimal'),
    ('limpio',      'minimal'),
    ('simple',      'minimal'),
    ('revista',     'editorial'),
    ('editorial',   'editorial'),
    ('elegante',    'luxury'),
    ('lujo',        'luxury'),
    ('premium',     'luxury'),
    ('atrevid',     'bold'),
    ('audaz',       'bold'),
    ('moderno',     'tech'),
    ('tecnologic',  'tech'),
    ('futurist',    'tech'),
    ('artesanal',   'craft'),
    ('calido',      'craft'),
    ('retro',       'retro'),
    ('vintage',     'retro'),
    ('catalogo',    'catalog'),
    ('vidriera',    'catalog'),
)

#Palabras -> tono del motor (R.TONES).
_TONE_WORDS =   (
    ('calid',       'calido'),
    ('cercan',      'calido'),
    ('serio',       'serio'),
    ('sobrio',      'serio'),
    ('confiable',   'serio'),
    ('modern',      'moderno'),
    ('simple',      'moderno'),
    ('audaz',       'audaz'),
    ('atrevid',     'audaz'),
    ('energi',      'audaz'),
)

#Palabras -> par tipográfico (TYPE_PAIRS).
_PAIR_WORDS =   (
    ('serif',       'serif-editorial'),
    ('revista',     'serif-editorial'),
    ('clasic',      'serif-classic'),
    ('elegante',    'serif-classic'),
    ('geometric',   'geometric'),
    ('modern',      'geometric'),
    ('impacto',     'display-heavy'),
    ('grande',      'display-heavy'),
    ('calid',       'warm-serif'),
)

_HEX =   re.compile(r'#([0-9a-f]{6})\b', re.IGNORECASE)


def _fold(value):
    raw =   unicodedata.normalize('NFD', str(value or ''))
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').lower()


def normalize_history(raw):
    rows    =   []
    for item in (raw if isinstance(raw, list) else []):
        if not isinstance(item, dict):
            continue
        role    =   str(item.get('role') or '').strip()
        content =   str(item.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            rows.append({'role': role, 'content': content[:MAX_MESSAGE]})
    return rows[-MAX_TURNS:]


def _intent(text):
    low     =   _fold(text)
    payload =   {}
    hexes   =   _HEX.findall(text)
    if hexes:
        payload['brand_color'] = f'#{hexes[-1].lower()}'
    else:
        for word, color in _COLORS.items():
            if re.search(rf'\b{re.escape(word)}\b', low):
                payload['brand_color'] = color
                break
    for word, style in _STYLE_WORDS:
        if word in low:
            payload['styles'] = [style]
            break
    for word, tone in _TONE_WORDS:
        if word in low:
            payload['tone'] = tone
            break
    for word, pair in _PAIR_WORDS:
        if word in low:
            payload['pair_override'] = pair
            break
    if 'mas aire' in low or 'espaciad' in low or 'amplio' in low:
        payload['density_override'] = 'spacious'
    elif 'compact' in low or 'apretad' in low or 'denso' in low:
        payload['density_override'] = 'compact'
    if 'modo oscuro' in low or 'noche' in low or 'oscur' in low:
        payload['night_mode'] = {'enabled': True, 'default': 'dark'}
    elif 'modo claro' in low or 'claro' in low:
        payload['night_mode'] = {'enabled': True, 'default': 'light'}
    return payload


def _reply_text(proposal, payload):
    look    =   proposal.get('look') or {}
    name    =   look.get('skin_label') or look.get('style_label') or ''
    parts   =   ['Listo: armé una versión de tu web']
    if name:
        parts.append(f'con el estilo {name}')
    if payload.get('brand_color'):
        parts.append('y el color que pediste')
    text    =   ' '.join(parts) + '.'
    if payload.get('density_override') == 'spacious':
        text += ' Le di más aire entre secciones.'
    elif payload.get('density_override') == 'compact':
        text += ' La compacté para que entre más contenido.'
    if payload.get('night_mode', {}).get('default') == 'dark':
        text += ' Queda con modo oscuro por defecto.'
    return text + ' Revisá la vista previa y aplicá el cambio si te gusta.'


def chat(store, message, history = None):
    """Interpreta el mensaje y devuelve {reply, patch, proposal_id, seed, needs}."""
    text    =   str(message or '').strip()
    if not text:
        raise AiDesignError('Escribí qué querés cambiar de tu web.')
    if len(text) > MAX_MESSAGE:
        raise AiDesignError(f'El mensaje admite hasta {MAX_MESSAGE} caracteres.')
    turns   =   normalize_history(history)
    context =   ' '.join([row['content'] for row in turns if row['role'] == 'user'][-HISTORY_USER:] + [text])
    payload =   _intent(context)
    result  =   generate(store, payload)
    proposals = result.get('proposals') or []
    if not proposals:
        raise AiDesignError('No pude armar una propuesta con eso: probá con otro estilo o color.')
    proposal    =   proposals[0]
    profile     =   store.user
    advanced    =   profile_has_benefit(profile, 'has_design_advanced')
    plus        =   advanced or profile_has_benefit(profile, 'has_design_plus')
    style       =   plus or profile_has_benefit(profile, 'has_customization')
    has_ai      =   profile_has_benefit(profile, 'has_ai_design')
    theme       =   clean_site_theme(
        proposal.get('site_theme') or {},
        has_plus = plus, has_advanced = advanced, has_style = style, store = store,
    )
    layout      =   clean_layout_config(proposal.get('layout_config') or {}, advanced, has_ai)
    return {
        'reply'         :   _reply_text(proposal, payload),
        'patch'         :   {
            'template'      :   proposal.get('template'),
            'site_theme'    :   theme,
            'layout_config' :   layout,
        },
        'proposal_id'   :   proposal.get('id'),
        'seed'          :   result.get('seed'),
        'needs'         :   [item.get('label') for item in (result.get('missing') or [])][:3],
    }
