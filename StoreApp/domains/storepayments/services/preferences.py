"""
Preferencias de Checkout Pro de Mercado Pago para pedidos de tienda.

Se crea SIEMPRE con el access token DEL VENDEDOR (StoreMpAccount) — la
plata cae directo en su cuenta de MP. PROHIBIDO `application_fee` y
cualquier split: DAVENT no toca el dinero de las ventas.

Contrato con el dominio orders (track B):
- `external_reference` = `ord:<tracking_token>` — con prefijo propio para
  no colisionar con las futuras referencias `sub:` de membresías. El
  webhook acepta también el token pelado por compatibilidad.
- `back_urls` → página pública de seguimiento del front:
      <web_store>/seguimiento?token=<tracking_token>&resultado=<estado>
  donde <web_store> es (en orden): dominio propio verificado
  (`https://<dominio>`), subdominio `https://<slug>.<PLATFORM_DOMAIN>`,
  o `{FRONTEND_URL}/<slug>` en modo path. `resultado` ∈
  `exitoso|pendiente|fallo` — el front (track J) implementa la ruta.
- Items desde los snapshots de OrderItem (`name`, `qty`, `price`/
  `unit_price`/`line_total` — getattr defensivo porque el modelo de B
  está en desarrollo). Si algún item no resuelve precio, se emite UN item
  agregado por order.total: jamás se manda un monto que no cuadre.
"""
import logging
import re
from decimal import Decimal, InvalidOperation

from decouple import config
from django.utils import timezone

from StoreApp.domains.storepayments.models import MpPayment
from StoreApp.domains.storepayments.services import mp_client
from StoreApp.domains.stores.models import StoreDomain

logger  =   logging.getLogger(__name__)

FRONTEND_URL            =   config('FRONTEND_URL', default = 'http://localhost:5173')
BACKEND_URL             =   config('BACKEND_URL', default = '')
PLATFORM_DOMAIN         =   (config('PLATFORM_DOMAIN', default = '') or '').strip().lower()

EXTERNAL_REF_PREFIX     =   'ord:'
TRACKING_PATH           =   '/seguimiento'
#MP: statement_descriptor admite hasta 22 chars alfanuméricos/espacios.
STATEMENT_DESCRIPTOR_MAX=   22


#=========================================
# HELPERS
#=========================================
def store_web_url(store):
    """
    URL pública de la web de la tienda (misma resolución que el front):
    dominio propio verificado > subdominio de plataforma > path en el
    frontend. Devuelve '' si no se puede determinar (no debería pasar:
    FRONTEND_URL siempre tiene default).
    """
    domain      =   getattr(store, 'domain', None)
    if domain is not None and getattr(domain, 'status', '') == StoreDomain.STATUS_VERIFIED and domain.domain:
        return f'https://{domain.domain}'
    if PLATFORM_DOMAIN:
        return f'https://{store.slug}.{PLATFORM_DOMAIN}'
    return f'{FRONTEND_URL.rstrip("/")}/{store.slug}'


def _order_items(order):
    """
    Items del pedido como lista. Tolera related manager (`items.all()`),
    lista prefetcheada o atributo inexistente (devuelve []). El
    related_name exacto lo define el track B — se prueban los candidatos
    probables y si ninguno existe cae el item agregado por order.total.
    """
    items   =   None
    for attr in ('items', 'order_items', 'lines'):
        items   =   getattr(order, attr, None)
        if items is not None:
            break
    if items is None:
        return []
    if hasattr(items, 'all'):
        try:
            return list(items.all())
        except Exception:
            return []
    try:
        return list(items)
    except TypeError:
        return []


def _item_qty(item):
    for attr in ('qty', 'quantity'):
        value   =   getattr(item, attr, None)
        try:
            qty =   int(value)
            if qty > 0:
                return qty
        except (TypeError, ValueError):
            continue
    return 1


def _item_name(item, index):
    for attr in ('name', 'product_name', 'title'):
        value   =   getattr(item, attr, None)
        if value:
            return str(value)[:200]
    return f'Item {index + 1}'


def _decimal_or_none(value):
    try:
        if value is None or value == '':
            return None
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _item_unit_price(item, qty):
    """
    Precio unitario del snapshot: `unit_price`/`price` directo, o
    `line_total`/`total`/`subtotal` dividido por qty. None si no hay
    forma confiable de determinarlo.
    """
    for attr in ('unit_price', 'price'):
        amount  =   _decimal_or_none(getattr(item, attr, None))
        if amount is not None and amount > 0:
            return amount
    for attr in ('line_total', 'total', 'subtotal'):
        amount  =   _decimal_or_none(getattr(item, attr, None))
        if amount is not None and amount > 0:
            return (amount / qty).quantize(Decimal('0.01'))
    return None


