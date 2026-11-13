"""
Tests de AUDITORÍA ADVERSARIAL del webhook de Mercado Pago del vendedor
(`POST /api/webhooks/store-mp/<slug>/` -> StoreMpWebhookQuery).

Complementan a tests.py (que cubre el happy path y la firma) atacando los
bordes que un auditor busca:

- Regresión de estado de MpPayment: MP reintenta notificaciones y pueden
  llegar DESORDENADAS — un 'approved' tardío no puede "des-reembolsar" un
  cobro ni un estado intermedio (in_process/in_mediation) puede
  "des-acreditar" un pago ya aprobado.
- Cobro aprobado sobre pedido CERRADO (EXPIRED/CANCELLED/REFUNDED):
  mark_order_paid solo acredita desde PENDING_PAYMENT — la plata entró
  igual y sin evento el dueño jamás se entera (debe reembolsar a mano).
- Doble cobro: un SEGUNDO payment_id aprobado sobre un pedido ya pago
  (PACKING/SHIPPED/...) es dinero duplicado del comprador -> OrderEvent.
- Reembolso/contracargo con pedido DELIVERED: REFUNDED es inalcanzable
  por TRANSITIONS — sin evento la devolución queda invisible.
- Carrera de refund: mark_order_refunded puede lanzar ValidationError si
  el pedido cambió entre la lectura y el lock interno -> el webhook NO
  debe devolver 500 (MP reintentaría en loop contra un estado terminal).
- Moneda ausente: currency_id faltante NO es ARS (fail-closed).
- live_mode ausente en producción: sin la señal no se puede distinguir
  un cobro real de uno de prueba -> rechazo (fail-closed).

Reusa los helpers/contrato de tests.py (StorePaymentsTestBase, _mp_payment,
_fake_order) — el modelo Order y los services de orders se patchean en
orders_bridge igual que en la suite principal.
"""
import uuid
from unittest.mock import patch

from django.test import override_settings
from rest_framework import serializers

from StoreApp.domains.storepayments.models import MpPayment
from StoreApp.domains.storepayments.tests import (
    BRIDGE,
    MP_CLIENT,
    StorePaymentsTestBase,
    _fake_order,
    _mp_payment,
)


class WebhookAuditBase(StorePaymentsTestBase):
    """SetUp + entrega firmada de un payment de MP con el bridge mockeado."""

    def setUp(self):
        self.user, _, self.store   =   self._make_owner('audit')
        self._connect_mp(self.store)
        self.order                 =   _fake_order(self.store)

    def _deliver(self, mp_payment, order = None, request_id = None, mark_refunded_side_effect = None):
        """POST firmado al webhook con get_mp_payment controlado.

        Devuelve (response, mocks). Cada llamada usa un x-request-id único
        (el dedup del view usa cache.add — un id repetido se tragaría la
        entrega como 'ya procesada' sin llegar al service).
        """
        order       =   self.order if order is None else order
        request_id  =   request_id or f'req-{uuid.uuid4().hex[:12]}'
        with patch(f'{MP_CLIENT}.get_mp_payment', return_value = mp_payment), \
             patch(f'{BRIDGE}.find_order_by_token', return_value = order), \
             patch(f'{BRIDGE}.mark_paid') as mark_paid, \
             patch(f'{BRIDGE}.mark_refunded', side_effect = mark_refunded_side_effect) as mark_refunded, \
             patch(f'{BRIDGE}.append_event') as append_event:
            response    =   self._post_webhook(self.store.slug, mp_payment['id'], request_id = request_id)
        return response, {
            'mark_paid'     :   mark_paid,
            'mark_refunded' :   mark_refunded,
            'append_event'  :   append_event,
        }

    def _event_kinds(self, mocks):
        return [call.kwargs.get('kind') for call in mocks['append_event'].call_args_list]


#=========================================
# REGRESIÓN DE ESTADO (notificaciones desordenadas de MP)
#=========================================
class WebhookStatusRegressionTests(WebhookAuditBase):

    def test_late_approved_after_refund_keeps_refunded(self):
        #1º entrega: el pago fue reembolsado -> MpPayment REFUNDED.
        paid_order  =   _fake_order(self.store, status = 'PACKING')
        response, _   =   self._deliver(_mp_payment(status = 'refunded'), order = paid_order)
        self.assertEqual(response.status_code, 200)
        #2º entrega: un reintento VIEJO de MP llega tarde con 'approved'
        #(las notificaciones no garantizan orden). El pedido ya está
        #REFUNDED — el registro NO puede volver a APPROVED.
        closed_order    =   _fake_order(self.store, status = 'REFUNDED')
        response, mocks =   self._deliver(_mp_payment(status = 'approved'), order = closed_order)
        self.assertEqual(response.status_code, 200)
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.REFUNDED)
        mocks['mark_paid'].assert_not_called()

    def test_intermediate_status_does_not_unapprove(self):
        #approved primero; después MP reporta un estado intermedio del
        #mismo pago (in_process/in_mediation -> PENDING en el mapeo).
        #El registro NO puede "des-acreditar" un cobro ya aprobado.
        response, _   =   self._deliver(_mp_payment(status = 'approved'))
        self.assertEqual(response.status_code, 200)
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.APPROVED)
        response, mocks =   self._deliver(_mp_payment(status = 'in_process'))
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.status, MpPayment.Status.APPROVED)
        mocks['mark_paid'].assert_not_called()
        mocks['mark_refunded'].assert_not_called()

    def test_rejected_then_approved_upgrades(self):
        #La regresión no debe bloquear la transición legítima
        #rejected -> approved (MP reintentó y el pago se acreditó).
        order   =   _fake_order(self.store, status = 'PENDING_PAYMENT')
        response, _   =   self._deliver(_mp_payment(status = 'rejected'), order = order)
        self.assertEqual(response.status_code, 200)
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.REJECTED)
        response, mocks =   self._deliver(_mp_payment(status = 'approved'), order = order)
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.status, MpPayment.Status.APPROVED)
        mocks['mark_paid'].assert_called_once()


