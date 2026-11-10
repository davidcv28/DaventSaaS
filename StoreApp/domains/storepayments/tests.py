"""
Tests de seguridad del dominio storepayments (sección 3.5 PROMPT_MAESTRO).

Cobertura:
- Webhook MP: firma x-signature inválida/ausente -> 401; live_mode=False
  rechazado en prod; payment de otra tienda/pedido ajeno ignorado;
  webhook duplicado -> un solo efecto PAID; monto distinto -> no marca
  pagado + OrderEvent amount_mismatch; token jamás en respuestas.
- Connect: token inválido -> 400 sin guardar; connect válido cifra y no
  filtra secretos; disconnect limpia.
- Refund: IDOR (pedido de otra tienda -> 404); método/estado inválidos.
- Config: validación WhatsApp/days/coherencia de métodos.
- Pay público: gates de tienda/MP/estado/método + payload de preferencia.

NOTA DE CONTRATO: el modelo Order y los services mark_order_paid /
mark_order_refunded / events.append_event los implementa el track B
(orders) en paralelo — todavía no existen. Los tests que tocan pedidos
parchean `services.orders_bridge` (el puente lazy del dominio) con
objetos fake y mocks, verificando el CONTRATO (source='mp', reference,
actor, kinds de evento) en vez del ORM de orders. Cuando orders aterrice
conviene migrar estos casos a objetos reales.
"""
import hashlib
import hmac
import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from StoreApp.domains.storepayments.models import MpPayment, StoreMpWebhookConfig
from StoreApp.domains.storepayments.services.mp_client import MpApiError
from StoreApp.domains.stores.models import (
    Store,
    StoreCustomization,
    StoreFiscalProfile,
    StoreMpAccount,
    StorePaymentConfig,
)

WEBHOOK_SECRET    =   'whsec-test-123'
MP_TOKEN_TEST     =   'TEST-1234567890-abcdef'
MP_TOKEN_LIVE     =   'APP_USR-1234567890-abcdef'

BRIDGE           =   'StoreApp.domains.storepayments.services.orders_bridge'
MP_CLIENT        =   'StoreApp.domains.storepayments.services.mp_client'


def _signature_headers(resource_id, request_id = 'req-1', secret = WEBHOOK_SECRET, ts = None):
    #Mismo manifest que el webhook de suscripciones: id del query string
    #firmado + request-id + ts (segundos; la vista acepta ms también).
    ts          =   ts or str(int(timezone.now().timestamp()))
    manifest    =   f'id:{resource_id};request-id:{request_id};ts:{ts};'
    v1          =   hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {
        'HTTP_X_SIGNATURE'  :   f'ts={ts},v1={v1}',
        'HTTP_X_REQUEST_ID' :   request_id,
    }


def _mp_payment(payment_id = 555, status = 'approved', amount = 1500.0, ref = 'ord:tok-1', live_mode = True, currency = 'ARS'):
    return {
        'id'                    :   payment_id,
        'status'                :   status,
        'status_detail'         :   'accredited',
        'transaction_amount'    :   amount,
        'currency_id'           :   currency,
        'external_reference'    :   ref,
        'live_mode'             :   live_mode,
        'date_approved'         :   '2024-01-01T00:00:00.000-00:00',
    }


def _fake_order(store, token = 'tok-1', status = 'PENDING_PAYMENT', total = '1500.00', payment_method = 'mp', pk = 1, mp_payment_id = ''):  # noqa: S107 — token = tracking_token público del pedido, no credencial
    """Order fake según el contrato del track B (ver docstring del módulo)."""
    return SimpleNamespace(
        pk              =   pk,
        id              =   pk,
        store           =   store,
        store_id        =   store.id,
        tracking_token  =   token,
        status          =   status,
        payment_method  =   payment_method,
        total           =   Decimal(total),
        customer_email  =   'comprador@example.com',
        items           =   [],
        expires_at      =   None,
        mp_payment_id   =   mp_payment_id,
    )


