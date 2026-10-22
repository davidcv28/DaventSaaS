"""
Tests de seguridad del dominio payments.

El webhook de Mercado Pago exige firma HMAC-SHA256 válida cuando
MP_WEBHOOK_SECRET está configurado; sin secret procesa igual (dev).
"""
import hashlib
import hmac
import os
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import Province, City, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from AdminApp.domains.payments.services.services import (
    CancelPreapprovalQuery,
    SyncPreapprovalQuery,
)

WEBHOOK_URL = '/api/payments/webhook/'
SECRET      = 'test-webhook-secret'


def _signature_headers(resource_id, request_id = 'req-1', secret = SECRET):
    ts          =   '1700000000'
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
    def test_processes_unsigned_request_when_secret_missing_in_debug(self, webhook_query):
        #Sin MP_WEBHOOK_SECRET con DEBUG=True (dev) el evento se procesa con warning.
        with patch('AdminApp.domains.payments.views.viewset.config', lambda *a, **kw: kw.get('default', '')):
            response    =   self._post()
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')

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
