"""
Tests de auditoría del circuito de cobros MP de tiendas (reembolsos,
integración de la cuenta MP del vendedor y transiciones de pago).

A diferencia de tests.py (que usa dobles del bridge porque orders estaba
en desarrollo), acá se ejercita el stack REAL: Order/OrderItem/
OrderEvent + services.payments + services.webhook de storepayments, con
solo la frontera HTTP de Mercado Pago mockeada (mp_client).

Cobertura:
- Refund endpoint: auth, IDOR real (pedido de otra tienda -> 404),
  método/estado inválidos, doble refund (MP llamado UNA vez), entrega.
- Webhook: 'approved' sobre pedido ya pago/entregado/vencido ->
  OrderEvent 'duplicate_payment'/'paid_after_close' (doble cobro /
  cobro tardío) en vez de no-op silencioso; 'refunded'/'charged_back'
  sobre DELIVERED -> 'refund_after_delivery'; idempotencia del estado.
- payments: mark_order_paid(source='mp') persiste order.mp_payment_id;
  advance a REFUNDED de un pedido 'mp' queda bloqueado (el reembolso
  real tiene que pasar por MP, si no la plata nunca vuelve).
- MpConnect: rotación/limpieza del webhook_secret, refresh_token
  cifrado, live_mode explícito.
- mp_client: refund total = body vacío; amount solo si se pide;
  ids fuera del regex rechazados antes de llamar a MP.
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework.test import APIClient

from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.customers.models import Customer
from StoreApp.domains.orders.models import Order, OrderEvent
from StoreApp.domains.orders.services.checkout import create_order
from StoreApp.domains.orders.services.payments import (
    advance_order,
    mark_order_paid,
    mark_order_refunded,
)
from StoreApp.domains.storepayments.models import MpPayment, StoreMpWebhookConfig
from StoreApp.domains.storepayments.services import webhook as mp_webhook
from StoreApp.domains.storepayments.services.mp_client import MpApiError
from StoreApp.domains.stores.models import (
    Store,
    StoreCustomization,
    StoreFiscalProfile,
    StoreMpAccount,
)
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

MP_CLIENT    =   'StoreApp.domains.storepayments.services.mp_client'
MP_TOKEN     =   'TEST-audit-token-123'
CUIT_VALIDO  =   '20123456786'
ADDRESS      =   {'line1': 'Av. Audit 100', 'city': 'CABA', 'province': 'CABA', 'postal_code': '1000', 'country': 'AR'}
REFUND_URL   =   '/api/store-payments/mp/refund/{}/'
_seq         =   [0]


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
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )


def _make_owner(username):
    user    =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'x')
    profile =   UserProfile.objects.create(user = user, email_verified = True)
    cache.delete(f'planben:{profile.pk}')
    _grant(profile, 'has_ecommerce')
    return user, profile


def _make_store(slug):
    user, profile   =   _make_owner(f'owner-{slug}')
    store   =   Store.objects.create(user = profile, slug = slug, is_published = True)
    StoreCustomization.objects.create(store = store, ecommerce_enabled = True)
    StoreFiscalProfile.objects.create(
        store           =   store,
        legal_name      =   'Audit SA',
        tax_condition   =   'RI',
        cuit            =   CUIT_VALIDO,
        fiscal_address  =   'Av. Audit 1',
        point_of_sale   =   '0001',
    )
    return user, store


def _connect_mp(store, token = MP_TOKEN, secret = None):
    account, _  =   StoreMpAccount.objects.get_or_create(store = store)
    account.set_tokens(token, 'REFRESH-enc', live_mode = False, mp_user_id = 'mp-user-1')
    account.save()
    if secret is not None:
        cfg, _  =   StoreMpWebhookConfig.objects.get_or_create(store = store)
        cfg.set_webhook_secret(secret)
        cfg.save()
    return account


def _make_customer():
    _seq[0] +=   1
    seq         =   _seq[0] + int(uuid.uuid4().hex[:6], 16) % 1000
    customer    =   Customer(
        email           =   f'buyer{seq}@example.com',
        email_verified  =   True,
        first_name      =   'Audit',
        last_name       =   'Buyer',
        phone           =   f'+54911{seq:08d}'[-15:],
        document_type   =   'DNI',
        document        =   f'30{seq:08d}'[-11:],
    )
    customer.set_password('x')
    customer.save()
    return customer


def _mp_order(store, customer, product, qty = 1, **extra):
    order, _created  =   create_order(
        store               =   store,
        customer            =   customer,
        items               =   [{'product_id': product.pk, 'qty': qty}],
        address             =   ADDRESS,
        payment_method      =   'mp',
        **extra,
    )
    return order


def _mp_payment_dict(payment_id, status = 'approved', amount = '50.00', ref = None, live_mode = True):
    return {
        'id'                    :   payment_id,
        'status'                :   status,
        'status_detail'         :   'accredited',
        'transaction_amount'    :   float(amount),
        'currency_id'           :   'ARS',
        'external_reference'    :   ref,
        'live_mode'             :   live_mode,
    }


class RefundEndpointAuditTests(TestCase):
    """POST /api/store-payments/mp/refund/<order_id>/ contra DB real."""

    def setUp(self):
        self.client     =   APIClient()
        self.user, self.store   =   _make_store('audit-a')
        _connect_mp(self.store)
        self.customer   =   _make_customer()
        self.product    =   Product.objects.create(store = self.store, name = 'Remera', price = Decimal('100.00'), stock = 10)
        self.order      =   _mp_order(self.store, self.customer, self.product, qty = 2)
        #Pago real: PACKING + stock descontado (10 -> 8) + payment_ref.
        self.order      =   mark_order_paid(self.order, source = 'mp', reference = '555001', actor = 'mp')
        self.mp_rec     =   MpPayment.objects.create(
            store               =   self.store,
            order_id            =   self.order.pk,
            tracking_token      =   self.order.tracking_token,
            mp_payment_id       =   '555001',
            status              =   MpPayment.Status.APPROVED,
            amount              =   self.order.total,
            currency            =   'ARS',
            live_mode           =   True,
        )

    def _refund(self, order_id, user = None):
        client  =   self.client if user is None else APIClient()
        if user is not None:
            client.force_authenticate(user = user)
        with patch(f'{MP_CLIENT}.refund_mp_payment', return_value = {'id': 'r1'}) as refund_mp:
            response    =   client.post(REFUND_URL.format(order_id), {}, format = 'json')
        return response, refund_mp

    def test_requires_auth(self):
        response, refund_mp   =   self._refund(self.order.pk)
        self.assertIn(response.status_code, (401, 403))
        refund_mp.assert_not_called()

    def test_user_without_store_404(self):
        user, _    =   _make_owner('audit-sin-tienda')
        self.client.force_authenticate(user = user)
        response    =   self.client.post(REFUND_URL.format(self.order.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_idor_foreign_order_404(self):
        #Owner de la tienda B no puede reembolsar el pedido de la A.
        user_b, store_b   =   _make_store('audit-b')
        _connect_mp(store_b)
        self.client.force_authenticate(user = user_b)
        with patch(f'{MP_CLIENT}.refund_mp_payment') as refund_mp:
            response    =   self.client.post(REFUND_URL.format(self.order.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 404)
        refund_mp.assert_not_called()

    def test_happy_path_refunds_in_mp_and_marks_order(self):
        self.client.force_authenticate(user = self.user)
        response, refund_mp   =   self._refund(self.order.pk, user = self.user)
        self.assertEqual(response.status_code, 200)
        #Se reembolsó con el token DEL VENDEDOR y el payment_id del cobro.
        args, _   =   refund_mp.call_args
        self.assertEqual(args[0], '555001')
        self.assertEqual(args[1], MP_TOKEN)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)
        self.mp_rec.refresh_from_db()
        self.assertEqual(self.mp_rec.status, MpPayment.Status.REFUNDED)
        #Audit trail: evento 'refunded' con actor owner.
        event   =   self.order.events.filter(kind = 'refunded').get()
        self.assertEqual(event.actor, OrderEvent.Actor.OWNER)
        #Stock NO se repone solo (decisión documentada del dominio).
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_double_refund_single_mp_call(self):
        #Doble click / retry del dueño: MP se llama UNA sola vez.
        self.client.force_authenticate(user = self.user)
        r1, refund_mp   =   self._refund(self.order.pk, user = self.user)
        self.assertEqual(r1.status_code, 200)
        #El mock vive dentro de _refund por llamada — para contar ambas
        #lladas se usa un solo patch externo.
        with patch(f'{MP_CLIENT}.refund_mp_payment', return_value = {'id': 'r1'}) as refund_mp2:
            r2  =   self.client.post(REFUND_URL.format(self.order.pk), {}, format = 'json')
        self.assertEqual(r2.status_code, 400)
        refund_mp2.assert_not_called()

    def test_refund_non_mp_order_400_no_mp_call(self):
        transfer_order =   create_order(
            store           =   self.store,
            customer        =   _make_customer(),
            items           =   [{'product_id': self.product.pk, 'qty': 1}],
            address         =   ADDRESS,
            payment_method  =   'transfer',
        )[0]
        mark_order_paid(transfer_order, source = 'manual', actor = 'owner')
        self.client.force_authenticate(user = self.user)
        response, refund_mp   =   self._refund(transfer_order.pk, user = self.user)
        self.assertEqual(response.status_code, 400)
        refund_mp.assert_not_called()

    def test_refund_unpaid_order_400(self):
        pending =   _mp_order(self.store, _make_customer(), self.product, qty = 1)
        self.client.force_authenticate(user = self.user)
        response, refund_mp   =   self._refund(pending.pk, user = self.user)
        self.assertEqual(response.status_code, 400)
        refund_mp.assert_not_called()

    def test_refund_delivered_order_400(self):
        #DELIVERED es terminal: la máquina no permite REFUNDED y el
        #reembolso no debe llegar a MP.
        order   =   _mp_order(self.store, _make_customer(), self.product, qty = 1)
        mark_order_paid(order, source = 'mp', reference = '555002', actor = 'mp')
        order   =   advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        order   =   advance_order(order, Order.Status.DELIVERED, actor = 'owner')
        MpPayment.objects.create(
            store               =   self.store,
            order_id            =   order.pk,
            tracking_token      =   order.tracking_token,
            mp_payment_id       =   '555002',
            status              =   MpPayment.Status.APPROVED,
            amount              =   order.total,
            currency            =   'ARS',
        )
        self.client.force_authenticate(user = self.user)
        response, refund_mp   =   self._refund(order.pk, user = self.user)
        self.assertEqual(response.status_code, 400)
        refund_mp.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_refund_shipped_order_ok(self):
        order   =   _mp_order(self.store, _make_customer(), self.product, qty = 1)
        mark_order_paid(order, source = 'mp', reference = '555003', actor = 'mp')
        order   =   advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        MpPayment.objects.create(
            store               =   self.store,
            order_id            =   order.pk,
            tracking_token      =   order.tracking_token,
            mp_payment_id       =   '555003',
            status              =   MpPayment.Status.APPROVED,
            amount              =   order.total,
            currency            =   'ARS',
        )
        self.client.force_authenticate(user = self.user)
        response, refund_mp   =   self._refund(order.pk, user = self.user)
        self.assertEqual(response.status_code, 200)
        refund_mp.assert_called_once()

    def test_refund_mp_rejected_keeps_order(self):
        self.client.force_authenticate(user = self.user)
        with patch(f'{MP_CLIENT}.refund_mp_payment', side_effect = MpApiError('rechazado', status_code = 400)):
            response    =   self.client.post(REFUND_URL.format(self.order.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 502)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PACKING)
        self.mp_rec.refresh_from_db()
        self.assertEqual(self.mp_rec.status, MpPayment.Status.APPROVED)


class WebhookTransitionAuditTests(TestCase):
    """StoreMpWebhookQuery contra DB real: transiciones + bitácora."""

    def setUp(self):
        self.user, self.store   =   _make_store('audit-wh')
        _connect_mp(self.store)
        self.customer   =   _make_customer()
        self.product    =   Product.objects.create(store = self.store, name = 'Jean', price = Decimal('50.00'), stock = 5)

    def _webhook(self, payment_id, mp_payment):
        with patch(f'{MP_CLIENT}.get_mp_payment', return_value = mp_payment):
            return mp_webhook.StoreMpWebhookQuery(self.store, str(payment_id))

    def _paid_mp_order(self, ref):
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'mp', reference = ref, actor = 'mp')
        return order

    def test_approved_webhook_marks_paid_and_sets_mp_payment_id(self):
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        record  =   self._webhook(777, _mp_payment_dict(777, ref = f'ord:{order.tracking_token}'))
        self.assertIsNotNone(record)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)
        self.assertEqual(order.mp_payment_id, '777')
        self.assertEqual(order.payment_ref, '777')
        self.assertTrue(order.events.filter(kind = 'paid').exists())

    def test_approved_on_manually_paid_order_flags_conflict(self):
        #El dueño confirmó el pago a mano (transferencia/efectivo) con un
        #checkout MP en vuelo: el comprador completa MP igual -> hay DOS
        #cobros. Antes: mark_paid no-op silencioso, nadie se enteraba.
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'manual', reference = 'TRANSF-1', actor = 'owner')
        stock_before =   Product.objects.get(pk = self.product.pk).stock
        record  =   self._webhook(778, _mp_payment_dict(778, ref = f'ord:{order.tracking_token}'))
        self.assertIsNotNone(record)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)
        #Sin segundo descuento de stock ni segundo 'paid'.
        self.assertEqual(Product.objects.get(pk = self.product.pk).stock, stock_before)
        self.assertEqual(order.events.filter(kind = 'paid').count(), 1)
        #PERO queda constancia para revisión/reembolso manual.
        conflict    =   order.events.filter(kind = 'duplicate_payment')
        self.assertEqual(conflict.count(), 1)
        self.assertIn('778', conflict.get().note)

    def test_approved_on_expired_order_flags_conflict(self):
        #El pedido venció pero el comprador pagó igual en MP: la plata
        #está cobrada y el pedido no puede acreditarse solo.
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        Order.objects.filter(pk = order.pk).update(status = Order.Status.EXPIRED)
        record  =   self._webhook(779, _mp_payment_dict(779, ref = f'ord:{order.tracking_token}'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EXPIRED)
        self.assertTrue(order.events.filter(kind = 'paid_after_close').exists())
        self.assertEqual(record.status, MpPayment.Status.APPROVED)

    def test_refunded_webhook_marks_refunded_and_is_idempotent(self):
        order   =   self._paid_mp_order('880001')
        record  =   self._webhook(880001, _mp_payment_dict(880001, status = 'refunded', ref = f'ord:{order.tracking_token}'))
        self.assertIsNotNone(record)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(record.status, MpPayment.Status.REFUNDED)
        #Re-entrega del mismo evento: no duplica eventos ni falla.
        record2 =   self._webhook(880001, _mp_payment_dict(880001, status = 'refunded', ref = f'ord:{order.tracking_token}'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(order.events.filter(kind = 'refunded').count(), 1)
        self.assertEqual(record2.status, MpPayment.Status.REFUNDED)

    def test_charged_back_on_delivered_order_flags_conflict(self):
        #Contracargo de un pedido YA ENTREGADO: MP devuelve la plata pero
        #la máquina no permite REFUNDED desde DELIVERED — sin evento el
        #dueño nunca se entera de que le reclaman el cobro.
        order   =   self._paid_mp_order('880002')
        order   =   advance_order(order, Order.Status.SHIPPED, actor = 'owner')
        order   =   advance_order(order, Order.Status.DELIVERED, actor = 'owner')
        record  =   self._webhook(880002, _mp_payment_dict(880002, status = 'charged_back', ref = f'ord:{order.tracking_token}'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(record.status, MpPayment.Status.REFUNDED)
        conflict    =   order.events.filter(kind = 'refund_after_delivery')
        self.assertEqual(conflict.count(), 1)
        self.assertIn('880002', conflict.get().note)

    def test_refunded_webhook_on_pending_order_ignored(self):
        #Un 'refunded' de un pago nunca aprobado no toca el pedido.
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        record  =   self._webhook(880003, _mp_payment_dict(880003, status = 'refunded', ref = f'ord:{order.tracking_token}'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertFalse(order.events.filter(kind = 'refunded').exists())


class PaymentsServiceAuditTests(TestCase):
    """Contrato de orders.services.payments ejercitado directo."""

    def setUp(self):
        self.user, self.store   =   _make_store('audit-pay')
        _connect_mp(self.store)
        self.customer   =   _make_customer()
        self.product    =   Product.objects.create(store = self.store, name = 'Zapatilla', price = Decimal('80.00'), stock = 4)

    def test_mark_paid_mp_persists_mp_payment_id(self):
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'mp', reference = '991234', actor = 'mp')
        self.assertEqual(order.mp_payment_id, '991234')
        order.refresh_from_db()
        self.assertEqual(order.mp_payment_id, '991234')

    def test_mark_paid_manual_does_not_touch_mp_payment_id(self):
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'manual', reference = 'TRANSF-9', actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.mp_payment_id, '')
        self.assertEqual(order.payment_ref, 'TRANSF-9')

    def test_advance_to_refunded_blocked_for_mp_orders(self):
        #Si el dueño marca REFUNDED por /advance/ en un pedido MP, la
        #plata NUNCA vuelve (MP no se entera) y el pedido queda terminal:
        #el reembolso real queda bloqueado para siempre. Debe usarse el
        #flujo de Cobros -> Mercado Pago.
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'mp', reference = '991235', actor = 'mp')
        with self.assertRaises(drf_serializers.ValidationError):
            advance_order(order, Order.Status.REFUNDED, actor = 'owner')
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PACKING)

    def test_advance_to_refunded_allowed_for_manual_methods(self):
        order   =   create_order(
            store               =   self.store,
            customer            =   _make_customer(),
            items               =   [{'product_id': self.product.pk, 'qty': 1}],
            address             =   ADDRESS,
            payment_method      =   'transfer',
        )[0]
        order   =   mark_order_paid(order, source = 'manual', actor = 'owner')
        order   =   advance_order(order, Order.Status.REFUNDED, actor = 'owner')
        self.assertEqual(order.status, Order.Status.REFUNDED)

    def test_mark_refunded_idempotent_contract(self):
        order   =   _mp_order(self.store, self.customer, self.product, qty = 1)
        order   =   mark_order_paid(order, source = 'mp', reference = '991236', actor = 'mp')
        order   =   mark_order_refunded(order, actor = 'owner')
        with self.assertRaises(drf_serializers.ValidationError):
            mark_order_refunded(order, actor = 'owner')


class MpConnectAuditTests(TestCase):
    """Rotación de webhook_secret + cifrado de refresh_token."""

    def setUp(self):
        self.client     =   APIClient()
        self.user, self.store   =   _make_store('audit-conn')
        self.client.force_authenticate(user = self.user)

    @patch(f'{MP_CLIENT}.get_mp_user', return_value = {'id': 4242})
    def test_webhook_secret_rotation_and_clear(self, _mock):
        url =   '/api/store-payments/mp/connect/'
        r1  =   self.client.post(url, {'access_token': MP_TOKEN, 'webhook_secret': 'secret-A'}, format = 'json')
        self.assertEqual(r1.status_code, 200)
        cfg =   StoreMpWebhookConfig.objects.get(store = self.store)
        self.assertEqual(cfg.get_webhook_secret(), 'secret-A')
        #Re-connect con otro secret: rota sin tocar el token.
        r2  =   self.client.post(url, {'access_token': MP_TOKEN, 'webhook_secret': 'secret-B'}, format = 'json')
        self.assertEqual(r2.status_code, 200)
        cfg.refresh_from_db()
        self.assertEqual(cfg.get_webhook_secret(), 'secret-B')
        #Connect SIN webhook_secret conserva el vigente (no lo borra).
        r3  =   self.client.post(url, {'access_token': MP_TOKEN}, format = 'json')
        self.assertEqual(r3.status_code, 200)
        cfg.refresh_from_db()
        self.assertEqual(cfg.get_webhook_secret(), 'secret-B')
        #'' explícito lo limpia (documentado: firma deja de validar).
        r4  =   self.client.post(url, {'access_token': MP_TOKEN, 'webhook_secret': ''}, format = 'json')
        self.assertEqual(r4.status_code, 200)
        cfg.refresh_from_db()
        self.assertEqual(cfg.get_webhook_secret(), '')
        self.assertFalse(r4.json()['webhook_configured'], msg = f"payload={r4.json()} enc={cfg.webhook_secret_enc!r}")

    @patch(f'{MP_CLIENT}.get_mp_user', return_value = {'id': 4242})
    def test_refresh_token_stored_encrypted(self, _mock):
        response    =   self.client.post(
            '/api/store-payments/mp/connect/',
            {'access_token': MP_TOKEN, 'refresh_token': 'RT-super-secreto'},
            format  =   'json',
        )
        self.assertEqual(response.status_code, 200)
        account =   StoreMpAccount.objects.get(store = self.store)
        self.assertTrue(account.refresh_token_enc.startswith('enc:v1:'))
        self.assertEqual(account.get_refresh_token(), 'RT-super-secreto')
        #Jamás sale en la respuesta.
        self.assertNotIn('RT-super-secreto', response.content.decode())
        self.assertNotIn(MP_TOKEN, response.content.decode())

    @patch(f'{MP_CLIENT}.get_mp_user', return_value = {'id': 4242})
    def test_live_mode_explicit_false_with_app_usr_token(self, _mock):
        #El dueño declara live_mode=False explícito: se respeta (no se
        #deriva del prefijo) — queda para reconciliación con MP.
        response    =   self.client.post(
            '/api/store-payments/mp/connect/',
            {'access_token': 'APP_USR-token', 'live_mode': False},
            format  =   'json',
        )
        self.assertEqual(response.status_code, 200)
        account =   StoreMpAccount.objects.get(store = self.store)
        self.assertFalse(account.live_mode)


class MpClientAuditTests(TestCase):
    """Contrato del cliente REST mínimo (sin red real)."""

    def test_refund_total_sends_empty_body(self):
        with patch(f'{MP_CLIENT}._request', return_value = {'id': 1}) as req:
            from StoreApp.domains.storepayments.services import mp_client
            mp_client.refund_mp_payment('12345', 'TOKEN')
        args, kwargs   =   req.call_args
        self.assertEqual(args[0], 'POST')
        self.assertIn('/v1/payments/12345/refunds', args[1])
        self.assertEqual(kwargs.get('payload'), {})
        self.assertEqual(kwargs.get('access_token'), 'TOKEN')

    def test_refund_partial_only_with_amount(self):
        with patch(f'{MP_CLIENT}._request', return_value = {'id': 1}) as req:
            from StoreApp.domains.storepayments.services import mp_client
            mp_client.refund_mp_payment('12345', 'TOKEN', amount = 30.5)
        self.assertEqual(req.call_args.kwargs.get('payload'), {'amount': 30.5})

    def test_payment_id_path_injection_rejected(self):
        from StoreApp.domains.storepayments.services import mp_client
        for bad in ('../../users/me', '123?x=1', '', 'a b', 'x' * 65):
            with self.assertRaises(MpApiError):
                mp_client.get_mp_payment(bad, 'TOKEN')
