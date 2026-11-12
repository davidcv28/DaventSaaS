"""
Tests de seguridad del dominio catalog.

Todo objeto vive dentro de la tienda del dueño autenticado: los querysets
están scopeados por owner, las taxonomías se validan por pertenencia y los
cupos del plan se rechequean bajo lock en el create.
"""
from datetime import UTC, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import (
    Brand,
    Category,
    Discount,
    Product,
    ProductReview,
    SpecialOfferCampaign,
)
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.stores.services import storage as storage_service
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CATEGORIES_URL    =   '/api/categories/'
BRANDS_URL        =   '/api/brands/'
PRODUCTS_URL      =   '/api/products/'
DISCOUNTS_URL     =   '/api/discounts/'
OFFERS_URL        =   '/api/offers/'
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

    def setUp(self):
        # plan_benefits_of cachea por PK (`planben:<pk>`) y SQLite reutiliza
        # PKs tras el rollback de cada test: sin limpiar, el plan del test
        # anterior se filtra al que corre sin plan y el gate deja de dar 403.
        cache.clear()

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


class BrandImageTests(TestCase):
    """Logo de marca: upload multipart -> WebP con alfa, cuota y borrado."""

    def _client(self, **benefits):
        user, profile   =   _make_user('duenio')
        benefits.setdefault('max_images', None)
        benefits.setdefault('max_storage_mb', None)
        _grant(profile, has_public_link = True, **benefits)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def _upload(self):
        return SimpleUploadedFile('logo.png', b'\x89PNG\r\n\x1a\nfake', content_type = 'image/png')

    def _storage_patches(self, key = 'stores/1/brands/logo.webp', body = b'webp-bytes'):
        return (
            patch.object(storage_service, 'storage_configured', return_value = True),
            patch.object(storage_service, 'validate_logo_file', return_value = ''),
            patch.object(storage_service, 'normalize_image', return_value = (body, 'webp', 'image/webp')),
            patch.object(storage_service, '_put_object', return_value = key),
            patch.object(storage_service, '_delete_object', return_value = None),
            patch('StoreApp.domains.catalog.serializers.serializers.object_url', side_effect = lambda k: f'https://cdn.test/{k}' if k else None),
        )

    def test_brand_image_upload_uses_logo_pipeline_and_serializes_url(self):
        client, store   =   self._client()
        brand           =   Brand.objects.create(store = store, name = 'Nike')
        cfg, val, norm, put, delete, urls   =   self._storage_patches()
        with cfg, val, norm as normalize, put as put_mock, delete, urls:
            response    =   client.post(f'{BRANDS_URL}{brand.pk}/image/', {'image': self._upload()}, format = 'multipart')
        self.assertEqual(response.status_code, 200, response.data)
        brand.refresh_from_db()
        store.refresh_from_db()
        self.assertEqual(brand.image_key, 'stores/1/brands/logo.webp')
        self.assertEqual(brand.image_size, len(b'webp-bytes'))
        self.assertEqual(store.storage_used_bytes, len(b'webp-bytes'))
        #El pipeline de logo conserva el alfa y achica el archivo antes de R2.
        self.assertEqual(normalize.call_args[0][1], 'logo')
        self.assertEqual(put_mock.call_args[0][1], 'brands')
        self.assertEqual(response.data['item']['image'], 'https://cdn.test/stores/1/brands/logo.webp')
        self.assertEqual(response.data['storage']['used_bytes'], len(b'webp-bytes'))

    def test_brand_image_delete_frees_quota_and_object(self):
        client, store   =   self._client()
        brand           =   Brand.objects.create(store = store, name = 'Nike', image_key = 'stores/1/brands/old.webp', image_size = 50)
        store.storage_used_bytes    =   50
        store.save(update_fields = ['storage_used_bytes'])
        cfg, val, norm, put, delete, urls   =   self._storage_patches()
        with delete as delete_mock:
            response    =   client.delete(f'{BRANDS_URL}{brand.pk}/image/')
        self.assertEqual(response.status_code, 200, response.data)
        brand.refresh_from_db()
        store.refresh_from_db()
        self.assertEqual(brand.image_key, '')
        self.assertEqual(brand.image_size, 0)
        self.assertEqual(store.storage_used_bytes, 0)
        delete_mock.assert_called_once_with('stores/1/brands/old.webp')

    def test_brand_destroy_deletes_image_and_frees_quota(self):
        client, store   =   self._client()
        brand           =   Brand.objects.create(store = store, name = 'Nike', image_key = 'stores/1/brands/old.webp', image_size = 40)
        store.storage_used_bytes    =   40
        store.save(update_fields = ['storage_used_bytes'])
        cfg, val, norm, put, delete, urls   =   self._storage_patches()
        with delete as delete_mock:
            response    =   client.delete(f'{BRANDS_URL}{brand.pk}/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(Brand.objects.filter(pk = brand.pk).exists())
        store.refresh_from_db()
        self.assertEqual(store.storage_used_bytes, 0)
        delete_mock.assert_called_once_with('stores/1/brands/old.webp')

    def test_brand_image_requires_own_brand(self):
        client, _       =   self._client()
        _, profile      =   _make_user('otro')
        _grant(profile, has_public_link = True)
        other           =   Store.objects.create(user = profile, slug = 'otra-tienda')
        foreign         =   Brand.objects.create(store = other, name = 'Ajena')
        response        =   client.post(f'{BRANDS_URL}{foreign.pk}/image/', {'image': self._upload()}, format = 'multipart')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.image_key, '')

    def test_public_catalog_exposes_brand_image(self):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        Brand.objects.create(store = store, name = 'Nike', image_key = 'stores/1/brands/logo.webp')
        cfg, val, norm, put, delete, urls   =   self._storage_patches()
        with urls:
            response    =   APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'))
        self.assertEqual(response.status_code, 200, response.data)
        brand           =   next(b for b in response.data['brands'] if b['name'] == 'Nike')
        self.assertEqual(brand['image'], 'https://cdn.test/stores/1/brands/logo.webp')


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


