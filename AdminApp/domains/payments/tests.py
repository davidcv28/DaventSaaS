"""
Tests de seguridad del dominio payments.

El webhook de Mercado Pago exige firma HMAC-SHA256 válida cuando
MP_WEBHOOK_SECRET está configurado; sin secret solo se procesa en dev con
el opt-in explícito MP_WEBHOOK_ALLOW_UNSIGNED (además de DEBUG).
"""
import hashlib
import hmac
import os
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import Province, City, ZipCode
from AdminApp.domains.payments.models import DailyRevenue, MonthlyRevenue, Payment
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.payments.services.services import (
    CancelPreapprovalQuery,
    CreatePaymentQuery,
    SyncPreapprovalQuery,
    UpdateRevenueRollupsQuery,
)

WEBHOOK_URL = '/api/payments/webhook/'
SECRET      = 'test-webhook-secret'


def _signature_headers(resource_id, request_id = 'req-1', secret = SECRET, ts = None):
    #El default es el instante actual para que la ventana anti-replay
    #(10 min) lo acepte; los tests de firma vieja pasan un ts explícito.
    ts          =   ts or str(int(timezone.now().timestamp()))
    manifest    =   f'id:{resource_id};request-id:{request_id};ts:{ts};'
    v1          =   hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {
        'HTTP_X_SIGNATURE'  :   f'ts={ts},v1={v1}',
        'HTTP_X_REQUEST_ID' :   request_id,
    }


class MercadoPagoWebhookSignatureTests(TestCase):
    #APIClient: el Client de Django ignora format='json' y form-encodea el
    #body, dejando 'data' como string (y el endpoint real recibe JSON de MP).
    client_class    =   APIClient

    def _post(self, signature_headers = None):
        return self.client.post(
            WEBHOOK_URL,
            {'type': 'payment', 'data': {'id': '12345'}},
            format = 'json',
            **(signature_headers or {}),
        )

    @override_settings(DEBUG = True)
    @patch('AdminApp.domains.payments.views.viewset.config', lambda *a, **kw: kw.get('default', ''))
    def test_malformed_data_does_not_crash(self):
        #Body malformado (data no-dict): 401/200, jamás 500.
        response    =   self.client.post(WEBHOOK_URL, {'type': 'payment', 'data': 'basura'}, format = 'json')
        self.assertIn(response.status_code, (200, 401))

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_rejects_request_without_signature(self):
        response    =   self._post()
        self.assertEqual(response.status_code, 401)

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_rejects_invalid_signature(self):
        response    =   self._post({
            'HTTP_X_SIGNATURE'  :   'ts=1700000000,v1=firma-trucha',
            'HTTP_X_REQUEST_ID' :   'req-1',
        })
        self.assertEqual(response.status_code, 401)

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_accepts_valid_signature(self, webhook_query):
        response    =   self._post(_signature_headers('12345'))
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')

    @override_settings(DEBUG = True)
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_processes_unsigned_request_only_with_explicit_flag(self, webhook_query):
        #El bypass de firma en dev exige MP_WEBHOOK_ALLOW_UNSIGNED=True además
        #de DEBUG: un DEBUG accidental en prod ya no abre el webhook.
        fake    =   lambda *a, **kw: True if a and a[0] == 'MP_WEBHOOK_ALLOW_UNSIGNED' else kw.get('default', '')
        with patch('AdminApp.domains.payments.views.viewset.config', side_effect = fake):
            response    =   self._post()
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')

    @override_settings(DEBUG = True)
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_rejects_unsigned_request_without_flag_in_debug(self, webhook_query):
        #Sin secret y sin el flag explícito se rechaza igual que en producción.
        with patch('AdminApp.domains.payments.views.viewset.config', lambda *a, **kw: kw.get('default', '')):
            response    =   self._post()
        self.assertEqual(response.status_code, 401)
        webhook_query.assert_not_called()

    @override_settings(DEBUG = False)
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_unsigned_flag_is_inert_outside_debug(self, webhook_query):
        #El flag colado a un entorno sin DEBUG no habilita el bypass.
        fake    =   lambda *a, **kw: True if a and a[0] == 'MP_WEBHOOK_ALLOW_UNSIGNED' else kw.get('default', '')
        with patch('AdminApp.domains.payments.views.viewset.config', side_effect = fake):
            response    =   self._post()
        self.assertEqual(response.status_code, 401)
        webhook_query.assert_not_called()

    @override_settings(DEBUG = False)
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_rejects_unsigned_request_when_secret_missing_in_prod(self, webhook_query):
        #Sin MP_WEBHOOK_SECRET en producción el evento se rechaza: un webhook
        #sin verificar permitiría forjar acreditaciones de pago.
        with patch('AdminApp.domains.payments.views.viewset.config', lambda *a, **kw: kw.get('default', '')):
            response    =   self._post()
        self.assertEqual(response.status_code, 401)
        webhook_query.assert_not_called()


