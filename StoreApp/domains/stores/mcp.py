"""
Tools MCP del dominio stores — solo la tienda del usuario en sesión.
"""

from datetime import timedelta

from django.utils import timezone

TOOLS   =   [
    {
        'name'          :   'my_store_summary',
        'description'   :   'Resumen de tu tienda: slug, publicación y conteos de productos/categorías/marcas.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
    {
        'name'          :   'my_store_visits',
        'description'   :   'Visitas de tu web pública en los últimos N días (máx 90): total y desglose diario.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {'days': {'type': 'integer', 'minimum': 1, 'maximum': 90, 'default': 30}},
        },
    },
]


def _store_of(user):
    return getattr(getattr(user, 'profile', None), 'store', None)


def my_store_summary(user) -> dict:
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


def my_store_visits(user, days : int = 30) -> dict:
    store   =   _store_of(user)
    if store is None:
        return {'visits': None}
    days    =   max(1, min(int(days or 30), 90))
    since   =   timezone.now().date() - timedelta(days = days - 1)
    rows    =   list(
        store.daily_visits.filter(date__gte = since).order_by('-date').values('date', 'count')
    )
    return {
        'visits': {
            'days'      :   days,
            'total'     :   sum(r['count'] for r in rows),
            'by_day'    :   [{'date': r['date'].isoformat(), 'count': r['count']} for r in rows],
        },
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'my_store_summary':
        return my_store_summary(user)
    if name == 'my_store_visits':
        return my_store_visits(user, days = args.get('days', 30))
    raise ValueError(f'Herramienta desconocida en stores: {name}')