class ProductStockGateTests(TestCase):
    """
    El control de stock es superficie de `has_ecommerce`: sin el beneficio
    el campo no se carga ni se limpia (400) y el valor queda intacto; con
    él el dueño setea unidades (0 = agotado) y '' vuelve a ilimitado.
    """

    def setUp(self):
        # Mismo motivo que CatalogOwnerIsolationTests: el cache de
        # beneficios se keyea por PK y SQLite reutiliza PKs entre tests.
        cache.clear()

    def _client(self, **benefits):
        user, profile   =   _make_user('duenio')
        benefits.setdefault('max_products', None)
        _grant(profile, has_public_link = True, **benefits)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def test_stock_write_requires_ecommerce_benefit(self):
        client, store   =   self._client()
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'stock': 5}, format = 'json')
        self.assertEqual(response.status_code, 400)
        product         =   Product.objects.create(store = store, name = 'Calza', price = 10, stock = 7)
        response        =   client.patch(f'{PRODUCTS_URL}{product.pk}/', {'stock': 2}, format = 'json')
        self.assertEqual(response.status_code, 400)
        product.refresh_from_db()
        self.assertEqual(product.stock, 7)
        #Sin la clave el resto del producto se edita normal.
        response        =   client.patch(f'{PRODUCTS_URL}{product.pk}/', {'price': '12'}, format = 'json')
        self.assertEqual(response.status_code, 200)

    def test_stock_write_with_ecommerce_benefit(self):
        client, store   =   self._client(has_ecommerce = True)
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'stock': 5}, format = 'json')
        self.assertEqual(response.status_code, 201)
        product         =   Product.objects.get(store = store)
        self.assertEqual(product.stock, 5)
        response        =   client.patch(f'{PRODUCTS_URL}{product.pk}/', {'stock': 0}, format = 'json')
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        #'' en multipart limpia el control: el producto vuelve a ilimitado.
        response        =   client.patch(f'{PRODUCTS_URL}{product.pk}/', {'stock': ''}, format = 'multipart')
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertIsNone(product.stock)

    def test_stock_negative_rejected(self):
        client, _       =   self._client(has_ecommerce = True)
        response        =   client.post(
            PRODUCTS_URL, {'name': 'Calza', 'price': '10', 'stock': -1}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_stock_travels_in_owner_list(self):
        client, store   =   self._client(has_ecommerce = True)
        Product.objects.create(store = store, name = 'Calza', price = 10, stock = 3)
        response        =   client.get(PRODUCTS_URL)
        item            =   response.data[0] if isinstance(response.data, list) else response.data['results'][0]
        self.assertEqual(item['stock'], 3)


class RemoveBackgroundGateTests(TestCase):
    """El editor de fondo es un recurso caro: solo con catálogo habilitado."""

    def setUp(self):
        # Mismo motivo que CatalogOwnerIsolationTests: el cache de beneficios
        # se keyea por PK y SQLite reutiliza PKs entre tests.
        cache.clear()

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
        self.assertEqual(calza['discount'], {'name': 'Promo', 'percent': 25, 'ends_at': None, 'campaign': None})
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

    def test_scheduled_discount_skips_product_with_manual_offer(self):
        #Un producto con oferta manual no recibe el descuento programado
        #aunque el descuento bajaría más: se salta y conserva su oferta.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Calza', price = 100, offer_price = 60)
        Discount.objects.create(
            store = store, name = 'Promo', percent = 50, scope = 'all',
            starts_at = timezone.now() - timedelta(hours = 1),
        )
        products        =   self._catalog().data['products']
        calza           =   next(p for p in products if p['name'] == 'Calza')
        self.assertEqual(float(calza['offer_price']), 60.0)
        self.assertIsNone(calza['discount'])
        #El panel del dueño tampoco anuncia el descuento sobre ese producto.
        user            =   store.user.user
        client          =   APIClient()
        client.force_authenticate(user = user)
        item            =   next(p for p in client.get(PRODUCTS_URL).data if p['name'] == 'Calza')
        self.assertIsNone(item['discount_offer'])
        self.assertEqual(item['discount_names'], [])

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

    def test_event_flag_and_count(self):
        #?event=1 deja solo los productos cuyo descuento programado vigente
        #firma su oferta (effective_discount). event_count es el total sin
        #filtrar — alimenta el checkbox "En evento", que la web solo muestra
        #cuando hay algo que filtrar. Una oferta manual no cuenta como evento.
        #has_discounts es premium: sin él running_discounts_of devuelve
        #vacío y no habría evento que filtrar — va en el mismo _grant.
        _, profile      =   _make_user('duenio-evento')
        _grant(profile, has_public_link = True, has_discounts = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        Product.objects.create(store = store, name = 'Evento', price = 100)
        Product.objects.create(store = store, name = 'Manual', price = 100, offer_price = 60)
        Product.objects.create(store = store, name = 'Llano', price = 100)
        Discount.objects.create(
            store = store, name = 'Hot Sale', percent = 25, scope = 'products',
            starts_at = timezone.now() - timedelta(hours = 1),
        ).products.add(Product.objects.get(store = store, name = 'Evento'))
        response        =   self._catalog()
        self.assertEqual(response.data['event_count'], 1)
        response        =   self._catalog(event = '1')
        self.assertEqual([p['name'] for p in response.data['products']], ['Evento'])
        #El evento convive con el resto de filtros: ?offer=1 también lo ve.
        response        =   self._catalog(offer = '1', event = '1')
        self.assertEqual([p['name'] for p in response.data['products']], ['Evento'])

    def test_inactive_and_exclusive_products_never_listed(self):
        #Contrato de la ficha pública (/tienda/:slug/producto/:id): el front
        #resuelve el producto dentro de products[] — uno inactivo, exclusivo
        #o inexistente cae en su estado "ya no está disponible". El endpoint
        #no devuelve 404 por producto (no existe retrieve público): la
        #garantía es que NUNCA viajen en la vidriera.
        store           =   self._setup()
        Product.objects.create(store = store, name = 'Visible', price = 10)
        Product.objects.create(store = store, name = 'Apagado', price = 10, is_active = False)
        Product.objects.create(store = store, name = 'Miembros', price = 10, is_exclusive = True)
        response        =   self._catalog()
        self.assertEqual([p['name'] for p in response.data['products']], ['Visible'])

    def test_facets_counts_and_price_max_payload(self):
        #El panel de filtros se alimenta del propio payload: facetas por
        #atributo con su conteo (solo con categoría elegida), products_count
        #por taxonomía, totales de ofertas/novedades y techo de precio.
        store           =   self._setup()
        calzas          =   Category.objects.create(store = store, name = 'Calzas')
        Product.objects.create(store = store, name = 'A', price = 10, category = calzas, features = {'Talle': 'S, M'})
        Product.objects.create(store = store, name = 'B', price = 90, category = calzas, features = {'Talle': 'M'}, offer_price = 45)
        Product.objects.create(store = store, name = 'C', price = 10, is_active = False, features = {'Talle': 'XXL'})
        response        =   self._catalog()
        #Sin categoría elegida no viajan facetas (el panel no mezcla los
        #atributos de todo el catálogo); los conteos sí son globales.
        self.assertEqual(response.data['facets'], [])
        calza           =   next(c for c in response.data['categories'] if c['name'] == 'Calzas')
        self.assertEqual(calza['products_count'], 2)
        self.assertEqual(response.data['offer_count'], 1)
        self.assertEqual(response.data['new_count'], 2)
        #El techo usa el precio efectivo: B cuesta 90 de lista pero se
        #muestra a 45 (su oferta), así que el máximo visible es 45.
        self.assertEqual(float(response.data['price_max']), 45.0)
        response        =   self._catalog(category = str(calzas.id))
        talle           =   next(f for f in response.data['facets'] if f['name'] == 'Talle')
        self.assertEqual(talle['values'], [{'value': 'M', 'count': 2}, {'value': 'S', 'count': 1}])
        self.assertFalse(any(v['value'] == 'XXL' for v in talle['values']))

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
        #Sin selección no viajan facetas: el panel aparece al elegir una
        #categoría, acotado a ella (o combinado si son varias).
        response        =   self._catalog()
        self.assertEqual(response.data['facets'], [])
        #Con varias categorías seleccionadas los atributos se combinan —
        #los schemas se aplican en el orden en que llegan las categorías.
        response        =   self._catalog(category = f'{remeras.id},{electro.id}')
        self.assertEqual([f['name'] for f in response.data['facets']], ['Color', 'Talle', 'Voltaje'])
        #Con categoría, solo sus atributos — y en el orden de su schema
        #(Color primero aunque Talle tenga más conteo).
        response        =   self._catalog(category = str(remeras.id))
        self.assertEqual([f['name'] for f in response.data['facets']], ['Color', 'Talle'])
        response        =   self._catalog(category = str(electro.id))
        self.assertEqual([f['name'] for f in response.data['facets']], ['Voltaje'])

    def test_facets_merge_same_feature_across_categories(self):
        #Regresión: dos categorías comparten el atributo con casing distinto
        #("Color"/"color") y los productos guardan el valor igualmente
        #variado ("verde"/"Verde") — el match ya ignora mayúsculas, así que
        #el panel tiene que agrupar todo en UN grupo y UN valor por clave;
        #sin esto se veían "Color" y "color" duplicados con "verde" x2.
        store           =   self._setup()
        pastas          =   Category.objects.create(store = store, name = 'Pastas de aceituna', feature_schema = ['Color'])
        aceitunas       =   Category.objects.create(store = store, name = 'Aceitunas')
        Product.objects.create(store = store, name = 'A', price = 10, category = pastas, features = {'Color': 'verde'})
        Product.objects.create(store = store, name = 'B', price = 10, category = aceitunas, features = {'color': 'Verde'})
        Product.objects.create(store = store, name = 'C', price = 10, category = aceitunas, features = {'COLOR': 'rojo'})
        response        =   self._catalog(category = f'{pastas.id},{aceitunas.id}')
        self.assertEqual(len(response.data['facets']), 1)
        color           =   response.data['facets'][0]
        #El casing que viaja es el que el dueño declaró en el feature_schema.
        self.assertEqual(color['name'], 'Color')
        verde           =   next(v for v in color['values'] if v['value'].casefold() == 'verde')
        self.assertEqual(verde['count'], 2)
        self.assertEqual(sum(v['count'] for v in color['values']), 3)
        #El filtro sigue matcheando cualquier casing del valor guardado.
        response        =   self._catalog(features = '{"Color": ["verde"]}')
        self.assertEqual(sorted(p['name'] for p in response.data['products']), ['A', 'B'])


class ReviewTests(TestCase):
    """
    Opiniones de compradores registrados (solo tiendas ecommerce): el
    listado es público; el alta exige Bearer customer_access y la
    identidad sale de la cuenta — el dueño modera borrando.
    """

    def setUp(self):
        #El throttle store_review (10/h por IP) comparte la cache entre
        #tests: sin limpiarla los POST acumulados devuelven 429 falsos.
        cache.clear()

    def _setup(self, comments = True, reviews = True, ecommerce = True):
        _, profile      =   _make_user('duenio')
        benefits        =   {
            'has_public_link'       :   True,
            'has_product_comments'  :   True,
            'has_customization'     :   True,
        }
        if ecommerce:
            benefits['has_ecommerce']       =   True
            benefits['has_customer_auth']   =   True
        _grant(profile, **benefits)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)
        StoreCustomization.objects.create(
            store = store, show_reviews = reviews, show_comments = comments,
        )
        product         =   Product.objects.create(store = store, name = 'Calza', price = 100)
        return store, product

    def _buyer(self):
        """Cliente comprador autenticado (Bearer customer_access)."""
        if getattr(self, '_buyer_ctx', None) is None:
            from StoreApp.domains.customers.models import Customer
            from StoreApp.domains.customers.services.tokens import issue_customer_tokens
            customer    =   Customer.objects.create(
                email       =   'maria@example.com',
                password    =   'x',
                first_name  =   'Maria',
                last_name   =   'Perez',
            )
            access, _   =   issue_customer_tokens(customer)
            client      =   APIClient()
            client.credentials(HTTP_AUTHORIZATION = f'Bearer {access}')
            self._buyer_ctx =   (client, customer)
        return self._buyer_ctx

    def _post(self, product, client = None, **extra):
        if client is None:
            client, _customer =   self._buyer()
        return client.post(PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id), extra)

    def test_review_create_vote_and_comment(self):
        _, product      =   self._setup()
        response        =   self._post(product, is_positive = True, text = 'Excelente calidad')
        self.assertEqual(response.status_code, 201)
        review          =   ProductReview.objects.get(product = product)
        self.assertTrue(review.is_positive)
        self.assertEqual(review.text, 'Excelente calidad')

    def test_review_identity_comes_from_customer_account(self):
        #La identidad la fija la sesión: name/email del payload se ignoran
        #y la opinión queda ligada al Customer que la escribió.
        _, product      =   self._setup()
        client, customer    =   self._buyer()
        response        =   client.post(
            PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id),
            {'is_positive': True, 'text': 'Genial', 'name': 'Hackeado', 'email': 'otro@x.com'},
        )
        self.assertEqual(response.status_code, 201)
        review          =   ProductReview.objects.get(product = product)
        self.assertEqual(review.customer, customer)
        self.assertEqual(review.name, 'Maria')
        self.assertEqual(review.surname, 'Perez')
        self.assertEqual(review.email, 'maria@example.com')

    def test_review_post_requires_customer_session(self):
        _, product      =   self._setup()
        url             =   PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)
        #Anónimo -> 401; el GET del listado sigue público.
        self.assertEqual(APIClient().post(url, {'is_positive': True}).status_code, 401)
        self.assertEqual(APIClient().get(url).status_code, 200)
        #El JWT del dueño (SaaS) no es credencial de comprador -> 401.
        from rest_framework_simplejwt.tokens import AccessToken
        owner_token     =   AccessToken.for_user(product.store.user.user)
        client          =   APIClient()
        client.credentials(HTTP_AUTHORIZATION = f'Bearer {owner_token}')
        self.assertEqual(client.post(url, {'is_positive': True}).status_code, 401)
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_reviews_require_ecommerce_plan(self):
        #Sin has_ecommerce (plan premium u otro) las opiniones no existen:
        #ni el alta ni el listado — 404 como con los toggles apagados.
        _, product      =   self._setup(ecommerce = False)
        client, _       =   self._buyer()
        url             =   PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)
        self.assertEqual(client.post(url, {'is_positive': True}).status_code, 404)
        self.assertEqual(APIClient().get(url).status_code, 404)

    def test_reviews_require_ecommerce_flag(self):
        #store_has_reviews exige has_ecommerce: quitarlo por separado
        #cierra las opiniones por completo (404) aunque los toggles
        #queden en True.
        _, product      =   self._setup()
        PlanBenefit.objects.filter(benefit__code = 'has_ecommerce').delete()
        cache.clear()
        client, _       =   self._buyer()
        url             =   PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)
        self.assertEqual(client.post(url, {'is_positive': True}).status_code, 404)
        self.assertEqual(APIClient().get(url).status_code, 404)

    def test_reviews_require_customer_auth_flag(self):
        #Ídem con has_customer_auth: sin registro de compradores las
        #opiniones no existen (404) aunque los toggles queden en True.
        _, product      =   self._setup()
        PlanBenefit.objects.filter(benefit__code = 'has_customer_auth').delete()
        cache.clear()
        client, _       =   self._buyer()
        url             =   PUBLIC_REVIEWS.format(slug = 'mi-tienda', pid = product.id)
        self.assertEqual(client.post(url, {'is_positive': True}).status_code, 404)
        self.assertEqual(APIClient().get(url).status_code, 404)

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
        _grant(other, has_public_link = True, has_product_comments = True, has_ecommerce = True, has_customer_auth = True)
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


