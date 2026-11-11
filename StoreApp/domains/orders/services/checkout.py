"""
Creación y serialización pública de pedidos (e-commerce DAVENT).

`create_order` es el ÚNICO camino que materializa un Order: valida
tienda/método de pago/productos/exclusividad/stock, recalcula TODOS los
precios server-side (effective_pricing_of + member_discount_percent —
jamás montos del cliente), congela el snapshot del comprador y crea
Order + OrderItems + OrderEvent 'created' en UN atomic con la fila de
Store bloqueada (numeración PED-XXXX serializada por tienda).

NO descuenta stock acá (eso es mark_order_paid al confirmar el pago):
la disponibilidad se RESERVA de forma blanda — `stock` menos las
unidades ya comprometidas por pedidos PENDING_PAYMENT del producto,
validada bajo `select_for_update` de las filas de Product dentro del
atomic — así dos checkouts concurrentes por la última unidad se
serializan y el segundo recibe ValidationError en vez de sobre-vender.
No hay campo ni tabla de reserva: cancelar/expirar el pedido pendiente
libera la disponibilidad por sí solo (el cambio de status es la
liberación, idempotente por la máquina de estados) y el
'stock_conflict' del pago queda como defensa residual (stock corregido
a mano por el dueño, pedidos emitidos antes de esta regla).

Decisiones documentadas:
- `use_cart`/`cart`: el pedido puede armase desde el Cart del cliente
  para ESA tienda (orders importa cart — cart no importa orders, no hay
  ciclo). Al crearse OK el carrito se vacía en el mismo atomic.
- `idempotency_key`: retry del cliente → MISMO pedido (lookup previo +
  UniqueConstraint(store, key) como segunda capa; IntegrityError →
  re-fetch, nunca duplicado).
- `shipping_cost`: tarifa fija de `StoreShippingConfig.home_price`
  (stores) cuando el envío es a domicilio y el dueño cargó precio —
  se cobra en el pedido y se suma al total. `home_price` NULL = "a
  coordinar" (shipping_cost=0 y `shipping_priced`=False: el 0 no
  significa gratis). Retiro en el local siempre es sin cargo.
  `free_shipping_for` de membresías queda consumible para una futura
  regla de envío gratis por monto/plan.
- Descuento de membresía: `member_discount_percent(customer, store)`
  se aplica POR ENCIMA del precio efectivo de catálogo, por unidad,
  half-up a 2 decimales — carrito y pedido muestran/cobran lo mismo.
- Comprobante: el comprador puede subir comprobante en CUALQUIER método
  manual (transfer/whatsapp/cash) con el pedido PENDING_PAYMENT — no
  solo cuando proof_required (spec: "permitir siempre en métodos
  manuales").
- Seguimiento público: se gatea por tienda publicada/no bloqueada, NO
  por orders_enabled — un pedido ya creado sigue siendo rastreable y
  pagable aunque el dueño apague la venta online después (orders_enabled
  gobierna ventas NUEVAS, no la vida de los pedidos emitidos). El gate
  de plan (`has_ecommerce`) vive DENTRO de orders_enabled: baja de plan
  = no hay pedidos nuevos, pero el tracking de los ya emitidos sigue.
"""
import logging
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from StoreApp.domains.cart.services.benefits import (
    apply_member_discount,
    has_exclusive_access,
    member_discount_percent,
)
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.catalog.services.services import (
    effective_pricing_of,
    running_discounts_of,
)
from StoreApp.domains.orders.models import (
    Order,
    OrderItem,
    OrderSequence,
    new_tracking_token,
)
from StoreApp.domains.orders.services.events import append_event
from StoreApp.domains.stores.models import Store, StoreShippingConfig
from StoreApp.domains.stores.services.commerce import orders_enabled

