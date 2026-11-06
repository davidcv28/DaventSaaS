import logging

from django.contrib.auth.models import User

from AdminApp.domains.chat.models import AssistantMessage
from McpApp.domains.skills.services import DASHBOARD_MAP, ask_llm, assistant_snapshot, llm_enabled

"""
"Tu Asistente": bot automático por usuario, hilo APARTE del soporte.

Responde consultas sobre la cuenta del usuario en sesión usando el
snapshot MCP (user_tools — tools my_* de cada dominio, filtradas por el
usuario y con gate mcp_user_access). Nunca ve ni expone datos de otros
clientes ni recorre la base general.

Motor: LLM multi-proveedor (ask_llm) con el snapshot en el system
prompt; fallback determinista con el mismo snapshot si el LLM no está
disponible — el asistente nunca deja de responder.
"""

logger          =   logging.getLogger(__name__)
BOT_USERNAME    =   'davent_assistant'
BOT_NAME        =   'Tu Asistente'
HISTORY_LIMIT   =   16
GREETING        =   (
    'Hola, soy Tu Asistente. Puedo contarte sobre tu cuenta: plan, tienda, '
    'productos, categorías, marcas, visitas, pagos, facturas y tu perfil, '
    'y te digo dónde está cada cosa en el panel. ¿Qué querés saber?'
)

#El mapa del dashboard vive en McpApp.domains.skills.services.dashboard_map
#(DASHBOARD_MAP): lo comparte el bot y la tool MCP `dashboard_guide`.

DATA_KEYWORDS   =   (
    'plan', 'suscrip', 'pago', 'pagos', 'factura', 'producto', 'tienda',
    'visita', 'estadist', 'cuenta', 'perfil', 'email', 'vence', 'precio',
    'marca', 'categoria', 'slug', 'web', 'dias', 'renov',
)


def get_bot_user() -> User:
    user, _ =   User.objects.get_or_create(
        username    =   BOT_USERNAME,
        defaults    =   {
            'first_name'    :   BOT_NAME,
            'is_active'     :   True,
            #No es staff: no aparece en el roster ni recibe hilos de soporte.
            'is_staff'      :   False,
        },
    )
    if user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields = ['password'])
    return user


def send_bot_message(user : User, body : str) -> AssistantMessage:
    return AssistantMessage.objects.create(
        user        =   user,
        from_bot    =   True,
        body        =   (body or '').strip()[:2000],
    )


def ensure_greeting(user : User):
    """La conversación del asistente arranca con el saludo (primer acceso)."""
    if not AssistantMessage.objects.filter(user = user).exists():
        send_bot_message(user, GREETING)


def history_of(user : User) -> list[dict]:
    rows    =   list(AssistantMessage.objects.filter(user = user).order_by('-pk')[:HISTORY_LIMIT])[::-1]
    history =   []
    for row in rows:
        role    =   'assistant' if row.from_bot else 'user'
        if history and history[-1]['role'] == role:
            history[-1]['content'] += '\n' + row.body
        else:
            history.append({'role': role, 'content': row.body})
    return history[-HISTORY_LIMIT:]


#=========================================
# ACCIONES QUE EL PANEL EJECUTA SOLO (respuesta aditiva `action`)
#=========================================
#El texto lo sigue redactando el LLM/fallback; la acción la decide este
#mapa determinista — nunca el modelo (no inventa ni navega a lo loco).
_ACTION_BUSINESS    =   'assist_business'   # sección "Sobre mi negocio" + Asistencia con IA
_ACTION_DESIGN      =   'assist_design'     # sección "Diseño" + diseño asistido
_ACTION_KEYS    =   [
    (_ACTION_BUSINESS, (
        'datos de mi negocio', 'datos de la empresa', 'datos de mi empresa',
        'mi negocio', 'mi empresa', 'sobre mi negocio', 'perfil del negocio',
        'completar mis datos', 'completar el perfil', 'completar mi negocio',
        'completar la empresa', 'cargar mis datos', 'cargo mis datos',
        'cargo los datos', 'cargar datos', 'rellenar', 'rellená', 'relleno', 'formulario',
        'descripción del negocio', 'descripcion de mi', 'mis horarios',
        'dirección', 'redes sociales', 'mi whatsapp', 'mis redes',
    )),
    (_ACTION_DESIGN, (
        'diseñ', 'plantilla', 'personaliz', 'estilo de mi web', 'estilo de la web',
        'colores de mi web', 'color de mi web', 'fuente de mi web', 'tipografía',
        'tipografia', 'armar mi web', 'hacer mi web', 'crear mi web', 'crear mi página',
        'armar mi página', 'hacer mi página', 'crear mi sitio', 'armar mi sitio',
        'hacer mi sitio', 'cómo se ve mi web', 'como se ve mi web', 'mejorar mi web',
        'cambiar el diseño', 'mi página se ve', 'logo', 'foto de portada',
    )),
]