def _order_expires_at(order):
    """Vencimiento del pedido (los nombres candidatos del contrato track B)."""
    for attr in ('expires_at', 'payment_expires_at', 'expires'):
        value   =   getattr(order, attr, None)
        if value:
            return value
    return None


def _preference_items(order):
    """
    Items para MP. Si TODOS los items resuelven qty+precio se mandan
    itemizados; si falta alguno, UN item agregado por order.total (el
    total siempre es el del servidor — nunca se confía en el cliente).

    INVARIANTE DE MONTO: la suma qty×unit_price DEBE ser exactamente
    order.total — MP Checkout Pro cobra lo que suman los items y el
    webhook solo acredita si transaction_amount == order.total. El
    envío a domicilio vive en order.shipping_cost (no en OrderItem):
    cuando items+envío == total se itemiza como línea "Envío"; ante
    cualquier otra diferencia (descuento, redondeo, dato inconsistente)
    se cae al item agregado por el total — jamás se emite un monto que
    no cuadre con el pedido.
    """
    total       =   _decimal_or_none(getattr(order, 'total', None)) or Decimal('0')
    items       =   _order_items(order)
    built       =   []
    charged     =   Decimal('0')
    if items:
        for index, item in enumerate(items):
            qty         =   _item_qty(item)
            unit_price  =   _item_unit_price(item, qty)
            if unit_price is None:
                built   =   []
                charged =   Decimal('0')
                break
            #Se acumula lo que MP va a cobrar (unit_price ya en float,
            #mismo valor que viaja en el payload — no el Decimal crudo).
            charged    +=  Decimal(str(float(unit_price))) * qty
            built.append({
                'title'         :   _item_name(item, index),
                'quantity'      :   qty,
                'unit_price'    :   float(unit_price),
                'currency_id'   :   'ARS',
            })
    if built and charged != total:
        #Envío a domicilio con tarifa fija: integra order.total pero no
        #es un OrderItem — línea propia para que la suma cuadre.
        shipping    =   _decimal_or_none(getattr(order, 'shipping_cost', None)) or Decimal('0')
        if shipping > 0 and (charged + shipping) == total:
            built.append({
                'title'         :   'Envío',
                'quantity'      :   1,
                'unit_price'    :   float(shipping),
                'currency_id'   :   'ARS',
            })
        else:
            #Diferencia no explicada por el envío: item único por el
            #total exacto del servidor (el webhook exige amount == total).
            built   =   []
    if not built:
        token   =   getattr(order, 'tracking_token', '') or 'pedido'
        built   =   [{
            'title'         :   f'Pedido {token}'[:200],
            'quantity'      :   1,
            'unit_price'    :   float(total),
            'currency_id'   :   'ARS',
        }]
    return built


def _statement_descriptor(store):
    """Nombre visible en el resumen de tarjeta de MP (≤22, alnum+espacios)."""
    customization    =   getattr(store, 'customization', None)
    name            =   (getattr(customization, 'display_name', '') or store.slug or 'DAVENT').strip()
    clean           =   re.sub(r'[^A-Za-z0-9 ]', '', name).strip() or 'DAVENT'
    return clean[:STATEMENT_DESCRIPTOR_MAX].strip() or 'DAVENT'


def build_preference_payload(order, store):
    """Arma el body de POST /checkout/preferences (sin llamar a MP)."""
    token           =   getattr(order, 'tracking_token', '') or ''
    web_url         =   store_web_url(store)
    result_param    =   'resultado'
    back_urls       =   {
        'success'   :   f'{web_url}{TRACKING_PATH}?token={token}&{result_param}=exitoso',
        'pending'   :   f'{web_url}{TRACKING_PATH}?token={token}&{result_param}=pendiente',
        'failure'   :   f'{web_url}{TRACKING_PATH}?token={token}&{result_param}=fallo',
    }
    payload         =   {
        'items'                 :   _preference_items(order),
        'external_reference'    :   f'{EXTERNAL_REF_PREFIX}{token}',
        'back_urls'             :   back_urls,
        'statement_descriptor'  :   _statement_descriptor(store),
    }
    #auto_return='approved' exige back_urls https (MP las rechaza en http).
    if web_url.startswith('https://'):
        payload['auto_return']  =   'approved'
    #IPN del vendedor: MP avisa al webhook de SU slug apenas se acredita.
    if BACKEND_URL:
        payload['notification_url'] =   f'{BACKEND_URL.rstrip("/")}/api/webhooks/store-mp/{store.slug}/'
    #Vencimiento del pedido (si orders lo modela): MP soporta
    #expiration_date_to en la preferencia.
    expires_at      =   _order_expires_at(order)
    if expires_at:
        payload['expires']              =   True
        payload['expiration_date_to']   =   expires_at.isoformat()
    #Payer pre-cargado con el email del snapshot del pedido.
    customer_email  =   getattr(order, 'customer_email', '') or ''
    if customer_email:
        payload['payer']    =   {'email': customer_email}
    return payload


