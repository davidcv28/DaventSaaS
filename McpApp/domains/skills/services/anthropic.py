import json
import logging

import requests
from django.conf import settings

"""
Cliente mínimo de Anthropic (Messages API).

Se usa la API key del plan gratuito que se carga en ANTHROPIC_API_KEY.
Sin key (o si la API falla) devuelve None y el llamador cae al flujo
determinista: el asistente nunca queda mudo.
"""

logger      =   logging.getLogger(__name__)
API_URL     =   'https://api.anthropic.com/v1/messages'
API_VERSION =   '2023-06-01'


def anthropic_enabled() -> bool:
    return bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def ask_claude(system : str, messages : list[dict], max_tokens : int = 400, temperature : float = 0.6) -> str | None:
    api_key =   getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return None
    payload =   {
        'model'         :   getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-haiku-latest'),
        'max_tokens'    :   max_tokens,
        'temperature'   :   temperature,
        'system'        :   system,
        'messages'      :   messages,
    }
    try:
        response    =   requests.post(  # nosec B113 — timeout dinámico vía ANTHROPIC_TIMEOUT
            getattr(settings, 'ANTHROPIC_BASE_URL', 'https://api.anthropic.com/v1') + '/messages',
            headers = {
                'x-api-key'         :   api_key,
                'anthropic-version' :   API_VERSION,
                'content-type'      :   'application/json',
            },
            data    =   json.dumps(payload),
            timeout =   getattr(settings, 'ANTHROPIC_TIMEOUT', 12),
        )
        if response.status_code >= 400:
            logger.warning('Anthropic %s: %s', response.status_code, response.text[:300])
            return None
        blocks  =   response.json().get('content') or []
        text    =   ''.join(block.get('text', '') for block in blocks if block.get('type') == 'text').strip()
        return text or None
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Anthropic no disponible: %s', exc)
        return None
