"""
Servicios del dominio cart: resolución de la tienda vendible, alta/
actualización/baja de items y serialización del carrito con precios
SIEMPRE del lado del servidor.

Precios: nunca se confía en montos del cliente ni se guardan snapshots
en el carrito — cada lectura recalcula `effective_pricing_of(product,
running_discounts_of(store))` (oferta manual vs mejor descuento vigente
del catálogo) y encima aplica `member_discount_percent(customer, store)`
(track D, tolerante: sin módulo = 0%). Es la MISMA composición que usa
orders.services.checkout.create_order para cobrar — carrito y pedido
muestran el mismo número.
"""
import logging
from decimal import Decimal

from rest_framework import serializers

from StoreApp.domains.cart.models import Cart, CartItem
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
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services.commerce import orders_enabled
from StoreApp.domains.stores.services.storage import object_url

logger  =   logging.getLogger(__name__)
#=========================================
# CONSTANTS
#=========================================
MAX_QTY                 =   100     # tope razonable por línea (anti-abuso)
#=========================================
# HELPERS
#=========================================
def customer_of(request):
    """
    Customer autenticado del request. La auth de compradores (track A)
    setea `request.customer` vía CustomerJWTAuthentication; como fallback
    se acepta `request.user` si ES un Customer (force_authenticate en
    tests / auths que devuelven el modelo como user).
    """
    customer    =   getattr(request, 'customer', None)
    if customer is not None:
        return customer
    user        =   getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    try:
        from StoreApp.domains.customers.models import Customer
    except ImportError:
        return None
    return user if isinstance(user, Customer) else None