logger  =   logging.getLogger(__name__)
#=========================================
# CONSTANTS
#=========================================
MAX_QTY                 =   100     # tope por línea (espejo de cart)
MAX_ITEMS               =   50      # tope de líneas distintas por pedido
DEFAULT_DEADLINE_HOURS  =   48
ADDRESS_FIELD_MAX       =   {'label': 40, 'line1': 160, 'line2': 160, 'city': 120, 'province': 120, 'postal_code': 20, 'country': 2}
ADDRESS_REQUIRED        =   ('line1', 'city', 'province')
MANUAL_PAYMENT_METHODS  =   {Order.PaymentMethod.TRANSFER, Order.PaymentMethod.WHATSAPP, Order.PaymentMethod.CASH}
#=========================================
# STORE / ORDER LOOKUP
#=========================================
def public_store(slug, *, require_orders_enabled = True):
    """
    Tienda por slug para endpoints de pedido. Publicada y no bloqueada
    siempre; `require_orders_enabled` agrega el gate de venta online
    (orders_enabled) — la creación de pedidos lo exige, el seguimiento
    de un pedido existente no (ver docstring del módulo).
    """
    slug    =   (slug or '').strip().lower()
    if not slug:
        return None
    store   =   (
        Store.objects
        .filter(slug = slug, is_published = True, is_blocked = False)
        .select_related('customization', 'fiscal_profile', 'payment_config', 'mp_account', 'user')
        .first()
    )
    if store is None:
        return None
    if require_orders_enabled and not orders_enabled(store):
        return None
    return store


def find_order_by_token(store, tracking_token):
    """
    Pedido por su identificador público ACOTADO a la tienda (IDOR: un
    token válido de otra tienda nunca matchea). Con items/events/proof
    prefetcheados — el feed de seguimiento no genera N+1.
    """
    token   =   (tracking_token or '').strip()
    if not token:
        return None
    return (Order.objects
        .filter(store = store, tracking_token = token)
        .select_related('store', 'customer')
        .prefetch_related('items', 'events', 'proof')
        .first())


#=========================================
# CREATE ORDER (contrato interno del dominio)
#=========================================
def _merge_lines(items, cart = None):
    """
    Normaliza `items` ([{product_id, qty}]) + las líneas del `cart`
    opcional a un dict {product_id: qty} sumado. Valida forma y topes;
    los errores son serializers.ValidationError → 400 en la vista.
    """
    merged  =   {}
    def _add(raw_id, raw_qty, source):
        try:
            pid =   int(raw_id)
            qty =   int(raw_qty)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'items': f'Item inválido en {source}.'})
        if pid <= 0 or qty < 1:
            raise serializers.ValidationError({'items': f'Cantidad fuera de rango en {source}.'})
        merged[pid]    =   merged.get(pid, 0) + qty
    for entry in items or []:
        if not isinstance(entry, dict):
            raise serializers.ValidationError({'items': 'Cada item debe ser un objeto {product_id, qty}.'})
        _add(entry.get('product_id'), entry.get('qty'), 'items')
    if cart is not None:
        for cart_item in cart.items.all():
            _add(cart_item.product_id, cart_item.qty, 'cart')
    if not merged:
        raise serializers.ValidationError({'items': 'El pedido no tiene items.'})
    if len(merged) > MAX_ITEMS:
        raise serializers.ValidationError({'items': f'El pedido admite hasta {MAX_ITEMS} productos distintos.'})
    for pid, qty in merged.items():
        if qty < 1 or qty > MAX_QTY:
            raise serializers.ValidationError({'items': f'Cantidad fuera de rango (1-{MAX_QTY}) para el producto {pid}.'})
    return merged


def _payment_config_of(store):
    """StorePaymentConfig o None — los defaults del modelo aplican si falta."""
    return getattr(store, 'payment_config', None)