def _intent_action(text : str) -> str | None:
    """Acción del panel que acompaña a la respuesta (o None si es charla)."""
    t   =   f' {(text or "").lower()} '
    for action, keys in _ACTION_KEYS:
        if any(k in t for k in keys):
            return action
    return None


#=========================================
# SYSTEM PROMPT — asistente de cuenta, no vendedor de diseño
#=========================================
def _system_prompt(user : User, latest : str) -> str:
    snapshot    =   assistant_snapshot(user, query = latest)
    data        =   f'\nDatos del cliente en sesión (fuente de verdad — solo de ESTE usuario):\n{snapshot}' if snapshot else ''
    return (
        f'Sos "{BOT_NAME}", el asistente automático de DAVENT. Respondés al dueño '
        'de una tienda sobre SU cuenta: plan, vencimiento, renovación, tienda, '
        'link público, productos, categorías, marcas, visitas, pagos, facturas y '
        'perfil. Español rioplatense, cercano y breve (2-4 frases, sin markdown).\n'
        'Reglas:\n'
        '- Respondé SOLO con los datos del bloque "Datos del cliente en sesión". '
        'Si el dato pedido no está en el bloque, decilo y orientalo a la sección '
        'del panel donde se ve. Nunca inventes números ni hables de otros clientes.\n'
        '- También respondés dudas de uso del panel (cómo cargar un producto, '
        'dónde cambiar el logo, cómo se renueva el plan). Orientate con este '
        'mapa — nombrá la sección y la pestaña exactas:\n'
        f'{DASHBOARD_MAP}\n'
        '- Cuando el usuario quiera diseñar su web o cargar los datos de su '
        'negocio, la app ABRE SOLA la "Asistencia con IA" de esa sección: '
        'avisalo ("te abrí la asistencia con IA para que la completes más '
        'cómodo") en vez de solo mandarlo a la sección.\n'
        '- Si piden algo que no podés hacer (cambiar datos, ejecutar acciones '
        'fuera de esas asistencias), decí que sos de solo consulta y señalá '
        'dónde hacerlo en el panel.'
        f'{data}'
    )


def _fallback_reply(user : User, latest : str) -> str:
    snapshot    =   assistant_snapshot(user, query = latest)
    if snapshot and any(key in (latest or '').lower() for key in DATA_KEYWORDS):
        return f'Te cuento con tus datos actuales: {snapshot} ¿Algo más?'
    if snapshot:
        return f'Soy Tu Asistente: puedo informarte sobre tu plan, tienda, productos, visitas, pagos y facturas. De paso, tu resumen: {snapshot}'
    return 'Soy Tu Asistente. Ahora mismo no puedo leer los datos de tu cuenta — revisá que tu plan esté vigente. Mientras tanto, ¿en qué te ayudo?'


def assistant_reply(user : User, latest : str = '') -> str:
    if llm_enabled():
        try:
            text    =   ask_llm(_system_prompt(user, latest), history_of(user))
            if text:
                return text
        except Exception as exc:  # noqa: BLE001 — el asistente nunca se rompe
            logger.warning('Asistente LLM falló, fallback: %s', exc)
    return _fallback_reply(user, latest)


def reply_to_user(user : User, body : str) -> tuple[AssistantMessage | None, str | None]:
    """El usuario escribió: guarda su mensaje y responde el bot.

    Devuelve (mensaje del bot, acción de panel) — la acción viaja suelta en
    la respuesta del endpoint (no se persiste ni se repite al releer el
    historial): el front la ejecuta una sola vez.
    """
    AssistantMessage.objects.create(user = user, from_bot = False, body = (body or '').strip()[:2000])
    try:
        return send_bot_message(user, assistant_reply(user, body)), _intent_action(body)
    except Exception as exc:  # noqa: BLE001
        logger.exception('Tu Asistente falló: %s', exc)
        return send_bot_message(user, 'Tuve un problema leyendo tus datos. Probá de nuevo en un momento.'), None
