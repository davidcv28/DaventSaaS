"""
Tests adversariales del checkout/preferencias MP (auditoría del ciclo de
vida preference -> pay -> webhook).

Cobertura:
- Integridad de monto: la suma de items DEBE ser order.total (MP cobra
  la suma de items y el webhook exige transaction_amount == total).
  Envío a domicilio (shipping_cost) no vive en OrderItem -> debe
  itemizarse o caer al item agregado.
- Gate de estado/vencimiento: PENDING_PAYMENT vencido por expires_at
  (cron aún no corrió) no admite preferencia.
- Doble submit: una preferencia ABIERTA (MpPayment CREATED sin
  mp_payment_id) se reutiliza — nunca dos links pagables por un pedido.
- mp_client.get_preference: validación de id antes de llamar a MP.
"""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.utils import timezone

from StoreApp.domains.storepayments.models import MpPayment
from StoreApp.domains.storepayments.services import mp_client
from StoreApp.domains.storepayments.services.mp_client import MpApiError
from StoreApp.domains.storepayments.services.preferences import build_preference_payload
from StoreApp.domains.storepayments.tests import (
    MP_CLIENT,
    MP_TOKEN_TEST,
    StorePaymentsTestBase,
    _fake_order,
)

BRIDGE      =   'StoreApp.domains.storepayments.services.orders_bridge'
PREFS       =   'StoreApp.domains.storepayments.services.preferences'


def _item(name, qty, unit_price):
    """OrderItem fake según el contrato del track B (name/qty/unit_price)."""
    return SimpleNamespace(name = name, qty = qty, unit_price = Decimal(str(unit_price)))


def _order(store, *, total, items = None, shipping_cost = None, status = 'PENDING_PAYMENT',
           expires_at = None, payment_method = 'mp', token = 'tok-audit', pk = 77):
    """Order fake con los attrs que lee el checkout/preferencias."""
    order   =   _fake_order(store, token = token, status = status, total = str(total),
                            payment_method = payment_method, pk = pk)
    order.items              =   items if items is not None else []
    order.shipping_cost      =   Decimal(str(shipping_cost)) if shipping_cost is not None else Decimal('0')
    order.shipping_priced    =   bool(order.shipping_cost)
    order.expires_at         =   expires_at
    return order


def _items_sum(payload):
    return sum(Decimal(str(i['unit_price'])) * i['quantity'] for i in payload['items'])


#=========================================
# INTEGRIDAD DE MONTO (items vs order.total)
#=========================================
class PreferenceAmountIntegrityTests(StorePaymentsTestBase):

    def setUp(self):
        _, _, self.store   =   self._make_owner('montos')

    def test_itemized_sum_equals_total_without_shipping(self):
        order   =   _order(self.store, total = '1500.00',
                           items = [_item('Remera', 2, '500.00'), _item('Gorra', 1, '500.00')])
        payload =   build_preference_payload(order, self.store)
        self.assertEqual(len(payload['items']), 2)
        self.assertEqual(_items_sum(payload), Decimal('1500.00'))

    def test_shipping_cost_is_charged_as_own_line(self):
        #total = subtotal(1000) + envio(500): MP cobra la SUMA DE ITEMS —
        #sin línea de envío el cliente paga 1000 y el webhook ve
        #amount != total -> amount_mismatch y el pedido jamás se acredita.
        order   =   _order(self.store, total = '1500.00', shipping_cost = '500.00',
                           items = [_item('Remera', 2, '500.00')])
        payload =   build_preference_payload(order, self.store)
        self.assertEqual(_items_sum(payload), Decimal('1500.00'))
        titles  =   [i['title'] for i in payload['items']]
        self.assertIn('Envío', titles)

    def test_unexplained_difference_falls_back_to_total(self):
        #Items que NO cuadran con el total por causa desconocida: mejor
        #UN item agregado por order.total que un cobro que no matchea.
        order   =   _order(self.store, total = '1000.00',
                           items = [_item('Remera', 1, '900.00')])
        payload =   build_preference_payload(order, self.store)
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(Decimal(str(payload['items'][0]['unit_price'])), Decimal('1000.00'))
        self.assertIn('tok-audit', payload['items'][0]['title'])

    def test_missing_item_price_falls_back_to_order_total(self):
        order   =   _order(self.store, total = '777.00',
                           items = [SimpleNamespace(name = 'Sin precio', qty = 1)])
        payload =   build_preference_payload(order, self.store)
        self.assertEqual(len(payload['items']), 1)
        self.assertEqual(Decimal(str(payload['items'][0]['unit_price'])), Decimal('777.00'))

    def test_back_urls_and_auto_return_by_domain_mode(self):
        order   =   _order(self.store, total = '100.00')
        #Sin PLATFORM_DOMAIN en test -> modo path con FRONTEND_URL (http):
        #auto_return NO se envía (MP exige https en back_urls).
        payload =   build_preference_payload(order, self.store)
        self.assertNotIn('auto_return', payload)
        self.assertTrue(all(u.startswith('http') for u in payload['back_urls'].values()))
        self.assertIn(f'/{self.store.slug}/seguimiento', payload['back_urls']['success'])
        #Con subdominio de plataforma -> https + auto_return approved.
        with patch(f'{PREFS}.PLATFORM_DOMAIN', 'davent.example.com'):
            payload =   build_preference_payload(order, self.store)
        self.assertEqual(payload['auto_return'], 'approved')
        self.assertTrue(payload['back_urls']['success'].startswith(f'https://{self.store.slug}.davent.example.com'))