#=========================================
# CREATE ORDER PREFERENCE (servicio público del dominio)
#=========================================
def _latest_open_attempt(order, store):
    """
    Intento de cobro ABIERTA del pedido: MpPayment con preference_id y
    mp_payment_id NULL (el webhook todavía no adoptó ningún pago MP).
    Es la preferencia que un retry/doble click del comprador debe
    reutilizar — dos preferencias vivas habilitan dos cobros por un
    solo pedido.
    """
    order_pk    =   getattr(order, 'pk', None) or getattr(order, 'id', None)
    if order_pk is None:
        return None
    return (
        MpPayment.objects
        .filter(store = store, order_id = order_pk, mp_payment_id__isnull = True)
        .exclude(preference_id = '')
        .order_by('-created_at')
        .first()
    )


def create_order_preference(order, store):
    """
    Crea la preferencia MP con el token del vendedor y registra el
    intento en MpPayment. IDEMPOTENTE por pedido: si ya existe una
    preferencia ABIERTA (MpPayment CREATED sin mp_payment_id) se
    re-lee de MP y se devuelve la MISMA — un doble click o retry del
    front nunca emite una segunda preferencia pagable; si MP ya no la
    tiene (400/404/410) se emite una nueva.

    Devuelve (mp_payment, preference_dict).
    Lanza MpApiError si MP rechaza, ValidationError si la cuenta no
    está conectada o el pedido venció, y VaultError si el token
    cifrado no se puede leer.
    """
    from rest_framework import serializers
    account     =   getattr(store, 'mp_account', None)
    access_token    =   account.get_access_token() if account else ''
    if not access_token:
        raise serializers.ValidationError({'detail': 'La tienda no tiene Mercado Pago conectado'})
    #Vencimiento por tiempo aunque el pedido siga PENDING_PAYMENT (el
    #cron expire_orders corre periódicamente): MP rechazaría una
    #expiration_date_to pasada y el cliente pagaría un pedido muerto.
    expires_at  =   _order_expires_at(order)
    if expires_at is not None and expires_at <= timezone.now():
        raise serializers.ValidationError({'detail': 'El pedido venció'})
    #Reuso idempotente de la preferencia abierta (ver docstring).
    attempt     =   _latest_open_attempt(order, store)
    if attempt is not None:
        try:
            preference  =   mp_client.get_preference(attempt.preference_id, access_token)
        except mp_client.MpApiError as exc:
            #Solo "ya no existe" habilita una preferencia nueva; un
            #error de red/5xx sube tal cual (el cliente reintenta y no
            #se arriesga una segunda preferencia pagable a ciegas).
            if exc.status_code not in (400, 404, 410):
                raise
            logger.info('Preferencia MP %s ya no existe (store=%s): se emite una nueva', attempt.preference_id, store.slug)
        else:
            if preference.get('id'):
                logger.info('Preferencia MP reutilizada: store=%s order_id=%s preference=%s',
                            store.slug, getattr(order, 'pk', None), attempt.preference_id)
                return attempt, preference
    payload     =   build_preference_payload(order, store)
    #MpApiError sube tal cual: la vista la traduce a 502.
    preference  =   mp_client.create_preference(payload, access_token)
    preference_id    =   str(preference.get('id') or '')[:64]
    amount           =   _decimal_or_none(getattr(order, 'total', None)) or Decimal('0')
    token            =   getattr(order, 'tracking_token', '') or ''
    order_pk         =   getattr(order, 'pk', None) or getattr(order, 'id', None)
    mp_payment       =   MpPayment.objects.create(
        store               =   store,
        order_id            =   order_pk,
        tracking_token      =   token[:128],
        preference_id       =   preference_id,
        status              =   MpPayment.Status.CREATED,
        amount              =   amount,
        currency            =   'ARS',
    )
    logger.info('Preferencia MP creada: store=%s order_id=%s preference=%s', store.slug, order_pk, preference_id)
    return mp_payment, preference
