"""
Sitemaps del sitio público: páginas de marketing (landing, registro, legales)
más la home de cada tienda publicada (/<slug>). Las URLs internas (dashboard,
login, admin) quedan fuera — robots.txt las desalienta y los headers
X-Robots-Tag las desindexan si igual se filtran.
"""
from datetime import timedelta

from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.utils import timezone

from AdminApp.domains.suscriptions.models import Suscription
from StoreApp.domains.stores.models.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

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


def _public_store_user_ids():
    """
    user_id de los perfiles cuya web pública es visible: suscripción con
    acceso vigente (mismo criterio que Suscription.grants_access: activa,
    end_date presente y ahora <= end_date + gracia si hay débito automático)
    en un plan que habilita 'has_public_link'. Set-based a propósito —
    el sitemap no puede pagar profile_has_benefit por tienda (N+1).
    """
    now         =   timezone.now()
    grace       =   timedelta(days = Suscription.GRACE_DAYS)
    plan_ids    =   PlanBenefit.objects.filter(
        benefit__code =   'has_public_link',
    ).filter(
        Q(benefit__kind = Benefit.FLAG, enabled = True) |
        Q(benefit__kind = Benefit.LIMIT, value__isnull = True) |
        Q(benefit__kind = Benefit.LIMIT, value__gt = 0)
    ).values('plan_id')
    return Suscription.objects.filter(
        status          =   Suscription.STATUS_ACTIVE,
        end_date__isnull =   False,
    ).filter(
        Q(end_date__gte = now) |
        Q(auto_renew = True, end_date__gte = now - grace)
    ).filter(
        plan_suscription_id__in =   plan_ids,
    ).values('user_id')


class StoreSitemap(Sitemap):
    """Home pública de cada web de cliente: solo tiendas publicadas, no
    bloqueadas Y con acceso público vigente — el mismo gate efectivo del
    endpoint público (is_published + is_blocked + has_public_link), sin
    el cual el sitemap anunciaba a crawlers tiendas que responden 404."""
    changefreq = 'weekly'
    priority = 0.6
    limit = 5000

    def items(self):
        return Store.objects.filter(
            is_published = True, is_blocked = False,
            user_id__in  = _public_store_user_ids(),
        ).only('slug', 'created_at').order_by('pk')

    def location(self, store):
        return f'/{store.slug}'

    def lastmod(self, store):
        return store.created_at
