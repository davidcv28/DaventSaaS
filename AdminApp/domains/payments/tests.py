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
    CreatePreapprovalQuery,
    PaymentWebhookQuery,
    SyncPreapprovalQuery,
    UpdateRevenueRollupsQuery,
)

WEBHOOK_URL = '/api/payments/webhook/'
#MP real: el data.id firmado viaja en el query string, no en el body.
SIGNED_URL  = WEBHOOK_URL + '?data.id=12345&topic=payment'
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

    def _post(self, signature_headers = None, url = None):
        return self.client.post(
            url or SIGNED_URL,
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


class PreapprovalCreateTests(TestCase):
    """Alta del débito automático (CreatePreapprovalQuery). Regresión del
    doble cobro: en el modelo pending de MP la primera cuota queda generada
    como pago pendiente y el checkout del init_point la cobra en el acto —
    start_date no la difiere. free_trial marca ese período como ya pagado:
    con el período abonado debe viajar en días hasta end_date."""

    def setUp(self):
        cache.clear()

    def _create(self, sdk):
        sdk.preapproval.return_value.create.return_value    =   {'status': 201, 'response': {'id': 'pre-1'}}
        return CreatePreapprovalQuery

    @patch(f'{SERVICES_MODULE}.sdk')
    def test_paid_period_sets_free_trial_until_end_date(self, sdk):
        suscription =   _make_suscription(
            auto_renew      =   False,
            preapproval_id  =   None,
            end_date        =   timezone.now() + timedelta(days = 20, hours = 1),
        )
        self._create(sdk)(suscription)
        recurring   =   sdk.preapproval.return_value.create.call_args.args[0]['auto_recurring']
        self.assertEqual(recurring['start_date'], suscription.end_date.isoformat())
        self.assertEqual(recurring['free_trial'], {'frequency': 21, 'frequency_type': 'days'})
        suscription.refresh_from_db()
        self.assertEqual(suscription.preapproval_id, 'pre-1')

    @patch(f'{SERVICES_MODULE}.sdk')
    def test_pending_payment_has_no_free_trial(self, sdk):
        #Sin período pago el cargo del checkout ES el pago del plan.
        suscription =   _make_suscription(
            auto_renew      =   False,
            preapproval_id  =   None,
            status          =   Suscription.STATUS_PENDING_PAYMENT,
        )
        self._create(sdk)(suscription)
        recurring   =   sdk.preapproval.return_value.create.call_args.args[0]['auto_recurring']
        self.assertNotIn('free_trial', recurring)
        self.assertNotIn('start_date', recurring)

    @patch(f'{SERVICES_MODULE}.sdk')
    def test_expired_period_has_no_free_trial(self, sdk):
        #end_date vencido: la primera cuota del checkout es la renovación.
        suscription =   _make_suscription(
            auto_renew      =   False,
            preapproval_id  =   None,
            end_date        =   timezone.now() - timedelta(hours = 2),
        )
        self._create(sdk)(suscription)
        recurring   =   sdk.preapproval.return_value.create.call_args.args[0]['auto_recurring']
        self.assertNotIn('free_trial', recurring)
        self.assertNotIn('start_date', recurring)

    @patch(f'{SERVICES_MODULE}.sdk')
    def test_free_plan_cannot_create_debit(self, sdk):
        #Un débito de $0 (plan trial) no tiene sentido en MP: se rechaza.
        suscription =   _make_suscription(auto_renew = False, preapproval_id = None)
        suscription.plan_suscription.price    =   0
        suscription.plan_suscription.save(update_fields = ['price'])
        with self.assertRaises(serializers.ValidationError):
            CreatePreapprovalQuery(suscription)
        sdk.preapproval.return_value.create.assert_not_called()


class WebhookReplayTests(TestCase):
    """Ventana anti-replay: una firma válida pero vieja ya no se procesa."""
    client_class    =   APIClient

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_rejects_stale_signature(self):
        #Regresión: antes cualquier firma capturada (logs, proxy) rejugaba
        #el mismo evento para siempre. ts >10min -> 401.
        old_ts          =   str(int(timezone.now().timestamp()) - 3600)
        response        =   self.client.post(
            SIGNED_URL,
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
                SIGNED_URL,
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
        first       =   self.client.post(SIGNED_URL, payload, format = 'json', **headers)
        second      =   self.client.post(SIGNED_URL, payload, format = 'json', **headers)
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
                SIGNED_URL, payload, format = 'json',
                **_signature_headers('12345', request_id = rid),
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(webhook_query.call_count, 2)

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_failed_processing_releases_dedup_key(self, webhook_query):
        #Si el procesamiento explota, la marca se libera: el retry de MP con
        #el mismo request-id no queda absorbido y puede reintentarse. El error
        #sale como 500 genérico (EXCEPTION_HANDLER), sin propagar la excepción.
        webhook_query.side_effect   =   [Exception('boom'), None]
        headers     =   _signature_headers('12345', request_id = 'req-retry')
        payload     =   {'type': 'payment', 'data': {'id': '12345'}}
        first       =   self.client.post(SIGNED_URL, payload, format = 'json', **headers)
        self.assertEqual(first.status_code, 500)
        second      =   self.client.post(SIGNED_URL, payload, format = 'json', **headers)
        self.assertEqual(second.status_code, 200)
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

    @patch('AdminApp.domains.payments.views.viewset.UpdatePreapprovalPlanQuery')
    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_with_live_debit_aligns_pending_plan_amount(self, preference, update_preapproval):
        #Cambio de plan por checkout con débito vivo: la preapproval de MP
        #también debe cargar el plan pendiente — si no, el próximo débito
        #cobra el monto viejo y el webhook lo rechaza (cobro huérfano).
        preference.return_value     =   {'id': 'pref-1', 'init_point': 'https://mp.test/init'}
        _, suscription              =   _suscription_for('cliente')
        suscription.preapproval_id  =   'pre-1'
        suscription.auto_renew      =   True
        suscription.save(update_fields = ['preapproval_id', 'auto_renew'])
        new_plan                    =   SuscriptionPlan.objects.create(name = 'Plan upgrade', price = 2000)
        client                      =   APIClient()
        client.force_authenticate(user = suscription.user.user)
        response                    =   client.post(self.URL, {'plan_suscription': new_plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        update_preapproval.assert_called_once()

    @patch('AdminApp.domains.payments.views.viewset.UpdatePreapprovalPlanQuery')
    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_without_debit_skips_preapproval_update(self, preference, update_preapproval):
        preference.return_value     =   {'id': 'pref-1', 'init_point': 'https://mp.test/init'}
        _, suscription              =   _suscription_for('cliente')
        new_plan                    =   SuscriptionPlan.objects.create(name = 'Plan upgrade', price = 2000)
        client                      =   APIClient()
        client.force_authenticate(user = suscription.user.user)
        response                    =   client.post(self.URL, {'plan_suscription': new_plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        update_preapproval.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.UpdatePreapprovalPlanQuery')
    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_with_cancelled_debit_skips_preapproval_update(self, preference, update_preapproval):
        #Un débito ya cancelado en MP rechazaría el update: no se intenta.
        preference.return_value     =   {'id': 'pref-1', 'init_point': 'https://mp.test/init'}
        _, suscription              =   _suscription_for('cliente')
        suscription.preapproval_id  =   'pre-1'
        suscription.cancelled_at    =   timezone.now()
        suscription.save(update_fields = ['preapproval_id', 'cancelled_at'])
        new_plan                    =   SuscriptionPlan.objects.create(name = 'Plan upgrade', price = 2000)
        client                      =   APIClient()
        client.force_authenticate(user = suscription.user.user)
        response                    =   client.post(self.URL, {'plan_suscription': new_plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        update_preapproval.assert_not_called()


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


class CancelRenewalOwnershipTests(TestCase):
    """cancel-renewal es detail=False y resuelve por request.user: un débito
    ajeno jamás es alcanzable aunque el caller conozca su id."""
    client_class    =   APIClient

    @patch('AdminApp.domains.payments.views.viewset.CancelPreapprovalQuery')
    def test_cancel_renewal_never_touches_foreign_suscription(self, cancel_query):
        _, foreign      =   _suscription_for('otro')
        foreign.preapproval_id  =   'pre-foreign'
        foreign.auto_renew      =   True
        foreign.save(update_fields = ['preapproval_id', 'auto_renew'])
        profile_a, _    =   _suscription_for('cliente')   # A sin débito propio
        client          =   APIClient()
        client.force_authenticate(user = profile_a.user)
        response        =   client.post(
            '/api/payments/cancel-renewal/', {'suscription': foreign.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        cancel_query.assert_called_once()
        #El target resuelto es la suscripción PROPIA: el id del body se ignora.
        self.assertEqual(cancel_query.call_args[0][0].user, profile_a)
        foreign.refresh_from_db()
        self.assertTrue(foreign.auto_renew)
        self.assertIsNone(foreign.cancelled_at)


class BillingDataGateTests(TestCase):
    """
    Gate de datos fiscales: el alta minimal deja el perfil sin ellos —
    checkout y débito automático los exigen recién al iniciar el cobro
    (la factura se emite sobre ese perfil).
    """
    CHECKOUT_URL    =   '/api/payments/checkout/'
    SUBSCRIPTION_URL=   '/api/payments/subscription/'

    def _bare_client(self):
        #Perfil recién registrado: sin datos fiscales (alta minimal).
        user        =   User.objects.create_user(
            username = 'cliente', email = 'cliente@gmail.com', password = 'Xq7#mP2vL9bT')
        profile     =   UserProfile.objects.create(user = user, phone = '+5491100000000')
        client      =   APIClient()
        client.force_authenticate(user = user)
        return client, profile

    def _complete_profile(self, profile):
        province    =   Province.objects.create(name_province = 'Mendoza')
        zipcode     =   ZipCode.objects.create(zipcode = '5500')
        city        =   City.objects.create(name_city = 'Mendoza', province = province, zipcode = zipcode)
        profile.first_name  =   'Ana'
        profile.last_name   =   'Perez'
        profile.document    =   '28123456'
        profile.province    =   province
        profile.city        =   city
        profile.save()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_requires_billing_data(self, preference):
        client, _       =   self._bare_client()
        plan            =   SuscriptionPlan.objects.create(name = 'Plan pago', price = 1000)
        response        =   client.post(self.CHECKOUT_URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        missing         =   response.json().get('billing_required')
        self.assertTrue(missing)
        for field in ('first_name', 'last_name', 'document', 'province', 'city'):
            self.assertIn(field, missing)
        #No se crea la preferencia de MP sin datos de facturación.
        preference.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreatePreapprovalQuery')
    def test_subscription_requires_billing_data(self, preapproval):
        client, _       =   self._bare_client()
        plan            =   SuscriptionPlan.objects.create(name = 'Plan pago', price = 1000)
        response        =   client.post(self.SUBSCRIPTION_URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('billing_required', response.json())
        preapproval.assert_not_called()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_checkout_proceeds_once_billing_complete(self, preference):
        preference.return_value     =   {'id': 'pref-1', 'init_point': 'https://mp.test/init'}
        client, profile =   self._bare_client()
        plan            =   SuscriptionPlan.objects.create(name = 'Plan pago', price = 1000)
        response        =   client.post(self.CHECKOUT_URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)
        #El plan elegido quedó pendiente: tras completar el perfil el retry
        #ya no necesita mandar el plan otra vez.
        self._complete_profile(profile)
        retry           =   client.post(self.CHECKOUT_URL, {}, format = 'json')
        self.assertEqual(retry.status_code, 200)
        preference.assert_called_once()

    @patch('AdminApp.domains.payments.views.viewset.CreateCheckoutPreferenceQuery')
    def test_billing_gate_also_covers_pending_suscription_retry(self, preference):
        #Un usuario con suscripción pendiente y perfil incompleto también
        #debe completar la facturación — el gate corre en todo cobro.
        client, profile =   self._bare_client()
        plan            =   SuscriptionPlan.objects.create(name = 'Plan pago', price = 1000)
        first           =   client.post(self.CHECKOUT_URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(first.status_code, 400)
        suscription     =   Suscription.objects.get(user = profile)
        retry           =   client.post(self.CHECKOUT_URL, {'suscription': suscription.pk}, format = 'json')
        self.assertEqual(retry.status_code, 400)
        self.assertIn('billing_required', retry.json())
        preference.assert_not_called()


#=========================================
# PENTEST: path injection por id de webhook + moneda
#=========================================
class WebhookIdInjectionTests(TestCase):
    client_class    =   APIClient

    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    def test_path_traversal_id_never_reaches_mp_api(self, webhook_query):
        evil        =   '../users/me?x='
        response    =   self.client.post(
            WEBHOOK_URL + f'?data.id={evil}&topic=payment',
            {'type': 'payment', 'data': {'id': evil}},
            format = 'json',
            **_signature_headers(evil),
        )
        self.assertEqual(response.status_code, 400)
        webhook_query.assert_not_called()

    def test_authorized_payment_lookup_rejects_traversal(self):
        from AdminApp.domains.payments.services.services import GetAuthorizedPayment
        with patch('AdminApp.domains.payments.services.services.requests.get') as http:
            with self.assertRaises(serializers.ValidationError):
                GetAuthorizedPayment('1/../../users')
            http.assert_not_called()


#=========================================
# WEBHOOK MP — DEFENSA EN PROFUNDIDAD
#=========================================
class WebhookSignedIdTests(TestCase):
    """El data.id procesado es SOLO el firmado (query string): el del body no
    está cubierto por la firma y un replay no puede redirigir el evento."""
    client_class    =   APIClient

    def setUp(self):
        #El dedup por x-request-id vive en el cache compartido de la suite.
        cache.clear()

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_body_id_is_ignored_when_query_id_signed(self, webhook_query):
        #Body forjado con otro id + firma válida del query: se procesa el 12345
        #firmado, jamás el 99999 del body (y queda logueado el mismatch).
        url         =   WEBHOOK_URL + '?data.id=12345&topic=payment'
        response    =   self.client.post(
            url,
            {'type': 'payment', 'data': {'id': '99999'}},
            format = 'json',
            **_signature_headers('12345', request_id = 'req-signed-1'),
        )
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_body_id_without_signed_query_id_is_rejected(self, webhook_query):
        #Una firma válida sobre un id que NO viajó en el query string no vale:
        #el data.id firmado es el único que cuenta.
        response    =   self.client.post(
            WEBHOOK_URL,
            {'type': 'payment', 'data': {'id': '99999'}},
            format = 'json',
            **_signature_headers('99999', request_id = 'req-signed-2'),
        )
        self.assertEqual(response.status_code, 401)
        webhook_query.assert_not_called()

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_rejects_oversized_body(self, webhook_query):
        #Un webhook de MP legítimo es chico; >16KB se corta antes del parseo.
        response    =   self.client.post(
            SIGNED_URL,
            {'type': 'payment', 'data': {'id': '12345', 'pad': 'x' * (17 * 1024)}},
            format = 'json',
            **_signature_headers('12345', request_id = 'req-signed-3'),
        )
        self.assertEqual(response.status_code, 413)
        webhook_query.assert_not_called()

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_unhandled_error_returns_generic_500(self, webhook_query):
        #Un bug en el procesamiento jamás devuelve la traza ni el mensaje
        #interno al cliente: el EXCEPTION_HANDLER responde 500 genérico.
        webhook_query.side_effect =   Exception('boom interno con datos de MP')
        response    =   self.client.post(
            SIGNED_URL,
            {'type': 'payment', 'data': {'id': '12345'}},
            format = 'json',
            **_signature_headers('12345', request_id = 'req-500'),
        )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('boom interno', response.content.decode())
        self.assertNotIn('Traceback', response.content.decode())
        self.assertNotIn('Exception', response.content.decode())

    @patch.dict(os.environ, {'MP_WEBHOOK_SECRET': SECRET})
    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_normal_sized_body_still_processed(self, webhook_query):
        response    =   self.client.post(
            SIGNED_URL,
            {'type': 'payment', 'data': {'id': '12345'}},
            format = 'json',
            **_signature_headers('12345', request_id = 'req-signed-4'),
        )
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')


class PaymentLiveModeTests(TestCase):
    """live_mode=False identifica cobros de prueba de MP: en producción se
    rechazan antes de acreditar el plan; el detalle viaja al Payment."""

    def _mp_payment(self, suscription, **overrides):
        payload     =   {
            'id'                :   555,
            'status'            :   'approved',
            'status_detail'     :   'accredited',
            'live_mode'         :   True,
            'external_reference':   str(suscription.id),
            'transaction_amount':   1000,
            'currency_id'       :   'ARS',
            'date_approved'     :   '2026-10-27T10:00:00.000-03:00',
        }
        payload.update(overrides)
        return payload

    @override_settings(DEBUG = False)
    @patch(f'{SERVICES_MODULE}.GetMercadoPagoPayment')
    def test_test_payment_rejected_in_production(self, get_payment):
        suscription                 =   _make_suscription()
        get_payment.return_value    =   self._mp_payment(suscription, live_mode = False)
        with self.assertRaises(serializers.ValidationError):
            CreatePaymentQuery({
                'user'          :   suscription.user,
                'suscription'   :   suscription,
                'payment_id'    :   '555',
            })
        self.assertFalse(Payment.objects.filter(external_reference = '555').exists())

    @override_settings(DEBUG = False)
    @patch(f'{SERVICES_MODULE}.GetMercadoPagoPayment')
    def test_webhook_test_payment_rejected_in_production(self, get_payment):
        suscription                 =   _make_suscription()
        get_payment.return_value    =   self._mp_payment(suscription, live_mode = False)
        with self.assertRaises(serializers.ValidationError):
            PaymentWebhookQuery('555')
        self.assertFalse(Payment.objects.filter(external_reference = '555').exists())

    @override_settings(DEBUG = True)
    @patch(f'{SERVICES_MODULE}.GetMercadoPagoPayment')
    def test_live_mode_and_status_detail_are_stored(self, get_payment):
        suscription                 =   _make_suscription()
        get_payment.return_value    =   self._mp_payment(suscription)
        payment                     =   CreatePaymentQuery({
            'user'          :   suscription.user,
            'suscription'   :   suscription,
            'payment_id'    :   '555',
        })
        self.assertEqual(payment.live_mode, True)
        self.assertEqual(payment.mp_status_detail, 'accredited')

    @override_settings(DEBUG = True)
    @patch(f'{SERVICES_MODULE}.GetMercadoPagoPayment')
    def test_webhook_updates_live_mode_and_status_detail(self, get_payment):
        suscription                 =   _make_suscription()
        payment                     =   Payment.objects.create(
            user = suscription.user, suscription = suscription, amount = 1000,
            status = Payment.Status.PENDING, external_reference = '555',
        )
        get_payment.return_value    =   self._mp_payment(suscription, status_detail = 'accredited', live_mode = True)
        PaymentWebhookQuery('555')
        payment.refresh_from_db()
        self.assertEqual(payment.live_mode, True)
        self.assertEqual(payment.mp_status_detail, 'accredited')