def sellable_store(slug):
    """
    Tienda que puede vender online AHORA: publicada, no bloqueada y con
    `orders_enabled` (ecommerce_enabled + perfil fiscal completo — el
    gate único de services.commerce). Devuelve la instancia con las
    relaciones del gate ya cargadas, o None → la vista responde 404
    (misma política de ocultamiento que el resto de la API pública).
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
    if store is None or not orders_enabled(store):
        return None
    return store


def get_or_create_cart(customer, store):
    """Carrito del comprador en ESA tienda (unique customer+store)."""
    cart, _created  =   Cart.objects.get_or_create(customer = customer, store = store)
    return cart


def _qty_or_error(qty):
    try:
        qty =   int(qty)
    except (TypeError, ValueError):
        raise serializers.ValidationError({'qty': f'La cantidad tiene que ser un entero entre 1 y {MAX_QTY}.'})
    if qty < 1 or qty > MAX_QTY:
        raise serializers.ValidationError({'qty': f'La cantidad tiene que ser un entero entre 1 y {MAX_QTY}.'})
    return qty


def purchasable_product(store, product_id, customer = None):
    """
    Producto comprable de ESTA tienda: existe, is_active y —si es
    exclusivo— el comprador tiene acceso de membresía (track D,
    tolerante). Lanza ValidationError es-AR; la vista la traduce a 400.
    """
    try:
        product_id  =   int(product_id)
    except (TypeError, ValueError):
        raise serializers.ValidationError({'product_id': 'Producto inválido.'})
    product =   Product.objects.filter(store = store, pk = product_id, is_active = True).first()
    if product is None:
        raise serializers.ValidationError({'product_id': 'El producto no existe o no está disponible.'})
    if product.is_exclusive and not has_exclusive_access(customer, store):
        raise serializers.ValidationError({'product_id': 'Este producto es exclusivo para miembros de la tienda.'})
    return product


def _check_stock(product, qty, *, extra_qty = 0):
    """
    Valida stock trackeado (stock NULL = ilimitado). `extra_qty` permite
    validar el total resultante al editar una línea existente.
    Lanza ValidationError si no alcanza — el carrito NO reserva stock,
    esta es solo una verificación de de cara al checkout.
    """
    if product.stock is None:
        return
    if qty + extra_qty > product.stock:
        raise serializers.ValidationError({'qty': f'Stock insuficiente: quedan {product.stock} unidad(es) de "{product.name}".'})


def add_item(cart, product, qty):
    """
    Upsert de la línea (cart, product): si ya existía, qty se REEMPLAZA
    (idempotente — un retry no infla la cantidad). Valida tope y stock.
    """
    qty         =   _qty_or_error(qty)
    _check_stock(product, qty)
    item, _created  =   CartItem.objects.get_or_create(
        cart    =   cart,
        product =   product,
        defaults=   {'qty': qty},
    )
    if not _created and item.qty != qty:
        item.qty     =   qty
        item.save(update_fields = ['qty'])
    return item


def update_item(cart, item_id, qty):
    """Cambia la cantidad de una línea del carrito (qty>0; para borrar, DELETE)."""
    item    =   CartItem.objects.filter(cart = cart, pk = item_id).select_related('product').first()
    if item is None:
        raise serializers.ValidationError({'item': 'El item no está en tu carrito.'})
    qty     =   _qty_or_error(qty)
    #Al subir qty hay que mirar el stock completo resultante; al bajarla
    #siempre entra (stock no reservado: otro pudo comprar mientras tanto,
    #el checkout revalida igual).
    if qty > item.qty:
        _check_stock(item.product, qty)
    item.qty =   qty
    item.save(update_fields = ['qty'])
    return item


def remove_item(cart, item_id):
    deleted, _  =   CartItem.objects.filter(cart = cart, pk = item_id).delete()
    if not deleted:
        raise serializers.ValidationError({'item': 'El item no está en tu carrito.'})


def clear_cart(cart):
    """Vacía el carrito (DELETE /items/ sin id). Devuelve las líneas borradas."""
    deleted, _  =   cart.items.all().delete()
    return deleted


#=========================================
# PRICING (siempre server-side)
#=========================================
def _unit_price(product, discounts, member_percent):
    """
    Precio unitario final que pagaría el comprador: oferta efectiva del
    catálogo (manual vs mejor descuento vigente) y encima el % de
    membresía. Misma composición que orders.services.checkout.
    """
    offer, _discount  =   effective_pricing_of(product, discounts)
    base                =   offer if offer is not None else product.price
    if base is None:
        return None
    return apply_member_discount(base, member_percent)


def cart_payload(cart, customer = None):
    """
    Carrito serializado con precios resueltos al leer. Una sola pasada
    de discounts por request (running_discounts_of ya viene con la M2M
    prefetcheada). Items con producto desactivado/exclusivo-sin-acceso
    viajan con `purchasable=False` + motivo — el checkout los rechaza
    igual, pero el front puede avisar antes.
    """
    store           =   cart.store
    discounts       =   running_discounts_of(store)
    member_percent  =   member_discount_percent(customer, store) if customer is not None else 0
    has_exclusive   =   has_exclusive_access(customer, store) if customer is not None else False
    items           =   []
    total_qty       =   0
    items_total     =   Decimal('0.00')
    #Una sola query para las líneas con producto (select_related evita
    #N+1 al serializar nombre/precio/imagen).
    for item in cart.items.select_related('product').all():
        product =   item.product
        unit    =   _unit_price(product, discounts, member_percent)
        line    =   (unit * item.qty).quantize(Decimal('0.01')) if unit is not None else Decimal('0.00')
        purchasable, reason  =   _purchasable(product, has_exclusive)
        items.append({
            'id'            :   item.pk,
            'product_id'    :   product.pk,
            'name'          :   product.name,
            'qty'           :   item.qty,
            'list_price'    :   str(product.price),
            'unit_price'    :   str(unit) if unit is not None else None,
            'line_total'    :   str(line),
            'image'         :   object_url(product.image_key),
            'stock'         :   product.stock,
            'purchasable'   :   purchasable,
            'unavailable_reason': reason,
        })
        if purchasable and unit is not None:
            items_total +=  line
        total_qty   +=  item.qty
    return {
        'store'                     :   store.slug,
        'items'                     :   items,
        'item_count'                :   total_qty,
        'items_total'               :   str(items_total.quantize(Decimal('0.01'))),
        'member_discount_percent'   :   member_percent,
    }


def _purchasable(product, has_exclusive):
    """(bool, motivo) de si la línea puede entrar a un pedido hoy."""
    if not product.is_active:
        return False, 'inactive'
    if product.is_exclusive and not has_exclusive:
        return False, 'exclusive'
    return True, ''
