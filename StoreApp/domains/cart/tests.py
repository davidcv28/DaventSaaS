"""
Tests del dominio cart (e-commerce DAVENT — track B).

Cobertura:
- Auth de comprador obligatoria (CustomerJWTAuthentication + IsCustomer);
  invitado → 401/403 (guest checkout NO soportado: el pedido exige
  cuenta — decisión documentada en orders.services.checkout).
- Gate de venta: tienda no publicada/bloqueada/sin ecommerce/fiscal → 404.
- Upsert idempotente por (cart, product), PATCH/DELETE por id, clear.
- Validaciones: qty 1..100, producto de OTRA tienda rechazado,
  producto inactivo rechazado, exclusivo sin membresía rechazado,
  stock insuficiente rechazado.
- Precios SIEMPRE server-side (payload con unit_price/line_total
  calculados; el body nunca acepta montos).
- Aislamiento: un carrito por (customer, store) — dos tiendas = dos
  carritos independientes.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.cart.models import Cart, CartItem
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.stores.models import (
    Store,
    StoreCustomization,
    StoreFiscalProfile,
)
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

CUIT_VALIDO   =   '20123456786'


def _grant(profile, *codes):
    suscription =   getattr(profile, 'suscription', None)
    plan    =   suscription.plan_suscription if suscription is not None else SuscriptionPlan.objects.create(name = f'Plan {profile.pk}')
    for code in codes:
        benefit =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': Benefit.FLAG})[0]
        PlanBenefit.objects.get_or_create(plan = plan, benefit = benefit, defaults = {'enabled': True})
    if suscription is None:
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + datetime.timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )


def _make_owner(username, *, ecommerce = True):
    user    =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'x')
    profile =   UserProfile.objects.create(user = user)
    #plan_benefits_of cachea por PK y SQLite las reutiliza entre tests.
    cache.delete(f'planben:{profile.pk}')
    if ecommerce:
        _grant(profile, 'has_ecommerce')
    return profile


def _make_store(slug, *, sellable = True, published = True, blocked = False, ecommerce = True):
    profile =   _make_owner(f'owner-{slug}', ecommerce = ecommerce)
    store   =   Store.objects.create(
        user            =   profile,
        slug            =   slug,
        is_published    =   published,
        is_blocked      =   blocked,
    )
    if sellable:
        StoreCustomization.objects.create(store = store, ecommerce_enabled = True)
        StoreFiscalProfile.objects.create(
            store           =   store,
            legal_name      =   'Prueba SA',
            tax_condition   =   'RI',
            cuit            =   CUIT_VALIDO,
            fiscal_address  =   'Av. Siempre Viva 1',
        )
    elif published:
        #Tienda publicada pero SIN ecommerce/fiscal: orders_enabled=False.
        StoreCustomization.objects.create(store = store, ecommerce_enabled = False)
    return store


def _make_customer(email = 'ana@example.com'):
    customer    =   Customer(email = email, first_name = 'Ana', last_name = 'Perez')
    customer.set_password('Comprador#2026')
    customer.save()
    return customer


def _bearer(client, customer):
    from StoreApp.domains.customers.services.tokens import issue_customer_tokens
    access, _refresh =   issue_customer_tokens(customer)
    client.credentials(HTTP_AUTHORIZATION = f'Bearer {access}')
    return access


def _make_product(store, name = 'Remera', price = '100.00', **kwargs):
    return Product.objects.create(store = store, name = name, price = Decimal(price), **kwargs)


class CartApiTests(TestCase):
    client_class    =   APIClient

    def setUp(self):
        self.store      =   _make_store('mitienda')
        self.store_b    =   _make_store('otratienda')
        self.customer   =   _make_customer()
        self.client     =   APIClient()
        _bearer(self.client, self.customer)
        self.product    =   _make_product(self.store, price = '100.00')

    @property
    def cart_url(self):
        return f'/api/cart/{self.store.slug}/'

    @property
    def items_url(self):
        return f'/api/cart/{self.store.slug}/items/'

    #AUTH / GATE
    def test_guest_gets_401(self):
        anon    =   APIClient()
        self.assertIn(anon.get(self.cart_url).status_code, (401, 403))
        self.assertIn(anon.post(self.items_url, {'product_id': self.product.pk, 'qty': 1}, format = 'json').status_code, (401, 403))

    def test_store_without_ecommerce_benefit_is_404(self):
        #Sesión de cliente válida, tienda "vendible" pero el plan del
        #dueño perdió has_ecommerce → el carrito de ESA tienda queda
        #inaccesible (misma semántica 404 que tienda cerrada).
        closed  =   _make_store('sinplan', ecommerce = False)
        response    =   self.client.get(f'/api/cart/{closed.slug}/')
        self.assertEqual(response.status_code, 404)

    def test_store_without_orders_enabled_is_404(self):
        closed  =   _make_store('cerrada', sellable = False)
        _bearer(self.client, self.customer)
        response    =   self.client.get(f'/api/cart/{closed.slug}/')
        self.assertEqual(response.status_code, 404)

    def test_unpublished_store_is_404(self):
        hidden  =   _make_store('oculta', published = False)
        response    =   self.client.get(f'/api/cart/{hidden.slug}/')
        self.assertEqual(response.status_code, 404)

    #READ / EMPTY
    def test_get_empty_cart_does_not_create_row(self):
        response    =   self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        data        =   response.json()
        self.assertEqual(data['items'], [])
        self.assertEqual(data['item_count'], 0)
        self.assertFalse(Cart.objects.exists())

    #ADD / PAYLOAD
    def test_add_item_returns_server_prices(self):
        response    =   self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': 2}, format = 'json')
        self.assertEqual(response.status_code, 200)
        data        =   response.json()
        self.assertEqual(len(data['items']), 1)
        item        =   data['items'][0]
        self.assertEqual(item['product_id'], self.product.pk)
        self.assertEqual(item['qty'], 2)
        self.assertEqual(item['unit_price'], '100.00')
        self.assertEqual(item['line_total'], '200.00')
        self.assertEqual(data['items_total'], '200.00')
        self.assertTrue(item['purchasable'])

    def test_upsert_same_product_replaces_qty(self):
        self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': 1}, format = 'json')
        response    =   self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': 3}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().qty, 3)

    def test_offer_price_used_as_unit_price(self):
        offer   =   _make_product(self.store, name = 'Jean', price = '100.00', offer_price = '70.00')
        response    =   self.client.post(self.items_url, {'product_id': offer.pk, 'qty': 1}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'][0]['unit_price'], '70.00')

    #VALIDATIONS
    def test_product_of_other_store_rejected(self):
        foreign =   _make_product(self.store_b, name = 'Ajeno')
        response    =   self.client.post(self.items_url, {'product_id': foreign.pk, 'qty': 1}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CartItem.objects.exists())

    def test_inactive_product_rejected(self):
        dead    =   _make_product(self.store, name = 'Baja', is_active = False)
        response    =   self.client.post(self.items_url, {'product_id': dead.pk, 'qty': 1}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_exclusive_product_rejected_without_membership(self):
        exclusive   =   _make_product(self.store, name = 'Exclusivo', is_exclusive = True)
        response    =   self.client.post(self.items_url, {'product_id': exclusive.pk, 'qty': 1}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_qty_bounds_enforced(self):
        for qty in (0, -2, 101, 'abc'):
            response    =   self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': qty}, format = 'json')
            self.assertEqual(response.status_code, 400, f'qty={qty}')

    def test_stock_insufficient_rejected(self):
        limited =   _make_product(self.store, name = 'Único', stock = 2)
        self.assertEqual(
            self.client.post(self.items_url, {'product_id': limited.pk, 'qty': 3}, format = 'json').status_code, 400)
        self.assertEqual(
            self.client.post(self.items_url, {'product_id': limited.pk, 'qty': 2}, format = 'json').status_code, 200)

    #PATCH / DELETE / CLEAR
    def _seed_cart(self, qty = 2):
        self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': qty}, format = 'json')
        return CartItem.objects.get()

    def test_patch_item_qty(self):
        item    =   self._seed_cart(2)
        response    =   self.client.patch(f'{self.items_url}{item.pk}/', {'qty': 5}, format = 'json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.qty, 5)

    def test_patch_item_of_other_cart_rejected(self):
        #Item de OTRA tienda del mismo customer: la ruta de store A no lo
        #toca (el service filtra por cart → ValidationError → 400).
        cart_b  =   Cart.objects.create(customer = self.customer, store = self.store_b)
        prod_b  =   _make_product(self.store_b, name = 'B', price = '10.00')
        item_b  =   CartItem.objects.create(cart = cart_b, product = prod_b, qty = 1)
        response    =   self.client.patch(f'{self.items_url}{item_b.pk}/', {'qty': 4}, format = 'json')
        self.assertEqual(response.status_code, 400)
        item_b.refresh_from_db()
        self.assertEqual(item_b.qty, 1)

    def test_delete_item(self):
        item    =   self._seed_cart()
        response    =   self.client.delete(f'{self.items_url}{item.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'], [])
        self.assertFalse(CartItem.objects.exists())

    def test_clear_cart(self):
        self._seed_cart()
        _make_product(self.store, name = 'Otro', price = '5.00')
        self.client.post(self.items_url, {'product_id': Product.objects.get(name = 'Otro').pk, 'qty': 1}, format = 'json')
        response    =   self.client.delete(self.items_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 0)

    #AISLAMIENTO
    def test_cart_is_per_store(self):
        other   =   _make_product(self.store_b, name = 'De B', price = '50.00')
        self.client.post(self.items_url, {'product_id': self.product.pk, 'qty': 1}, format = 'json')
        self.client.post(f'/api/cart/{self.store_b.slug}/items/', {'product_id': other.pk, 'qty': 1}, format = 'json')
        self.assertEqual(Cart.objects.count(), 2)
        cart_a  =   Cart.objects.get(store = self.store)
        cart_b  =   Cart.objects.get(store = self.store_b)
        self.assertEqual(cart_a.items.count(), 1)
        self.assertEqual(cart_b.items.count(), 1)
        #Y el carrito de A no mezcla el producto de B.
        data_a  =   self.client.get(self.cart_url).json()
        self.assertEqual(data_a['items'][0]['product_id'], self.product.pk)
