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
