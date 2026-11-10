"""
Beneficios de membresía del comprador en UNA tienda (track D —
desarrollo en paralelo).

IMPORTACIÓN TOLERANTE (contrato): `StoreApp.domains.memberships.services
.benefits` expone `member_discount_percent(customer, store) -> int`,
`has_exclusive_access(customer, store) -> bool`,
`free_shipping_for(customer, store) -> bool` y
`active_subscription_of(customer, store)`. Mientras el track D no
aterrice (o si el módulo falta/rompe), ESTE dominio funciona igual:
la ausencia se trata como "sin beneficios" — descuento 0%, sin
acceso a exclusivos y sin envío gratis por membresía.

Las llamadas al servicio de D van envueltas en try/except: un fallo de
su código NUNCA debe tumbar el carrito ni el checkout (se loguea y se
responde con el beneficio en su valor neutro).
"""
import logging

logger  =   logging.getLogger(__name__)

BENEFITS_MODULE_PATH    =   'StoreApp.domains.memberships.services.benefits'


def _benefits_module():
    """Import perezoso y tolerante: None si memberships aún no existe."""
    try:
        import importlib
        return importlib.import_module(BENEFITS_MODULE_PATH)
    except ImportError:
        return None


def _call(fn_name, customer, store, default):
    """
    Invoca `fn_name(customer, store)` del módulo de beneficios de D.
    Devuelve `default` si el módulo/función no existe o la llamada falla
    (beneficio neutro — nunca propaga la excepción al flujo de compra).
    """
    if customer is None:
        return default
    module  =   _benefits_module()
    fn      =   getattr(module, fn_name, None) if module is not None else None
    if fn is None:
        return default
    try:
        return fn(customer, store)
    except Exception:                                   # noqa: BLE001 — track D en desarrollo
        logger.warning('memberships.benefits.%s falló; se usa el valor neutro', fn_name, exc_info = True)
        return default


def member_discount_percent(customer, store):
    """
    % de descuento del plan vigente del comprador en esta tienda
    (0 si no hay membresía/beneficio). Acotado a [0, 99]: un 100%
    dejaría el pedido en $0 — casi seguro un error de configuración
    del dueño, no una promo válida.
    """
    try:
        value   =   int(_call('member_discount_percent', customer, store, 0) or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, min(99, value))


def has_exclusive_access(customer, store):
    """True si el comprador puede ver/comprar productos is_exclusive."""
    return bool(_call('has_exclusive_access', customer, store, False))


def free_shipping_for(customer, store):
    """True si la membresía del comprador regala el envío en esta tienda."""
    return bool(_call('free_shipping_for', customer, store, False))


def active_subscription_of(customer, store):
    """Suscripción vigente del comprador en la tienda (o None si D no está)."""
    return _call('active_subscription_of', customer, store, None)


def apply_member_discount(unit_price, percent):
    """
    Precio unitario tras el descuento de membresía: misma regla que el
    pedido (half-up a 2 decimales). `percent` ya viene acotado por
    member_discount_percent.
    """
    from decimal import ROUND_HALF_UP, Decimal
    if not percent:
        return unit_price
    return (unit_price * Decimal(100 - percent) / Decimal(100)).quantize(
        Decimal('0.01'), rounding = ROUND_HALF_UP)
