"""
Tests de seguridad del dominio catalog.

Todo objeto vive dentro de la tienda del dueño autenticado: los querysets
están scopeados por owner, las taxonomías se validan por pertenencia y los
cupos del plan se rechequean bajo lock en el create.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Brand, Category, Discount, Product
from StoreApp.domains.stores.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CATEGORIES_URL    =   '/api/categories/'
BRANDS_URL        =   '/api/brands/'
PRODUCTS_URL      =   '/api/products/'
DISCOUNTS_URL     =   '/api/discounts/'
PUBLIC_CATALOG    =   '/api/stores/public/{slug}/catalog/'


def _make_user(username, verified = True):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'6{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'26{abs(hash(username + username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
    )
    return user, profile


def _grant(profile, **benefits):
    """Plan + suscripción vigente de 30 días (bool = flag, int|None = limit)."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username}')
    for code, value in benefits.items():
        kind        =   Benefit.FLAG if isinstance(value, bool) else Benefit.LIMIT
        benefit     =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': kind})[0]
        PlanBenefit.objects.create(
            plan        =   plan,
            benefit     =   benefit,
            enabled     =   value if kind == Benefit.FLAG else True,
            value       =   None if kind == Benefit.FLAG else value,
        )
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    return plan


class CatalogOwnerIsolationTests(TestCase):
    """
    El catálogo es privado del dueño: sin auth 401, sin tienda 404 y los
    objetos de otro comercio no se leen ni se tocan.
    """

    def _owner(self, username = 'duenio', slug = 'mi-tienda', with_plan = True, **benefits):
        user, profile   =   _make_user(username)
        if with_plan:
            _grant(profile, has_public_link = True, **benefits)
        store           =   Store.objects.create(user = profile, slug = slug)
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def test_anonymous_rejected(self):
        for url in (CATEGORIES_URL, BRANDS_URL, PRODUCTS_URL, DISCOUNTS_URL):
            self.assertEqual(APIClient().get(url).status_code, 401, url)

    def test_write_without_plan_forbidden(self):
        client, _       =   self._owner(with_plan = False)
        self.assertEqual(client.post(CATEGORIES_URL, {'name': 'Calzas'}, format = 'json').status_code, 403)
        self.assertEqual(client.post(PRODUCTS_URL, {'name': 'Calza', 'price': '10'}, format = 'json').status_code, 403)
        self.assertEqual(client.post(DISCOUNTS_URL, {'name': 'Promo', 'percent': 10, 'starts_at': '2030-01-01T00:00:00Z'}, format = 'json').status_code, 403)

    def test_foreign_category_detail_not_exposed(self):
        #El viewset no implementa retrieve: el detalle responde 405 para
        #propios y ajenos — nunca expone la taxonomía de otra tienda.
        client, store   =   self._owner()
        _, store2       =   self._owner(username = 'otro', slug = 'otra-tienda')
        foreign         =   Category.objects.create(store = store2, name = 'Ajena')
        response        =   client.get(f'{CATEGORIES_URL}{foreign.pk}/')
        self.assertIn(response.status_code, (404, 405))

    def test_owner_cannot_update_foreign_category(self):
        client, _       =   self._owner()
        _, store2       =   self._owner(username = 'otro', slug = 'otra-tienda')
        foreign         =   Category.objects.create(store = store2, name = 'Ajena')
        response        =   client.patch(f'{CATEGORIES_URL}{foreign.pk}/', {'name': 'Robada'}, format = 'json')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.name, 'Ajena')

    def test_owner_cannot_delete_foreign_product(self):
        client, _       =   self._owner()
        _, store2       =   self._owner(username = 'otro', slug = 'otra-tienda')
        foreign         =   Product.objects.create(store = store2, name = 'Ajeno', price = 10)
        response        =   client.delete(f'{PRODUCTS_URL}{foreign.pk}/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Product.objects.filter(pk = foreign.pk).exists())

    def test_product_list_only_own_store(self):
        client, store   =   self._owner()
        _, store2       =   self._owner(username = 'otro', slug = 'otra-tienda')
        Product.objects.create(store = store, name = 'Mío', price = 10)
        Product.objects.create(store = store2, name = 'Ajeno', price = 10)
        response        =   client.get(PRODUCTS_URL)
        names           =   [p['name'] for p in response.data]
        self.assertEqual(names, ['Mío'])


class TaxonomyValidationTests(TestCase):
    """Unicidad por tienda (case-insensitive) y schema acotado."""

    def _client(self):
        user, profile   =   _make_user('duenio')
        _grant(profile, has_public_link = True, max_products = None)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def test_category_create_ok(self):
        response        =   self._client().post(CATEGORIES_URL, {'name': 'Calzas', 'feature_schema': ['Talle']}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_category_duplicate_name_case_insensitive(self):
        client          =   self._client()
        client.post(CATEGORIES_URL, {'name': 'Calzas'}, format = 'json')
        response        =   client.post(CATEGORIES_URL, {'name': 'CALZAS'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_category_same_name_allowed_in_other_store(self):
        Category.objects.create(store = Store.objects.create(user = _make_user('otro')[1], slug = 'otra'), name = 'Calzas')
        response        =   self._client().post(CATEGORIES_URL, {'name': 'Calzas'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_category_schema_too_long_rejected(self):
        response        =   self._client().post(
            CATEGORIES_URL, {'name': 'X', 'feature_schema': [f'f{i}' for i in range(30)]}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_brand_create_ok(self):
        response        =   self._client().post(BRANDS_URL, {'name': 'Nike'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_brand_duplicate_name_rejected(self):
        client          =   self._client()
        client.post(BRANDS_URL, {'name': 'Nike'}, format = 'json')
        response        =   client.post(BRANDS_URL, {'name': 'nike'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class ProductValidationTests(TestCase):
    """
    Reglas del producto: oferta < precio, features acotadas y las
    taxonomías deben pertenecer a la tienda del dueño.
    """

    def _client(self, **benefits):
        user, profile   =   _make_user('duenio')
        benefits.setdefault('max_products', None)
        _grant(profile, has_public_link = True, **benefits)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def test_product_create_ok(self):
        response        =   self._client()[0].post(PRODUCTS_URL, {'name': 'Calza', 'price': '10.00'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_product_limit_enforced(self):
        #max_products del plan: el cupo se rechequea bajo lock en el create.
        client, _       =   self._client(max_products = 1)
        self.assertEqual(client.post(PRODUCTS_URL, {'name': 'Producto A', 'price': '10'}, format = 'json').status_code, 201)
        self.assertEqual(client.post(PRODUCTS_URL, {'name': 'Producto B', 'price': '10'}, format = 'json').status_code, 403)

    def test_product_rejects_foreign_category(self):
        client, _       =   self._client()
        foreign         =   Category.objects.create(
            store = Store.objects.create(user = _make_user('otro')[1], slug = 'otra'), name = 'Ajena')
        response        =   client.post(PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'category': foreign.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_product_rejects_foreign_brand(self):
        client, _       =   self._client()
        foreign         =   Brand.objects.create(
            store = Store.objects.create(user = _make_user('otro')[1], slug = 'otra'), name = 'Ajena')
        response        =   client.post(PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'brand': foreign.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_offer_price_must_be_below_price(self):
        client, _       =   self._client()
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'offer_price': '10'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'offer_price': '12'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_offer_price_below_price_ok(self):
        client, _       =   self._client()
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'offer_price': '8'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_features_bounded(self):
        client, _       =   self._client()
        response        =   client.post(
            PRODUCTS_URL,
            {'name': 'Calza', 'price': '10', 'features': {f'f{i}': 'v' for i in range(25)}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 400)

    def test_features_non_dict_rejected(self):
        client, _       =   self._client()
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'features': ['no-es-dict']}, format = 'json')
        self.assertEqual(response.status_code, 400)


class RemoveBackgroundGateTests(TestCase):
    """El editor de fondo es un recurso caro: solo con catálogo habilitado."""

    def test_remove_background_forbidden_without_plan(self):
        user, profile   =   _make_user('duenio')
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(f'{PRODUCTS_URL}remove-background/', {}, format = 'multipart')
        self.assertEqual(response.status_code, 403)

    def test_remove_background_requires_file(self):
        user, profile   =   _make_user('duenio')
        _grant(profile, has_public_link = True)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(f'{PRODUCTS_URL}remove-background/', {}, format = 'multipart')
        self.assertEqual(response.status_code, 400)


class DiscountTests(TestCase):
    """
    Descuentos programados del dueño: scopeado a su tienda (un id ajeno
    devuelve 404 y nunca descuenta productos ajenos) y con la ventana
    validada server-side.
    """

    def _client(self, username = 'duenio', slug = 'mi-tienda'):
        user, profile   =   _make_user(username)
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = slug)
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def _payload(self, **overrides):
        payload     =   {
            'name'      :   'Promo finde',
            'percent'   :   25,
            'scope'     :   'all',
            'starts_at' :   '2030-01-01T00:00:00Z',
        }
        payload.update(overrides)
        return payload

    def test_discount_list_only_own_store(self):
        client, store   =   self._client()
        _, store2       =   self._client(username = 'otro', slug = 'otra-tienda')
        Discount.objects.create(store = store, name = 'Mío', percent = 10, starts_at = timezone.now())
        Discount.objects.create(store = store2, name = 'Ajeno', percent = 10, starts_at = timezone.now())
        names           =   [d['name'] for d in client.get(DISCOUNTS_URL).data]
        self.assertEqual(names, ['Mío'])

    def test_owner_cannot_update_foreign_discount(self):
        client, _       =   self._client()
        _, store2       =   self._client(username = 'otro', slug = 'otra-tienda')
        foreign         =   Discount.objects.create(store = store2, name = 'Ajeno', percent = 10, starts_at = timezone.now())
        response        =   client.patch(f'{DISCOUNTS_URL}{foreign.pk}/', {'percent': 99}, format = 'json')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.percent, 10)

    def test_owner_cannot_delete_foreign_discount(self):
        client, _       =   self._client()
        _, store2       =   self._client(username = 'otro', slug = 'otra-tienda')
        foreign         =   Discount.objects.create(store = store2, name = 'Ajeno', percent = 10, starts_at = timezone.now())
        response        =   client.delete(f'{DISCOUNTS_URL}{foreign.pk}/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Discount.objects.filter(pk = foreign.pk).exists())

    def test_percent_bounds(self):
        client, _       =   self._client()
        for percent in (0, 100, -5):
            response    =   client.post(DISCOUNTS_URL, self._payload(percent = percent), format = 'json')
            self.assertEqual(response.status_code, 400, percent)

    def test_window_must_end_after_start(self):
        client, _       =   self._client()
        response        =   client.post(DISCOUNTS_URL, self._payload(
            starts_at   =   '2030-01-10T00:00:00Z',
            ends_at     =   '2030-01-05T00:00:00Z'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_scope_rejected(self):
        client, _       =   self._client()
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'todo'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_category_scope_requires_category(self):
        client, store   =   self._client()
        self.assertEqual(client.post(DISCOUNTS_URL, self._payload(scope = 'category'), format = 'json').status_code, 400)
        category        =   Category.objects.create(store = store, name = 'Calzas')
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'category', category = category.pk), format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_discount_rejects_foreign_category(self):
        client, _       =   self._client()
        _, store2       =   self._client(username = 'otro', slug = 'otra-tienda')
        foreign         =   Category.objects.create(store = store2, name = 'Ajena')
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'category', category = foreign.pk), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_products_scope_requires_products(self):
        client, _       =   self._client()
        self.assertEqual(client.post(DISCOUNTS_URL, self._payload(scope = 'products'), format = 'json').status_code, 400)
        self.assertEqual(client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = []), format = 'json').status_code, 400)

    def test_discount_rejects_foreign_product(self):
        client, _       =   self._client()
        _, store2       =   self._client(username = 'otro', slug = 'otra-tienda')
        foreign         =   Product.objects.create(store = store2, name = 'Ajeno', price = 10)
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [foreign.pk]), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_discount_create_and_toggle(self):
        client, store   =   self._client()
        product         =   Product.objects.create(store = store, name = 'Calza', price = 10)
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk]), format = 'json')
        self.assertEqual(response.status_code, 201)
        discount_id     =   response.data['item']['id']
        response        =   client.patch(f'{DISCOUNTS_URL}{discount_id}/', {'is_active': False}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['item']['status'], 'paused')

    def test_changing_scope_clears_leftovers(self):
        #Pasar de products a all limpia la M2M: no quedan restos de la
        #selección anterior limitando el alcance.
        client, store   =   self._client()
        product         =   Product.objects.create(store = store, name = 'Calza', price = 10)
        response        =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk]), format = 'json')
        discount_id     =   response.data['item']['id']
        response        =   client.patch(f'{DISCOUNTS_URL}{discount_id}/', {'scope': 'all'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Discount.objects.get(pk = discount_id).products.count(), 0)


class DiscountPublicTests(TestCase):
    """
    La automatización del descuento vive en la ventana [starts_at,
    ends_at) evaluada al leer el catálogo público: se activa y vence
    solo, sin tocar offer_price ni requerir un worker.
    """

    def _setup(self):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        return store

    def _catalog(self):
        return APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'))

    def _offer_of(self, products, name):
        return next(p for p in products if p['name'] == name)['offer_price']

    def test_running_discount_applies_to_public_offer(self):
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 25, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        self.assertEqual(float(self._offer_of(products, 'Calza')), 75.0)

    def test_scheduled_discount_does_not_apply_yet(self):
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Futuro', percent = 25, scope = 'all',
            starts_at = timezone.now() + timedelta(days = 1),
        )
        products        =   self._catalog().data['products']
        self.assertIsNone(self._offer_of(products, 'Calza'))

    def test_ended_discount_does_not_apply(self):
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Viejo', percent = 25, scope = 'all',
            starts_at = timezone.now() - timedelta(days = 2),
            ends_at     =   timezone.now() - timedelta(days = 1),
        )
        products        =   self._catalog().data['products']
        self.assertIsNone(self._offer_of(products, 'Calza'))

    def test_paused_discount_does_not_apply(self):
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Pausado', percent = 25, scope = 'all', is_active = False,
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        self.assertIsNone(self._offer_of(products, 'Calza'))

    def test_manual_offer_wins_when_lower(self):
        #La oferta efectiva es el mínimo: un descuento peor que la oferta
        #manual del producto no sube el precio mostrado.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100, offer_price = 60)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 25, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        self.assertEqual(float(self._offer_of(products, 'Calza')), 60.0)

    def test_category_scope_only_covers_that_category(self):
        store           =   self._setup()
        category        =   Category.objects.create(store = store, name = 'Calzas')
        Product.objects.create(store = store, name = 'Dentro', price = 100, category = category)
        Product.objects.create(store = store, name = 'Fuera', price = 100)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 50, scope = 'category', category = category,
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        self.assertEqual(float(self._offer_of(products, 'Dentro')), 50.0)
        self.assertIsNone(self._offer_of(products, 'Fuera'))

    def test_price_filter_uses_discounted_price(self):
        #?min_price filtra por el precio efectivo: un producto que solo
        #entra al rango por el descuento aparece.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 50, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        response        =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'), {'max_price': '60'})
        self.assertEqual([p['name'] for p in response.data['products']], ['Calza'])
        response        =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'), {'min_price': '60'})
        self.assertEqual(response.data['products'], [])

    def test_owner_list_exposes_discount_fields(self):
        #El panel del dueño ve el precio promocionado sin tocar offer_price:
        #editar el producto no pisa la oferta manual con el descuento.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 10, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        user            =   store.user.user
        client          =   APIClient()
        client.force_authenticate(user = user)
        item            =   next(p for p in client.get(PRODUCTS_URL).data if p['name'] == 'Calza')
        self.assertEqual(item['offer_price'], None)
        self.assertEqual(float(item['discount_offer']), 90.0)
        self.assertEqual(item['discount_names'], ['Promo'])
