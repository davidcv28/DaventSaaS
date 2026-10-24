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
from StoreApp.domains.catalog.models import Brand, Category, Product
from StoreApp.domains.stores.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CATEGORIES_URL    =   '/api/categories/'
BRANDS_URL        =   '/api/brands/'
PRODUCTS_URL      =   '/api/products/'


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
        for url in (CATEGORIES_URL, BRANDS_URL, PRODUCTS_URL):
            self.assertEqual(APIClient().get(url).status_code, 401, url)

    def test_write_without_plan_forbidden(self):
        client, _       =   self._owner(with_plan = False)
        self.assertEqual(client.post(CATEGORIES_URL, {'name': 'Calzas'}, format = 'json').status_code, 403)
        self.assertEqual(client.post(PRODUCTS_URL, {'name': 'Calza', 'price': '10'}, format = 'json').status_code, 403)

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
