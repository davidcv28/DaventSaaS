"""
Sitemaps del sitio público: páginas de marketing (landing, registro, legales)
más la home de cada tienda publicada (/<slug>). Las URLs internas (dashboard,
login, admin) quedan fuera — robots.txt las desalienta y los headers
X-Robots-Tag las desindexan si igual se filtran.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from StoreApp.domains.stores.models.models import Store

# Rutas públicas indexables de la SPA (espejo de frontend/src/router).
# login/forgot-password/dashboard/etc. se excluyen a propósito: no aportan
# a la búsqueda y consumirían crawl budget.
STATIC_URLS = [
    ('/', 'daily', 1.0),
    ('/register', 'weekly', 0.8),
    ('/acerca-de', 'monthly', 0.5),
    ('/terminos', 'yearly', 0.3),
    ('/denuncias', 'yearly', 0.3),
    ('/descargar', 'monthly', 0.4),
]


class StaticSitemap(Sitemap):
    """Páginas institucionales/marketing del dominio principal."""

    def items(self):
        return STATIC_URLS

    def location(self, item):
        return item[0]

    def changefreq(self, item):
        return item[1]

    def priority(self, item):
        return item[2]


class StoreSitemap(Sitemap):
    """Home pública de cada web de cliente: solo tiendas publicadas y no
    bloqueadas (las mismas reglas del endpoint público)."""
    changefreq = 'weekly'
    priority = 0.6
    limit = 5000

    def items(self):
        return Store.objects.filter(
            is_published=True, is_blocked=False,
        ).only('slug', 'created_at').order_by('pk')

    def location(self, store):
        return f'/{store.slug}'

    def lastmod(self, store):
        return store.created_at