def _payment_method_allowed(store, method):
    """
    True si el método está habilitado en StorePaymentConfig (sin fila =
    defaults del modelo). 'mp' además exige StoreMpAccount conectado —
    misma regla que el checkout de track C.
    """
    config      =   _payment_config_of(store)
    if method == Order.PaymentMethod.TRANSFER:
        return config.accept_transfer if config else True
    if method == Order.PaymentMethod.WHATSAPP:
        return config.accept_whatsapp if config else True
    if method == Order.PaymentMethod.CASH:
        return config.accept_cash if config else False
    if method == Order.PaymentMethod.MP:
        mp_enabled  =   config.mp_enabled if config else True
        account     =   getattr(store, 'mp_account', None)
        return bool(mp_enabled and account and account.is_connected)
    return False


def _address_snapshot(address):
    """
    Normaliza la dirección a un dict plano para el JSONField. Acepta
    dict o cualquier objeto con los atributos de CustomerAddress.
    """
    def _get(key):
        if isinstance(address, dict):
            return address.get(key)
        return getattr(address, key, None)
    snapshot    =   {}
    for key, max_len in ADDRESS_FIELD_MAX.items():
        value           =   str(_get(key) or '').strip()[:max_len]
        if value:
            snapshot[key]   =   value
    return snapshot


def _require_home_address(address):
    """Para envío a domicilio la dirección es obligatoria (campos mínimos)."""
    snapshot    =   _address_snapshot(address) if address else {}
    missing     =   [key for key in ADDRESS_REQUIRED if not snapshot.get(key)]
    if missing:
        raise serializers.ValidationError({'address': f'Falta la dirección de envío ({", ".join(missing)}).'})
    return snapshot


def _customer_snapshot(customer):
    """Datos del comprador congelados al crear (perfil puede cambiar después)."""
    return {
        'customer_first_name'       :   (customer.first_name or '').strip()[:150],
        'customer_last_name'        :   (customer.last_name or '').strip()[:150],
        'customer_email'            :   (customer.email or '').strip().lower()[:254],
        'customer_phone'            :   str(customer.phone or '')[:24],
        'customer_document_type'    :   (customer.document_type or '')[:4],
        'customer_document'         :   str(customer.document or '')[:11],
    }


def _resolve_lines(store, customer, merged):
    """
    Valida productos de ESA tienda (activos, no exclusivos-sin-acceso,
    stock suficiente en qty agregado) y devuelve las líneas listas para
    precios: [{product, qty}]. Todo ValidationError → 400.

    DECISIÓN (carrera de stock): se adopta RESERVA BLANDA — validar con
    lock + dejar el decremento al pago era el mínimo cambio, pero deja
    abierta la ventana (dos checkouts leen el mismo stock, nacen dos
    pedidos por la última unidad y el segundo paga en stock_conflict).
    Acá las filas de Product se bloquean con select_for_update (orden
    por pk → anti-deadlock entre checkouts/pagos multi-producto) y la
    disponibilidad es `stock` menos las unidades comprometidas por
    pedidos PENDING_PAYMENT: el segundo checkout espera el lock, ve el
    compromiso del primero y falla ANTES de crear el pedido. La reserva
    no se persiste: se libera sola cuando el pedido pendiente sale de
    PENDING_PAYMENT (cancel/expire/pago), exactamente una vez porque la
    transición de status es única. El descuento físico de `stock` sigue
    siendo una sola vez, en mark_order_paid.
    """
    products    =   {
        product.pk: product
        for product in (Product.objects
            .select_for_update()
            .filter(store = store, pk__in = list(merged.keys()), is_active = True)
            .order_by('pk'))
    }
    missing     =   [pid for pid in merged if pid not in products]
    if missing:
        raise serializers.ValidationError({'items': f'Producto(s) no disponible(s): {", ".join(str(p) for p in missing)}.'})
    #Unidades ya comprometidas por pedidos pendientes de pago (reserva
    #blanda — solo para productos con control de stock).
    controlled  =   [pid for pid, product in products.items() if product.stock is not None]
    claimed     =   {}
    if controlled:
        for row in (OrderItem.objects
                .filter(product_id__in = controlled, order__status = Order.Status.PENDING_PAYMENT)
                .values('product_id')
                .annotate(total = Sum('qty'))):
            claimed[row['product_id']]  =   row['total'] or 0
    has_exclusive   =   has_exclusive_access(customer, store)
    lines           =   []
    for pid, qty in merged.items():
        product =   products[pid]
        if product.is_exclusive and not has_exclusive:
            raise serializers.ValidationError({'items': f'"{product.name}" es exclusivo para miembros de la tienda.'})
        if product.stock is not None:
            available   =   product.stock - claimed.get(pid, 0)
            if qty > available:
                raise serializers.ValidationError({'items': f'Stock insuficiente de "{product.name}": quedan {max(available, 0)} unidad(es), pediste {qty}.'})
        lines.append({'product': product, 'qty': qty})
    return lines