#=========================================
# COBRO APROBADO SOBRE PEDIDO CERRADO / YA PAGO
#=========================================
class WebhookClosedOrderTests(WebhookAuditBase):

    def test_approved_on_expired_order_flags_manual_review(self):
        #El comprador pagó DESPUÉS del vencimiento del pedido: la plata
        #entró pero mark_order_paid no puede acreditar EXPIRED — sin un
        #evento el dueño jamás se entera de que debe reembolsar.
        order   =   _fake_order(self.store, status = 'EXPIRED')
        response, mocks =   self._deliver(_mp_payment(), order = order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        self.assertIn('paid_after_close', self._event_kinds(mocks))
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.APPROVED)

    def test_approved_on_cancelled_order_flags_manual_review(self):
        order   =   _fake_order(self.store, status = 'CANCELLED')
        response, mocks =   self._deliver(_mp_payment(), order = order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        self.assertIn('paid_after_close', self._event_kinds(mocks))

    def test_second_payment_on_paid_order_flags_duplicate(self):
        #Pedido ya pago (PACKING) y llega OTRO payment_id aprobado con el
        #mismo monto: es un cobro duplicado real del comprador — debe
        #quedar OrderEvent para que el dueño devuelva el excedente.
        order   =   _fake_order(self.store, status = 'PACKING')
        response, mocks =   self._deliver(_mp_payment(payment_id = 999), order = order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        self.assertIn('duplicate_payment', self._event_kinds(mocks))
        record  =   MpPayment.objects.get(mp_payment_id = '999')
        self.assertEqual(record.status, MpPayment.Status.APPROVED)

    def test_approved_never_pays_non_mp_order(self):
        #Un pago MP aprobado NO puede acreditar un pedido creado para
        #transferencia/efectivo: el método del pedido se valida fresco
        #bajo lock antes de mark_paid — si no, cualquier cobro MP
        #registrado contra ese pedido lo "pagaba" sin transferencia.
        order   =   _fake_order(self.store, status = 'PENDING_PAYMENT', payment_method = 'transfer')
        response, mocks =   self._deliver(_mp_payment(), order = order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        #Queda flagged para revisión manual (la plata MP existe).
        self.assertIn('paid_after_close', self._event_kinds(mocks))


#=========================================
# REEMBOLSO / CONTRACARGO
#=========================================
class WebhookRefundTests(WebhookAuditBase):

    def test_refund_on_delivered_order_flags_manual_review(self):
        #Contracargo/reembolso MP sobre un pedido DELIVERED: la máquina
        #de estados no permite REFUNDED — la devolución queda invisible
        #si no se registra el evento.
        order   =   _fake_order(self.store, status = 'DELIVERED')
        response, mocks =   self._deliver(_mp_payment(status = 'charged_back'), order = order)
        self.assertEqual(response.status_code, 200)
        mocks['mark_refunded'].assert_not_called()
        self.assertIn('refund_after_delivery', self._event_kinds(mocks))
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.REFUNDED)

    def test_refund_transition_error_does_not_500(self):
        #Carrera: el pedido era SHIPPED al leerlo pero cambió antes del
        #lock interno de mark_order_refunded (otro refund, DELIVERED…).
        #ValidationError NO puede propagar -> MP reintentaría en loop.
        order   =   _fake_order(self.store, status = 'SHIPPED')
        response, mocks =   self._deliver(
            _mp_payment(status = 'refunded'),
            order   =   order,
            mark_refunded_side_effect =   serializers.ValidationError({'status': 'sin transición'}),
        )
        self.assertEqual(response.status_code, 200)
        record  =   MpPayment.objects.get(mp_payment_id = '555')
        self.assertEqual(record.status, MpPayment.Status.REFUNDED)


#=========================================
# HARDENING (fail-closed)
#=========================================
class WebhookHardeningTests(WebhookAuditBase):

    @override_settings(DEBUG = False)
    def test_missing_live_mode_rejected_in_prod(self):
        #Sin live_mode no hay forma de distinguir un cobro real de uno
        #de prueba: en producción se rechaza (fail-closed).
        payment =   _mp_payment()
        payment.pop('live_mode')
        response, mocks =   self._deliver(payment)
        self.assertEqual(response.status_code, 400)
        mocks['mark_paid'].assert_not_called()
        self.assertFalse(MpPayment.objects.filter(mp_payment_id = '555').exists())

    def test_missing_currency_never_credits(self):
        #currency_id ausente NO es ARS por defecto: un payment sin
        #moneda verificable jamás acredita un pedido ARS.
        response, mocks =   self._deliver(_mp_payment(currency = None))
        self.assertEqual(response.status_code, 200)
        mocks['mark_paid'].assert_not_called()
        self.assertFalse(MpPayment.objects.filter(mp_payment_id = '555').exists())
