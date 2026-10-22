"""
Tests de seguridad del dominio payments.

El webhook de Mercado Pago exige firma HMAC-SHA256 válida cuando
MP_WEBHOOK_SECRET está configurado; sin secret procesa igual (dev).
"""
import hashlib
import hmac
import os
from unittest.mock import patch

from django.test import TestCase

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

    def _post(self, signature_headers = None):
        return self.client.post(
            WEBHOOK_URL,
            {'type': 'payment', 'data': {'id': '12345'}},
            format = 'json',
            **(signature_headers or {}),
        )

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

    @patch('AdminApp.domains.payments.views.viewset.PaymentWebhookQuery')
    def test_processes_unsigned_request_when_secret_missing(self, webhook_query):
        #Sin MP_WEBHOOK_SECRET (dev) el evento se procesa con warning.
        with patch('AdminApp.domains.payments.views.viewset.config', lambda *a, **kw: kw.get('default', '')):
            response    =   self._post()
        self.assertEqual(response.status_code, 200)
        webhook_query.assert_called_once_with('12345')
