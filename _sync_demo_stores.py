# Sync: copia las tiendas ilustrativas (demo_slug del catálogo de diseño)
# de la base local a Neon (prod). Idempotente: upsert por slug/nombre.
# Las tiendas demo quedan con suscripción activa sin vencimiento (año 2100)
# para que el "Ejemplo ilustrativo" del dashboard nunca las pierda.
#
# Uso: venv/Scripts/python.exe _sync_demo_stores.py [--dry-run] [slug ...]
import os, sys, copy
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django
django.setup()

import dj_database_url
from decouple import config
from django.conf import settings
from django.db.models import ForeignKey
from django.utils import timezone

from django.contrib.auth.models import User
from AdminApp.domains.users.models.models import UserProfile
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.catalog.models.models import Category, Product, Brand
from StoreApp.domains.services.models import StoreService

DRY = '--dry-run' in sys.argv
SLUGS = [a for a in sys.argv[1:] if not a.startswith('--')]
if not SLUGS:
    from StoreApp.domains.design.models import DesignPattern
    SLUGS = list(DesignPattern.objects.exclude(demo_slug = '').values_list('demo_slug', flat = True))

NEON = config('NEON_DATABASE_URL', default = '')
if not NEON:
    raise SystemExit('Falta NEON_DATABASE_URL en .env')
_neon = dict(settings.DATABASES['default'])
_neon.update(dj_database_url.parse(NEON, conn_max_age = 0))
settings.DATABASES['neon'] = _neon
REMOTE = 'neon'

import datetime
FOREVER = timezone.make_aware(datetime.datetime(2100, 1, 1))


def fields_of(obj, exclude = ()):
    """{campo: valor} sin PK ni FK (los FK se resuelven aparte)."""
    skip = {'id', *exclude}
    vals = {}
    for f in obj._meta.fields:
        if f.name in skip or isinstance(f, ForeignKey):
            continue
        vals[f.name] = copy.deepcopy(getattr(obj, f.name))
    return vals


def run():
    stores = Store.objects.filter(slug__in = SLUGS).select_related('user__user', 'customization')
    found = {s.slug: s for s in stores}
    missing = set(SLUGS) - set(found)
    if missing:
        print('NO están en local:', ', '.join(sorted(missing)))
    # El plan se resuelve EN Neon (un objeto de otra base no puede ser FK).
    plan = (SuscriptionPlan.objects.using(REMOTE).filter(name__icontains = 'premium').first()
            or SuscriptionPlan.objects.using(REMOTE).exclude(is_trial = True).first())
    print('plan demo:', plan.name if plan else 'NINGUNO')
    for slug, store in found.items():
        print(f'--- {slug} ---')
        if DRY:
            print('  dry-run')
            continue
        _store(store, plan)
    print('DONE')


