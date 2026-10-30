import json
import logging

import requests
from django.conf import settings

from McpApp.domains.skills.services.anthropic import ask_claude

"""
Capa LLM multi-proveedor del asistente de diseño.

Anthropic quedó con la cuenta sin crédito, así que el orden por defecto
prioriza los planes gratuitos con más margen:
  1. Google Gemini (free tier: ~15 RPM / 1.500 req/día)
  2. Groq (free tier, muy rápido, sin tarjeta)
  3. OpenRouter (modelos :free)
  4. Anthropic (si hay crédito)

Se elige con AI_PROVIDER=gemini|groq|openrouter|anthropic; vacío = auto
(el primero con key). Si el proveedor falla se prueba el siguiente; si
ninguno responde, el llamador usa el guion determinista.
"""

logger          =   logging.getLogger(__name__)
GEMINI_URL      =   'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GROQ_URL        =   'https://api.groq.com/openai/v1/chat/completions'
OPENROUTER_URL  =   'https://openrouter.ai/api/v1/chat/completions'


#=========================================
# CONFIGURACIÓN
#=========================================
def _provider_order() -> list[str]:
    configured  =   (getattr(settings, 'AI_PROVIDER', '') or '').strip().lower()
    order       =   ['gemini', 'groq', 'openrouter', 'anthropic']
    if configured in order:
        order.remove(configured)
        order.insert(0, configured)
    return order


def _key(provider : str) -> str:
    return {
        'gemini'        :   getattr(settings, 'GEMINI_API_KEY', ''),
        'groq'          :   getattr(settings, 'GROQ_API_KEY', ''),
        'openrouter'    :   getattr(settings, 'OPENROUTER_API_KEY', ''),
        'anthropic'     :   getattr(settings, 'ANTHROPIC_API_KEY', ''),
    }.get(provider, '')


def llm_enabled() -> bool:
    return any(_key(p) for p in _provider_order())


#=========================================
# PROVEEDORES
#=========================================
def _ask_gemini(system : str, messages : list[dict], max_tokens : int, temperature : float) -> str | None:
    model   =   getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
    contents    =   [
        {
            'role'  :   'model' if m['role'] == 'assistant' else 'user',
            'parts' :   [{'text': m['content']}],
        }
        for m in messages
    ]
    payload =   {
        'systemInstruction' :   {'parts': [{'text': system}]},
        'contents'          :   contents,
        'generationConfig'  :   {'maxOutputTokens': max_tokens, 'temperature': temperature},
    }
    response    =   requests.post(
        GEMINI_URL.format(model = model),
        params  =   {'key': _key('gemini')},
        headers =   {'content-type': 'application/json'},
        data    =   json.dumps(payload),
        timeout =   getattr(settings, 'LLM_TIMEOUT', 15),
    )
    if response.status_code >= 400:
        logger.warning('Gemini %s: %s', response.status_code, response.text[:300])
        return None
    candidates  =   response.json().get('candidates') or []
    parts       =   ((candidates[0].get('content') or {}).get('parts') or []) if candidates else []
    text        =   ''.join(p.get('text', '') for p in parts).strip()
    return text or None


def _ask_openai_compatible(url : str, api_key : str, model : str, system : str, messages : list[dict], max_tokens : int, temperature : float, extra_headers : dict | None = None) -> str | None:
    payload =   {
        'model'         :   model,
        'max_tokens'    :   max_tokens,
        'temperature'   :   temperature,
        'messages'      :   [{'role': 'system', 'content': system}] + messages,
    }
    response    =   requests.post(
        url,
        headers =   {'Authorization': f'Bearer {api_key}', 'content-type': 'application/json', **(extra_headers or {})},
        data    =   json.dumps(payload),
        timeout =   getattr(settings, 'LLM_TIMEOUT', 15),
    )
    if response.status_code >= 400:
        logger.warning('%s %s: %s', url, response.status_code, response.text[:300])
        return None
    choices =   response.json().get('choices') or []
    text    =   ((choices[0].get('message') or {}).get('content') or '').strip() if choices else ''
    return text or None


#=========================================
# ENTRADA ÚNICA
#=========================================
def ask_llm(system : str, messages : list[dict], max_tokens : int = 400, temperature : float = 0.6) -> str | None:
    for provider in _provider_order():
        if not _key(provider):
            continue
        try:
            if provider == 'gemini':
                text    =   _ask_gemini(system, messages, max_tokens, temperature)
            elif provider == 'groq':
                text    =   _ask_openai_compatible(
                    GROQ_URL, _key('groq'), getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile'),
                    system, messages, max_tokens, temperature,
                )
            elif provider == 'openrouter':
                text    =   _ask_openai_compatible(
                    OPENROUTER_URL, _key('openrouter'),
                    getattr(settings, 'OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct:free'),
                    system, messages, max_tokens, temperature,
                    extra_headers = {'HTTP-Referer': getattr(settings, 'FRONTEND_URL', ''), 'X-Title': 'DAVENT'},
                )
            else:
                text    =   ask_claude(system, messages, max_tokens = max_tokens, temperature = temperature)
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning('%s no disponible: %s', provider, exc)
            text    =   None
        if text:
            return text
    return None
