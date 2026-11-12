"""
Cliente REST mínimo de la API de Mercado Pago para cobros de tiendas.

DECISIÓN SDK vs requests: se usa `requests` (ya instalado) en vez del SDK
`mercadopago` porque cada tienda tiene SU PROPIO access token — el SDK
oficial se inicializa con una credencial global por proceso
(`mercadopago.SDK(...)`), lo que obligaría a re-instanciarlo por request
y aporta poco sobre 4 endpoints REST. Acá el token viaja explícito por
llamada (Authorization: Bearer) y jamás se loguea ni sale en errores.

Todos los paths se validan contra un regex de id antes de interpolarse:
un payment_id manipulado no puede redirigir la consulta autenticada.
"""
import logging
import re

import requests

logger  =   logging.getLogger(__name__)

MP_API_BASE     =   'https://api.mercadopago.com'
MP_TIMEOUT      =   15
#Ids de MP (payments, preferences, users): numéricos o alfanumérico corto.
MP_ID_RE        =   re.compile(r'[A-Za-z0-9_-]{1,64}')


class MpApiError(Exception):
    """Falla de la API de Mercado Pago. `status_code` None = error de red."""
    def __init__(self, message, *, status_code = None):
        super().__init__(message)
        self.status_code    =   status_code


def _check_id(value, field = 'id'):
    if not value or not MP_ID_RE.fullmatch(str(value)):
        raise MpApiError(f'Identificador de Mercado Pago inválido ({field})', status_code = 400)
    return str(value)


def _request(method, path, *, access_token, payload = None, params = None):
    """
    Una llamada autenticada con el token DEL VENDEDOR. El token nunca se
    loguea: los errores solo registran método/path/status.
    """
    url             =   f'{MP_API_BASE}{path}'
    headers         =   {
        'Authorization' :   f'Bearer {access_token}',
        'Accept'        :   'application/json',
    }
    try:
        response    =   requests.request(
            method,
            url,
            headers     =   headers,
            json        =   payload,
            params      =   params,
            timeout     =   MP_TIMEOUT,
        )
    except requests.RequestException as exc:
        #Solo el tipo de excepción: el mensaje de requests puede incluir la URL
        #y nunca el header, pero se recorta por las dudas.
        logger.warning('MP API inaccesible: %s %s (%s)', method, path, type(exc).__name__)
        raise MpApiError('No se pudo comunicar con Mercado Pago') from exc
    if response.status_code >= 400:
        #El body de error de MP no contiene el token; se loguea truncado
        #solo para diagnóstico (message/cause), nunca headers ni credenciales.
        detail      =   ''
        try:
            detail  =   str((response.json() or {}).get('message') or '')[:200]
        except ValueError:
            pass
        logger.warning('MP API error: %s %s -> %s %s', method, path, response.status_code, detail)
        raise MpApiError(f'Mercado Pago respondió {response.status_code}', status_code = response.status_code)
    try:
        return response.json() if response.content else {}
    except ValueError:
        return {}

#=========================================
# USUARIO MP (validación de credenciales del dueño)
#=========================================
def get_mp_user(access_token):
    """GET /users/me — valida el access token del vendedor antes de guardarlo."""
    return _request('GET', '/users/me', access_token = access_token)

#=========================================
# PAYMENTS (webhook + reembolsos)
#=========================================
def get_mp_payment(payment_id, access_token):
    """GET /v1/payments/<id> — fuente de verdad del estado del cobro."""
    return _request('GET', f'/v1/payments/{_check_id(payment_id, "payment_id")}', access_token = access_token)


def refund_mp_payment(payment_id, access_token, amount = None):
    """
    POST /v1/payments/<id>/refunds — reembolso TOTAL si amount es None
    (body vacío = refund total en MP); parcial solo si se pasa amount.
    """
    pid     =   _check_id(payment_id, 'payment_id')
    payload =   {'amount': float(amount)} if amount is not None else {}
    return _request('POST', f'/v1/payments/{pid}/refunds', access_token = access_token, payload = payload)

#=========================================
# PREFERENCES (Checkout Pro del pedido)
#=========================================
def create_preference(payload, access_token):
    """POST /checkout/preferences — devuelve el dict de MP (id, init_point...)."""
    return _request('POST', '/checkout/preferences', access_token = access_token, payload = payload)


def get_preference(preference_id, access_token):
    """
    GET /checkout/preferences/<id> — re-lee una preferencia ya emitida.
    Lo usa el checkout para IDEMPOTENCIA: un retry/doble click del
    comprador devuelve el MISMO init_point en vez de crear una segunda
    preferencia pagable (dos links vivos = dos cobros por un pedido).
    """
    return _request('GET', f'/checkout/preferences/{_check_id(preference_id, "preference_id")}', access_token = access_token)
