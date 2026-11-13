import logging
from urllib.parse import quote

import requests
from rest_framework import serializers

logger = logging.getLogger(__name__)

"""
Correos del e-commerce: código de seguimiento del pedido.

- Manual: el dueño genera el envío en el panel de su correo (OCA,
  Andreani, Correo Argentino o cualquier otro) y pega el código al
  marcar el pedido como enviado — funciona para cualquier empresa.
- Integrada (`generate_shipment`): DAVENT crea la orden de envío en la
  API del correo CON LAS CREDENCIALES DEL DUEÑO — el contrato y el
  costo del flete los paga la tienda, nunca la plataforma. Hoy:
  Andreani (REST v2). OCA se cubre por código manual hasta que exista
  el adaptador de su webservice.

El link público de tracking (`tracking_url`) va al comprador en
/seguimiento — cada correo resuelve el estado real en su propia web.
"""

CARRIER_LABELS = {
    'oca'               :   'OCA',
    'andreani'          :   'Andreani',
    'correo_argentino'  :   'Correo Argentino',
    'other'             :   'Otro correo',
}

CARRIER_CHOICES = tuple(CARRIER_LABELS.keys())


def carrier_display(order):
    """Nombre legible del correo del pedido (custom label si cargó uno)."""
    return order.carrier_label or CARRIER_LABELS.get(order.carrier, order.carrier or '')


_TRACKING_URLS = {
    'oca'               :   'https://www.oca.com.ar/seguimiento?numero={code}',
    'andreani'          :   'https://www.andreani.com/seguimiento?numero={code}',
    'correo_argentino'  :   'https://www.correoargentino.com.ar/formularios/e-commerce?id={code}',
}


def tracking_url(carrier, code):
    """URL pública del correo para que el comprador siga el paquete.

    El código se URL-encodea: lo pega el dueño a mano y sin quote un
    `&`/`?`/`#` inyectaría parámetros extra en la query del correo.
    """
    if not carrier or not code:
        return ''
    tpl = _TRACKING_URLS.get(carrier)
    return tpl.format(code = quote(str(code), safe = '')) if tpl else ''


#=========================================
# ANDREANI — API REST v2 (credenciales del dueño)
#=========================================
ANDREANI_BASE   =   'https://api.andreani.com'
ANDREANI_TIMEOUT =   20


def _andreani_token(creds):
    user, pwd = (creds.get('usuario') or '').strip(), (creds.get('password') or '').strip()
    if not user or not pwd:
        raise serializers.ValidationError({'carrier': 'Faltan usuario y contraseña de Andreani en Cobros → Envíos.'})
    try:
        res = requests.get(f'{ANDREANI_BASE}/login', auth = (user, pwd), timeout = ANDREANI_TIMEOUT)
    except requests.RequestException:
        raise serializers.ValidationError({'carrier': 'No pudimos conectar con Andreani. Probá de nuevo en un rato.'})
    if res.status_code != 200:
        raise serializers.ValidationError({'carrier': 'Andreani rechazó las credenciales (revisá usuario/contraseña).'})
    token = (res.json() or {}).get('token')
    if not token:
        raise serializers.ValidationError({'carrier': 'Andreani no devolvió token de sesión.'})
    return token


def _andreani_create_shipment(creds, order):
    contrato = (creds.get('contrato') or '').strip()
    if not contrato:
        raise serializers.ValidationError({'carrier': 'Falta el número de contrato de Andreani en Cobros → Envíos.'})
    token           =   _andreani_token(creds)
    addr            =   order.shipping_address or {}
    destino_postal  =   (addr.get('postal_code') or '').strip()
    if not destino_postal:
        raise serializers.ValidationError({'carrier': 'El pedido no tiene código postal de destino para generar el envío.'})
    origen_postal   =   (creds.get('cp_origen') or '').strip()
    if not origen_postal:
        raise serializers.ValidationError({'carrier': 'Falta el código postal de origen en Cobros → Envíos.'})
    nombre          =   f'{order.customer_first_name} {order.customer_last_name}'.strip() or 'Cliente'
    body = {
        'contrato'      :   contrato,
        'origen'        :   {'postal': {'codigoPostal': origen_postal, 'pais': 'AR'}},
        'destino'       :   {'postal': {'codigoPostal': destino_postal, 'pais': 'AR'}},
        'destinatario'  :   [{
            'tipo'          :   'fisica',
            'nombreCompleto':   nombre,
            'email'         :   order.customer_email,
        }],
        'productoAEntregar':  'a domicilio',
        'bultos'        :   [{
            'kilos'     :   float(creds.get('peso_kg') or 1),
            'volumenCm' :   float(creds.get('volumen_cm3') or 0) or None,
            'valorDeclaradoSinImpuestos': float(order.subtotal or 0),
            'valorDeclaradoConImpuestos': float(order.total or 0),
            'referencias'   :   [{'tipo': 'P', 'referencia': f'Pedido {order.code or order.number}'}],
        }],
    }
    try:
        res = requests.post(
            f'{ANDREANI_BASE}/v2/ordenes-de-envio',
            json    =   body,
            headers =   {'x-authorization-token': token, 'Authorization': f'Bearer {token}'},
            timeout =   ANDREANI_TIMEOUT,
        )
    except requests.RequestException:
        raise serializers.ValidationError({'carrier': 'No pudimos conectar con Andreani. Probá de nuevo en un rato.'})
    if res.status_code not in (200, 201):
        detail = (res.text or '')[:240]
        logger.warning('Andreani orden-de-envio %s: %s', res.status_code, detail)
        raise serializers.ValidationError({'carrier': f'Andreani rechazó la orden ({res.status_code}). Revisá contrato y datos del pedido.'})
    data    =   res.json() or {}
    bultos  =   data.get('bultos') or []
    code    =   (bultos[0].get('numeroDeEnvio') if bultos else '') or data.get('numeroDeEnvio') or data.get('numero') or ''
    if not code:
        raise serializers.ValidationError({'carrier': 'Andreani creó la orden pero no devolvió número de envío.'})
    return str(code)


def generate_shipment(store, order):
    """
    Crea la orden de envío en el correo configurado del dueño y devuelve
    `(carrier, tracking_code)`. Sin configuración o correo sin adaptador
    → ValidationError: el dueño siempre puede pegar el código a mano.
    """
    cfg = getattr(store, 'shipping_config', None)
    provider = (getattr(cfg, 'carrier', '') or '').strip()
    if not provider:
        raise serializers.ValidationError({'carrier': 'Configurá tu correo en Cobros → Envíos, o pegá el código de seguimiento a mano.'})
    creds = cfg.get_carrier_credentials() if hasattr(cfg, 'get_carrier_credentials') else {}
    if provider == 'andreani':
        return 'andreani', _andreani_create_shipment(creds, order)
    if provider == 'oca':
        raise serializers.ValidationError({'carrier': 'La generación automática con OCA todavía no está — generá la orden en tu panel OCA y pegá el código acá.'})
    raise serializers.ValidationError({'carrier': f'Correo no soportado para generación automática: {provider}.'})
