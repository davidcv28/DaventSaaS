import re
import unicodedata

from . import ai_design_recipes as R
from .ai_design import AiDesignError, generate

"""
Proxy del wizard "Diseño asistido" hacia el MCP de estilos.

El frontend acumula las respuestas del wizard en UN mensaje legible
("Rubro: … / Objetivo: … / Tono: …") y lo manda acá. El service traduce ese
texto a las respuestas que entiende el motor de diseño existente y devuelve
las propuestas con el mismo contrato que `ai-design/` (proposals + seed +
missing), así el wizard, el ajuste fino y la publicación siguen usando el
mismo motor y la misma caché de tanda.

El token del MCP y cualquier credencial quedan del lado del servidor: el
navegador nunca ve nada más que este endpoint.
"""

MAX_MESSAGE     =   4000
MAX_TURNS       =   20

#Claves del mensaje -> campo del motor. Se comparan normalizadas (sin
#acentos ni mayúsculas) y por prefijo, así "Objetivo:" y "Objetivos:" caen
#en el mismo lado.
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
    ('testimonials', ('opinion', 'testimonio', 'reseña', 'resena', 'clientes dicen')),
    ('faqs', ('pregunta', 'faq', 'duda')),
)

_LINE           =   re.compile(r'^\s*([^:]{3,32}?)\s*:\s*(.+?)\s*$')
_SPLIT          =   re.compile(r'\s*(?:,|;|/|\+|\by\b|\+)\s*', re.IGNORECASE)


def _fold(value):
    raw =   unicodedata.normalize('NFD', str(value or ''))
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').lower().strip()


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


def parse_message(message):
    """
    Traduce el mensaje acumulado del wizard a las respuestas del motor.
    Tolerante a propósito: el dueño puede editar los bloques a mano y el
    mensaje sigue entrando (nunca 400 por una coma).
    """
    payload =   {}
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
            payload['rubro'] = _match(value, _RUBRO_WORDS) or payload.get('rubro', '')
        elif key == 'tone':
            payload['tone'] = _match(value, _TONE_WORDS) or payload.get('tone', '')
        elif key == 'goals':
            goals = [goal for goal in _matches(value, _GOAL_WORDS) if goal in R.GOALS]
            payload['goals'] = (goals or payload.get('goals') or [])[:2]
        elif key == 'must_have':
            must = [item for item in _matches(value, _MUST_WORDS) if item in R.MUST_HAVE_BLOCKS]
            payload['must_have'] = (must or payload.get('must_have') or [])
        elif key == 'audience':
            payload['audience'] = value[:120]
        elif key == 'content_hint':
            payload['content_hint'] = value[:160]
    if notes and 'content_hint' not in payload:
        payload['content_hint'] = ' '.join(notes)[:160]
    return payload


def generate_from_message(store, message, history = None, seed = None):
    """Mensaje acumulado -> propuestas del motor (mismo contrato que `ai-design/`)."""
    text    =   str(message or '').strip()
    if not text:
        raise AiDesignError('Contanos lo mínimo de tu negocio para armar la propuesta.')
    if len(text) > MAX_MESSAGE:
        raise AiDesignError(f'El pedido admite hasta {MAX_MESSAGE} caracteres.')
    #El historial aporta contexto de turnos anteriores sin pisar el mensaje
    #actual: el pedido del último turno manda.
    turns   =   normalize_history(history)
    context =   ' '.join([row['content'] for row in turns if row['role'] == 'user'][-6:] + [text])
    payload =   parse_message(text)
    if not payload:
        #Sin bloques reconocibles el motor deduce todo de la tienda: no es
        #un error, es "prefiero que decidas vos".
        payload =   parse_message(context)
    #`seed` extra pide "otra tanda" con las MISMAS respuestas (el motor
    #suma la semilla del pedido a la derivada de la tienda).
    if seed:
        try:
            payload['seed'] = max(0, int(seed))
        except (TypeError, ValueError):
            pass
    result  =   generate(store, payload)
    return {
        'proposals' :   result.get('proposals') or [],
        'seed'      :   result.get('seed'),
        'missing'   :   result.get('missing') or [],
        'checks'    :   result.get('checks') or [],
        'echo'      :   text,
        'parsed'    :   {
            'rubro'         :   payload.get('rubro') or '',
            'goals'         :   payload.get('goals') or [],
            'tone'          :   payload.get('tone') or '',
            'audience'      :   payload.get('audience') or '',
            'must_have'     :   payload.get('must_have') or [],
            'content_hint'  :   payload.get('content_hint') or '',
        },
    }
