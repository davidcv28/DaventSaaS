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
from django.core import mail
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

from AdminApp.domains.notifications.models import Notification
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
from StoreApp.domains.orders.services.events import append_event
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


_customer_seq    =   [0]
def _make_customer(email = 'ana@example.com'):
    #phone/document son unique globales vía su hash HMAC — dos buyers de
    #la misma suite no pueden compartirlos; se derivan del email.
    _customer_seq[0] +=   1
    seq         =   _customer_seq[0]
    customer    =   Customer(
        email       =   email,
        #Los mails de ciclo de vida solo salen a direcciones verificadas
        #— los tests que esperan mail al comprador necesitan el flag.
        email_verified =   True,
        first_name  =   'Ana',
        last_name   =   'Perez',
        phone       =   f'+549110{seq:07d}',
        document_type = 'DNI',
        document    =   f'30{seq:07d}',
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


#=========================================
# TRACK F — dispatch de mails + Notification in-app
#=========================================
class OrderEventNotifyTests(TestCase):
    """
    `_dispatch_order_event` (services/events.py → services/notify.py):
    - 'created' → Notification kind='order' al dueño + mail al dueño.
    - estados (paid/packing/shipped/…) → mail al COMPRADOR con link
      /seguimiento?token=… (el token es la credencial pública).
    - 'note' y kinds sin mail → no disparan nada.
    - una falla de SMTP NUNCA rompe append_event (best-effort total).

    Los mails viajan por Celery: en tests corre eager, pero el encolado
    es `transaction.on_commit` — `captureOnCommitCallbacks(execute=True)`
    lo dispara dentro del atomic de TestCase (mismo criterio que los
    tests de customers, que llaman al Query directo porque on_commit no
    corre solo).
    """
    def setUp(self):
        cache.clear()
        self.owner_a    =   _make_owner('duenio-f')
        self.store      =   _make_store('tienda-f')
        self.store.user =   self.owner_a
        self.store.save()
        self.customer   =   _make_customer('fana@example.com')
        self.product    =   _make_product(self.store, price = '100.00', stock = 5)
        #El 'created' de este pedido ya disparó notification + encolado
        #pendiente (on_commit no corre en TestCase — queda sin efecto).
        self.order      =   _pending_order(self.store, self.customer, self.product, qty = 2)

    @property
    def owner_email(self):
        #Store.user = UserProfile → .user = auth.User (cadena real).
        return self.owner_a.user.email

    def _mails_to(self, email):
        return [m for m in mail.outbox if email in (m.to or [])]

    def test_created_notifies_owner_and_emails(self):
        product2    =   _make_product(self.store, name = 'Otro', price = '50.00')
        with self.captureOnCommitCallbacks(execute = True):
            order2, _created  =   create_order(**_order_kwargs(self.store, self.customer, product2))
        #Notification in-app 'order' deduplicada por pedido.
        notif   =   Notification.objects.get(dedupe_key = f'order:{order2.pk}:created')
        self.assertEqual(notif.kind, Notification.KIND_ORDER)
        self.assertEqual(notif.target, 'orders')
        self.assertEqual(notif.user, self.owner_a.user)
        self.assertIn(order2.code, notif.title)
        self.assertIn('50,00', notif.body)      #total con formato es-AR ($50,00)
        #Y el mail salió al DUEÑO con code + total + link al panel.
        owner_mails =   self._mails_to(self.owner_email)
        self.assertTrue(owner_mails)
        last    =   owner_mails[-1]
        self.assertIn(order2.code, last.subject)
        self.assertIn('Nuevo pedido', last.subject)
        self.assertIn(order2.code, last.body)
        self.assertIn('/dashboard', last.body)

    def test_notification_dedupe_returns_to_unread(self):
        """Re-disparar 'created' actualiza el aviso (no duplica) y lo
        devuelve a no-leído — contrato de upsert_notification."""
        notif   =   Notification.objects.get(dedupe_key = f'order:{self.order.pk}:created')
        notif.read_at  =   timezone.now()
        notif.save(update_fields = ['read_at'])
        append_event(self.order, 'created', actor = 'system', status_to = Order.Status.PENDING_PAYMENT)
        notif.refresh_from_db()
        self.assertIsNone(notif.read_at)
        self.assertEqual(
            Notification.objects.filter(dedupe_key = f'order:{self.order.pk}:created').count(), 1,
        )

    def test_paid_packing_shipped_email_customer_with_tracking_link(self):
        with self.captureOnCommitCallbacks(execute = True):
            order   =   mark_order_paid(self.order, source = 'manual', actor = 'owner')
            advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        #paid + packing (auto-avance) + shipped → 3 mails al comprador.
        customer_mails  =   self._mails_to('fana@example.com')
        self.assertEqual(len(customer_mails), 3)
        last    =   customer_mails[-1]
        self.assertIn('enviado', last.subject.lower())
        #Link de seguimiento con el tracking_token (credencial pública).
        self.assertIn(f'/seguimiento?token={self.order.tracking_token}', last.body)
        #El mail va al SNAPSHOT del pedido, no a otra dirección.
        self.assertEqual(last.to, ['fana@example.com'])

    def test_unverified_customer_gets_no_lifecycle_mail(self):
        """El alta no prueba la titularidad del email: si el comprador
        nunca verificó, los mails de ciclo de vida no salen (anti-spam
        con marca DAVENT a direcciones ajenas)."""
        Customer.objects.filter(pk = self.order.customer_id).update(email_verified = False)
        with self.captureOnCommitCallbacks(execute = True):
            order   =   mark_order_paid(self.order, source = 'manual', actor = 'owner')
            advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        self.assertEqual(self._mails_to('fana@example.com'), [])
        #El aviso interno al dueño (Notification) sigue creándose — solo
        #se suprime el correo saliente al comprador no verificado.
        self.assertTrue(Notification.objects.filter(
            kind = Notification.KIND_ORDER,
            dedupe_key__startswith = f'order:{self.order.pk}:',
        ).exists())

    def test_note_event_sends_nothing(self):
        outbox_before     =   len(mail.outbox)
        notif_before      =   Notification.objects.count()
        with self.captureOnCommitCallbacks(execute = True):
            append_event(self.order, 'note', actor = 'owner', note = 'prueba interna')
        self.assertEqual(len(mail.outbox), outbox_before)
        self.assertEqual(Notification.objects.count(), notif_before)

    def test_stock_conflict_notifies_and_emails_owner(self):
        #Otro pedido se llevó la unidad entre la creación y el pago.
        Product.objects.filter(pk = self.product.pk).update(stock = 1)
        with self.captureOnCommitCallbacks(execute = True):
            mark_order_paid(self.order, source = 'manual', actor = 'owner')
        #Notification 'order' deduplicada POR EVENTO (lleva el pk).
        notif   =   Notification.objects.filter(
            kind = Notification.KIND_ORDER,
            dedupe_key__startswith = f'order:{self.order.pk}:stock_conflict:',
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.user, self.owner_a.user)
        #Y el mail al dueño pide revisión (subject de incidencia).
        issue_mails =   [m for m in self._mails_to(self.owner_email) if 'revisi' in m.subject.lower()]
        self.assertTrue(issue_mails)

    def test_smtp_failure_never_breaks_append_event(self):
        """Si el SMTP explota, append_event devuelve el evento igual —
        la notificación ya quedó y el mail se perdió en el log."""
        with patch('StoreApp.domains.orders.services.mails.EmailMultiAlternatives') as mock_mail_cls:
            mock_mail_cls.return_value.send.side_effect   =   RuntimeError('SMTP caído')
            with self.captureOnCommitCallbacks(execute = True):
                event   =   append_event(self.order, 'paid', actor = 'system',
                                         status_from = Order.Status.PENDING_PAYMENT,
                                         status_to   = Order.Status.PAID)
        self.assertIsNotNone(event.pk)
        self.assertTrue(OrderEvent.objects.filter(pk = event.pk).exists())
        #El mock se llamó (se intentó el envío) pero la excepción se tragó.
        mock_mail_cls.return_value.send.assert_called()

    def test_missing_order_or_event_is_silent(self):
        """La task con ids inexistentes (rollback/borrado) no explota."""
        from StoreApp.domains.orders.services.mails import deliver_order_event_email
        deliver_order_event_email(999999, 999999)          # no raise
        deliver_order_event_email(self.order.pk, 999999)   # evento inexistente


#=========================================
# TRACK F — listado de pedidos del comprador
#=========================================
class CustomerOrdersApiTests(TestCase):
    """
    GET /api/customer/orders/ (+ /<tracking_token>/): solo pedidos del
    customer logueado (anti-IDOR cross-customer → 404), filtros
    store/status, sin PII del snapshot en la respuesta.
    """
    client_class    =   APIClient
    def setUp(self):
        cache.clear()
        self.store_a    =   _make_store('compras-a')
        self.store_b    =   _make_store('compras-b')
        self.customer   =   _make_customer('mia@example.com')
        self.other      =   _make_customer('otra@example.com')
        product_a       =   _make_product(self.store_a, price = '100.00')
        product_b       =   _make_product(self.store_b, name = 'B', price = '50.00')
        #Dos pedidos del customer (uno por tienda) + uno de OTRO customer.
        self.order_a    =   _pending_order(self.store_a, self.customer, product_a)
        self.order_b    =   _pending_order(self.store_b, self.customer, product_b)
        self.order_other=   _pending_order(self.store_a, self.other, product_a)
        self.client     =   APIClient()
        _bearer(self.client, self.customer)
        self.list_url   =   '/api/customer/orders/'

    def _results(self, response):
        return response.json().get('results', response.json())

    def test_requires_customer_auth(self):
        self.assertEqual(APIClient().get(self.list_url).status_code, 401)
        self.assertEqual(
            APIClient().get(f'{self.list_url}{self.order_a.tracking_token}/').status_code, 401,
        )

    def test_lists_only_own_orders_across_stores(self):
        response    =   self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        results =   self._results(response)
        tokens  =   {row['tracking_token'] for row in results}
        self.assertEqual(tokens, {self.order_a.tracking_token, self.order_b.tracking_token})
        #Más nuevos primero: order_b se creó después que order_a.
        self.assertEqual(results[0]['tracking_token'], self.order_b.tracking_token)
        for row in results:
            #Sin id numérico — la credencial pública es tracking_token.
            self.assertNotIn('id', row)
            self.assertIn('store_slug', row)
            self.assertIn('store_name', row)
            self.assertIn('code', row)
            self.assertIn('status', row)
            self.assertIn('items_count', row)
        by_token    =   {row['tracking_token']: row for row in results}
        self.assertEqual(by_token[self.order_a.tracking_token]['store_slug'], 'compras-a')
        self.assertEqual(by_token[self.order_b.tracking_token]['store_slug'], 'compras-b')
        self.assertEqual(by_token[self.order_a.tracking_token]['items_count'], 1)

    def test_filter_by_store_and_status(self):
        response    =   self.client.get(self.list_url, {'store': 'compras-a'})
        results =   self._results(response)
        self.assertEqual([r['tracking_token'] for r in results], [self.order_a.tracking_token])
        response    =   self.client.get(self.list_url, {'status': 'PENDING_PAYMENT'})
        self.assertEqual(len(self._results(response)), 2)
        response    =   self.client.get(self.list_url, {'status': 'delivered'})
        self.assertEqual(self._results(response), [])
        #Status inválido → lista vacía (validado contra Order.Status).
        response    =   self.client.get(self.list_url, {'status': 'bogus;DROP'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._results(response), [])
        #Combinados.
        response    =   self.client.get(self.list_url, {'store': 'compras-b', 'status': 'PENDING_PAYMENT'})
        self.assertEqual([r['tracking_token'] for r in self._results(response)], [self.order_b.tracking_token])

    def test_detail_own_order_tracking_payload(self):
        response    =   self.client.get(f'{self.list_url}{self.order_a.tracking_token}/')
        self.assertEqual(response.status_code, 200)
        body    =   response.json()
        self.assertEqual(body['tracking_token'], self.order_a.tracking_token)
        self.assertEqual(body['code'], 'PED-0001')
        self.assertIn('events', body)
        self.assertIn('items', body)
        self.assertIn('payment_instructions', body)   #PENDING_PAYMENT + transfer
        #PII del snapshot NUNCA en la respuesta del comprador.
        for forbidden in ('customer_email', 'customer_phone', 'customer_document', 'customer_document_type'):
            self.assertNotIn(forbidden, body)

    def test_detail_cross_customer_is_404(self):
        """Anti-IDOR: el token de OTRO customer es 404 — ni siquiera se
        revela que el pedido existe (mismo 404 que un token inventado)."""
        response    =   self.client.get(f'{self.list_url}{self.order_other.tracking_token}/')
        self.assertEqual(response.status_code, 404)
        response    =   self.client.get(f'{self.list_url}token-que-no-existe/')
        self.assertEqual(response.status_code, 404)
        #Y en el listado tampoco aparece el pedido ajeno (ya cubierto,
        #pero el detalle es la superficie crítica).
        other_client   =   APIClient()
        _bearer(other_client, self.other)
        response    =   other_client.get(f'{self.list_url}{self.order_a.tracking_token}/')
        self.assertEqual(response.status_code, 404)
