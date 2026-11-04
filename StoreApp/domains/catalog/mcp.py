"""
Tools MCP del dominio catalog — solo el catálogo de la tienda del
usuario en sesión. Nunca consulta productos de otras tiendas.
"""

from django.db.models import Q

from McpApp.domains.skills.services.services import clamp_limit

TOOLS   =   [
    {
        'name'          :   'search_my_products',
        'description'   :   'Busca productos SOLO en tu catálogo (nombre/descripción). Devuelve nombre, precio, oferta, categoría, marca y visibilidad.',
        'inputSchema'   :   {
            'type'      :   'object',
            'properties':   {
                'query' :   {'type': 'string', 'description': 'Texto a buscar en nombre/descripción.'},
                'limit' :   {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 10},
            },
        },
    },
    {
        'name'          :   'list_my_categories',
        'description'   :   'Tus categorías con la cantidad de productos de cada una.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
    {
        'name'          :   'list_my_brands',
        'description'   :   'Tus marcas con la cantidad de productos de cada una.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
]


def _store_of(user):
    return getattr(getattr(user, 'profile', None), 'store', None)


def search_my_products(user, query : str = '', limit : int = 10) -> dict:
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


def list_my_categories(user) -> dict:
    store   =   _store_of(user)
    if store is None:
        return {'categories': []}
    return {
        'categories': [
            {'name': c.name, 'products': c.products.count()}
            for c in store.categories.prefetch_related('products')
        ],
    }


def list_my_brands(user) -> dict:
    store   =   _store_of(user)
    if store is None:
        return {'brands': []}
    return {
        'brands': [
            {'name': b.name, 'products': b.products.count()}
            for b in store.brands.prefetch_related('products')
        ],
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'search_my_products':
        return search_my_products(user, query = args.get('query', ''), limit = args.get('limit', 10))
    if name == 'list_my_categories':
        return list_my_categories(user)
    if name == 'list_my_brands':
        return list_my_brands(user)
    raise ValueError(f'Herramienta desconocida en catalog: {name}')