def _price_lines(lines, store, customer):
    """
    Precios server-side por línea: oferta efectiva de catálogo
    (effective_pricing_of sobre los descuentos vigentes) y encima el %
    de membresía por unidad. Devuelve (priced, subtotal, discount_total)
    donde priced = [{product, qty, list_price, unit_price, line_total}].
    """
    discounts       =   running_discounts_of(store)
    member_percent  =   member_discount_percent(customer, store)
    priced          =   []
    subtotal        =   Decimal('0.00')
    discount_total  =   Decimal('0.00')
    for line in lines:
        product     =   line['product']
        qty         =   line['qty']
        offer, _    =   effective_pricing_of(product, discounts)
        base        =   offer if offer is not None else product.price
        unit        =   apply_member_discount(base, member_percent) if base is not None else Decimal('0.00')
        line_total  =   (unit * qty).quantize(Decimal('0.01'))
        list_total  =   ((product.price or Decimal('0')) * qty).quantize(Decimal('0.01'))
        priced.append({
            'product'       :   product,
            'qty'           :   qty,
            'list_price'    :   product.price or Decimal('0.00'),
            'unit_price'    :   unit,
            'line_total'    :   line_total,
        })
        subtotal        +=  line_total
        discount_total  +=  max(Decimal('0.00'), list_total - line_total)
    return priced, subtotal.quantize(Decimal('0.01')), discount_total.quantize(Decimal('0.01'))


