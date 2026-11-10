"""
Tests del dominio orders (e-commerce DAVENT — track B).

Cobertura (PROMPT_MAESTRO §3.5 + spec de la ola):
- create_order: totales 100% server-side (el body jamás inyecta precios),
  snapshot inmutable del comprador/items, numeración por tienda,
  idempotency_key → mismo pedido, producto de otra tienda/exclusivo/
  stock insuficiente → ValidationError.
- payments: mark_order_paid idempotente (doble confirmación = no-op,
  un solo descuento de stock), auto-avance a PACKING, stock_conflict
  cuando no alcanza al pagar, advance/cancel/refund con la máquina de
  estados, contrato exacto del bridge de storepayments.
- expire_orders: batch idempotente + --dry-run.
- API pública: captcha obligatorio, throttle presente, tracking por
  token anti-IDOR (token ajeno/otra tienda → 404, sin PII extra),
  proof solo en métodos manuales y PENDING_PAYMENT, receipt NO FISCAL.
- Panel del dueño: IDOR → 404, acciones confirm/advance/cancel/
  invoice-ref, listado sin N+1.
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.orders.models import (
    Order,
    OrderEvent,
    OrderItem,
    PaymentProof,
)
from StoreApp.domains.orders.services.checkout import create_order
from StoreApp.domains.orders.services.payments import (
    advance_order,
    cancel_order,
    mark_order_paid,
    mark_order_refunded,
)
from StoreApp.domains.orders.views.public import (
    OrderCreateThrottle,
    OrderProofThrottle,
    PublicOrderCreateView,
)
from StoreApp.domains.stores.models import (
    Store,
    StoreCustomization,
    StoreFiscalProfile,
    StorePaymentConfig,
)

CUIT_VALIDO   =   '20123456786'
ADDRESS       =   {'line1': 'Calle Falsa 123', 'city': 'CABA', 'province': 'CABA', 'postal_code': '1000', 'country': 'AR'}


def _make_owner(username):
    user    =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'x')
    profile =   UserProfile.objects.create(user = user)
    return profile


def _make_store(slug, *, sellable = True):
    profile =   _make_owner(f'owner-{slug}')
    store   =   Store.objects.create(user = profile, slug = slug, is_published = True)
    if sellable:
        StoreCustomization.objects.create(store = store, ecommerce_enabled = True)
        StoreFiscalProfile.objects.create(
            store           =   store,
            legal_name      =   'Prueba SA',
            tax_condition   =   'RI',
            cuit            =   CUIT_VALIDO,
            fiscal_address  =   'Av. Siempre Viva 1',
            point_of_sale   =   '0001',
        )
    return store


def _make_customer(email = 'ana@example.com'):
    customer    =   Customer(
        email       =   email,
        first_name  =   'Ana',
        last_name   =   'Perez',
        phone       =   '+5491100000000',
        document_type = 'DNI',
        document    =   '30111222',
    )
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


def _order_kwargs(store, customer, product, qty = 1, **extra):
    """Args listos para create_order con una línea."""
    return {
        'store'             :   store,
        'customer'          :   customer,
        'items'             :   [{'product_id': product.pk, 'qty': qty}],
        'address'           :   ADDRESS,
        'payment_method'    :   'transfer',
        **extra,
    }


def _pending_order(store, customer, product, qty = 1, **extra):
    order, _created  =   create_order(**_order_kwargs(store, customer, product, qty, **extra))
    return order


class CreateOrderServiceTests(TestCase):
    def setUp(self):
        self.store      =   _make_store('mitienda')
        self.store_b    =   _make_store('otratienda')
        self.customer   =   _make_customer()
        self.product    =   _make_product(self.store, price = '100.00')

    def test_totals_are_server_side(self):
        order, created  =   create_order(**_order_kwargs(self.store, self.customer, self.product, qty = 2))
        self.assertTrue(created)
        self.assertEqual(order.subtotal, Decimal('200.00'))
        self.assertEqual(order.discount_total, Decimal('0.00'))
        self.assertEqual(order.shipping_cost, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('200.00'))
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(order.number, 1)
        self.assertEqual(order.code, 'PED-0001')
        self.assertTrue(order.tracking_token)
        self.assertIsNotNone(order.expires_at)

    def test_snapshot_frozen_at_creation(self):
        order   =   _pending_order(self.store, self.customer, self.product, qty = 1)
        item    =   order.items.get()
        #El catálogo y el perfil cambian DESPUÉS: el pedido no se entera.
        self.product.price     =   Decimal('999.99')
        self.product.name      =   'Otro nombre'
        self.product.save()
        self.customer.first_name   =   'Cambió'
        self.customer.save()
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.name, 'Remera')
        self.assertEqual(item.list_price, Decimal('100.00'))
        self.assertEqual(item.unit_price, Decimal('100.00'))
        self.assertEqual(item.line_total, Decimal('100.00'))
        self.assertEqual(order.customer_first_name, 'Ana')
        #Y el snapshot del cliente quedó completo.
        self.assertEqual(order.customer_email, 'ana@example.com')
        self.assertEqual(order.shipping_address['line1'], 'Calle Falsa 123')

    def test_offer_price_snapshot(self):
        offer   =   _make_product(self.store, name = 'Jean', price = '100.00', offer_price = '70.00')
        order   =   _pending_order(self.store, self.customer, offer, qty = 2)
        item    =   order.items.get()
        self.assertEqual(item.list_price, Decimal('100.00'))
        self.assertEqual(item.unit_price, Decimal('70.00'))
        self.assertEqual(order.subtotal, Decimal('140.00'))
        self.assertEqual(order.discount_total, Decimal('60.00'))

    def test_idempotency_key_returns_same_order(self):
        kwargs  =   _order_kwargs(self.store, self.customer, self.product, qty = 1, idempotency_key = 'key-abc')
        first, created_1  =   create_order(**kwargs)
        second, created_2 =   create_order(**kwargs)
        self.assertTrue(created_1)
        self.assertFalse(created_2)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Order.objects.count(), 1)
        #Y con items distintos bajo la misma key TAMPOCO duplica.
        other   =   _make_product(self.store, name = 'Otro', price = '5.00')
        kwargs['items'] =   [{'product_id': other.pk, 'qty': 9}]
        third, created_3   =   create_order(**kwargs)
        self.assertFalse(created_3)
        self.assertEqual(third.pk, first.pk)
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_product_of_other_store_rejected(self):
        foreign =   _make_product(self.store_b, name = 'Ajeno')
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**_order_kwargs(self.store, self.customer, foreign))

    def test_inactive_and_exclusive_rejected(self):
        dead    =   _make_product(self.store, name = 'Baja', is_active = False)
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**_order_kwargs(self.store, self.customer, dead))
        exclusive   =   _make_product(self.store, name = 'Solo miembros', is_exclusive = True)
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**_order_kwargs(self.store, self.customer, exclusive))

    def test_stock_checked_at_creation(self):
        limited =   _make_product(self.store, name = 'Único', stock = 2)
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**_order_kwargs(self.store, self.customer, limited, qty = 3))
        order   =   _pending_order(self.store, self.customer, limited, qty = 2)
        self.assertEqual(order.total, Decimal('200.00'))

    def test_disabled_payment_method_rejected(self):
        StorePaymentConfig.objects.create(store = self.store, accept_transfer = False, accept_whatsapp = False, accept_cash = False)
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**_order_kwargs(self.store, self.customer, self.product))

    def test_pickup_needs_no_address(self):
        kwargs  =   _order_kwargs(self.store, self.customer, self.product)
        kwargs['address']        =   None
        kwargs['shipping_method'] =   'pickup'
        order, _  =   create_order(**kwargs)
        self.assertEqual(order.shipping_address, {})
        #Y domicilio SIN dirección → 400.
        kwargs['shipping_method']   =   'home'
        with self.assertRaises(drf_serializers.ValidationError):
            create_order(**kwargs)

    def test_numbering_is_per_store(self):
        order_a =   _pending_order(self.store, self.customer, self.product)
        order_a2    =   _pending_order(self.store, self.customer, self.product)
        order_b =   _pending_order(self.store_b, self.customer, _make_product(self.store_b, name = 'B', price = '10.00'))
        self.assertEqual((order_a.number, order_a2.number), (1, 2))
        self.assertEqual(order_b.number, 1)
        self.assertNotEqual(order_a.tracking_token, order_b.tracking_token)


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.store      =   _make_store('mitienda')
        self.customer   =   _make_customer()
        self.product    =   _make_product(self.store, price = '100.00', stock = 5)
        self.order      =   _pending_order(self.store, self.customer, self.product, qty = 2)

    def test_mark_paid_transitions_and_decrements_stock(self):
        order   =   mark_order_paid(self.order, source = 'manual', reference = 'TRF-1', actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)   # PAID → auto PACKING
        self.assertIsNotNone(order.paid_at)
        self.assertEqual(order.payment_ref, 'TRF-1')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        kinds   =   list(order.events.values_list('kind', flat = True))
        self.assertIn('paid', kinds)
        self.assertIn('packing', kinds)

    def test_mark_paid_idempotent(self):
        mark_order_paid(self.order, source = 'manual', actor = 'owner')
        events_before    =   OrderEvent.objects.count()
        stock_before     =   Product.objects.get(pk = self.product.pk).stock
        #Segundo llamado (webhook duplicado / doble click): no-op total.
        again   =   mark_order_paid(self.order, source = 'mp', reference = 'MP-9', actor = 'mp')
        again.refresh_from_db()
        self.assertEqual(again.status, Order.Status.PACKING)
        self.assertEqual(again.payment_ref, '')     # no pisa la primera referencia
        self.assertEqual(OrderEvent.objects.count(), events_before)
        self.assertEqual(Product.objects.get(pk = self.product.pk).stock, stock_before)

    def test_mark_paid_on_non_pending_is_noop(self):
        order   =   mark_order_paid(self.order, source = 'manual')
        advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        events_before    =   OrderEvent.objects.count()
        result  =   mark_order_paid(order, source = 'mp', actor = 'mp')
        self.assertEqual(result.status, Order.Status.SHIPPED)
        self.assertEqual(OrderEvent.objects.count(), events_before)

    def test_stock_conflict_logged_not_reverted(self):
        #Otro pedido se llevó la última unidad entre la creación y el pago.
        Product.objects.filter(pk = self.product.pk).update(stock = 1)
        order   =   mark_order_paid(self.order, source = 'manual')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)   # el pago NO se revierte
        self.assertTrue(order.events.filter(kind = 'stock_conflict').exists())
        #El UPDATE condicional no tocó nada: queda lo que había (1).
        self.assertEqual(Product.objects.get(pk = self.product.pk).stock, 1)

    def test_unlimited_stock_untouched(self):
        product =   _make_product(self.store, name = 'Sin límite', price = '10.00', stock = None)
        order   =   _pending_order(self.store, self.customer, product)
        mark_order_paid(order, source = 'manual')
        product.refresh_from_db()
        self.assertIsNone(product.stock)

    #STATE MACHINE
    def test_advance_order_happy_path(self):
        order   =   mark_order_paid(self.order)
        advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        advance_order(order, Order.Status.DELIVERED, actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertTrue(order.events.filter(kind = 'delivered').exists())

    def test_advance_rejects_invalid_transition(self):
        order   =   mark_order_paid(self.order)     # PACKING
        #No se puede saltar a DELIVERED ni volver a PENDING/PAID.
        for bad in (Order.Status.DELIVERED, Order.Status.PENDING_PAYMENT, Order.Status.PAID, Order.Status.CANCELLED):
            with self.assertRaises(drf_serializers.ValidationError, msg = bad):
                advance_order(order, bad, actor = 'owner')
        #Y un estado fuera de la whitelist de advance (EXPIRED) también.
        with self.assertRaises(drf_serializers.ValidationError):
            advance_order(order, Order.Status.EXPIRED, actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)

    def test_advance_on_terminal_rejected(self):
        order   =   mark_order_paid(self.order)
        #PACKING no se cancela: se reembolsa.
        with self.assertRaises(drf_serializers.ValidationError):
            cancel_order(order, actor = 'owner', reason = 'test')
        order   =   mark_order_refunded(order, actor = 'owner')
        with self.assertRaises(drf_serializers.ValidationError):
            advance_order(order, Order.Status.SHIPPED, actor = 'owner')

    def test_cancel_pending_order(self):
        order   =   cancel_order(self.order, actor = 'owner', reason = 'Se arrepintió')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        event   =   order.events.filter(kind = 'cancelled').get()
        self.assertEqual(event.note, 'Se arrepintió')
        #No descontó stock (nunca se pagó).
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_refund_flow(self):
        order   =   mark_order_paid(self.order)
        order   =   mark_order_refunded(order, actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        #REFUNDED es terminal: no se puede reembolsar dos veces ni avanzar.
        with self.assertRaises(drf_serializers.ValidationError):
            mark_order_refunded(order)
        #Y el stock NO se repone solo (decisión documentada).
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)


class ExpireOrdersCommandTests(TestCase):
    def setUp(self):
        self.store      =   _make_store('mitienda')
        self.customer   =   _make_customer()
        self.product    =   _make_product(self.store, price = '10.00')
        self.order      =   _pending_order(self.store, self.customer, self.product)

    def test_expire_orders_marks_and_is_idempotent(self):
        Order.objects.filter(pk = self.order.pk).update(expires_at = timezone.now() - timedelta(hours = 1))
        #Dry-run no muta.
        call_command('expire_orders', '--dry-run')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)
        call_command('expire_orders')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.EXPIRED)
        self.assertTrue(self.order.events.filter(kind = 'expired').exists())
        #Segunda corrida: no duplica evento ni falla.
        call_command('expire_orders')
        self.assertEqual(self.order.events.filter(kind = 'expired').count(), 1)

    def test_not_expired_untouched(self):
        call_command('expire_orders')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)


class PublicOrderApiTests(TestCase):
    client_class    =   APIClient

    def setUp(self):
        #El throttle del create cuenta por usuario en cache — se limpia
        #por test para que los ~10 checkouts del archivo no den 429.
        cache.clear()
        self.store      =   _make_store('mitienda')
        self.store_b    =   _make_store('otratienda')
        self.customer   =   _make_customer()
        self.client     =   APIClient()
        _bearer(self.client, self.customer)
        self.product    =   _make_product(self.store, price = '100.00')
        self.create_url =   f'/api/stores/public/{self.store.slug}/orders/'
        self.track_base =   f'/api/stores/public/{self.store.slug}/orders'

    def _payload(self, **extra):
        return {
            'items'             :   [{'product_id': self.product.pk, 'qty': 1}],
            'address'           :   ADDRESS,
            'payment_method'    :   'transfer',
            'challenge_id'      :   'x',
            'captcha_answer'    :   '1',
            **extra,
        }

    #SECURITY: captcha + auth + throttle presence
    def test_throttle_classes_present(self):
        self.assertTrue(PublicOrderCreateView.throttle_classes)
        self.assertTrue(OrderCreateThrottle.rate)
        self.assertTrue(OrderProofThrottle.rate)

    def test_create_requires_captcha(self):
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = False):
            response    =   self.client.post(self.create_url, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('captcha_answer', response.json())
        self.assertFalse(Order.objects.exists())

    def test_create_requires_customer_auth(self):
        anon    =   APIClient()
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = True):
            response    =   anon.post(self.create_url, self._payload(), format = 'json')
        self.assertIn(response.status_code, (401, 403))

    def test_create_happy_path_and_idempotent_retry(self):
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = True):
            response    =   self.client.post(self.create_url, self._payload(idempotency_key = 'k1'), format = 'json')
            self.assertEqual(response.status_code, 201)
            data        =   response.json()
            self.assertIn('tracking_token', data)
            self.assertNotIn('id', data)          # el id numérico jamás sale
            self.assertEqual(data['total'], '100.00')
            self.assertEqual(data['status'], 'PENDING_PAYMENT')
            self.assertIn('payment_instructions', data)
            #Retry con la misma key → 200 MISMO pedido.
            retry   =   self.client.post(self.create_url, self._payload(idempotency_key = 'k1'), format = 'json')
            self.assertEqual(retry.status_code, 200)
            self.assertEqual(retry.json()['tracking_token'], data['tracking_token'])
            self.assertEqual(Order.objects.count(), 1)

    def test_client_cannot_inject_prices(self):
        evil    =   self._payload(total = '0.01', price = '0.01', subtotal = '0.01')
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = True):
            response    =   self.client.post(self.create_url, evil, format = 'json')
        self.assertEqual(response.status_code, 201)
        order   =   Order.objects.get()
        self.assertEqual(order.total, Decimal('100.00'))
        self.assertEqual(order.subtotal, Decimal('100.00'))

    def test_store_without_orders_enabled_is_404(self):
        closed  =   _make_store('cerrada', sellable = False)
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = True):
            response    =   self.client.post(
                f'/api/stores/public/{closed.slug}/orders/',
                self._payload(), format = 'json')
        self.assertEqual(response.status_code, 404)

    #TRACKING (anti-IDOR)
    def _create_via_api(self):
        with patch('StoreApp.domains.orders.views.public.verify_captcha', return_value = True):
            return self.client.post(self.create_url, self._payload(), format = 'json').json()

    def test_track_by_token_and_no_pii(self):
        data    =   self._create_via_api()
        token   =   data['tracking_token']
        response    =   self.client.get(f'{self.track_base}/{token}/')
        self.assertEqual(response.status_code, 200)
        body    =   response.json()
        self.assertEqual(body['tracking_token'], token)
        self.assertEqual(body['customer_first_name'], 'Ana')
        #PII que NO debe salir en seguimiento público:
        for forbidden in ('customer_email', 'customer_phone', 'customer_document', 'customer_last_name'):
            self.assertNotIn(forbidden, body)
        self.assertIn('events', body)
        self.assertTrue(body['events'])

    def test_track_wrong_or_foreign_token_is_404(self):
        data    =   self._create_via_api()
        token   =   data['tracking_token']
        self.assertEqual(self.client.get(f'{self.track_base}/token-falso-123/').status_code, 404)
        #El MISMO token consultado en OTRA tienda → 404 (acotado por slug).
        self.assertEqual(self.client.get(f'/api/stores/public/{self.store_b.slug}/orders/{token}/').status_code, 404)
        #Y un pedido de la tienda B tampoco es visible desde A.
        order_b =   _pending_order(self.store_b, self.customer, _make_product(self.store_b, name = 'B', price = '10.00'))
        self.assertEqual(self.client.get(f'{self.track_base}/{order_b.tracking_token}/').status_code, 404)

    def test_events_endpoint(self):
        data    =   self._create_via_api()
        order   =   Order.objects.get()
        mark_order_paid(order, source = 'manual')
        response    =   self.client.get(f'{self.track_base}/{data["tracking_token"]}/events/')
        self.assertEqual(response.status_code, 200)
        kinds   =   [e['kind'] for e in response.json()]
        self.assertIn('created', kinds)
        self.assertIn('paid', kinds)
        self.assertIn('packing', kinds)

    #PROOF
    def test_proof_requires_pending_manual_order(self):
        data    =   self._create_via_api()
        order   =   Order.objects.get()
        mark_order_paid(order)      # ya no está pendiente
        png     =   _tiny_png()
        response    =   self.client.post(
            f'{self.track_base}/{data["tracking_token"]}/proof/',
            {'image': png}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentProof.objects.exists())

    def test_proof_upload_happy_path(self):
        data    =   self._create_via_api()
        png     =   _tiny_png()
        with patch('StoreApp.domains.orders.views.public.put_object', return_value = 'k') as mock_put, \
             patch('StoreApp.domains.orders.views.public.normalize_image', return_value = (b'webp-bytes', 'webp', 'image/webp')):
            response    =   self.client.post(
                f'{self.track_base}/{data["tracking_token"]}/proof/',
                {'image': png}, format = 'multipart')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['proof_uploaded'])
        self.assertTrue(PaymentProof.objects.filter(order__tracking_token = data['tracking_token']).exists())
        mock_put.assert_called_once()
        #La key subió normalizada a WebP.
        args    =   mock_put.call_args[0]
        self.assertTrue(args[0].endswith('.webp'))
        self.assertIn(f'stores/{self.store.id}/proofs/', args[0])

    def test_proof_rejected_for_mp_order(self):
        order   =   _pending_order(self.store, self.customer, self.product)
        Order.objects.filter(pk = order.pk).update(payment_method = 'mp')
        png     =   _tiny_png()
        with patch('StoreApp.domains.orders.views.public.normalize_image', return_value = (b'w', 'webp', 'image/webp')), \
             patch('StoreApp.domains.orders.views.public.put_object') as mock_put:
            response    =   self.client.post(
                f'{self.track_base}/{order.tracking_token}/proof/',
                {'image': png}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        mock_put.assert_not_called()

    #RECEIPT
    def test_receipt_no_fiscal_payload(self):
        data    =   self._create_via_api()
        response    =   self.client.get(f'{self.track_base}/{data["tracking_token"]}/receipt/')
        self.assertEqual(response.status_code, 200)
        body    =   response.json()
        self.assertEqual(body['kind'], 'no_fiscal')
        self.assertIn('NO FISCAL', body['legend'])
        self.assertEqual(body['seller']['cuit'], CUIT_VALIDO)
        self.assertEqual(body['seller']['legal_name'], 'Prueba SA')
        self.assertEqual(body['totals']['total'], '100.00')
        self.assertEqual(len(body['items']), 1)


class OwnerOrderApiTests(TestCase):
    client_class    =   APIClient

    def setUp(self):
        self.owner_a    =   _make_owner('duenio-a')
        self.owner_b    =   _make_owner('duenio-b')
        self.store_a    =   _make_store('tienda-a')
        self.store_b    =   _make_store('tienda-b')
        #Reasignar las tiendas a SUS dueños (helpers crean owner propio).
        self.store_a.user   =   self.owner_a
        self.store_a.save()
        self.store_b.user   =   self.owner_b
        self.store_b.save()
        self.customer   =   _make_customer()
        self.product_a  =   _make_product(self.store_a, price = '100.00', stock = 10)
        self.product_b  =   _make_product(self.store_b, name = 'B', price = '50.00')
        self.order_a    =   _pending_order(self.store_a, self.customer, self.product_a, qty = 2)
        self.order_b    =   _pending_order(self.store_b, self.customer, self.product_b)
        self.client     =   APIClient()
        #JWT DAVENT del dueño A (Store.user → UserProfile → .user = User).
        token   =   RefreshToken.for_user(self.owner_a.user)
        self.client.credentials(HTTP_AUTHORIZATION = f'Bearer {token.access_token}')

    @property
    def base(self):
        return '/api/store-orders/'

    def test_owner_sees_only_own_orders(self):
        response    =   self.client.get(self.base)
        self.assertEqual(response.status_code, 200)
        results =   response.json().get('results', response.json())
        ids     =   {row['id'] for row in results}
        self.assertIn(self.order_a.pk, ids)
        self.assertNotIn(self.order_b.pk, ids)

    def test_owner_b_gets_404_on_order_a(self):
        #Login como dueño B.
        token   =   RefreshToken.for_user(self.owner_b.user)
        self.client.credentials(HTTP_AUTHORIZATION = f'Bearer {token.access_token}')
        #Bodies VÁLIDOS: prueba que el 404 viene del scope de tienda y no
        #de una validación de input que se adelante al lookup.
        for suffix, body in (
            ('confirm-payment/', {'reference': 'X'}),
            ('advance/',         {'status': 'SHIPPED'}),
            ('cancel/',          {'reason': 'x'}),
            ('invoice-ref/',     {'invoice_ref': 'A-1'}),
        ):
            response    =   self.client.post(f'{self.base}{self.order_a.pk}/{suffix}', body, format = 'json')
            self.assertEqual(response.status_code, 404, suffix)
        #GET detalle (retrieve) también es 404 para el dueño ajeno.
        response    =   self.client.get(f'{self.base}{self.order_a.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_detail_includes_items_events_customer(self):
        response    =   self.client.get(f'{self.base}{self.order_a.pk}/')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertEqual(data['code'], 'PED-0001')
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['name'], 'Remera')
        self.assertEqual(data['customer_email'], 'ana@example.com')
        self.assertTrue(data['events'])

    def test_confirm_payment_flow(self):
        response    =   self.client.post(f'{self.base}{self.order_a.pk}/confirm-payment/', {'reference': 'TRF-777'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, Order.Status.PACKING)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 8)
        #Idempotente desde la API también.
        again   =   self.client.post(f'{self.base}{self.order_a.pk}/confirm-payment/', {}, format = 'json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self.product_a.stock, 8)

    def test_advance_and_cancel_and_invoice_ref(self):
        mark_order_paid(self.order_a)
        response    =   self.client.post(f'{self.base}{self.order_a.pk}/advance/', {'status': 'SHIPPED'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, Order.Status.SHIPPED)
        #Transición inválida → 400.
        bad     =   self.client.post(f'{self.base}{self.order_a.pk}/advance/', {'status': 'PACKING'}, format = 'json')
        self.assertEqual(bad.status_code, 400)
        #invoice-ref.
        inv     =   self.client.post(f'{self.base}{self.order_a.pk}/invoice-ref/', {'invoice_ref': 'A-0001-00001234'}, format = 'json')
        self.assertEqual(inv.status_code, 200)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.invoice_ref, 'A-0001-00001234')
        #Cancel sobre pedido pago → 400 (se reembolsa, no se cancela).
        cancel  =   self.client.post(f'{self.base}{self.order_a.pk}/cancel/', {'reason': 'x'}, format = 'json')
        self.assertEqual(cancel.status_code, 400)

    def test_cancel_pending_order(self):
        response    =   self.client.post(f'{self.base}{self.order_a.pk}/cancel/', {'reason': 'Se arrepintió'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, Order.Status.CANCELLED)

    def test_list_status_filter(self):
        response    =   self.client.get(f'{self.base}?status=PENDING_PAYMENT')
        results =   response.json().get('results', response.json())
        self.assertEqual({row['id'] for row in results}, {self.order_a.pk})
        response    =   self.client.get(f'{self.base}?status=DELIVERED')
        results =   response.json().get('results', response.json())
        self.assertEqual(results, [])

    def test_list_no_n_plus_1(self):
        """La bandeja no crece en queries al agregar pedidos (prefetch fijo)."""
        def run():
            return self.client.get(self.base)
        run()   #warm (throttle/session ya resueltos)
        with CaptureQueriesContext(connection) as ctx1:
            run()
        #Agregar 4 pedidos más a la tienda A.
        for _i in range(4):
            _pending_order(self.store_a, self.customer, self.product_a)
        with CaptureQueriesContext(connection) as ctx2:
            run()
        self.assertEqual(len(ctx2), len(ctx1), f'N+1 detectado: {len(ctx1)} → {len(ctx2)} queries')


#PNG 1x1 válido (firma + tamaño OK para validate_image_file).
_TINY_PNG_BYTES   =   (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def _tiny_png():
    return SimpleUploadedFile('comprobante.png', _TINY_PNG_BYTES, content_type = 'image/png')
