from decimal import Decimal, ROUND_HALF_UP

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
    """
    from StoreApp.domains.catalog.models import Discount
    moment      =   moment or timezone.now()
    return list(
        Discount.objects.filter(store = store, is_active = True, starts_at__lte = moment)
        .filter(Q(ends_at__isnull = True) | Q(ends_at__gt = moment))
        .select_related('category', 'brand')
        .prefetch_related('products')
    )
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
def discount_price_of(product, discounts):
    """
    Mejor precio que deja algún descuento vigente sobre el producto
    (el más bajo si se solapan). None si ninguno lo cubre o el precio
    de lista es 0 (un 0% real no es oferta).
    """
    if product.price is None or product.price <= 0:
        return None
    best    =   None
    for discount in discounts:
        if not discount_covers(discount, product):
            continue
        price   =   (product.price * Decimal(100 - discount.percent) / Decimal(100)).quantize(
            Decimal('0.01'), rounding = ROUND_HALF_UP)
        if best is None or price < best:
            best    =   price
    return best
def effective_offer_of(product, discounts):
    """
    Oferta efectiva del producto: la menor entre la oferta manual
    (offer_price) y el mejor descuento vigente — misma regla que la web
    pública (solo cuenta si queda por debajo del precio de lista).
    """
    offers  =   [
        offer for offer in (product.offer_price, discount_price_of(product, discounts))
        if offer is not None and product.price is not None and offer < product.price
    ]
    return min(offers) if offers else None