def create_order(*, store, customer, items = None, address = None, shipping_method = 'home',
                 payment_method = 'transfer', idempotency_key = '', cart = None):
    """
    Crea el pedido del comprador en `store`. Devuelve (order, created):
    `created=False` cuando la idempotency_key ya existía (se devuelve el
    pedido original — el retry nunca duplica).

    Lanza serializers.ValidationError (→400) por items/pago/dirección/
    stock/exclusividad inválidos.
    """
    method      =   str(payment_method or '').strip().lower()
    if method not in Order.PaymentMethod.values:
        raise serializers.ValidationError({'payment_method': 'Método de pago inválido.'})
    ship        =   str(shipping_method or 'home').strip().lower()
    if ship not in Order.ShippingMethod.values:
        raise serializers.ValidationError({'shipping_method': 'Método de entrega inválido.'})
    key         =   str(idempotency_key or '').strip()[:80]
    #Idempotencia: replay → el MISMO pedido (200 en la vista, no 201).
    if key:
        existing    =   Order.objects.filter(store = store, idempotency_key = key).first()
        if existing is not None:
            return existing, False
    merged      =   _merge_lines(items, cart)
    #Validación de métodos ANTES del atomic (solo lecturas).
    if not _payment_method_allowed(store, method):
        raise serializers.ValidationError({'payment_method': 'Esta tienda no tiene habilitado ese método de pago.'})
    snapshot_addr   =   _require_home_address(address) if ship == Order.ShippingMethod.HOME else _address_snapshot(address)
    try:
        with transaction.atomic():
            #Serializa la numeración por tienda: dos checkouts simultáneos
            #no pueden leer el mismo last_number ni pisarse el unique.
            locked_store    =   Store.objects.select_for_update().get(pk = store.pk)
            lines           =   _resolve_lines(locked_store, customer, merged)
            priced, subtotal, discount_total   =   _price_lines(lines, locked_store, customer)
            config          =   _payment_config_of(locked_store)
            deadline_hours  =   (config.payment_deadline_hours if config and config.payment_deadline_hours else DEFAULT_DEADLINE_HOURS)
            #Envío a domicilio con tarifa fija: StoreShippingConfig.
            #home_price NULL = "a coordinar" (shipping_cost=0 y
            #shipping_priced=False — el 0 NO significa gratis). Pickup
            #siempre es sin cargo. El envío gratis por membresía
            #(`free_shipping_for`) queda para una regla futura.
            #Query aparte (no select_related): el join nullable del
            #OneToOne inverso rompe FOR UPDATE en Postgres.
            shipping_cfg    =   StoreShippingConfig.objects.filter(store_id = locked_store.pk).first()
            shipping_cost   =   Decimal('0.00')
            shipping_priced =   False
            if ship == Order.ShippingMethod.HOME and shipping_cfg is not None and shipping_cfg.home_price is not None:
                shipping_cost   =   shipping_cfg.home_price
                shipping_priced =   True
            sequence, _     =   OrderSequence.objects.get_or_create(store = locked_store)
            sequence.last_number    +=  1
            sequence.save(update_fields = ['last_number'])
            now             =   timezone.now()
            order           =   Order.objects.create(
                store               =   locked_store,
                number              =   sequence.last_number,
                tracking_token      =   new_tracking_token(),
                customer            =   customer,
                shipping_method     =   ship,
                payment_method      =   method,
                idempotency_key     =   key,
                shipping_address    =   snapshot_addr,
                subtotal            =   subtotal,
                discount_total      =   discount_total,
                shipping_cost       =   shipping_cost,
                shipping_priced     =   shipping_priced,
                total               =   (subtotal + shipping_cost).quantize(Decimal('0.01')),
                status              =   Order.Status.PENDING_PAYMENT,
                expires_at          =   now + timedelta(hours = deadline_hours),
                proof_required      =   bool(config.require_payment_proof) if config else False,
                **_customer_snapshot(customer),
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order       =   order,
                    product     =   line['product'],
                    name        =   line['product'].name[:160],
                    list_price  =   line['list_price'],
                    unit_price  =   line['unit_price'],
                    qty         =   line['qty'],
                    line_total  =   line['line_total'],
                    image_key   =   line['product'].image_key or '',
                )
                for line in priced
            ])
            append_event(order, 'created', actor = 'customer', status_to = Order.Status.PENDING_PAYMENT)
            #Carrito consumido en el mismo atomic: si el pedido commitea,
            #las líneas ya no están para un segundo checkout.
            if cart is not None:
                cart.items.all().delete()
            return order, True
    except IntegrityError:
        #Carrera de idempotencia: dos requests con la misma key pasaron el
        #pre-check — el unique (store, idempotency_key) cortó al segundo;
        #se devuelve el pedido ganador en vez de un 500.
        if key:
            existing    =   Order.objects.filter(store = store, idempotency_key = key).first()
            if existing is not None:
                return existing, False
        raise


