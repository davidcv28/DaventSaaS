from importlib import import_module

from django.contrib.auth.models import User

"""
Registro de tools MCP de USUARIO (datos del cliente en sesión).

Cada dominio declara sus tools en `<app>/domains/<dominio>/mcp.py`
(constante TOOLS + función call(name, args, user)). Este módulo es el
único que los conoce y los despacha: ni las views ni el servidor
FastMCP tocan la DB.

Regla de seguridad: el `user` lo inyecta el transporte (request.user en
/api/mcp/ o el Bearer JWT en fastmcp_server); NUNCA llega en
`arguments` — ninguna tool acepta user_id, store_id ni slug ajenos, así
un cliente no puede pivotear a datos de otro. El servidor stdio no pasa
user → estas tools quedan ciegas ahí.

Acceso: usuario autenticado con suscripción vigente NO trial
(básico/estándar/premium). Sin eso, ValueError (el endpoint lo expone
como error JSON-RPC -32602).
"""

DOMAIN_MODULES  =   [
    'AdminApp.domains.users.mcp',
    'AdminApp.domains.suscriptions.mcp',
    'AdminApp.domains.payments.mcp',
    'AdminApp.domains.invoices.mcp',
    'StoreApp.domains.stores.mcp',
    'StoreApp.domains.catalog.mcp',
]


def _domains() -> list:
    return [import_module(path) for path in DOMAIN_MODULES]


def user_tool_schemas() -> list[dict]:
    tools   =   []
    for domain in _domains():
        tools.extend(getattr(domain, 'TOOLS', []))
    return tools


def user_tool_names() -> set[str]:
    return {tool['name'] for tool in user_tool_schemas()}


def call_user_tool(name : str, args : dict, user) -> dict:
    for domain in _domains():
        if name in {tool['name'] for tool in getattr(domain, 'TOOLS', [])}:
            return domain.call(name, args, user)
    raise ValueError(f'Herramienta de usuario desconocida: {name}')


def mcp_user_access(user : User | None) -> bool:
    if user is None or not user.is_authenticated:
        return False
    suscription =   getattr(getattr(user, 'profile', None), 'suscription', None)
    return bool(
        suscription
        and suscription.grants_access()
        and not suscription.plan_suscription.is_trial
    )


#=========================================
# SNAPSHOT PARA EL ASISTENTE (system prompt del bot)
#=========================================
def assistant_snapshot(user : User, query : str = '') -> str:
    """Resumen compacto de los datos del cliente en sesión para el prompt."""
    if not mcp_user_access(user):
        return ''
    from AdminApp.domains.suscriptions.mcp import my_plan_summary
    from AdminApp.domains.users.mcp import my_profile
    from StoreApp.domains.catalog.mcp import search_my_products
    from StoreApp.domains.stores.mcp import my_store_summary, my_store_visits

    lines   =   []
    profile =   my_profile(user)['profile']
    if profile:
        verified    =   'email verificado' if profile['email_verified'] else 'email SIN verificar'
        lines.append(f"Cuenta: {profile['business_name'] or profile['username']} ({profile['email']}, {verified}).")
    plan    =   my_plan_summary(user)['plan']
    if plan:
        lines.append(f"Plan: {plan['name']} (${plan['price']}), estado {plan['status']}, vence {plan['end_date'] or '—'}.")
    store   =   my_store_summary(user)['store']
    if store:
        visits  =   (my_store_visits(user, days = 7)['visits'] or {}).get('total', 0)
        lines.append(
            f"Tienda: /{store['slug']} ({'publicada' if store['is_published'] else 'sin publicar'}), "
            f"{store['products_active']}/{store['products_total']} productos visibles, "
            f"{store['categories']} categorías, {store['brands']} marcas, {visits} visitas en 7 días."
        )
        hits    =   search_my_products(user, query = query, limit = 5)['products']
        if hits:
            found   =   '; '.join(f"{h['name']} (${h['offer_price'] or h['price']})" for h in hits)
            lines.append(f'Productos que coinciden con el último mensaje: {found}.')
    return '\n'.join(lines)
