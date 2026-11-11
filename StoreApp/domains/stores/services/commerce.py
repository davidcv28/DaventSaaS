"""
Reglas comerciales compartidas del e-commerce de tiendas: validación
de datos fiscales y el interruptor efectivo de venta online.
"""
#=========================================
# CUIT (dígito verificador argentino — 11 dígitos)
#=========================================
def cuit_is_valid(cuit):
    """
    True si `cuit` (11 dígitos, con o sin guiones) pasa el dígito
    verificador módulo 11. No valida tipo de persona ni existencia en
    AFIP — eso lo resuelve el vendedor con su constancia.
    """
    digits  =   ''.join(ch for ch in (cuit or '') if ch.isdigit())
    if len(digits) != 11:
        return False
    def _check(base):
        weights =   [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        total   =   sum(int(digit) * weight for digit, weight in zip(base, weights))
        mod     =   11 - (total % 11)
        return 0 if mod == 11 else 9 if mod == 10 else mod
    return _check(digits[:10]) == int(digits[10])
#=========================================
# PLAN GATES (beneficios del plan vigente del dueño)
#=========================================
def store_has_ecommerce(store):
    """
    True si el plan vigente del dueño incluye `has_ecommerce` — toda la
    superficie de venta online (panel de pedidos/ventas/cobros, membresías,
    legal, soporte, checkout y carrito) cuelga de este flag.
    """
    from StoreApp.domains.stores.services.services import profile_has_benefit
    return profile_has_benefit(store.user, 'has_ecommerce')


def store_has_customer_auth(store):
    """True si el plan del dueño habilita cuentas de comprador (has_customer_auth)."""
    from StoreApp.domains.stores.services.services import profile_has_benefit
    return profile_has_benefit(store.user, 'has_customer_auth')


def store_has_own_storage(store):
    """True si el plan del dueño habilita el bucket R2 propio (has_own_storage)."""
    from StoreApp.domains.stores.services.services import profile_has_benefit
    return profile_has_benefit(store.user, 'has_own_storage')
#=========================================
# ORDERS ENABLED (regla efectiva de venta online)
#=========================================
def orders_enabled(store):
    """
    True solo si la tienda puede vender online: `ecommerce_enabled` en
    la customización Y perfil fiscal completo (Fase 0 legal — sin datos
    fiscales del vendedor no se habilita el checkout) Y el plan vigente
    del dueño con `has_ecommerce` — un plan sin el beneficio deja de
    vender aunque el toggle y el fiscal sigan OK (downgrade/vencimiento).
    Los endpoints de pedido y el payload público la usan como gate único.
    """
    customization    =   getattr(store, 'customization', None)
    if customization is None or not customization.ecommerce_enabled:
        return False
    profile          =   getattr(store, 'fiscal_profile', None)
    if not (profile and profile.is_complete):
        return False
    return store_has_ecommerce(store)