#=========================================
# PAYMENT INSTRUCTIONS / PAYLOADS
#=========================================
def payment_instructions_of(order, store = None):
    """
    Instrucciones de pago del método elegido, armadas desde
    StorePaymentConfig (nunca hardcodeadas). Solo tiene sentido mientras
    el pedido está PENDING_PAYMENT — la vista decide cuándo incluirlas.
    """
    store   =   store or order.store
    config  =   getattr(store, 'payment_config', None)
    method  =   order.payment_method
    display =   (getattr(getattr(store, 'customization', None), 'display_name', '') or store.slug)
    total   =   f'${order.total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if method == Order.PaymentMethod.TRANSFER:
        return {
            'method'            :   'transfer',
            'alias'             :   config.transfer_alias if config else '',
            'holder'            :   config.transfer_holder if config else '',
            'instructions'      :   config.transfer_instructions if config else '',
            'deadline_hours'    :   config.payment_deadline_hours if config else DEFAULT_DEADLINE_HOURS,
        }
    if method == Order.PaymentMethod.WHATSAPP:
        raw_number =   (config.whatsapp_number if config else '') or (getattr(getattr(store, 'customization', None), 'whatsapp', '') or '')
        digits      =   ''.join(ch for ch in str(raw_number) if ch.isdigit())
        message     =   f'Hola {display}, te escribo por el pedido {order.code} — quiero coordinar el pago de {total}.'
        return {
            'method'            :   'whatsapp',
            'number'            :   digits,
            'url'               :   f'https://wa.me/{digits}?text={quote(message)}' if digits else '',
            'instructions'      :   config.transfer_instructions if config else '',
            'deadline_hours'    :   config.payment_deadline_hours if config else DEFAULT_DEADLINE_HOURS,
        }
    if method == Order.PaymentMethod.CASH:
        return {
            'method'            :   'cash',
            'instructions'      :   'Coordiná el pago en efectivo con el comercio.',
            'deadline_hours'    :   config.payment_deadline_hours if config else DEFAULT_DEADLINE_HOURS,
        }
    #MP: el cobro lo inicia el comprador contra la preferencia del
    #vendedor (track C) — se expone el path del endpoint, no montos.
    return {
        'method'            :   'mp',
        'instructions'      :   'Pagá con Mercado Pago desde el botón de pago.',
        'pay_path'          :   f'/api/stores/public/{store.slug}/orders/{order.tracking_token}/pay/',
        'deadline_hours'    :   config.payment_deadline_hours if config else DEFAULT_DEADLINE_HOURS,
    }


def _item_public(item):
    """Línea del pedido para la API pública (snapshot, sin ids internos)."""
    from StoreApp.domains.stores.services.storage import object_url
    return {
        'name'          :   item.name,
        'qty'           :   item.qty,
        'unit_price'    :   str(item.unit_price),
        'list_price'    :   str(item.list_price),
        'line_total'    :   str(item.line_total),
        'image'         :   object_url(item.image_key),
    }


def order_public_payload(order, store = None):
    """
    Respuesta de creación/idempotencia: lo mínimo para que el front
    muestre "pedido creado" + cómo pagar + link de seguimiento.
    NUNCA expone el id numérico (anti-IDOR: solo tracking_token).
    """
    store   =   store or order.store
    payload =   {
        'tracking_token'    :   order.tracking_token,
        'number'            :   order.number,
        'code'              :   order.code,
        'status'            :   order.status,
        'payment_method'    :   order.payment_method,
        'shipping_method'   :   order.shipping_method,
        #Envío a domicilio sin tarifa fija se coordina por WhatsApp:
        #shipping_cost=0 NO significa "gratis" — shipping_note le da al
        #front el texto listo para mostrar "A coordinar" en
        #tracking/recibo sin adivinar la semántica del 0. None cuando el
        #envío se cobró con precio fijo (incl. $0 = gratis) y en pickup
        #(retiro sin cargo).
        'shipping_priced'   :   order.shipping_priced,
        'shipping_note'     :   'A coordinar' if (order.shipping_method == Order.ShippingMethod.HOME and not order.shipping_priced) else None,
        'subtotal'          :   str(order.subtotal),
        'discount_total'    :   str(order.discount_total),
        'shipping_cost'     :   str(order.shipping_cost),
        'total'             :   str(order.total),
        'expires_at'        :   order.expires_at.isoformat() if order.expires_at else None,
        'proof_required'    :   order.proof_required,
        'proof_uploaded'    :   hasattr(order, 'proof'),
        'customer_first_name': order.customer_first_name,
        'created_at'        :   order.created_at.isoformat() if order.created_at else None,
        'items'             :   [_item_public(item) for item in order.items.all()],
    }
    if order.status == Order.Status.PENDING_PAYMENT:
        payload['payment_instructions']   =   payment_instructions_of(order, store)
    return payload