class StorePaymentsTestBase(TestCase):
    client_class    =   APIClient

    def _make_owner(self, username = 'duenio', with_store = True, sellable = True):
        user        =   User.objects.create_user(username = username, email = f'{username}@example.com', password = 'Xq7#mP2vL9bT')
        from AdminApp.domains.users.models import UserProfile
        profile     =   UserProfile.objects.create(user = user, email_verified = True)
        store       =   None
        if with_store:
            store   =   Store.objects.create(user = profile, slug = f'tienda-{username}')
            if sellable:
                StoreCustomization.objects.create(store = store, ecommerce_enabled = True)
                #CUIT válido (dígito verificador módulo 11).
                StoreFiscalProfile.objects.create(
                    store           =   store,
                    legal_name      =   'Prueba SA',
                    tax_condition   =   'RI',
                    cuit            =   '20123456786',
                    fiscal_address  =   'Av. Siempre Viva 1',
                )
        return user, profile, store

    def _connect_mp(self, store, token = MP_TOKEN_TEST, live_mode = False, secret = WEBHOOK_SECRET):
        account, _  =   StoreMpAccount.objects.get_or_create(store = store)
        account.set_tokens(token, '', live_mode = live_mode, mp_user_id = '777')
        account.save()
        if secret is not None:
            cfg, _  =   StoreMpWebhookConfig.objects.get_or_create(store = store)
            cfg.set_webhook_secret(secret)
            cfg.save()
        return account

    def _post_webhook(self, slug, payment_id, *, secret = WEBHOOK_SECRET, request_id = 'req-1', ts = None, body_id = None, signed = True):
        url     =   f'/api/webhooks/store-mp/{slug}/?data.id={payment_id}'
        headers =   _signature_headers(str(payment_id), request_id = request_id, secret = secret, ts = ts) if signed else {}
        return self.client.post(
            url,
            {'type': 'payment', 'data': {'id': body_id if body_id is not None else payment_id}},
            format  =   'json',
            **headers,
        )