SERVICES_MODULE   =   'AdminApp.domains.payments.services.services'


def _make_suscription(**overrides):
    province    =   Province.objects.create(name_province = 'Mendoza')
    zipcode     =   ZipCode.objects.create(zipcode = '5500')
    city        =   City.objects.create(name_city = 'Mendoza', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = 'cliente', email = 'cliente@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user        =   user,
        first_name  =   'Ana',
        last_name   =   'Perez',
        document    =   '27123456',
        province    =   province,
        city        =   city,
    )
    plan        =   SuscriptionPlan.objects.create(name = 'Plan premium', price = 1000)
    defaults    =   {
        'status'            :   Suscription.STATUS_ACTIVE,
        'start_date'        :   timezone.now(),
        'end_date'          :   timezone.now() + timedelta(days = 20),
        'auto_renew'        :   True,
        'preapproval_id'    :   'pre-123',
    }
    defaults.update(overrides)
    return Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        **defaults,
    )


class PreapprovalCancelTests(TestCase):
    """Baja del débito automático: cancela en MP, apaga auto_renew y el
    acceso muere en end_date (sin gracia). Un estado 'cancelled' en MP
    jamás puede volver a habilitar auto_renew."""

    @patch(f'{SERVICES_MODULE}.sdk')
    @patch(f'{SERVICES_MODULE}.GetPreapproval')
    def test_cancel_calls_mp_and_disables_auto_renew(self, get_preapproval, sdk):
        suscription                 =   _make_suscription()
        get_preapproval.return_value    =   {'status': 'authorized'}
        sdk.preapproval.return_value.update.return_value    =   {'status': 200}
        CancelPreapprovalQuery(suscription)
        suscription.refresh_from_db()
        sdk.preapproval.return_value.update.assert_called_once_with('pre-123', {'status': 'cancelled'})
        self.assertFalse(suscription.auto_renew)
        self.assertIsNotNone(suscription.cancelled_at)

    @patch(f'{SERVICES_MODULE}.GetPreapproval')
    def test_sync_cancelled_never_reenables_auto_renew(self, get_preapproval):
        suscription                 =   _make_suscription()
        suscription.auto_renew      =   False
        suscription.cancelled_at    =   timezone.now()
        suscription.save(update_fields = ['auto_renew', 'cancelled_at'])
        get_preapproval.return_value    =   {'status': 'cancelled'}
        mp_status   =   SyncPreapprovalQuery(suscription)
        suscription.refresh_from_db()
        self.assertEqual(mp_status, 'cancelled')
        self.assertFalse(suscription.auto_renew)

    def test_access_ends_at_end_date_without_grace_when_cancelled(self):
        suscription     =   _make_suscription(
            auto_renew  =   False,
            end_date    =   timezone.now() - timedelta(days = 1),
        )
        self.assertFalse(suscription.grants_access())

    def test_grace_applies_only_while_auto_renew_active(self):
        suscription     =   _make_suscription(
            auto_renew  =   True,
            end_date    =   timezone.now() - timedelta(days = 1),
        )
        self.assertTrue(suscription.grants_access())