def order_tracking_payload(order):
    """
    Seguimiento público por tracking_token: estado + timeline de eventos
    + totales + instrucciones si sigue pendiente de pago. PII mínima:
    solo el nombre del comprador y su dirección de envío (es SUYA — el
    token es la credencial); email/teléfono/documento NUNCA salen.
    """
    store   =   order.store
    payload =   order_public_payload(order, store)
    payload['events']   =   [
        {
            'kind'          :   event.kind,
            'status_from'   :   event.status_from,
            'status_to'     :   event.status_to,
            'created_at'    :   event.created_at.isoformat() if event.created_at else None,
        }
        for event in order.events.all()[:50]
    ]
    payload['shipping_address'] =   order.shipping_address or {}
    payload['invoice_ref']       =   order.invoice_ref or None
    payload['paid_at']           =   order.paid_at.isoformat() if order.paid_at else None
    return payload


def build_receipt_payload(order):
    """
    Datos para el comprobante "NO FISCAL" que arma el front (el PDF no
    se genera en backend — decisión: el front lo renderiza). Incluye
    los datos fiscales del VENDEDOR (StoreFiscalProfile), items con
    snapshot, totales y la leyenda legal.
    """
    store           =   order.store
    profile         =   getattr(store, 'fiscal_profile', None)
    from StoreApp.domains.stores.models import StoreFiscalProfile
    tax_labels      =   dict(StoreFiscalProfile.TAX_CONDITION)
    seller          =   {
        'legal_name'        :   profile.legal_name if profile else '',
        'tax_condition'     :   profile.tax_condition if profile else '',
        'tax_condition_label': tax_labels.get(profile.tax_condition if profile else '', ''),
        'cuit'              :   profile.cuit if profile else '',
        'fiscal_address'    :   profile.fiscal_address if profile else '',
        'point_of_sale'     :   profile.point_of_sale if profile else '',
        'store_name'        :   getattr(getattr(store, 'customization', None), 'display_name', '') or store.slug,
    }
    return {
        'kind'              :   'no_fiscal',
        'seller'            :   seller,
        'order'             :   {
            'code'          :   order.code,
            'status'        :   order.status,
            'created_at'    :   order.created_at.isoformat() if order.created_at else None,
            'shipping_method': order.shipping_method,
            #Mismo criterio que order_public_payload: el 0 de envío a
            #domicilio sin tarifa fija es "a coordinar", no "gratis".
            'shipping_priced': order.shipping_priced,
            'shipping_note' :   'A coordinar' if (order.shipping_method == Order.ShippingMethod.HOME and not order.shipping_priced) else None,
        },
        #PII mínima (misma política que order_tracking_payload): email,
        #documento y apellido NUNCA salen por la API pública — el
        #tracking_token es credencial de seguimiento, no de identidad.
        'customer'          :   {
            'first_name'        :   order.customer_first_name,
        },
        'shipping_address'  :   order.shipping_address or {},
        'items'             :   [_item_public(item) for item in order.items.all()],
        'totals'            :   {
            'subtotal'          :   str(order.subtotal),
            'discount_total'    :   str(order.discount_total),
            'shipping_cost'     :   str(order.shipping_cost),
            'total'             :   str(order.total),
        },
        'invoice_ref'       :   order.invoice_ref or None,
        'legend'            :   'DOCUMENTO NO FISCAL — El comprobante fiscal autorizado lo emite el comercio.',
    }
