import logging

from django.conf import settings
from django.contrib.auth.models import User

from AdminApp.domains.chat.models import ChatMessage, ChatThread
from McpApp.domains.skills.services import (
    anthropic_enabled,
    ask_claude,
    catalog_summary,
    search_design_styles,
)

"""
Asistente de diseño del chat.

Reemplaza al soporte genérico: es un entrevistador que le hace preguntas
al cliente sobre su web (rubro, objetivo, público, estilo, colores,
secciones, fotos, contacto) y, con las respuestas, recomienda uno de los
estilos del catálogo MCP.

Motor:
  1. Anthropic (API key gratuita en ANTHROPIC_API_KEY) con el catálogo
     de estilos inyectado en el system prompt.
  2. Fallback determinista por preguntas si no hay key o la API falla:
     el bot nunca deja de responder.
"""

logger          =   logging.getLogger(__name__)
BOT_USERNAME    =   getattr(settings, 'DESIGN_BOT_USERNAME', 'davent_design_bot')
HISTORY_LIMIT   =   16

#Preguntas de la entrevista (orden fijo; el fallback avanza una por turno).
QUESTIONS   =   [
    ('rubro',       '¡Hola! Soy el asistente de diseño de DAVENT. Te voy a hacer unas preguntas para armar la web de tu negocio. Para empezar, ¿qué vendés o qué servicio ofrecés?'),
    ('objetivo',    '¿Cuál es el objetivo principal de tu web: vender online, mostrar el catálogo, que te contacten o reservar turnos?'),
    ('publico',     '¿A quién le hablás? Contame el perfil de tu cliente ideal (edad, zona, estilo de vida).'),
    ('estilo',      '¿Qué sensación querés transmitir: premium y elegante, moderno y tecnológico, cálido y artesanal, o divertido y colorido?'),
    ('colores',     '¿Tenés colores de marca o preferencias? Si no, te propongo una paleta a partir de tu rubro.'),
    ('secciones',   '¿Qué secciones necesitás? Por ejemplo: inicio, productos, servicios, sobre nosotros, testimonios, preguntas frecuentes y contacto.'),
    ('fotos',       '¿Tenés fotos del local, los productos o el equipo? Con 3 o 4 imágenes alcanza para que la web se vea real.'),
    ('contacto',    '¿Cómo querés que te contacten: WhatsApp, formulario, email, Instagram o turnos online?'),
    ('dominio',     'Por último, ¿ya tenés un nombre de dominio pensado o usamos el nombre de tu negocio?'),
]

STYLE_HINTS =   {
    'premium':      ['luxury-gold', 'monochrome-editorial', 'jewelry-rose'],
    'elegante':     ['luxury-gold', 'monochrome-editorial', 'jewelry-rose'],
    'tecnologico':  ['tech-saas-clean', 'cyberpunk-dark', 'glass-frost'],
    'moderno':      ['tech-saas-clean', 'minimal-nordic', 'glass-frost'],
    'calido':       ['coffee-warm', 'organic-terracotta', 'barber-vintage'],
    'artesanal':    ['organic-terracotta', 'coffee-warm', 'green-eco'],
    'divertido':    ['kids-playful', 'tropical-vibrant', 'pastel-bakery'],
    'colorido':     ['tropical-vibrant', 'kids-playful', 'retro-arcade'],
    'oscuro':       ['cyberpunk-dark', 'gym-power', 'automotive-steel'],
    'minimal':      ['minimal-nordic', 'tech-saas-clean', 'monochrome-editorial'],
}


#=========================================
# BOT USER
#=========================================
def get_bot_user() -> User:
    user, _ =   User.objects.get_or_create(
        username    =   BOT_USERNAME,
        defaults    =   {
            'email'         :   'diseno@davent.local',
            'first_name'    :   'Asistente',
            'last_name'     :   'de diseño',
            'is_active'     :   True,
            #No es staff: no aparece en el roster del equipo ni recibe hilos.
            'is_staff'      :   False,
        },
    )
    if user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields = ['password'])
    return user


def send_bot_message(thread, body : str) -> ChatMessage:
    #from_staff=True lo fija el service (nunca el request): el cliente lo ve
    #como respuesta del asistente y no como mensaje propio.
    message =   ChatMessage.objects.create(
        thread      =   thread,
        sender      =   get_bot_user(),
        from_staff  =   True,
        body        =   (body or '').strip()[:2000],
    )
    ChatThread.objects.filter(pk = thread.pk).update(updated_at = message.created_at)
    return message