def _store(store, plan):
    profile_src = store.user
    user_src = profile_src.user

    # ---- usuario + perfil ----
    user, _ = User.objects.using(REMOTE).get_or_create(
        username = user_src.username,
        defaults = {'email': user_src.email, 'password': user_src.password,
                    'is_active': True},
    )
    # conserva hash de password y activo
    changed = False
    if user.password != user_src.password:
        user.password = user_src.password; changed = True
    if not user.is_active:
        user.is_active = True; changed = True
    if changed:
        user.save(using = REMOTE)

    pvals = fields_of(profile_src, exclude = ('user',))
    profile, _ = UserProfile.objects.using(REMOTE).update_or_create(
        user = user, defaults = pvals,
    )
    # Campos EncryptedCharField: el ORM los re-cifraría con la llave LOCAL
    # (distinta del keyring de prod) y prod no podría descifrarlos -> 500.
    # Se escriben en claro por SQL crudo: from_db_value tolera filas sin
    # prefijo enc: y la primera save() de prod las re-cifra con su llave.
    # Las huellas quedan NULL (solo sirven para dedupe de altas reales).
    from django.db import connections
    enc_cols = ['business_name', 'document', 'first_name', 'last_name', 'address', 'phone']
    with connections[REMOTE].cursor() as cur:
        cur.execute(
            'UPDATE users_userprofile SET '
            + ', '.join(f'{c} = %s' for c in enc_cols)
            + ', document_hash = NULL, phone_hash = NULL WHERE user_id = %s',
            [getattr(profile_src, c) or None for c in enc_cols] + [user.pk],
        )

    Suscription.objects.using(REMOTE).update_or_create(
        user = profile,
        defaults = {
            'plan_suscription': plan,
            'pending_plan_suscription': None,
            'status': Suscription.STATUS_ACTIVE,
            'start_date': timezone.now(),
            'end_date': FOREVER,          # acceso "infinito": nunca vence
            'auto_renew': True,
        },
    )
    print('  user/profile/sub ok')

    # ---- tienda ----
    svals = fields_of(store, exclude = ('user',))
    svals['is_published'] = True
    rstore, _ = Store.objects.using(REMOTE).update_or_create(
        slug = store.slug, defaults = {**svals, 'user': profile},
    )
    print('  store ok ->', rstore.id)

    # ---- customization (todas las columnas tal cual) ----
    cust_src = store.customization
    cvals = fields_of(cust_src, exclude = ('store',))
    StoreCustomization.objects.using(REMOTE).update_or_create(
        store = rstore, defaults = cvals,
    )
    print('  customization ok')

    # ---- carrusel + galería ----
    # position no es único (puede repetirse entre fotos) -> delete + create
    # para no pisar filas por una clave ambigua.
    rstore.carousel_images.using(REMOTE).all().delete()
    rstore.gallery_images.using(REMOTE).all().delete()
    for img in store.carousel_images.order_by('position', 'id'):
        rstore.carousel_images.using(REMOTE).create(
            store = rstore, position = img.position, image_key = img.image_key,
        )
    for img in store.gallery_images.order_by('position', 'id'):
        rstore.gallery_images.using(REMOTE).create(
            store = rstore, position = img.position,
            image_key = img.image_key, kind = img.kind,
        )

    # ---- categorías / marcas (mapa por nombre) ----
    cats = {}
    for c in store.categories.order_by('position', 'id'):
        rc, _ = Category.objects.using(REMOTE).update_or_create(
            store = rstore, name = c.name,
            defaults = fields_of(c, exclude = ('store',)),
        )
        cats[c.name] = rc
    brands = {}
    for b in store.brands.order_by('position', 'id'):
        rb, _ = Brand.objects.using(REMOTE).update_or_create(
            store = rstore, name = b.name,
            defaults = fields_of(b, exclude = ('store',)),
        )
        brands[b.name] = rb
    print('  cats/brands ok')

    # ---- servicios ----
    for sv in store.service_items.order_by('position', 'id'):
        StoreService.objects.using(REMOTE).update_or_create(
            store = rstore, name = sv.name,
            defaults = fields_of(sv, exclude = ('store',)),
        )

    # ---- productos ----
    n = 0
    for p in store.products.order_by('id'):
        pvals = fields_of(p, exclude = ('store', 'category', 'brand'))
        if p.category_id:
            pvals['category'] = cats.get(p.category.name)
        if p.brand_id:
            pvals['brand'] = brands.get(p.brand.name)
        # name no es único por tienda: si la remota ya tiene duplicados
        # (corridas parciales), se queda con una y borra el resto.
        qs = Product.objects.using(REMOTE).filter(store = rstore, name = p.name)
        extra = list(qs.values_list('id', flat = True)[1:])
        if extra:
            Product.objects.using(REMOTE).filter(id__in = extra).delete()
        if qs.exists():
            qs.first()._state.db = None
            qs.update(**pvals)
        else:
            Product.objects.using(REMOTE).create(store = rstore, **pvals)
        n += 1
    print(f'  services ok · products {n}')


run()