class WebhookReplayTests(TestCase):
    """Ventana anti-replay: una firma válida pero vieja ya no se procesa."""
    client_class    =   APIClient

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_rejects_stale_signature(self):
        #Regresión: antes cualquier firma capturada (logs, proxy) rejugaba
        #el mismo evento para siempre. ts >10min -> 401.
        old_ts          =   str(int(timezone.now().timestamp()) - 3600)
        response        =   self.client.post(
            WEBHOOK_URL,
            {'type': 'payment', 'data': {'id': '12345'}},
            format = 'json',
            **_signature_headers('12345', ts = old_ts),
        )
        self.assertEqual(response.status_code, 401)

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_accepts_millisecond_timestamp(self):
        #Hay despliegues de MP que firman ts en milisegundos: se normalizan.
        ts_ms           =   str(int(timezone.now().timestamp() * 1000))
        with patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery'):
            response    =   self.client.post(
                WEBHOOK_URL,
                {'type': 'payment', 'data': {'id': '12345'}},
                format = 'json',
                **_signature_headers('12345', ts = ts_ms),
            )
        self.assertEqual(response.status_code, 200)


class WebhookDedupTests(TestCase):
    """Entregas repetidas del mismo evento (mismo x-request-id) se absorben:
    el replay dentro de la ventana de frescura no vuelve a llamar a MP."""
    client_class    =   APIClient

    def setUp(self):
        #El dedup vive en el cache compartido de la suite.
        cache.clear()

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_duplicate_delivery_is_deduped(self, webhook_query):
        headers     =   _signature_headers('12345', request_id = 'req-dup-1')
        payload     =   {'type': 'payment', 'data': {'id': '12345'}}
        first       =   self.client.post(WEBHOOK_URL, payload, format = 'json', **headers)
        second      =   self.client.post(WEBHOOK_URL, payload, format = 'json', **headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        webhook_query.assert_called_once_with('12345')

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_distinct_request_ids_are_processed(self, webhook_query):
        #Reintentos legítimos de MP llegan con otro request-id y sí se procesan
        #(la idempotencia real está en las queries).
        payload     =   {'type': 'payment', 'data': {'id': '12345'}}
        for rid in ('req-a', 'req-b'):
            response    =   self.client.post(
                WEBHOOK_URL, payload, format = 'json',
                **_signature_headers('12345', request_id = rid),
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(webhook_query.call_count, 2)


def _suscription_for(username, **plan_kwargs):
    """Profile + suscripción vigente para un usuario distinto de 'cliente'."""
    province    =   Province.objects.create(name_province = f'P {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'4{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'C {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user        =   user,
        first_name  =   'Ana',
        last_name   =   'Perez',
        document    =   f'33{abs(hash(username)) % 10**6:06d}',
        province    =   province,
        city        =   city,
    )
    plan        =   SuscriptionPlan.objects.create(
        name = plan_kwargs.pop('name', f'Plan {username}'),
        price = plan_kwargs.pop('price', 1000),
        **plan_kwargs,
    )
    suscription =   Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        status              =   Suscription.STATUS_ACTIVE,
        start_date          =   timezone.now(),
        end_date            =   timezone.now() + timedelta(days = 20),
    )
    return profile, suscription


class CheckoutResolutionTests(TestCase):
    """_resolve_suscription: parse defensivo de ids, ownership y trial no pagable."""

    URL     =   '/api/payments/checkout/'

    def _client(self):
        profile, _      =   _suscription_for('cliente')
        Suscription.objects.filter(user = profile).delete()
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client, profile

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_rejects_non_numeric_ids(self, preference):
        #Regresión: int('abc') al ORM -> 500; ahora 400 con error de campo.
        client, _       =   self._client()
        for payload in ({'suscription': 'abc'}, {'plan_suscription': 'xyz'}):
            response    =   client.post(self.URL, payload, format = 'json')
            self.assertEqual(response.status_code, 400, payload)
        preference.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_rejects_foreign_suscription(self, preference):
        #IDOR: no se puede iniciar el cobro sobre la suscripción de otro usuario.
        client, _       =   self._client()
        _, foreign      =   _suscription_for('otro')
        response        =   client.post(self.URL, {'suscription': foreign.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        preference.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_rejects_trial_plan(self, preference):
        #El plan de prueba no es pagable: solo se otorga en el registro.
        client, _       =   self._client()
        trial           =   SuscriptionPlan.objects.create(name = 'Trial', price = 0, is_trial = True)
        response        =   client.post(self.URL, {'plan_suscription': trial.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        preference.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_requires_plan_when_no_suscription(self, preference):
        client, _       =   self._client()
        response        =   client.post(self.URL, {}, format = 'json')
        self.assertEqual(response.status_code, 400)
        preference.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_creates_pending_suscription(self, preference):
        preference.return_value     =   {'id': 'pref-1', 'init_point': 'https://mp.test/init'}
        client, profile =   self._client()
        plan            =   SuscriptionPlan.objects.create(name = 'Plan pago', price = 1000)
        response        =   client.post(self.URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        suscription     =   Suscription.objects.get(user = profile)
        self.assertEqual(suscription.status, Suscription.STATUS_PENDING_PAYMENT)


class CreatePaymentSecurityTests(TestCase):
    """Alta del cobro: ownership del payment_id de MP, monto exacto e idempotencia."""

    def _setup(self, pending_plan = None):
        suscription     =   _make_suscription(auto_renew = False, preapproval_id = None)
        if pending_plan:
            suscription.pending_plan_suscription    =   pending_plan
            suscription.save(update_fields = ['pending_plan_suscription'])
        return suscription

    def _mp(self, suscription, status = 'approved', amount = None, pid = '999001'):
        return {
            'id'                :   pid,
            'external_reference':   str(suscription.id),
            'transaction_amount':   str(amount if amount is not None else suscription.plan_suscription.price),
            'currency_id'       :   'ARS',
            'status'            :   status,
            'date_approved'     :   timezone.now().isoformat() if status == 'approved' else None,
        }

    def test_payment_with_foreign_external_reference_rejected(self):
        #Regresión: un payment_id ajeno (cuyo monto casualmente coincide con
        #el plan) podía registrarse en la suscripción propia — IDOR de cobros.
        suscription     =   self._setup()
        mp              =   self._mp(suscription)
        mp['external_reference']    =   '99999'
        with self.assertRaises(serializers.ValidationError):
            CreatePaymentQuery(
                {'user': suscription.user, 'suscription': suscription, 'payment_id': 999001},
                mp_payment = mp,
            )
        self.assertFalse(Payment.objects.exists())

    def test_amount_mismatch_rejected(self):
        #El monto se verifica contra MP: un cobro de $1 no compra el plan de $1000.
        suscription     =   self._setup()
        with self.assertRaises(serializers.ValidationError):
            CreatePaymentQuery(
                {'user': suscription.user, 'suscription': suscription, 'payment_id': 999001},
                mp_payment = self._mp(suscription, amount = '1'),
            )

    def test_same_payment_id_is_idempotent(self):
        suscription     =   self._setup()
        params          =   {'user': suscription.user, 'suscription': suscription, 'payment_id': 999001}
        first           =   CreatePaymentQuery(params, mp_payment = self._mp(suscription))
        second          =   CreatePaymentQuery(params, mp_payment = self._mp(suscription))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Payment.objects.count(), 1)

    def test_existing_payment_from_other_suscription_rejected(self):
        #IDOR inverso: pedir el payment_id ya registrado en otra suscripción
        #no devuelve el pago ajeno ni le aplica el plan pendiente.
        suscription_a   =   self._setup()
        CreatePaymentQuery(
            {'user': suscription_a.user, 'suscription': suscription_a, 'payment_id': 777001},
            mp_payment = self._mp(suscription_a, pid = '777001'),
        )
        profile_b, suscription_b    =   _suscription_for('otro')
        with self.assertRaises(serializers.ValidationError):
            CreatePaymentQuery(
                {'user': profile_b, 'suscription': suscription_b, 'payment_id': 777001},
                mp_payment = self._mp(suscription_b, pid = '777001'),
            )

    def test_approved_payment_applies_pending_plan(self):
        new_plan        =   SuscriptionPlan.objects.create(name = 'Plan upgrade', price = 2000)
        suscription     =   self._setup(pending_plan = new_plan)
        CreatePaymentQuery(
            {'user': suscription.user, 'suscription': suscription, 'payment_id': 999001},
            mp_payment = self._mp(suscription, amount = '2000'),
        )
        suscription.refresh_from_db()
        self.assertEqual(suscription.plan_suscription, new_plan)
        self.assertIsNone(suscription.pending_plan_suscription)
        self.assertEqual(suscription.status, Suscription.STATUS_ACTIVE)

    def test_rejected_payment_does_not_grant_access(self):
        suscription     =   self._setup()
        payment         =   CreatePaymentQuery(
            {'user': suscription.user, 'suscription': suscription, 'payment_id': 999001},
            mp_payment = self._mp(suscription, status = 'rejected'),
        )
        self.assertEqual(payment.status, Payment.Status.REJECTED)


class RevenueRollupTests(TestCase):
    """Rollups materializados: F() atómico y contador clampeado a 0."""

    def _payment(self):
        suscription     =   _make_suscription(auto_renew = False, preapproval_id = None)
        return Payment.objects.create(
            user = suscription.user, suscription = suscription,
            amount = 1000, status = Payment.Status.APPROVED,
            external_reference = 'ext-1', paid_at = timezone.now(),
        )

    def test_approve_then_refund_nets_zero(self):
        payment         =   self._payment()
        UpdateRevenueRollupsQuery(payment, sign = 1)
        UpdateRevenueRollupsQuery(payment, sign = -1)
        daily           =   DailyRevenue.objects.get()
        monthly         =   MonthlyRevenue.objects.get()
        self.assertEqual(daily.payments_count, 0)
        self.assertEqual(daily.total_amount, 0)
        self.assertEqual(monthly.payments_count, 0)

    def test_refund_on_empty_rollup_clamps_to_zero(self):
        #Un refund solitario (payment registrado directo en refunded en MP)
        #no deja el contador del día en negativo.
        payment         =   self._payment()
        UpdateRevenueRollupsQuery(payment, sign = -1)
        self.assertEqual(DailyRevenue.objects.get().payments_count, 0)


class PaymentVisibilityTests(TestCase):
    """El listado de pagos es privado del dueño; aprobar es solo staff."""

    def test_payment_list_scoped_to_owner(self):
        profile_a, suscription_a    =   _suscription_for('cliente')
        _, suscription_b            =   _suscription_for('otro')
        Payment.objects.create(user = profile_a, suscription = suscription_a, amount = 100, external_reference = 'p1')
        Payment.objects.create(user = suscription_b.user, suscription = suscription_b, amount = 200, external_reference = 'p2')
        client          =   APIClient()
        client.force_authenticate(user = profile_a.user)
        response        =   client.get('/api/payments/')
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual([row['amount'] for row in rows], ['100.00'])

    def test_approve_requires_staff(self):
        profile, suscription        =   _suscription_for('cliente')
        payment         =   Payment.objects.create(
            user = profile, suscription = suscription, amount = 100, external_reference = 'p3')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        response        =   client.post(f'/api/payments/{payment.pk}/approve/', {}, format = 'json')
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_admin_summary_requires_staff(self):
        profile, _      =   _suscription_for('cliente')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        response        =   client.get('/api/payments/admin-summary/')
        self.assertEqual(response.status_code, 403)
