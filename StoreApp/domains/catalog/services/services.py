from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.utils import timezone

from StoreApp.domains.stores.services import plan_benefits_of

"""

Servicios del dominio Catalog.
Los cupos salen de los beneficios del plan vigente
(SuscriptionApp/benefits): sin suscripción activa no hay catálogo.

"""
#=========================================
# PRODUCTS LIMIT (cupos max_products del plan)
#=========================================
def products_limit(profile):
    """Tope de productos del plan vigente. None = ilimitado, 0 = sin catálogo."""
    benefits        =   plan_benefits_of(profile)
    if 'max_products' not in benefits:
        return 0
    return benefits['max_products']
def can_add_product(store):
    """True si el plan vigente admite un producto más en la tienda."""
    limit           =   products_limit(store.user)
    if limit is None:
        return True
    return store.products.count() < limit
#=========================================
# CATALOG ENABLED (flag has_public_link del plan)
#=========================================
def catalog_enabled(profile):
    """El catálogo se edita solo con suscripción activa (has_public_link)."""
    return 'has_public_link' in plan_benefits_of(profile)
#=========================================
# DISCOUNTS (descuentos programados: vigencia evaluada al leer, nunca se
# materializa en offer_price — sin worker ni tarea cron)
#=========================================
def running_discounts_of(store, moment = None):
    """
    Descuentos vigentes de la tienda en `moment` (ahora por defecto):
    is_active y dentro de la ventana [starts_at, ends_at). Devuelve una
    lista con la M2M de productos ya resuelta (prefetch) — evaluar el
    alcance no vuelve a pegarle a la base.
    Los descuentos son premium ('has_discounts'): sin el flag la lista
    sale vacía — la tienda que baja de plan deja de descontar en la web
    pública y en el panel aunque el descuento quede guardado.
    Un descuento atado a una campaña solo descuenta mientras la campaña
    esté vigente (su ventana anual recurrente), además de la propia del
    descuento.
    """
    from StoreApp.domains.catalog.models import Discount
    if not plan_benefits_of(store.user).get('has_discounts'):
        return []
    moment      =   moment or timezone.now()
    return [
        discount
        for discount in (
            Discount.objects.filter(store = store, is_active = True, starts_at__lte = moment)
            .filter(Q(ends_at__isnull = True) | Q(ends_at__gt = moment))
            .select_related('category', 'brand', 'campaign')
            .prefetch_related('products')
        )
        if discount.campaign_id is None or discount.campaign.is_running(moment)
    ]
def discount_covers(discount, product):
    """True si el producto entra en el alcance del descuento."""
    from StoreApp.domains.catalog.models import Discount
    scope   =   discount.scope
    if scope == Discount.Scope.ALL:
        return True
    if scope == Discount.Scope.CATEGORY:
        return discount.category_id is not None and product.category_id == discount.category_id
    if scope == Discount.Scope.BRAND:
        return discount.brand_id is not None and product.brand_id == discount.brand_id
    return any(item.id == product.id for item in discount.products.all())
def manual_offer_of(product):
    """
    Oferta manual vigente del producto: offer_price cargado y por debajo
    del precio de lista (misma regla que effective_pricing_of). None si
    no hay o el precio no está cargado.
    """
    offer   =   product.offer_price
    if offer is None or product.price is None:
        return None
    return offer if offer < product.price else None
def winning_discount_of(product, discounts):
    """
    (precio, descuento) del descuento vigente que más baja el producto.
    (None, None) si ninguno lo cubre, el precio de lista es 0 (un 0%
    real no es oferta) o el producto ya tiene oferta manual: un descuento
    programado nunca se monta encima de un precio ya bajado a mano —
    en un alcance amplio (categoría, marca, todo el catálogo) el producto
    con oferta simplemente se salta.
    """
    best_price, best_discount   =   None, None
    if product.price is None or product.price <= 0:
        return best_price, best_discount
    if manual_offer_of(product) is not None:
        return best_price, best_discount
    for discount in discounts:
        if not discount_covers(discount, product):
            continue
        price   =   (product.price * Decimal(100 - discount.percent) / Decimal(100)).quantize(
            Decimal('0.01'), rounding = ROUND_HALF_UP)
        if best_price is None or price < best_price:
            best_price, best_discount   =   price, discount
    return best_price, best_discount
def discount_price_of(product, discounts):
    """
    Mejor precio que deja algún descuento vigente sobre el producto
    (el más bajo si se solapan). None si ninguno lo cubre.
    """
    return winning_discount_of(product, discounts)[0]
def effective_pricing_of(product, discounts):
    """
    (oferta, descuento) efectivos del producto: la oferta es la menor
    entre la manual (offer_price) y el mejor descuento vigente — solo
    cuenta si queda por debajo del precio de lista. El descuento solo
    "firma" la oferta cuando realmente gana: si la manual queda más baja,
    el producto no lleva su nombre ni su fecha (sería engañar al público).
    """
    d_price, d_discount =   winning_discount_of(product, discounts)
    manual              =   product.offer_price
    if manual is not None and (product.price is None or manual >= product.price):
        manual          =   None
    discount_wins       =   d_price is not None and (manual is None or d_price < manual)
    return (d_price if discount_wins else manual, d_discount if discount_wins else None)
def effective_offer_of(product, discounts):
    """
    Oferta efectiva del producto: la menor entre la oferta manual
    (offer_price) y el mejor descuento vigente — misma regla que la web
    pública (solo cuenta si queda por debajo del precio de lista).
    """
    return effective_pricing_of(product, discounts)[0]
