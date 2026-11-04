from django.contrib.auth.models import User
from django.db.models import Q

from McpApp.domains.skills.services.services import clamp_limit

"""
Herramientas MCP de USUARIO (datos del cliente en sesión).

Regla de seguridad: el `user` lo inyecta el transporte (request.user en
/api/mcp/); NUNCA llega en `arguments` — ninguna tool acepta user_id,
store_id ni slug ajenos, así un cliente no puede pivotear a datos de
otro. El servidor stdio no pasa user → estas tools quedan ciegas ahí.

Acceso: usuario autenticado con suscripción vigente NO trial
(básico/estándar/premium). Sin eso, ValueError (el endpoint lo expone
como error JSON-RPC -32602).
"""


def mcp_user_access(user : User | None) -> bool:
    if user is None or not user.is_authenticated:
        return False
    suscription =   getattr(getattr(user, 'profile', None), 'suscription', None)
    return bool(
        suscription
        and suscription.grants_access()
        and not suscription.plan_suscription.is_trial
    )


def _store_of(user : User):
    return getattr(getattr(user, 'profile', None), 'store', None)


#=========================================
# TOOLS (todas filtradas por la store del usuario en sesión)
#=========================================
def my_store_summary(user : User) -> dict:
    store   =   _store_of(user)
    if store is None:
        return {'store': None}
    return {
        'store': {
            'slug'              :   store.slug,
            'is_published'      :   store.is_published,
            'products_total'    :   store.products.count(),
            'products_active'   :   store.products.filter(is_active = True).count(),
            'categories'        :   store.categories.count(),
            'brands'            :   store.brands.count(),
        },
    }


def search_my_products(user : User, query : str = '', limit : int = 10) -> dict:
    from StoreApp.domains.catalog.models import Product
    store   =   _store_of(user)
    if store is None:
        return {'products': []}
    qs      =   Product.objects.filter(store = store).select_related('category', 'brand')
    terms   =   [t for t in (query or '').replace(',', ' ').split() if t]
    for term in terms[:6]:
        qs  =   qs.filter(Q(name__icontains = term) | Q(description__icontains = term))
    return {
        'products': [
            {
                'name'      :   p.name,
                'price'     :   str(p.price),
                'offer_price'   :   str(p.offer_price) if p.offer_price is not None else None,
                'category'  :   p.category.name if p.category else '',
                'brand'     :   p.brand.name if p.brand else '',
                'is_active' :   p.is_active,
            }
            for p in qs[:clamp_limit(limit)]
        ],
    }


def my_plan_summary(user : User) -> dict:
    suscription =   getattr(getattr(user, 'profile', None), 'suscription', None)
    if suscription is None:
        return {'plan': None}
    return {
        'plan': {
            'name'          :   suscription.plan_suscription.name,
            'price'         :   str(suscription.plan_suscription.price),
            'status'        :   suscription.status,
            'end_date'      :   suscription.end_date.isoformat() if suscription.end_date else None,
            'auto_renew'    :   suscription.auto_renew,
        },
    }


#=========================================
# SNAPSHOT PARA EL ASISTENTE (system prompt del bot)
#=========================================
def assistant_snapshot(user : User, query : str = '') -> str:
    """Resumen compacto de los datos del cliente en sesión para el prompt."""
    if not mcp_user_access(user):
        return ''
    lines   =   []
    plan    =   my_plan_summary(user)['plan']
    if plan:
        lines.append(f"Plan: {plan['name']} (${plan['price']}), estado {plan['status']}, vence {plan['end_date'] or '—'}.")
    store   =   my_store_summary(user)['store']
    if store:
        lines.append(
            f"Tienda: /{store['slug']} ({'publicada' if store['is_published'] else 'sin publicar'}), "
            f"{store['products_active']}/{store['products_total']} productos visibles, "
            f"{store['categories']} categorías, {store['brands']} marcas."
        )
        hits    =   search_my_products(user, query = query, limit = 5)['products']
        if hits:
            found   =   '; '.join(f"{h['name']} (${h['offer_price'] or h['price']})" for h in hits)
            lines.append(f'Productos que coinciden con el último mensaje: {found}.')
    return '\n'.join(lines)