#=========================================
# CONTEXTO
#=========================================
def _system_prompt() -> str:
    catalog =   catalog_summary(limit = 50)
    lines   =   '\n'.join(f"- {s['slug']} · {s['nombre']} · {s['categoria']} · {', '.join(s['tags'])}" for s in catalog)
    return (
        'Sos el asistente de diseño de DAVENT. Entrevistás al dueño de un negocio '
        'para armar la web de su tienda, en español rioplatense, cercano y breve.\n'
        'Reglas:\n'
        '- Hacé UNA sola pregunta por mensaje.\n'
        '- Cubrí en orden: rubro, objetivo, público, estilo, colores, secciones, fotos, contacto y dominio.\n'
        '- Cuando tengas rubro + objetivo + estilo, recomendá UN estilo del catálogo por su slug y explicá en una frase por qué.\n'
        '- Respondé en 2 o 3 frases máximo. No uses markdown ni listas largas.\n'
        f'- Catálogo de estilos disponibles:\n{lines}\n'
        '- Si el cliente se desvía, respondé su duda y retomá la próxima pregunta.'
    )


def _history(thread) -> list[dict]:
    rows    =   list(thread.messages.order_by('-created_at')[:HISTORY_LIMIT])[::-1]
    history =   []
    for row in rows:
        role    =   'assistant' if row.from_staff else 'user'
        body    =   (row.body or '').strip()
        if not body:
            continue
        if history and history[-1]['role'] == role:
            history[-1]['content'] += '\n' + body
        else:
            history.append({'role': role, 'content': body})
    if not history or history[0]['role'] != 'user':
        history.insert(0, {'role': 'user', 'content': 'Hola, quiero armar la web de mi negocio.'})
    return history[-HISTORY_LIMIT:]


def _business_context(user) -> str:
    profile =   getattr(user, 'profile', None)
    if profile is None:
        return ''
    bits    =   [getattr(profile, 'business_name', ''), getattr(profile, 'description', '')]
    return ' '.join(b for b in bits if b)


#=========================================
# FALLBACK DETERMINISTA
#=========================================
def _fallback_reply(thread, latest : str) -> str:
    #asked = preguntas que el bot ya hizo; la próxima es la siguiente del guion.
    asked   =   thread.messages.filter(from_staff = True).count()
    if asked < len(QUESTIONS):
        return QUESTIONS[asked][1]
    #Entrevista completa: recomendar por palabras clave de todas las respuestas.
    answers =   ' '.join(
        thread.messages.filter(from_staff = False).values_list('body', flat = True)
    ).lower()
    slug    =   ''
    for keyword, candidates in STYLE_HINTS.items():
        if keyword in answers:
            slug    =   candidates[0]
            break
    if not slug:
        rows    =   search_design_styles(query = answers, limit = 1)
        slug    =   rows[0].slug if rows else 'minimal-nordic'
    style   =   next((s for s in catalog_summary(limit = 50) if s['slug'] == slug), None)
    name    =   style['nombre'] if style else slug
    return (
        f'¡Listo! Con lo que me contaste, el estilo que mejor le queda es "{name}" ({slug}). '
        'Ya podés aplicarlo desde Diseñar con IA y después ajustar colores y secciones en el editor. '
        '¿Querés que lo probemos?'
    )


#=========================================
# RESPUESTA
#=========================================
def design_reply(thread, latest : str = '') -> str:
    if anthropic_enabled():
        history =   _history(thread)
        context =   _business_context(thread.customer)
        system  =   _system_prompt() + (f'\nDatos ya cargados del negocio: {context}' if context else '')
        text    =   ask_claude(system, history)
        if text:
            return text
    return _fallback_reply(thread, latest)


def welcome_question(thread) -> ChatMessage:
    return send_bot_message(thread, QUESTIONS[0][1])


def reply_to_customer(thread, latest : str = '') -> ChatMessage | None:
    try:
        return send_bot_message(thread, design_reply(thread, latest))
    except Exception as exc:  # noqa: BLE001 — el chat del cliente nunca debe romperse
        logger.exception('Asistente de diseño falló: %s', exc)
        return None