BULK_PRICES_URL   =   '/api/products/bulk-prices/'
IMPORT_PRICES_URL =   '/api/products/import-prices/'
EXPORT_PRICES_URL =   '/api/products/export-prices/'


class PriceUpdateTests(TestCase):
    """
    Actualización masiva e importación de precios del dueño: bulk por
    alcance con redondeo y clamp en 0, CSV por id/nombre con dry_run y
    reporte de filas sin matchear. Todo scopeado a su tienda y al plan.
    """

    def setUp(self):
        cache.clear()

    def _owner(self, with_plan = True):
        user, profile   =   _make_user('precios')
        if with_plan:
            _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'tienda-precios')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def test_bulk_percent_all(self):
        client, store   =   self._owner()
        Product.objects.create(store = store, name = 'A', price = 100)
        Product.objects.create(store = store, name = 'B', price = 50)
        response        =   client.post(BULK_PRICES_URL, {'mode': 'percent', 'value': '10'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated'], 2)
        self.assertEqual(list(Product.objects.order_by('name').values_list('price', flat = True)), [110, 55])

    def test_bulk_scope_and_rounding(self):
        client, store   =   self._owner()
        cat             =   Category.objects.create(store = store, name = 'Indumentaria')
        Product.objects.create(store = store, name = 'A', price = 101, category = cat)
        Product.objects.create(store = store, name = 'B', price = 50)
        response        =   client.post(BULK_PRICES_URL, {'mode': 'percent', 'value': '10', 'scope': 'category', 'category': cat.id, 'rounding': 'ten'}, format = 'json')
        self.assertEqual(response.data['updated'], 1)
        self.assertEqual(Product.objects.get(name = 'A').price, 110)
        self.assertEqual(Product.objects.get(name = 'B').price, 50)

    def test_bulk_delta_clamps_at_zero(self):
        client, store   =   self._owner()
        Product.objects.create(store = store, name = 'A', price = 30)
        response        =   client.post(BULK_PRICES_URL, {'mode': 'delta', 'value': '-50'}, format = 'json')
        self.assertEqual(response.data['updated'], 1)
        self.assertEqual(Product.objects.get(name = 'A').price, 0)

    def test_bulk_rejects_foreign_category_and_bad_input(self):
        client, store   =   self._owner()
        _, profile2     =   _make_user('otro')
        store2          =   Store.objects.create(user = profile2, slug = 'otra')
        foreign_cat     =   Category.objects.create(store = store2, name = 'Ajena')
        response        =   client.post(BULK_PRICES_URL, {'mode': 'percent', 'value': '10', 'scope': 'category', 'category': foreign_cat.id}, format = 'json')
        self.assertEqual(response.status_code, 400)
        response        =   client.post(BULK_PRICES_URL, {'mode': 'percent', 'value': '-100'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_bulk_needs_plan(self):
        client, _       =   self._owner(with_plan = False)
        self.assertEqual(client.post(BULK_PRICES_URL, {'mode': 'set', 'value': '10'}, format = 'json').status_code, 403)

    def _csv(self, text):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('precios.csv', text.encode('utf-8'), content_type = 'text/csv')

    def test_import_matches_and_dry_run(self):
        client, store   =   self._owner()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        Product.objects.create(store = store, name = 'Remera', price = 80)
        payload         =   'id,nombre,precio,oferta\n,Calza,"1.234,56",\n,Remera,70,60\n999,Falta,10,\n'
        dry             =   client.post(IMPORT_PRICES_URL, {'file': self._csv(payload), 'dry_run': '1'}, format = 'multipart')
        self.assertEqual(dry.status_code, 200)
        self.assertEqual(dry.data['matched'], 2)
        self.assertEqual(len(dry.data['skipped']), 1)
        self.assertEqual(Product.objects.get(name = 'Calza').price, 100)
        real            =   client.post(IMPORT_PRICES_URL, {'file': self._csv(payload)}, format = 'multipart')
        self.assertEqual(real.data['updated'], 2)
        self.assertEqual(str(Product.objects.get(name = 'Calza').price), '1234.56')
        self.assertEqual(str(Product.objects.get(name = 'Remera').offer_price), '60.00')

    def test_import_offer_cleared_when_price_rises(self):
        #La oferta vieja dejaría de ser menor que el nuevo precio: se limpia.
        client, store   =   self._owner()
        Product.objects.create(store = store, name = 'Calza', price = 100, offer_price = 90)
        response        =   client.post(IMPORT_PRICES_URL, {'file': self._csv('nombre,precio\nCalza,50\n')}, format = 'multipart')
        self.assertEqual(response.status_code, 200)
        calza           =   Product.objects.get(name = 'Calza')
        self.assertEqual(calza.price, 50)
        self.assertIsNone(calza.offer_price)

    def test_import_rejects_bad_file(self):
        client, _       =   self._owner()
        response        =   client.post(IMPORT_PRICES_URL, {'file': self._csv('a,b\n1,2\n')}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_export_csv(self):
        client, store   =   self._owner()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        response        =   client.get(EXPORT_PRICES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Calza', response.content.decode('utf-8-sig'))


class SpecialOfferCampaignTests(TestCase):
    """
    Campañas de ofertas (calendario del sistema): el descuento etiquetado
    solo descuenta mientras la campaña está vigente (su ventana anual
    recurrente, además de la propia). El listado /api/offers/ es público
    y la escritura es solo staff; la campaña no pertenece a ninguna
    tienda (aislamiento intacto: sigue sin viajar store_id).
    """

    def setUp(self):
        cache.clear()

    def _store(self, premium = True):
        _, profile      =   _make_user('duenio')
        _grant(profile, has_public_link = True, has_discounts = premium)
        return Store.objects.create(user = profile, slug = 'mi-tienda', is_published = True)

    def _campaign(self, running = True):
        now             =   timezone.now()
        if running:
            month, day  =   (now - timedelta(days = 1)).month, (now - timedelta(days = 1)).day
        else:
            other       =   now + timedelta(days = 180)
            month, day  =   other.month, other.day
        return SpecialOfferCampaign.objects.create(
            slug = f'camp-{running}', name = f'Camp {running}', accent = '#E64415',
            month = month, day = day, duration_days = 3,
        )

    def _discount(self, store, campaign = None):
        return Discount.objects.create(
            store = store, name = 'Promo', percent = 25, scope = 'all',
            campaign = campaign,
            starts_at = timezone.now() - timedelta(hours = 1),
        )

    def _calza(self, response):
        return next(p for p in response.data['products'] if p['name'] == 'Calza')

    def _catalog(self):
        return APIClient().get(PUBLIC_CATALOG.format(slug = 'mi-tienda'))

    def test_campaign_outside_window_does_not_discount(self):
        #Campaña que arranca en ~6 meses: el descuento queda guardado pero
        #no aplica — una promo "Black Friday" no puede correr en marzo.
        store           =   self._store()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        self._discount(store, self._campaign(running = False))
        calza           =   self._calza(self._catalog())
        self.assertIsNone(calza['offer_price'])
        self.assertIsNone(calza['discount'])

    def test_running_campaign_discount_applies_and_exposes_payload(self):
        #Dentro de la ventana anual, el descuento firma la oferta y viaja
        #la campaña (aditivo) con su acento y etiqueta.
        store           =   self._store()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        campaign        =   self._campaign(running = True)
        self._discount(store, campaign)
        response        =   self._catalog()
        calza           =   self._calza(response)
        self.assertEqual(float(calza['offer_price']), 75.0)
        payload         =   calza['discount']['campaign']
        self.assertEqual(payload['slug'], campaign.slug)
        self.assertEqual(payload['accent'], campaign.accent)
        self.assertIn('label_url', payload)
        self.assertEqual(response.data['promotions'][0]['campaign']['slug'], campaign.slug)

    def test_discount_without_campaign_behaves_as_before(self):
        #Compat: un descuento sin campaña aplica igual que siempre (la
        #única fuente de verdad sigue siendo su propia ventana).
        store           =   self._store()
        Product.objects.create(store = store, name = 'Calza', price = 100)
        self._discount(store)
        calza           =   self._calza(self._catalog())
        self.assertEqual(float(calza['offer_price']), 75.0)
        self.assertIsNone(calza['discount']['campaign'])

    def test_campaign_gate_still_requires_has_discounts(self):
        #Sin el flag premium ni la campaña salva: la lista sale vacía.
        store           =   self._store(premium = False)
        Product.objects.create(store = store, name = 'Calza', price = 100)
        self._discount(store, self._campaign(running = True))
        calza           =   self._calza(self._catalog())
        self.assertIsNone(calza['offer_price'])
        self.assertIsNone(calza['discount'])

    def test_campaign_crossing_year_end(self):
        #Año Nuevo arranca en diciembre y corre en enero: la ventana del
        #año anterior se evalúa aunque la del año nuevo no llegó.
        campaign        =   SpecialOfferCampaign(
            slug = 'ano-nuevo', name = 'Año Nuevo', accent = '#0E7C7B',
            month = 12, day = 28, duration_days = 6,
        )
        self.assertTrue(campaign.is_running(timezone.datetime(2030, 1, 1, 12, 0, tzinfo = UTC)))
        self.assertTrue(campaign.is_running(timezone.datetime(2030, 12, 30, 12, 0, tzinfo = UTC)))
        self.assertFalse(campaign.is_running(timezone.datetime(2030, 1, 10, 12, 0, tzinfo = UTC)))

    def test_campaign_window_returns_coherent_occurrence(self):
        #window() devuelve el par (inicio, fin) del tramo vigente o del
        #próximo: fin = inicio + duration_days, aunque cruce de año.
        campaign        =   SpecialOfferCampaign(
            slug = 'win', name = 'W', accent = '#000',
            month = 12, day = 28, duration_days = 6,
        )
        start, end      =   campaign.window(timezone.datetime(2030, 1, 1, tzinfo = UTC))
        self.assertEqual((start.year, start.month, start.day), (2029, 12, 28))
        self.assertEqual(end - start, timedelta(days = 6))
        start, end      =   campaign.window(timezone.datetime(2030, 1, 10, tzinfo = UTC))
        self.assertEqual((start.year, start.month, start.day), (2030, 12, 28))
        self.assertEqual(end - start, timedelta(days = 6))

    def test_owner_can_tag_discount_with_active_campaign(self):
        #El dueño etiqueta su descuento por id de campaña; el listado le
        #devuelve el bloque de campaña y el estado real (unavailable
        #fuera de la ventana de la campaña).
        store           =   self._store()
        campaign        =   self._campaign(running = False)
        client          =   APIClient()
        client.force_authenticate(user = store.user.user)
        response        =   client.post(DISCOUNTS_URL, {
            'name': 'Promo', 'percent': 25, 'scope': 'all',
            'campaign': campaign.pk,
            'starts_at': (timezone.now() - timedelta(hours = 1)).isoformat(),
        }, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['item']['campaign']['slug'], campaign.slug)
        #Fuera de la ventana de la campaña el descuento queda "no
        #disponible": está activo pero la oferta especial no corre.
        self.assertEqual(response.data['item']['status'], 'unavailable')

    def test_offers_list_is_public_and_write_is_staff_only(self):
        self._campaign(running = True)
        response        =   APIClient().get(OFFERS_URL)
        self.assertEqual(response.status_code, 200)
        items           =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(items[0]['slug'], 'camp-True')
        self.assertIn('is_running', items[0])
        #Anónimo y dueño no-staff no escriben el calendario.
        self.assertIn(APIClient().post(OFFERS_URL, {}, format = 'json').status_code, (401, 403))
        user, _         =   _make_user('duenio2')
        client          =   APIClient()
        client.force_authenticate(user = user)
        self.assertEqual(client.post(OFFERS_URL, {}, format = 'json').status_code, 403)

    def test_offer_label_404_without_label_key(self):
        campaign        =   self._campaign(running = True)
        response        =   APIClient().get(f'{OFFERS_URL}{campaign.slug}/label/')
        #Sin label_key (o sin R2 configurado en tests) no hay nada que servir.
        self.assertEqual(response.status_code, 404)

    def test_seed_command_is_idempotent(self):
        from django.core.management import call_command
        call_command('seed_special_offers')
        self.assertEqual(SpecialOfferCampaign.objects.count(), 15)
        call_command('seed_special_offers', '--only', 'hot-sale')
        self.assertEqual(SpecialOfferCampaign.objects.count(), 15)
