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
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
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
    StoreOAuthConfig,
    StorePaymentConfig,
    StoreStorageConfig,
)
from StoreApp.domains.stores.services import storage as storage_service

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

    def test_refund_packing_order_ok(self):
        #mark_order_paid auto-avanza PAID→PACKING: el reembolso debe
        #aceptar los estados desde los que la máquina permite REFUNDED.
        user_b, _, store_b   =   self._make_owner('duenio-b2b')
        self._connect_mp(store_b)
        order_b              =   self._order_for(store_b, status = 'PACKING')
        self.client.force_authenticate(user = user_b)
        with patch(f'{BRIDGE}.get_order_for_store', return_value = order_b), \
             patch(f'{MP_CLIENT}.refund_mp_payment', return_value = {'id': 1}), \
             patch(f'{BRIDGE}.mark_refunded') as mark_refunded:
            response    =   self.client.post(self.REFUND_URL_FMT.format(order_b.pk), {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        mark_refunded.assert_called_once()

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


#=========================================
# FISCAL PROFILE (dueño — panel Cobros)
#=========================================
class FiscalProfileOwnerTests(StorePaymentsTestBase):
    URL     =   '/api/store-payments/fiscal-profile/'
    VALID   =   {
        'legal_name'        :   'Comercio Demo SA',
        'tax_condition'     :   'RI',
        'cuit'              :   '20-12345678-6',
        'fiscal_address'    :   'Av. Corrientes 1234',
        'point_of_sale'     :   '0001',
    }

    def test_requires_auth(self):
        self.assertIn(self.client.get(self.URL).status_code, (401, 403))

    def test_no_store_404(self):
        user, _, _   =   self._make_owner('fiscal-sin', with_store = False)
        self.client.force_authenticate(user = user)
        self.assertEqual(self.client.get(self.URL).status_code, 404)

    def test_get_defaults_without_row(self):
        #sellable=False: no hay StoreFiscalProfile ni customization.
        user, _, store   =   self._make_owner('fiscal-vacio', sellable = False)
        self.client.force_authenticate(user = user)
        response    =   self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertEqual(data['tax_condition'], 'CF')
        self.assertEqual(data['cuit'], '')
        self.assertFalse(data['is_complete'])
        #GET no persiste nada.
        self.assertFalse(StoreFiscalProfile.objects.filter(store = store).exists())

    def test_put_valid_normalizes_cuit_and_completes(self):
        user, _, store   =   self._make_owner('fiscal-ok', sellable = False)
        StoreCustomization.objects.create(store = store, ecommerce_enabled = True)
        self.client.force_authenticate(user = user)
        response    =   self.client.put(self.URL, self.VALID, format = 'json')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        #CUIT 'XX-XXXXXXXX-X' normalizado a 11 dígitos.
        self.assertEqual(data['cuit'], '20123456786')
        self.assertTrue(data['is_complete'])
        profile =   StoreFiscalProfile.objects.get(store = store)
        self.assertEqual(profile.cuit, '20123456786')
        #Espejo de orders_enabled: con perfil completo + ecommerce_enabled
        #la tienda queda habilitada para vender.
        from StoreApp.domains.stores.services.commerce import orders_enabled
        self.assertTrue(orders_enabled(Store.objects.get(pk = store.pk)))

    def test_put_11_digits_accepted(self):
        user, _, _   =   self._make_owner('fiscal-digitos', sellable = False)
        self.client.force_authenticate(user = user)
        payload     =   dict(self.VALID, cuit = '20123456786')
        response    =   self.client.put(self.URL, payload, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cuit'], '20123456786')

    def test_put_invalid_cuit_400(self):
        user, _, _   =   self._make_owner('fiscal-cuit', sellable = False)
        self.client.force_authenticate(user = user)
        for bad in ('20123456789', '123', '20-ABC-567-8'):
            response    =   self.client.put(self.URL, dict(self.VALID, cuit = bad), format = 'json')
            self.assertEqual(response.status_code, 400, f'cuit={bad}')
        self.assertFalse(StoreFiscalProfile.objects.filter(store__slug = 'tienda-fiscal-cuit').exists())

    def test_put_bad_tax_condition_400(self):
        user, _, _   =   self._make_owner('fiscal-iva', sellable = False)
        self.client.force_authenticate(user = user)
        response    =   self.client.put(self.URL, dict(self.VALID, tax_condition = 'XX'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_put_missing_required_fields_400(self):
        user, _, _   =   self._make_owner('fiscal-parcial', sellable = False)
        self.client.force_authenticate(user = user)
        #Sin los campos que orders_enabled exige no se guarda nada.
        response    =   self.client.put(self.URL, {'legal_name': 'Solo nombre'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_idor_store_id_in_body_ignored(self):
        #No hay id de tienda en la ruta ni el serializer acepta store_id:
        #un owner no puede escribir la config fiscal de otra tienda.
        user_a, _, store_a   =   self._make_owner('fiscal-a', sellable = False)
        _, _, store_b        =   self._make_owner('fiscal-b', sellable = False)
        self.client.force_authenticate(user = user_a)
        response    =   self.client.put(self.URL, dict(self.VALID, store_id = store_b.id), format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StoreFiscalProfile.objects.filter(store = store_a).exists())
        self.assertFalse(StoreFiscalProfile.objects.filter(store = store_b).exists())


#=========================================
# OAUTH CONFIG — login social Google (dueño)
#=========================================
class OAuthConfigOwnerTests(StorePaymentsTestBase):
    URL         =   '/api/store-payments/oauth-config/'
    CLIENT_ID   =   '1234567890-abcdef.apps.googleusercontent.com'
    SECRET      =   'GOCSPX-test-secret-123'

    def _owner(self, name = 'oauth'):
        user, _, store   =   self._make_owner(name, sellable = False)
        self.client.force_authenticate(user = user)
        return user, store

    def test_get_defaults(self):
        self._owner('oauth-get')
        response    =   self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertFalse(data['enabled'])
        self.assertEqual(data['google_client_id'], '')
        self.assertFalse(data['has_client_secret'])
        self.assertFalse(data['has_own_client'])
        self.assertNotIn('google_client_secret', data)

    def test_put_secret_write_only_and_roundtrip(self):
        _, store   =   self._owner('oauth-put')
        response    =   self.client.put(self.URL, {
            'enabled'               :   True,
            'google_client_id'      :   self.CLIENT_ID,
            'google_client_secret'  :   self.SECRET,
        }, format = 'json')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertTrue(data['enabled'])
        self.assertTrue(data['has_own_client'])
        self.assertTrue(data['has_client_secret'])
        #El secret JAMÁS sale — ni como campo ni dentro del body.
        self.assertNotIn('google_client_secret', data)
        self.assertNotIn(self.SECRET, response.content.decode())
        cfg =   StoreOAuthConfig.objects.get(store = store)
        self.assertTrue(cfg.google_client_secret_enc.startswith('enc:v1:'))
        #Round-trip vault: solo el service lo descifra.
        self.assertEqual(cfg.get_client_secret(), self.SECRET)
        #GET tampoco lo expone.
        get_body    =   self.client.get(self.URL).content.decode()
        self.assertNotIn(self.SECRET, get_body)

    def test_secret_absent_keeps_existing(self):
        _, store   =   self._owner('oauth-merge')
        cfg, _      =   StoreOAuthConfig.objects.get_or_create(store = store)
        cfg.set_client_secret(self.SECRET)
        cfg.enabled =   True
        cfg.save()
        response    =   self.client.put(self.URL, {'enabled': False}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['enabled'])
        self.assertTrue(response.json()['has_client_secret'])
        cfg.refresh_from_db()
        self.assertEqual(cfg.get_client_secret(), self.SECRET)

    def test_secret_empty_string_clears(self):
        _, store   =   self._owner('oauth-clear')
        cfg, _      =   StoreOAuthConfig.objects.get_or_create(store = store)
        cfg.set_client_secret(self.SECRET)
        cfg.save()
        response    =   self.client.put(self.URL, {'google_client_secret': ''}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['has_client_secret'])
        cfg.refresh_from_db()
        self.assertEqual(cfg.get_client_secret(), '')

    def test_invalid_client_id_400(self):
        self._owner('oauth-badid')
        response    =   self.client.put(self.URL, {'google_client_id': 'no-es-google'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_idor_store_id_in_body_ignored(self):
        user_a, store_a   =   self._owner('oauth-a')
        _, _, store_b        =   self._make_owner('oauth-b', sellable = False)
        response    =   self.client.put(self.URL, {'enabled': True, 'store_id': store_b.id}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StoreOAuthConfig.objects.filter(store = store_a, enabled = True).exists())
        self.assertFalse(StoreOAuthConfig.objects.filter(store = store_b).exists())


#=========================================
# STORAGE CONFIG — bucket R2 propio (dueño)
#=========================================
class StorageConfigOwnerTests(StorePaymentsTestBase):
    URL         =   '/api/store-payments/storage-config/'
    GUIDE_URL   =   '/api/store-payments/storage-config/guide/'
    PAYLOAD     =   {
        'endpoint'          :   'https://abc123.r2.cloudflarestorage.com',
        'bucket'            :   'fotos-mi-tienda',
        'region'            :   'auto',
        'access_key'        :   'AKIAOWNER123',
        'secret_key'        :   'owner-secret-xyz',
        'public_base_url'   :   'https://pub-abc123.r2.dev',
        'enabled'           :   True,
    }

    def _owner(self, name = 'storage'):
        user, _, store   =   self._make_owner(name, sellable = False)
        self.client.force_authenticate(user = user)
        return user, store

    def test_get_defaults(self):
        self._owner('storage-get')
        response    =   self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertFalse(data['enabled'])
        self.assertFalse(data['is_configured'])
        self.assertFalse(data['has_credentials'])
        self.assertEqual(data['region'], 'auto')
        self.assertNotIn('access_key', data)
        self.assertNotIn('secret_key', data)

    def test_put_full_never_returns_secrets(self):
        _, store   =   self._owner('storage-put')
        cache.clear()
        response    =   self.client.put(self.URL, self.PAYLOAD, format = 'json')
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertTrue(data['enabled'])
        self.assertTrue(data['is_configured'])
        self.assertTrue(data['has_credentials'])
        self.assertEqual(data['url_mode'], 'public')
        self.assertEqual(data['bucket'], 'fotos-mi-tienda')
        body    =   response.content.decode()
        self.assertNotIn('AKIAOWNER123', body)
        self.assertNotIn('owner-secret-xyz', body)
        cfg =   StoreStorageConfig.objects.get(store = store)
        self.assertTrue(cfg.access_key_enc.startswith('enc:v1:'))
        self.assertTrue(cfg.secret_key_enc.startswith('enc:v1:'))
        #Round-trip vault: el service lo descifra, la API no.
        self.assertEqual(cfg.get_access_key(), 'AKIAOWNER123')
        self.assertEqual(cfg.get_secret_key(), 'owner-secret-xyz')
        get_body    =   self.client.get(self.URL).content.decode()
        self.assertNotIn('AKIAOWNER123', get_body)
        self.assertNotIn('owner-secret-xyz', get_body)

    def test_put_validation(self):
        self._owner('storage-val')
        #Endpoint sin https (http solo pasa en DEBUG con MinIO — acá no).
        response    =   self.client.put(self.URL, dict(self.PAYLOAD, endpoint = 'example.com'), format = 'json')
        self.assertEqual(response.status_code, 400)
        response    =   self.client.put(self.URL, dict(self.PAYLOAD, public_base_url = 'javascript:alert(1)'), format = 'json')
        self.assertEqual(response.status_code, 400)
        response    =   self.client.put(self.URL, dict(self.PAYLOAD, bucket = 'Bucket_Malo'), format = 'json')
        self.assertEqual(response.status_code, 400)
        #Sin credenciales el PUT igual guarda la config (enabled no la activa).
        response    =   self.client.put(self.URL, {'endpoint': self.PAYLOAD['endpoint'], 'bucket': 'otro-bucket'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['has_credentials'])

    def test_credentials_merge_and_clear(self):
        _, store   =   self._owner('storage-cred')
        self.client.put(self.URL, self.PAYLOAD, format = 'json')
        #Solo access_key -> has_credentials False (falta secret).
        response    =   self.client.put(self.URL, {'access_key': ''}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['has_credentials'])
        cfg =   StoreStorageConfig.objects.get(store = store)
        self.assertEqual(cfg.get_access_key(), '')
        self.assertEqual(cfg.get_secret_key(), 'owner-secret-xyz')

    def test_delete_disables_and_clears_secrets(self):
        _, store   =   self._owner('storage-del')
        self.client.put(self.URL, self.PAYLOAD, format = 'json')
        response    =   self.client.delete(self.URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertFalse(data['enabled'])
        self.assertFalse(data['has_credentials'])
        self.assertFalse(data['is_configured'])
        #Los secretos se limpiaron; la config no secreta queda.
        self.assertEqual(data['bucket'], 'fotos-mi-tienda')
        cfg =   StoreStorageConfig.objects.get(store = store)
        self.assertEqual(cfg.get_access_key(), '')
        self.assertEqual(cfg.get_secret_key(), '')

    def test_guide_es_ar(self):
        self._owner('storage-guide')
        response    =   self.client.get(self.GUIDE_URL)
        self.assertEqual(response.status_code, 200)
        data    =   response.json()
        self.assertIn('steps', data)
        self.assertIn('warnings', data)
        self.assertTrue(any('R2' in s for s in data['steps']))

    def test_idor_store_id_in_body_ignored(self):
        user_a, store_a   =   self._owner('storage-a')
        _, _, store_b        =   self._make_owner('storage-b', sellable = False)
        response    =   self.client.put(self.URL, dict(self.PAYLOAD, store_id = store_b.id), format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StoreStorageConfig.objects.filter(store = store_a, enabled = True).exists())
        self.assertFalse(StoreStorageConfig.objects.filter(store = store_b).exists())

    def test_put_invalidates_byo_cache(self):
        #El PUT deja el cache BYO invalidado: storage.py resuelve el
        #backend nuevo en la próxima llamada sin esperar el TTL.
        _, store   =   self._owner('storage-cache')
        cache.clear()
        self.assertIsNone(storage_service._byo_backend(store.id))
        self.client.put(self.URL, self.PAYLOAD, format = 'json')
        backend =   storage_service._byo_backend(store.id)
        self.assertIsNotNone(backend)
        self.assertEqual(backend['bucket'], 'fotos-mi-tienda')
        self.assertEqual(backend['access_key'], 'AKIAOWNER123')


#=========================================
# STORAGE BYO — resolución de backend por tienda (stores.services.storage)
#=========================================
class StoreStorageByoTests(StorePaymentsTestBase):
    """
    Routing del storage: con BYO activo los objetos 'stores/<id>/...' van
    al bucket del dueño; sin BYO (o con secreto ilegible) al DAVENT;
    object_url prefiere public_base_url del dueño o firma con SUS
    credenciales. boto3 se mockea en `_client` — el dispatch devuelve
    un mock distinto según el backend resuelto.
    """

    def setUp(self):
        cache.clear()
        self.user, _, self.store   =   self._make_owner('byo-store', sellable = False)
        self.byo_client            =   Mock()
        self.davent_client         =   Mock()
        self.byo_client.put_object.return_value                  =   {}
        self.byo_client.delete_object.return_value               =   {}
        self.byo_client.generate_presigned_url.return_value      =   'https://signed-owner.example/x'
        self.davent_client.put_object.return_value               =   {}
        self.davent_client.delete_object.return_value            =   {}
        self.davent_client.generate_presigned_url.return_value   =   'https://signed-davent.example/x'

    def _client_dispatch(self, backend = None):
        return self.byo_client if backend is not None else self.davent_client

    def _patches(self):
        return (
            patch.object(storage_service, 'storage_configured', return_value = True),
            patch.object(storage_service, '_public_base', return_value = 'https://cdn.davent.test'),
            patch.object(storage_service, '_bucket', return_value = 'davent-bucket'),
            patch.object(storage_service, '_client', side_effect = self._client_dispatch),
        )

    def _byo_config(self, store = None, *, enabled = True, public_base_url = 'https://pub-owner.r2.dev'):
        store   =   store or self.store
        cfg     =   StoreStorageConfig.objects.create(
            store           =   store,
            endpoint        =   'https://acct.r2.cloudflarestorage.com',
            bucket          =   'bucket-del-duenio',
            region          =   'auto',
            public_base_url =   public_base_url,
            enabled         =   enabled,
        )
        cfg.set_credentials('OWNER_ACCESS', 'OWNER_SECRET')
        cfg.save()
        return cfg

    def test_put_object_byo_goes_to_owner_bucket(self):
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            key =   storage_service.put_object(f'stores/{self.store.id}/proofs/x.webp', b'1', 'image/webp')
        self.assertTrue(key.startswith(f'stores/{self.store.id}/proofs/'))
        self.byo_client.put_object.assert_called_once()
        self.assertEqual(self.byo_client.put_object.call_args.kwargs['Bucket'], 'bucket-del-duenio')
        self.davent_client.put_object.assert_not_called()

    def test_put_object_without_byo_goes_davent(self):
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            storage_service.put_object(f'stores/{self.store.id}/proofs/x.webp', b'1', 'image/webp')
        self.davent_client.put_object.assert_called_once()
        self.assertEqual(self.davent_client.put_object.call_args.kwargs['Bucket'], 'davent-bucket')
        self.byo_client.put_object.assert_not_called()

    def test_put_object_byo_failure_falls_back_davent(self):
        self._byo_config()
        self.byo_client.put_object.side_effect   =   Exception('bucket caído')
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            key =   storage_service.put_object(f'stores/{self.store.id}/proofs/x.webp', b'1', 'image/webp')
        self.assertTrue(key)
        self.davent_client.put_object.assert_called_once()

    def test_put_object_non_store_key_always_davent(self):
        #Chat/adjuntos sin patrón stores/<id>/ nunca van al bucket del dueño.
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            storage_service.put_object('chat/1/adj.webp', b'1', 'image/webp')
        self.davent_client.put_object.assert_called_once()
        self.byo_client.put_object.assert_not_called()

    def test_put_object_byo_disabled_goes_davent(self):
        self._byo_config(enabled = False)
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            storage_service.put_object(f'stores/{self.store.id}/x/y.webp', b'1', 'image/webp')
        self.davent_client.put_object.assert_called_once()
        self.byo_client.put_object.assert_not_called()

    def test_object_url_byo_public_base(self):
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            url =   storage_service.object_url(f'stores/{self.store.id}/logo/abc.webp')
        self.assertEqual(url, f'https://pub-owner.r2.dev/stores/{self.store.id}/logo/abc.webp')
        self.byo_client.generate_presigned_url.assert_not_called()
        self.davent_client.generate_presigned_url.assert_not_called()

    def test_object_url_byo_without_public_base_presigns_with_owner_creds(self):
        #BYO sin URL pública: URLs firmadas con las credenciales DEL DUEÑO
        #(el objeto vive en su bucket, no en el de DAVENT).
        self._byo_config(public_base_url = '')
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            url =   storage_service.object_url(f'stores/{self.store.id}/logo/abc.webp')
        self.assertEqual(url, 'https://signed-owner.example/x')
        self.byo_client.generate_presigned_url.assert_called_once()
        params  =   self.byo_client.generate_presigned_url.call_args.kwargs['Params']
        self.assertEqual(params['Bucket'], 'bucket-del-duenio')
        self.davent_client.generate_presigned_url.assert_not_called()

    def test_object_url_private_byo_presigns(self):
        #Comprobantes de la tienda con BYO: private=True fuerza firma
        #aunque haya public_base_url — con el cliente del dueño.
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            url =   storage_service.object_url(f'stores/{self.store.id}/proofs/x.webp', private = True, expires = 600)
        self.assertEqual(url, 'https://signed-owner.example/x')
        self.byo_client.generate_presigned_url.assert_called_once()
        self.assertEqual(self.byo_client.generate_presigned_url.call_args.kwargs['ExpiresIn'], 600)

    def test_object_url_chat_key_uses_davent(self):
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            url =   storage_service.object_url('chat/1/x.webp')
        self.assertEqual(url, 'https://cdn.davent.test/chat/1/x.webp')

    def test_object_url_other_store_key_unaffected(self):
        #La key de OTRA tienda sin BYO resuelve DAVENT aunque exista una
        #config BYO en este store.
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            url =   storage_service.object_url('stores/999999/logo/x.webp')
        self.assertEqual(url, 'https://cdn.davent.test/stores/999999/logo/x.webp')

    def test_delete_object_byo_then_davent_fallback(self):
        self._byo_config()
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            storage_service._delete_object(f'stores/{self.store.id}/logo/viejo.webp')
        self.byo_client.delete_object.assert_called_once()
        self.davent_client.delete_object.assert_not_called()
        #Si el delete del dueño falla se intenta DAVENT (el objeto pudo
        #haber quedado ahí por un fallback de upload).
        self.byo_client.delete_object.side_effect   =   Exception('fail')
        with p1, p2, p3, p4:
            storage_service._delete_object(f'stores/{self.store.id}/logo/viejo2.webp')
        self.davent_client.delete_object.assert_called_once()

    def test_tampered_secret_falls_back_to_davent(self):
        #enc:v1: manipulado/desconocido -> VaultError -> backend None ->
        #todo cae a DAVENT (nunca romper la tienda por un secreto roto).
        cfg =   self._byo_config()
        cfg.access_key_enc   =   'enc:v1:kid-inexistente:AAAA'
        cfg.save()
        storage_service.invalidate_store_storage(self.store.id)
        p1, p2, p3, p4   =   self._patches()
        with p1, p2, p3, p4:
            storage_service.put_object(f'stores/{self.store.id}/proofs/x.webp', b'1', 'image/webp')
        self.davent_client.put_object.assert_called_once()
        self.byo_client.put_object.assert_not_called()

    def test_store_storage_configured_byo_without_davent(self):
        #Con BYO activo el upload funciona aunque DAVENT no tenga envs.
        self._byo_config()
        with patch.object(storage_service, 'storage_configured', return_value = False):
            self.assertTrue(storage_service.store_storage_configured(self.store))
            #Sin BYO ni DAVENT -> False.
            _, _, store2   =   self._make_owner('byo-sin', sellable = False)
            self.assertFalse(storage_service.store_storage_configured(store2))
