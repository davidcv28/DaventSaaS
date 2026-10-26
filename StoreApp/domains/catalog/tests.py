"""
Tests de seguridad del dominio catalog.

Todo objeto vive dentro de la tienda del dueño autenticado: los querysets
están scopeados por owner, las taxonomías se validan por pertenencia y los
cupos del plan se rechequean bajo lock en el create.
"""
import time
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core import signing
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Brand, Category, Discount, Product, ProductReview
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.stores.services.contact import CAPTCHA_SALT, _answer_hash
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CATEGORIES_URL    =   '/api/categories/'
BRANDS_URL        =   '/api/brands/'
PRODUCTS_URL      =   '/api/products/'
DISCOUNTS_URL     =   '/api/discounts/'
REVIEWS_URL       =   '/api/reviews/'
PUBLIC_CATALOG    =   '/api/stores/public/{slug}/catalog/'
PUBLIC_STORE      =   '/api/stores/public/{slug}/'
PUBLIC_REVIEWS    =   '/api/stores/public/{slug}/products/{pid}/reviews/'
CUSTOMIZATION_URL =   '/api/stores/customization/'


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
    devuelve 404 y nunca descuenta productos ajenos), con la ventana
    validada server-side y la función gated por 'has_discounts' (premium).
    """

    def _client(self, username = 'duenio', slug = 'mi-tienda', premium = True):
        user, profile   =   _make_user(username)
        _grant(profile, has_public_link = True, has_discounts = premium)
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

    def test_product_lives_in_one_products_discount_only(self):
        #Un producto no puede estar en dos grupos de ofertas (scope=products)
        #que sigan vivos — vigente, programado o pausado (reactivarlo chocaría).
        #El error nombra el descuento que lo ocupa; un grupo terminado libera.
        client, store   =   self._client()
        product         =   Product.objects.create(store = store, name = 'Calza', price = 10)
        other           =   Product.objects.create(store = store, name = 'Remera', price = 20)
        first           =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk]), format = 'json')
        self.assertEqual(first.status_code, 201)
        first_id        =   first.data['item']['id']
        dup             =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk, other.pk]), format = 'json')
        self.assertEqual(dup.status_code, 400)
        self.assertIn('Promo finde', dup.data['products'][0])
        #Pausado también bloquea: reactivarlo crearía el solape.
        client.patch(f'{DISCOUNTS_URL}{first_id}/', {'is_active': False}, format = 'json')
        dup             =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk]), format = 'json')
        self.assertEqual(dup.status_code, 400)
        #Terminado libera el producto para un grupo nuevo (por ORM porque el
        #PATCH validaría ends_at > starts_at del propio registro).
        Discount.objects.filter(pk = first_id).update(ends_at = timezone.now() - timedelta(hours = 1))
        ok              =   client.post(DISCOUNTS_URL, self._payload(scope = 'products', products = [product.pk]), format = 'json')
        self.assertEqual(ok.status_code, 201)
        #Editar el propio grupo no se cuenta como conflicto consigo mismo.
        second_id       =   ok.data['item']['id']
        edit            =   client.patch(f'{DISCOUNTS_URL}{second_id}/', {'products': [product.pk, other.pk]}, format = 'json')
        self.assertEqual(edit.status_code, 200)

    def test_discount_endpoints_require_premium_benefit(self):
        #has_discounts es premium: sin el flag el CRUD completo responde
        #403 — ni siquiera el listado viaja (la función no existe para el plan).
        client, store   =   self._client(premium = False)
        discount        =   Discount.objects.create(store = store, name = 'Viejo', percent = 10, starts_at = timezone.now())
        self.assertEqual(client.get(DISCOUNTS_URL).status_code, 403)
        self.assertEqual(client.post(DISCOUNTS_URL, self._payload(), format = 'json').status_code, 403)
        self.assertEqual(client.patch(f'{DISCOUNTS_URL}{discount.pk}/', {'percent': 20}, format = 'json').status_code, 403)
        self.assertEqual(client.delete(f'{DISCOUNTS_URL}{discount.pk}/').status_code, 403)

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

    def _setup(self, premium = True):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True, has_discounts = premium)
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
        response        =   self._catalog()
        products        =   response.data['products']
        self.assertEqual(float(self._offer_of(products, 'Calza')), 75.0)
        #El producto expone qué promo firma su oferta (nombre, %, fin) y la
        #lista de promos vigentes viaja a nivel catálogo para el banner.
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertEqual(calza['discount'], {'name': 'Promo', 'percent': 25, 'ends_at': None})
        self.assertEqual([p['name'] for p in response.data['promotions']], ['Promo'])

    def test_winning_discount_is_none_when_manual_offer_wins(self):
        #Si la oferta manual gana, el producto no firma el descuento: el
        #público no vería un nombre/fecha que no corresponde a su precio.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100, offer_price = 60)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 25, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertEqual(float(calza['offer_price']), 60.0)
        self.assertIsNone(calza['discount'])

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

    def test_discount_not_applied_without_premium_benefit(self):
        #Tienda que bajó de plan: el descuento queda guardado pero la web
        #pública deja de descontar (oferta, firma del descuento y banner
        #de promos salen todos vacíos).
        store           =   self._setup(premium = False)
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 25, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        response        =   self._catalog()
        calza           =   next(p for p in response.data['products'] if p['name'] == 'Calza')
        self.assertIsNone(calza['offer_price'])
        self.assertIsNone(calza['discount'])
        self.assertEqual(response.data['promotions'], [])


class PublicCatalogFilterTests(TestCase):
    """
    Filtros avanzados del catálogo público: taxonomías multi-selección,
    búsqueda sobre categoría/marca/características, facetas dinámicas por
    atributo (?features=), banderas offer/new y conteos del panel.
    """

    def _setup(self):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        return store

    def _catalog(self, **params):
        return APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'), params)

    def test_multi_category_and_brand_filters(self):
        #?category=1,2 suma categorías (OR): cada id seleccionado aporta
        #sus productos, igual que los checkboxes del panel de filtros.
        store           =   self._setup()
        calzas          =   Category.objects.create(store = store, name = 'Calzas')
        remeras         =   Category.objects.create(store = store, name = 'Remeras')
        nike            =   Brand.objects.create(store = store, name = 'Nike')
        adidas          =   Brand.objects.create(store = store, name = 'Adidas')
        Product.objects.create(store = store, name = 'A', price = 10, category = calzas)
        Product.objects.create(store = store, name = 'B', price = 10, category = remeras)
        Product.objects.create(store = store, name = 'C', price = 10)
        Product.objects.create(store = store, name = 'D', price = 10, brand = nike)
        Product.objects.create(store = store, name = 'E', price = 10, brand = adidas)
        response        =   self._catalog(category = f'{calzas.id},{remeras.id}')
        self.assertEqual(sorted(p['name'] for p in response.data['products']), ['A', 'B'])
        response        =   self._catalog(brand = f'{nike.id},{adidas.id}')
        self.assertEqual(sorted(p['name'] for p in response.data['products']), ['D', 'E'])
        #Un id solo sigue funcionando (compat) y uno inválido no rompe.
        response        =   self._catalog(category = str(calzas.id))
        self.assertEqual([p['name'] for p in response.data['products']], ['A'])
        response        =   self._catalog(category = 'abc')
        self.assertEqual(len(response.data['products']), 5)

    def test_search_covers_taxonomies_and_features(self):
        #El buscador no solo mira nombre/descripción: también encuentra por
        #categoría, marca y valores de características (talle, color...).
        store           =   self._setup()
        calzas          =   Category.objects.create(store = store, name = 'Calzas')
        Product.objects.create(store = store, name = 'A', price = 10, category = calzas)
        Product.objects.create(store = store, name = 'B', price = 10, brand = Brand.objects.create(store = store, name = 'Puma'))
        Product.objects.create(store = store, name = 'C', price = 10, features = {'Color': 'Bordó'})
        for term, expected in (('calzas', ['A']), ('puma', ['B']), ('bordó', ['C'])):
            response    =   self._catalog(q = term)
            self.assertEqual([p['name'] for p in response.data['products']], expected, term)

    def test_feature_filter_or_within_and_across(self):
        #?features={"Talle":["S","M"],"Color":["Azul"]}: dentro de un grupo
        #los valores suman; entre grupos todas las condiciones se exigen.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'A', price = 10, features = {'Talle': 'S, M', 'Color': 'Azul'})
        Product.objects.create(store = store, name = 'B', price = 10, features = {'Talle': 'L', 'Color': 'Azul'})
        Product.objects.create(store = store, name = 'C', price = 10, features = {'Talle': 'M', 'Color': 'Rojo'})
        response        =   self._catalog(features = '{"Talle": ["S", "M"]}')
        self.assertEqual(sorted(p['name'] for p in response.data['products']), ['A', 'C'])
        response        =   self._catalog(features = '{"Talle": ["M"], "Color": ["Azul"]}')
        self.assertEqual([p['name'] for p in response.data['products']], ['A'])
        #JSON inválido o con otra forma no filtra nada (criterio defensivo).
        response        =   self._catalog(features = 'no-json')
        self.assertEqual(len(response.data['products']), 3)

    def test_offer_and_new_flags(self):
        #?offer=1 deja solo ofertas efectivas; ?new=1 solo las novedades
        #(CATALOG_NEW_DAYS, espejo de PRODUCT_NEW_DAYS del frontend).
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Vieja', price = 10)
        Product.objects.create(store = store, name = 'Oferta', price = 10, offer_price = 5)
        viejo           =   Product.objects.create(store = store, name = 'Antigua', price = 10)
        Product.objects.filter(pk = viejo.pk).update(created_at = timezone.now() - timedelta(days = 30))
        response        =   self._catalog(offer = '1')
        self.assertEqual([p['name'] for p in response.data['products']], ['Oferta'])
        response        =   self._catalog(new = '1')
        self.assertEqual(sorted(p['name'] for p in response.data['products']), ['Oferta', 'Vieja'])

    def test_facets_counts_and_price_max_payload(self):
        #El panel de filtros se alimenta del propio payload: facetas por
        #atributo con su conteo, products_count por taxonomía, totales de
        #ofertas/novedades y el techo de precio para el slider.
        store           =   self._setup()
        calzas          =   Category.objects.create(store = store, name = 'Calzas')
        Product.objects.create(store = store, name = 'A', price = 10, category = calzas, features = {'Talle': 'S, M'})
        Product.objects.create(store = store, name = 'B', price = 90, category = calzas, features = {'Talle': 'M'}, offer_price = 45)
        Product.objects.create(store = store, name = 'C', price = 10, is_active = False, features = {'Talle': 'XXL'})
        response        =   self._catalog()
        talle           =   next(f for f in response.data['facets'] if f['name'] == 'Talle')
        self.assertEqual(talle['values'], [{'value': 'M', 'count': 2}, {'value': 'S', 'count': 1}])
        self.assertFalse(any(v['value'] == 'XXL' for v in talle['values']))
        calza           =   next(c for c in response.data['categories'] if c['name'] == 'Calzas')
        self.assertEqual(calza['products_count'], 2)
        self.assertEqual(response.data['offer_count'], 1)
        self.assertEqual(response.data['new_count'], 2)
        #El techo usa el precio efectivo: B cuesta 90 de lista pero se
        #muestra a 45 (su oferta), así que el máximo visible es 45.
        self.assertEqual(float(response.data['price_max']), 45.0)

    def test_facets_scope_and_schema_order_by_category(self):
        #Las facetas se adaptan a la categoría elegida: solo viajan los
        #atributos de SUS productos y ordenados según su feature_schema
        #(la plantilla del dueño), no por frecuencia global.
        store           =   self._setup()
        remeras         =   Category.objects.create(store = store, name = 'Remeras', feature_schema = ['Color', 'Talle'])
        electro         =   Category.objects.create(store = store, name = 'Electro', feature_schema = ['Voltaje'])
        Product.objects.create(store = store, name = 'A', price = 10, category = remeras, features = {'Talle': 'M', 'Color': 'Azul'})
        Product.objects.create(store = store, name = 'B', price = 10, category = remeras, features = {'Talle': 'L'})
        Product.objects.create(store = store, name = 'C', price = 10, category = electro, features = {'Voltaje': '220v'})
        #Sin selección, todo el catálogo aporta sus atributos.
        response        =   self._catalog()
        self.assertEqual([f['name'] for f in response.data['facets']], ['Talle', 'Color', 'Voltaje'])
        #Con categoría, solo sus atributos — y en el orden de su schema
        #(Color primero aunque Talle tenga más conteo).
        response        =   self._catalog(category = str(remeras.id))
        self.assertEqual([f['name'] for f in response.data['facets']], ['Color', 'Talle'])
        response        =   self._catalog(category = str(electro.id))
        self.assertEqual([f['name'] for f in response.data['facets']], ['Voltaje'])


def _review_captcha(slug, answer = 7):
    """
    Challenge válido y envejecido (30s > CAPTCHA_MIN_SECONDS): pasa la
    verificación real de firma + antigüedad + respuesta.
    """
    payload =   {'s': slug, 'h': _answer_hash(slug, answer), 't': time.time() - 30}
    return {
        'challenge_id'  :   signing.dumps(payload, salt = CAPTCHA_SALT),
        'captcha_answer':   str(answer),
    }


class ReviewTests(TestCase):
    """
    Opiniones de visitantes: like/dislike (show_reviews, todos los planes) y
    comentarios (show_comments, premium por has_product_comments). El alta
    pública pide nombre+apellido+email+captcha; el dueño modera borrando.
    """

    def setUp(self):
        #El throttle store_review (10/h por IP) comparte la cache entre
        #tests: sin limpiarla los POST acumulados devuelven 429 falsos.
        cache.clear()

    def _setup(self, comments = True, reviews = True):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True, has_product_comments = True, has_customization = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        StoreCustomization.objects.create(
            store = store, show_reviews = reviews, show_comments = comments,
        )
        product         =   Product.objects.create(store = store, name = 'Calza', price = 100)
        return store, product

    def _post(self, product, **extra):
        payload     =   {
            'name'      :   'Maria', 'surname': 'Perez',
            'email'     :   'maria@example.com',
            **_review_captcha('mi-tienda'),
            **extra,
        }
        return APIClient().post(PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id), payload)

    def test_review_create_vote_and_comment(self):
        _, product      =   self._setup()
        response        =   self._post(product, is_positive = True, text = 'Excelente calidad')
        self.assertEqual(response.status_code, 201)
        review          =   ProductReview.objects.get(product = product)
        self.assertTrue(review.is_positive)
        self.assertEqual(review.text, 'Excelente calidad')

    def test_review_list_public_privacy(self):
        _, product      =   self._setup()
        self._post(product, is_positive = True, text = 'Muy buena')
        items           =   APIClient().get(PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)).data
        self.assertEqual(len(items), 1)
        item            =   items[0]
        #La ficha muestra "Maria P.": el apellido viaja reducido a inicial
        #y el email jamás sale en la API pública (solo lo ve el dueño).
        self.assertEqual(item['name'], 'Maria')
        self.assertEqual(item['surname_initial'], 'P.')
        self.assertNotIn('email', item)
        self.assertNotIn('surname', item)

    def test_endpoints_404_with_features_off(self):
        _, product      =   self._setup(comments = False, reviews = False)
        self.assertEqual(self._post(product, is_positive = True).status_code, 404)
        self.assertEqual(
            APIClient().get(PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)).status_code, 404,
        )

    def test_reviews_require_premium_benefit(self):
        #Las opiniones (valoraciones + comentarios) son premium: los
        #toggles quedaron en True pero el plan bajó — los endpoints
        #públicos cierran por completo (404 para votos y comentarios).
        _, product      =   self._setup(comments = True)
        PlanBenefit.objects.filter(benefit__code = 'has_product_comments').delete()
        self.assertEqual(self._post(product, text = 'Hola').status_code, 404)
        self.assertEqual(self._post(product, is_positive = True).status_code, 404)

    def test_reviews_only_store_rejects_text(self):
        _, product      =   self._setup(comments = False)
        self.assertEqual(self._post(product, is_positive = True, text = 'Hola').status_code, 400)
        self.assertEqual(self._post(product, is_positive = True).status_code, 201)

    def test_comments_only_store_requires_text(self):
        _, product      =   self._setup(reviews = False)
        self.assertEqual(self._post(product, is_positive = True).status_code, 400)
        self.assertEqual(self._post(product, text = 'Muy buena').status_code, 201)

    def test_review_needs_vote_or_text(self):
        _, product      =   self._setup()
        self.assertEqual(self._post(product).status_code, 400)

    def test_review_vote_must_be_boolean(self):
        _, product      =   self._setup()
        self.assertEqual(self._post(product, is_positive = 'quiza').status_code, 400)
        self.assertEqual(self._post(product, is_positive = False).status_code, 201)

    def test_review_bad_captcha_rejected(self):
        _, product      =   self._setup()
        captcha         =   _review_captcha('mi-tienda', answer = 7)
        captcha['captcha_answer']   =   '9'
        response        =   APIClient().post(
            PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id),
            {'name': 'Maria', 'surname': 'Perez', 'email': 'm@x.com', 'is_positive': True, **captcha},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_review_honeypot_fakes_success(self):
        _, product      =   self._setup()
        response        =   self._post(product, is_positive = True, website = 'http://spam')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_public_catalog_rating_aggregates(self):
        store, product  =   self._setup()
        #1 like + 1 dislike: el score público es 5 × likes/votos = 2.5,
        #y el conteo suma solo votos (los comentarios solo-texto no puntúan).
        ProductReview.objects.create(store = store, product = product, is_positive = True, name = 'A', surname = 'B', email = 'a@x.com')
        ProductReview.objects.create(store = store, product = product, is_positive = False, name = 'C', surname = 'D', email = 'c@x.com')
        ProductReview.objects.create(store = store, product = product, text = 'Solo texto', name = 'E', surname = 'F', email = 'e@x.com')
        products        =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda')).data['products']
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertEqual(calza['rating_avg'], 2.5)
        self.assertEqual(calza['rating_count'], 2)

    def test_public_catalog_hides_ratings_without_flag(self):
        store, product  =   self._setup(reviews = False)
        ProductReview.objects.create(store = store, product = product, is_positive = True, name = 'A', surname = 'B', email = 'a@x.com')
        products        =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda')).data['products']
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertIsNone(calza['rating_avg'])
        self.assertIsNone(calza['rating_count'])

    def test_owner_moderation_list_and_delete(self):
        store, product  =   self._setup()
        review          =   ProductReview.objects.create(
            store = store, product = product, is_positive = True, text = 'Buena',
            name = 'Maria', surname = 'Perez', email = 'm@x.com',
        )
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        items           =   client.get(REVIEWS_URL).data
        self.assertEqual(len(items), 1)
        #El dueño sí ve el email completo para poder responder o moderar.
        self.assertEqual(items[0]['email'], 'm@x.com')
        self.assertEqual(items[0]['product_name'], 'Calza')
        self.assertEqual(client.delete(f'{REVIEWS_URL}{review.id}/').status_code, 200)
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_owner_cannot_moderate_foreign_review(self):
        _, product      =   self._setup()
        review          =   ProductReview.objects.create(
            store = product.store, product = product, is_positive = False, text = 'Mala',
            name = 'X', surname = 'Y', email = 'x@x.com',
        )
        _, other        =   _make_user('otro')
        _grant(other, has_public_link = True, has_product_comments = True)
        Store.objects.create(user = other, slug = 'otra-tienda', is_published = True)
        client          =   APIClient()
        client.force_authenticate(user = other.user)
        self.assertEqual(client.get(REVIEWS_URL).data, [])
        self.assertEqual(client.delete(f'{REVIEWS_URL}{review.id}/').status_code, 404)
        self.assertTrue(ProductReview.objects.filter(pk = review.id).exists())

    def test_owner_moderation_requires_premium_benefit(self):
        #Sin has_product_comments el panel tampoco lista ni borra opiniones:
        #la moderación viaja con la sección premium (el dato queda intacto).
        store, product  =   self._setup()
        review          =   ProductReview.objects.create(
            store = store, product = product, is_positive = True, text = 'Buena',
            name = 'Maria', surname = 'Perez', email = 'm@x.com',
        )
        PlanBenefit.objects.filter(benefit__code = 'has_product_comments').delete()
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        self.assertEqual(client.get(REVIEWS_URL).status_code, 403)
        self.assertEqual(client.delete(f'{REVIEWS_URL}{review.id}/').status_code, 403)
        self.assertTrue(ProductReview.objects.filter(pk = review.id).exists())

    def test_reviews_create_via_owner_endpoint_rejected(self):
        store, _        =   self._setup()
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        self.assertEqual(client.post(REVIEWS_URL, {'is_positive': True}).status_code, 405)

    def test_customization_patch_discards_reviews_without_benefit(self):
        store, _        =   self._setup(reviews = False, comments = False)
        PlanBenefit.objects.filter(benefit__code = 'has_product_comments').delete()
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        client.patch(CUSTOMIZATION_URL, {'show_reviews': True, 'show_comments': True}, format = 'json')
        store.customization.refresh_from_db()
        self.assertFalse(store.customization.show_reviews)
        self.assertFalse(store.customization.show_comments)

    def test_customization_patch_saves_reviews_with_benefit(self):
        store, _        =   self._setup(reviews = False, comments = False)
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        client.patch(CUSTOMIZATION_URL, {'show_reviews': True, 'show_comments': True}, format = 'json')
        store.customization.refresh_from_db()
        self.assertTrue(store.customization.show_reviews)
        self.assertTrue(store.customization.show_comments)

    def test_public_store_hides_reviews_flags_without_benefit(self):
        store, _        =   self._setup()
        PlanBenefit.objects.filter(benefit__code = 'has_product_comments').delete()
        data            =   APIClient().get(PUBLIC_STORE.format(slug = 'mi-tienda')).data
        self.assertFalse(data['customization']['show_comments'])
        self.assertFalse(data['customization']['show_reviews'])

    def test_public_catalog_hides_ratings_without_benefit(self):
        #Las estrellas del catálogo también se apagan sin el flag: el
        #rating no se anota aunque show_reviews quedara en True.
        store, product  =   self._setup()
        PlanBenefit.objects.filter(benefit__code = 'has_product_comments').delete()
        ProductReview.objects.create(store = store, product = product, is_positive = True, name = 'A', surname = 'B', email = 'a@x.com')
        products        =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda')).data['products']
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertIsNone(calza['rating_avg'])
        self.assertIsNone(calza['rating_count'])