#=========================================
# MP STATUS / CONNECT / DISCONNECT (dueño)
#=========================================
class MpAccountOwnerTests(StorePaymentsTestBase):

    def test_status_requires_auth(self):
        response    =   self.client.get('/api/store-payments/mp/status/')
        self.assertIn(response.status_code, (401, 403))

    def test_status_without_store_404(self):
        user, _, _   =   self._make_owner('sin-tienda', with_store = False)
        self.client.force_authenticate(user = user)
        response    =   self.client.get('/api/store-payments/mp/status/')
        self.assertEqual(response.status_code, 404)

    def test_status_never_returns_tokens(self):
        user, _, store   =   self._make_owner('con-mp')
        self._connect_mp(store)
        self.client.force_authenticate(user = user)
        response    =   self.client.get('/api/store-payments/mp/status/')
        self.assertEqual(response.status_code, 200)
        data        =   response.json()
        self.assertTrue(data['connected'])
        self.assertFalse(data['live_mode'])
        self.assertEqual(data['mp_user_id'], '777')
        self.assertIn('has_payment_config', data)
        self.assertNotIn('access_token', data)
        self.assertNotIn(MP_TOKEN_TEST, response.content.decode())

    @patch(f'{MP_CLIENT}.get_mp_user', side_effect = MpApiError('no', status_code = 401))
    def test_connect_invalid_token_400_and_not_saved(self, _mock):
        user, _, store   =   self._make_owner('token-malo')
        self.client.force_authenticate(user = user)
        response    =   self.client.post('/api/store-payments/mp/connect/', {'access_token': 'TOKEN-FALSO'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(StoreMpAccount.objects.filter(store = store).exists())

    @patch(f'{MP_CLIENT}.get_mp_user', return_value = {'id': 777})
    def test_connect_success_never_leaks_secrets(self, _mock):
        user, _, store   =   self._make_owner('token-ok')
        self.client.force_authenticate(user = user)
        response    =   self.client.post(
            '/api/store-payments/mp/connect/',
            {'access_token': MP_TOKEN_LIVE, 'webhook_secret': WEBHOOK_SECRET},
            format  =   'json',
        )
        self.assertEqual(response.status_code, 200)
        account =   StoreMpAccount.objects.get(store = store)
        self.assertTrue(account.is_connected)
        #live_mode derivado del prefijo APP_USR- cuando no se declara.
        self.assertTrue(account.live_mode)
        body    =   response.content.decode()
        self.assertNotIn(MP_TOKEN_LIVE, body)
        self.assertNotIn(WEBHOOK_SECRET, body)
        self.assertTrue(response.json()['webhook_configured'])
        #Round-trip vault: el token guardado es cifrado, no el claro.
        self.assertTrue(account.access_token_enc.startswith('enc:v1:'))
        self.assertEqual(account.get_access_token(), MP_TOKEN_LIVE)

    @patch(f'{MP_CLIENT}.get_mp_user', return_value = {'id': 777})
    def test_disconnect_clears_tokens(self, _mock):
        user, _, store   =   self._make_owner('logout-mp')
        self._connect_mp(store)
        self.client.force_authenticate(user = user)
        response    =   self.client.post('/api/store-payments/mp/disconnect/', {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['connected'])
        account =   StoreMpAccount.objects.get(store = store)
        self.assertFalse(account.is_connected)
        self.assertEqual(account.get_access_token(), '')


#=========================================
# WEBHOOK MP (público, auth por firma)
#=========================================
class StoreMpWebhookTests(StorePaymentsTestBase):

    def setUp(self):
        self.user, _, self.store   =   self._make_owner('webhook')
        self._connect_mp(self.store)
        self.order                 =   _fake_order(self.store)

    def _run(self, mp_payment, order = None, request_id = None):
        order   =   self.order if order is None else order
        #request_id único por llamada: el dedup del webhook usa
        #cache.add(x-request-id) y el cache (Redis) sobrevive entre tests
        #— un id fijo haría que el 2º test del mismo payment se trague
        #como "ya procesada" sin llegar al service.
        request_id  =   request_id or f'req-{uuid.uuid4().hex[:12]}'
        with patch(f'{MP_CLIENT}.get_mp_payment', return_value = mp_payment) as get_pay, \
             patch(f'{BRIDGE}.find_order_by_token', return_value = order) as find_order, \
             patch(f'{BRIDGE}.mark_paid') as mark_paid, \
             patch(f'{BRIDGE}.mark_refunded') as mark_refunded, \
             patch(f'{BRIDGE}.append_event') as append_event:
            response    =   self._post_webhook(self.store.slug, mp_payment['id'], request_id = request_id)
        return response, {'get_pay': get_pay, 'find_order': find_order, 'mark_paid': mark_paid, 'mark_refunded': mark_refunded, 'append_event': append_event}

    def test_missing_signature_401(self):
        response    =   self._post_webhook(self.store.slug, 555, signed = False)
        self.assertEqual(response.status_code, 401)

    def test_invalid_signature_401(self):
        response    =   self._post_webhook(self.store.slug, 555, secret = 'otro-secret')
        self.assertEqual(response.status_code, 401)

    def test_stale_signature_401(self):
        old_ts  =   str(int((timezone.now() - timedelta(minutes = 30)).timestamp()))
        response    =   self._post_webhook(self.store.slug, 555, ts = old_ts)
        self.assertEqual(response.status_code, 401)

    def test_valid_signature_approved_marks_paid(self):
        response, mocks   =   self._run(_mp_payment())
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_called_once()
        _, kwargs   =   mocks['mark_paid'].call_args
        self.assertEqual(kwargs.get('source'), 'mp')
        self.assertEqual(kwargs.get('reference'), '555')
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.APPROVED)
        self.assertEqual(record.store_id, self.store.id)
        self.assertEqual(record.order_id, self.order.pk)

    @override_settings(DEBUG = False)
    def test_live_mode_false_rejected_in_prod(self):
        #DEBUG=False: un payment TEST no acredita en producción.
        response, mocks   =   self._run(_mp_payment(live_mode = False))
        self.assertEqual(response.status_code, 400)
        mocks['mark_paid'].assert_not_called()
        self.assertFalse(MpPayment.objects.filter(mp_payment_id = '555').exists())

    def test_foreign_order_ignored(self):
        #external_reference resuelve un token, pero el pedido es de OTRA
        #tienda (store_id distinto): IDOR -> no se acredita nada.
        foreign =   _fake_order(self.store, token = 'tok-ajeno', pk = 9)
        foreign.store_id    =   999999
        response, mocks    =   self._run(_mp_payment(ref = 'ord:tok-ajeno'), order = foreign)
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()

    def test_order_not_found_ignored(self):
        with patch(f'{MP_CLIENT}.get_mp_payment', return_value = _mp_payment(ref = 'ord:inexistente')), \
             patch(f'{BRIDGE}.find_order_by_token', return_value = None), \
             patch(f'{BRIDGE}.mark_paid') as mark_paid:
            response    =   self._post_webhook(self.store.slug, 555, request_id = 'req-nf')
        self.assertEqual(response.status_code, 200)
        mark_paid.assert_not_called()

    def test_duplicate_webhook_single_effect(self):
        mp_payment  =   _mp_payment()
        with patch(f'{MP_CLIENT}.get_mp_payment', return_value = mp_payment), \
             patch(f'{BRIDGE}.find_order_by_token', return_value = self.order), \
             patch(f'{BRIDGE}.mark_paid') as mark_paid:
            r1  =   self._post_webhook(self.store.slug, 555, request_id = 'req-1')
            r2  =   self._post_webhook(self.store.slug, 555, request_id = 'req-2')
            r3  =   self._post_webhook(self.store.slug, 555, request_id = 'req-3')
        self.assertEqual((r1.status_code, r2.status_code, r3.status_code), (200, 200, 200))
        #Tres entregas del mismo payment -> UN solo efecto PAID.
        mark_paid.assert_called_once()
        self.assertEqual(MpPayment.objects.filter(mp_payment_id = '555').count(), 1)

    def test_amount_mismatch_not_paid(self):
        response, mocks   =   self._run(_mp_payment(amount = 100.0))
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        mocks['append_event'].assert_called_once()
        _, kwargs   =   mocks['append_event'].call_args
        self.assertEqual(kwargs.get('kind'), 'amount_mismatch')
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertTrue(record.amount_mismatch)

    def test_refunded_marks_order_refunded(self):
        paid_order =   _fake_order(self.store, status = 'PAID')
        response, mocks   =   self._run(_mp_payment(status = 'refunded'), order = paid_order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_refunded'].assert_called_once()
        mocks['mark_paid'].assert_not_called()

    def test_rejected_only_records(self):
        response, mocks   =   self._run(_mp_payment(status = 'rejected'), request_id = 'req-rj')
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.REJECTED)

    def test_unknown_slug_404(self):
        response    =   self._post_webhook('no-existe', 555)
        self.assertEqual(response.status_code, 404)

    def test_adopts_open_attempt_row(self):
        #Una preferencia ya emitida (mp_payment_id NULL) adopta el
        #payment_id del webhook: una sola fila por intento de cobro.
        attempt =   MpPayment.objects.create(
            store           =   self.store,
            order_id        =   self.order.pk,
            tracking_token  =   'tok-1',
            preference_id   =   'pref-abc',
            status          =   MpPayment.Status.CREATED,
            amount          =   Decimal('1500.00'),
        )
        response, _   =   self._run(_mp_payment())
        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.mp_payment_id, '555')
        self.assertEqual(MpPayment.objects.filter(order_id = self.order.pk).count(), 1)


#=========================================
# PAY PÚBLICO DEL COMPRADOR
#=========================================
class PublicOrderPayTests(StorePaymentsTestBase):
    PAY_URL     =   '/api/stores/public/tienda-pagador/orders/tok-1/pay/'

    def setUp(self):
        self.user, _, self.store   =   self._make_owner('pagador')
        self._connect_mp(self.store)
        StorePaymentConfig.objects.create(store = self.store, mp_enabled = True)
        self.order                 =   _fake_order(self.store)

    def _pay(self, order = None, create_side_effect = None):
        order   =   self.order if order is None else order
        preference    =   {'id': 'pref-9', 'init_point': 'https://mp.example/init', 'sandbox_init_point': 'https://mp.example/sandbox'}
        with patch(f'{MP_CLIENT}.create_preference', return_value = preference, side_effect = create_side_effect) as create_pref, \
             patch(f'{BRIDGE}.find_order_by_token', return_value = order):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        return response, create_pref

    def test_pay_creates_preference_with_seller_contract(self):
        #BACKEND_URL vacío en dev: se patchea para verificar notification_url.
        with patch('StoreApp.domains.storepayments.services.preferences.BACKEND_URL', 'https://api.test'):
            response, create_pref   =   self._pay()
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertEqual(data['init_point'], 'https://mp.example/init')
        self.assertEqual(data['preference_id'], 'pref-9')
        payload =   create_pref.call_args[0][0]
        #external_reference namespaced 'ord:' — no colisiona con 'sub:'.
        self.assertEqual(payload['external_reference'], 'ord:tok-1')
        self.assertIn('/api/webhooks/store-mp/tienda-pagador/', payload['notification_url'])
        self.assertIn('token=tok-1', payload['back_urls']['success'])
        self.assertIn('seguimiento', payload['back_urls']['success'])
        #El token del vendedor solo viaja como 2º arg (Authorization),
        #nunca dentro del payload ni de la respuesta.
        self.assertNotIn(MP_TOKEN_TEST, response.content.decode())
        record  =   MpPayment.objects.get(preference_id = 'pref-9')
        self.assertEqual(record.status, MpPayment.Status.CREATED)
        self.assertEqual(record.amount, Decimal('1500.00'))

    def test_pay_mp_not_connected_400(self):
        StoreMpAccount.objects.filter(store = self.store).delete()
        response, _   =   self._pay()
        self.assertEqual(response.status_code, 400)

    def test_pay_mp_disabled_in_config_400(self):
        StorePaymentConfig.objects.filter(store = self.store).update(mp_enabled = False)
        response, _   =   self._pay()
        self.assertEqual(response.status_code, 400)

    def test_pay_order_not_pending_409(self):
        response, _   =   self._pay(order = _fake_order(self.store, status = 'PAID'))
        self.assertEqual(response.status_code, 409)

    def test_pay_wrong_payment_method_400(self):
        response, _   =   self._pay(order = _fake_order(self.store, payment_method = 'transfer'))
        self.assertEqual(response.status_code, 400)

    def test_pay_order_not_found_404(self):
        with patch(f'{BRIDGE}.find_order_by_token', return_value = None):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_pay_store_not_sellable_404(self):
        user2, _, store2   =   self._make_owner('no-vende', sellable = False)
        self._connect_mp(store2)
        url     =   '/api/stores/public/tienda-no-vende/orders/tok-1/pay/'
        with patch(f'{BRIDGE}.find_order_by_token', return_value = _fake_order(store2)):
            response    =   self.client.post(url, {}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_pay_mp_api_error_502(self):
        response, _   =   self._pay(create_side_effect = MpApiError('mp caído', status_code = 500))
        self.assertEqual(response.status_code, 502)


#=========================================
# CONFIG DE COBROS (dueño)
#=========================================
class StorePaymentConfigTests(StorePaymentsTestBase):
    CONFIG_URL  =   '/api/store-payments/config/'

    def setUp(self):
        self.user, _, self.store   =   self._make_owner('config')
        self.client.force_authenticate(user = self.user)

    def test_get_returns_defaults(self):
        response    =   self.client.get(self.CONFIG_URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertTrue(data['accept_transfer'])
        self.assertTrue(data['mp_enabled'])
        self.assertEqual(data['payment_deadline_hours'], 48)

    def test_patch_whatsapp_invalid_400(self):
        response    =   self.client.patch(self.CONFIG_URL, {'whatsapp_number': 'abc!!'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_patch_whatsapp_normalized(self):
        response    =   self.client.patch(self.CONFIG_URL, {'whatsapp_number': '+54 9 11 5555-1234'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['whatsapp_number'], '+5491155551234')

    def test_patch_deadline_bounds(self):
        for bad in (0, 721):
            response    =   self.client.patch(self.CONFIG_URL, {'payment_deadline_hours': bad}, format = 'json')
            self.assertEqual(response.status_code, 400)
        response    =   self.client.patch(self.CONFIG_URL, {'payment_deadline_hours': 72}, format = 'json')
        self.assertEqual(response.status_code, 200)

    def test_patch_all_methods_off_400(self):
        response    =   self.client.patch(self.CONFIG_URL, {
            'accept_transfer'   :   False,
            'accept_whatsapp'   :   False,
            'accept_cash'       :   False,
            'mp_enabled'        :   False,
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_patch_whatsapp_requires_number(self):
        #accept_whatsapp activo sin número -> incoherente.
        StorePaymentConfig.objects.create(store = self.store, accept_whatsapp = True, whatsapp_number = '')
        response    =   self.client.patch(self.CONFIG_URL, {'transfer_instructions': 'x'}, format = 'json')
        self.assertEqual(response.status_code, 400)


#=========================================
# REFUND (dueño)
#=========================================
class MpRefundTests(StorePaymentsTestBase):
    REFUND_URL_FMT   =   '/api/store-payments/mp/refund/{}/'

    def _order_for(self, store, **kw):
        return _fake_order(
            store,
            status          =   kw.pop('status', 'PAID'),
            payment_method  =   kw.pop('payment_method', 'mp'),
            mp_payment_id   =   kw.pop('mp_payment_id', 'mp-pay-1'),
            pk              =   kw.pop('pk', 5),
            **kw,
        )

    def test_refund_idor_404(self):
        #Dos tiendas: el dueño A no puede reembolsar el pedido de B.
        user_a, _, store_a   =   self._make_owner('duenio-a')
        _, _, store_b        =   self._make_owner('duenio-b')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b)
        self.client.force_authenticate(user = user_a)
        with patch(f'{BRIDGE}.get_order_for_store', side_effect = lambda store, oid: order_b if order_b.store_id == store.id else None):
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_refund_happy_path(self):
        user_b, _, store_b   =   self._make_owner('duenio-b2')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b)
        self.client.force_authenticate(user = user_b)
        with patch(f'{BRIDGE}.get_order_for_store', return_value = order_b), \
             patch(f'{MP_CLIENT}.refund_mp_payment', return_value = {'id': 1}) as refund_mp, \
             patch(f'{BRIDGE}.mark_refunded') as mark_refunded:
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        refund_mp.assert_called_once()
        args, _   =   refund_mp.call_args
        self.assertEqual(args[0], 'mp-pay-1')
        mark_refunded.assert_called_once()
        _, kwargs   =   mark_refunded.call_args
        self.assertEqual(kwargs.get('actor'), user_b)

    def test_refund_non_mp_order_400(self):
        user_b, _, store_b   =   self._make_owner('duenio-b3')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b, payment_method = 'transfer')
        self.client.force_authenticate(user = user_b)
        with patch(f'{BRIDGE}.get_order_for_store', return_value = order_b):
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_refund_unpaid_order_400(self):
        user_b, _, store_b   =   self._make_owner('duenio-b4')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b, status = 'PENDING_PAYMENT')
        self.client.force_authenticate(user = user_b)
        with patch(f'{BRIDGE}.get_order_for_store', return_value = order_b):
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_refund_mp_rejected_502_and_order_untouched(self):
        user_b, _, store_b   =   self._make_owner('duenio-b5')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b)
        self.client.force_authenticate(user = user_b)
        with patch(f'{BRIDGE}.get_order_for_store', return_value = order_b), \
             patch(f'{MP_CLIENT}.refund_mp_payment', side_effect = MpApiError('rechazado', status_code = 400)), \
             patch(f'{BRIDGE}.mark_refunded') as mark_refunded:
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 502)
        mark_refunded.assert_not_called()