#=========================================
# GATE DEL ENDPOINT /pay/ (estado + vencimiento + submit)
#=========================================
class PublicOrderPayAuditTests(StorePaymentsTestBase):
    PAY_URL     =   '/api/stores/public/tienda-pagador-audit/orders/tok-audit/pay/'

    def setUp(self):
        self.user, _, self.store   =   self._make_owner('pagador-audit')
        self._connect_mp(self.store)
        self.order                 =   _order(self.store, total = '1500.00')
        self.preference            =   {'id': 'pref-new', 'init_point': 'https://mp.example/init',
                                        'sandbox_init_point': 'https://mp.example/sandbox'}

    def _pay(self, order = None):
        order   =   self.order if order is None else order
        with patch(f'{MP_CLIENT}.create_preference', return_value = self.preference) as create_pref, \
             patch(f'{MP_CLIENT}.get_preference') as get_pref, \
             patch(f'{BRIDGE}.find_order_by_token', return_value = order):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        return response, create_pref, get_pref

    def test_expired_pending_order_rejected_409(self):
        #expires_at ya pasó pero el cron expire_orders no corrió: el
        #pedido sigue PENDING_PAYMENT — no debe emitir preferencia.
        order   =   _order(self.store, total = '100.00',
                           expires_at = timezone.now() - timedelta(minutes = 1))
        response, create_pref, _   =   self._pay(order = order)
        self.assertEqual(response.status_code, 409)
        create_pref.assert_not_called()

    def test_terminal_states_rejected_409(self):
        for st in ('EXPIRED', 'CANCELLED', 'REFUNDED', 'PAID', 'PACKING', 'SHIPPED', 'DELIVERED'):
            order   =   _order(self.store, total = '100.00', status = st)
            response, create_pref, _   =   self._pay(order = order)
            self.assertEqual(response.status_code, 409, f'status={st}')
            create_pref.assert_not_called()

    def test_open_preference_is_reused_not_duplicated(self):
        #Doble click / retry: ya hay una preferencia ABIERTA para el
        #pedido -> se re-lee de MP y se devuelve la MISMA. Dos
        #preferencias vivas = dos cobros posibles por un solo pedido.
        attempt =   MpPayment.objects.create(
            store               =   self.store,
            order_id            =   self.order.pk,
            tracking_token      =   'tok-audit',
            preference_id       =   'pref-open-1',
            status              =   MpPayment.Status.CREATED,
            amount              =   Decimal('1500.00'),
        )
        #Sin sandbox_init_point: con token TEST- el checkout_url cae al init_point.
        reused  =   {'id': 'pref-open-1', 'init_point': 'https://mp.example/reuse'}
        with patch(f'{MP_CLIENT}.create_preference', return_value = self.preference) as create_pref, \
             patch(f'{MP_CLIENT}.get_preference', return_value = reused) as get_pref, \
             patch(f'{BRIDGE}.find_order_by_token', return_value = self.order):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preference_id'], 'pref-open-1')
        self.assertEqual(response.json()['checkout_url'], 'https://mp.example/reuse')
        create_pref.assert_not_called()
        #Se re-leyó con el token DEL VENDEDOR (nunca uno global DAVENT).
        args, _   =   get_pref.call_args
        self.assertEqual(args[0], 'pref-open-1')
        self.assertEqual(args[1], MP_TOKEN_TEST)
        self.assertEqual(MpPayment.objects.filter(order_id = self.order.pk).count(), 1)

    def test_gone_preference_falls_back_to_new(self):
        #La preferencia abierta ya no existe en MP (404/410/400): se
        #emite una nueva en vez de devolver un link muerto.
        MpPayment.objects.create(
            store               =   self.store,
            order_id            =   self.order.pk,
            tracking_token      =   'tok-audit',
            preference_id       =   'pref-dead',
            status              =   MpPayment.Status.CREATED,
            amount              =   Decimal('1500.00'),
        )
        with patch(f'{MP_CLIENT}.create_preference', return_value = self.preference) as create_pref, \
             patch(f'{MP_CLIENT}.get_preference', side_effect = MpApiError('gone', status_code = 404)), \
             patch(f'{BRIDGE}.find_order_by_token', return_value = self.order):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preference_id'], 'pref-new')
        create_pref.assert_called_once()

    def test_mp_network_error_on_reuse_does_not_duplicate(self):
        #Si MP no responde al re-lectura NO se crea una segunda
        #preferencia a ciegas: el cliente reintenta y obtiene 502.
        MpPayment.objects.create(
            store               =   self.store,
            order_id            =   self.order.pk,
            tracking_token      =   'tok-audit',
            preference_id       =   'pref-open-2',
            status              =   MpPayment.Status.CREATED,
            amount              =   Decimal('1500.00'),
        )
        with patch(f'{MP_CLIENT}.create_preference', return_value = self.preference) as create_pref, \
             patch(f'{MP_CLIENT}.get_preference', side_effect = MpApiError('red', status_code = None)), \
             patch(f'{BRIDGE}.find_order_by_token', return_value = self.order):
            response    =   self.client.post(self.PAY_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 502)
        create_pref.assert_not_called()

    def test_create_uses_seller_token_never_global(self):
        response, create_pref, _   =   self._pay()
        self.assertEqual(response.status_code, 200)
        args, _   =   create_pref.call_args
        self.assertEqual(args[1], MP_TOKEN_TEST)


#=========================================
# mp_client.get_preference (idempotencia del checkout)
#=========================================
class MpClientGetPreferenceTests(StorePaymentsTestBase):

    def test_get_preference_validates_id_before_http(self):
        with patch('requests.request') as req:
            for bad in ('', '../admin', 'a' * 65, 'con espacio'):
                with self.assertRaises(MpApiError):
                    mp_client.get_preference(bad, 'tok')
        req.assert_not_called()

    def test_get_preference_calls_seller_token_endpoint(self):
        fake    =   SimpleNamespace(status_code = 200, content = b'{"id":"p1"}',
                                    json = lambda: {'id': 'p1'})
        with patch('requests.request', return_value = fake) as req:
            data    =   mp_client.get_preference('pref-123', 'SELLER-TOKEN')
        self.assertEqual(data['id'], 'p1')
        args, kwargs   =   req.call_args
        self.assertEqual(args[0], 'GET')
        self.assertIn('/checkout/preferences/pref-123', args[1])
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer SELLER-TOKEN')
        self.assertEqual(kwargs['timeout'], mp_client.MP_TIMEOUT)
