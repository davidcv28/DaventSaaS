"""
Tests de seguridad del dominio invoices.

La factura se emite solo con el pago acreditado, es idempotente por pago
(OneToOne) y la numeración es secuencial por tipo/punto de venta bajo
lock — dos emisiones concurrentes no pisan el correlativo.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from AdminApp.domains.invoices.models import Invoice, TypeInvoice
from AdminApp.domains.invoices.services import IssueInvoiceQuery, FinalizeInvoiceQuery, RequestCaeQuery
from AdminApp.domains.invoices.services.afip import AfipError
from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.payments.models import Payment
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile


def _profile(username):
    province    =   Province.objects.create(name_province = f'P {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'3{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'C {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    return UserProfile.objects.create(
        user        =   user,
        first_name  =   'Ana',
        last_name   =   'Perez',
        document    =   f'31{abs(hash(username)) % 10**6:06d}',
        province    =   province,
        city        =   city,
    )


def _payment(profile = None, status = Payment.Status.APPROVED, ref = 'ext-1'):
    profile     =   profile or _profile('cliente')
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {ref}', price = 1000)
    suscription =   Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        status              =   Suscription.STATUS_ACTIVE,
        start_date          =   timezone.now(),
        end_date            =   timezone.now() + timedelta(days = 30),
    )
    return Payment.objects.create(
        user                =   profile,
        suscription         =   suscription,
        amount              =   1000,
        status              =   status,
        external_reference  =   ref,
        paid_at             =   timezone.now() if status == Payment.Status.APPROVED else None,
    )


class IssueInvoiceTests(TestCase):
    """Emisión de comprobante: solo APPROVED, idempotente y correlativa."""

    def test_pending_payment_cannot_be_invoiced(self):
        #Sin este chequeo un pago pendiente ya tendría comprobante fiscal.
        payment     =   _payment(status = Payment.Status.PENDING)
        with self.assertRaises(serializers.ValidationError):
            IssueInvoiceQuery(payment)
        self.assertFalse(Invoice.objects.exists())

    def test_issue_is_idempotent_per_payment(self):
        #El webhook de MP + la confirmación del checkout pueden disparar la
        #emisión dos veces: OneToOne + select_for_update -> una sola factura.
        payment     =   _payment()
        first       =   IssueInvoiceQuery(payment)
        second      =   IssueInvoiceQuery(payment)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_numbering_is_sequential_per_type_pos(self):
        first       =   IssueInvoiceQuery(_payment(profile = _profile('a'), ref = 'a'))
        second      =   IssueInvoiceQuery(_payment(profile = _profile('b'), ref = 'b'))
        self.assertEqual(second.number, first.number + 1)

    def test_invoice_type_derives_from_issuer(self):
        #Emisor monotributo (default): todo cobro emite Factura C.
        invoice     =   IssueInvoiceQuery(_payment())
        self.assertEqual(invoice.type, TypeInvoice.C)
        self.assertEqual(invoice.total, 1000)


class InvoiceVisibilityTests(TestCase):
    """Las facturas del usuario son privadas; el admin ve todas."""

    def _invoice(self, username, ref):
        profile     =   _profile(username)
        payment     =   _payment(profile = profile, ref = ref)
        return profile, IssueInvoiceQuery(payment)

    def test_invoice_list_scoped_to_owner(self):
        profile, mine   =   self._invoice('cliente', 'm1')
        _, foreign      =   self._invoice('otro', 'o1')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        response        =   client.get('/api/invoices/')
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual([row['id'] for row in rows], [mine.pk])

    def test_foreign_invoice_retrieve_404(self):
        profile, _      =   self._invoice('cliente', 'm1')
        _, foreign      =   self._invoice('otro', 'o1')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        response        =   client.get(f'/api/invoices/{foreign.pk}/')
        self.assertEqual(response.status_code, 404)


AFIP_ON         =   {'enabled': True, 'env': 'testing', 'cuit': '20123456789', 'cert': 'x', 'key': 'x'}
AFIP_RESULT     =   {'number': 7, 'cae': '72456789012345', 'cae_due': date(2026, 11, 3)}


class RequestCaeTests(TestCase):
    """CAE de ARCA: nunca bloquea el cobro — el resultado queda en afip_status."""

    def _pending_invoice(self, ref = 'c1'):
        payment     =   _payment(ref = ref)
        return  IssueInvoiceQuery(payment)

    def test_disabled_marks_invoice_disabled(self):
        #Sin AFIP_ENABLED la factura queda como interna y no se llama a ARCA.
        invoice     =   self._pending_invoice()
        with patch('AdminApp.domains.invoices.services.afip.authorize_invoice') as mocked:
            self.assertFalse(RequestCaeQuery(invoice))
        mocked.assert_not_called()
        self.assertEqual(Invoice.objects.get(pk = invoice.pk).afip_status, Invoice.AfipStatus.DISABLED)

    @override_settings(AFIP = AFIP_ON)
    def test_granted_cae_stores_fiscal_data(self):
        invoice     =   self._pending_invoice()
        with patch('AdminApp.domains.invoices.services.afip.authorize_invoice', return_value = AFIP_RESULT) as mocked:
            self.assertTrue(RequestCaeQuery(invoice))
        mocked.assert_called_once()
        invoice.refresh_from_db()
        self.assertEqual(invoice.afip_status, Invoice.AfipStatus.OK)
        self.assertEqual(invoice.cae, '72456789012345')
        self.assertEqual(invoice.fiscal_number, 7)
        self.assertEqual(invoice.cae_due, date(2026, 11, 3))

    @override_settings(AFIP = AFIP_ON)
    def test_afip_failure_is_recorded_not_raised(self):
        #Un cobro aprobado no puede romperse por una caída/rechazo de ARCA.
        invoice     =   self._pending_invoice()
        with patch('AdminApp.domains.invoices.services.afip.authorize_invoice', side_effect = AfipError('timeout')):
            self.assertFalse(RequestCaeQuery(invoice))
        invoice.refresh_from_db()
        self.assertEqual(invoice.afip_status, Invoice.AfipStatus.ERROR)
        self.assertIn('timeout', invoice.afip_error)
        self.assertEqual(invoice.cae, '')

    @override_settings(AFIP = AFIP_ON)
    def test_granted_invoice_is_not_requested_twice(self):
        #Webhook + reintento en paralelo: el CAE se pide una sola vez por factura.
        invoice     =   self._pending_invoice()
        with patch('AdminApp.domains.invoices.services.afip.authorize_invoice', return_value = AFIP_RESULT) as mocked:
            RequestCaeQuery(invoice)
            self.assertTrue(RequestCaeQuery(invoice))
        mocked.assert_called_once()

    @override_settings(AFIP = AFIP_ON)
    def test_finalize_requests_cae_then_sends_email(self):
        #El mail sale después del CAE: el comprobante viaja con número fiscal.
        invoice     =   self._pending_invoice()
        calls       =   []
        with patch('AdminApp.domains.invoices.services.afip.RequestCaeQuery', side_effect = lambda inv: calls.append('cae') or True), \
             patch('AdminApp.domains.invoices.services.services.SendInvoiceEmailQuery', side_effect = lambda inv: calls.append('mail')):
            FinalizeInvoiceQuery(invoice.pk)
        self.assertEqual(calls, ['cae', 'mail'])


class RetryCaeEndpointTests(TestCase):
    """POST /api/invoices-admin/<id>/retry-cae/: solo staff, solo sin CAE."""

    def _invoice(self, ref = 'r1'):
        return  IssueInvoiceQuery(_payment(ref = ref))

    def test_non_staff_cannot_retry(self):
        invoice     =   self._invoice()
        client      =   APIClient()
        client.force_authenticate(user = invoice.user.user)
        response    =   client.post(f'/api/invoices-admin/{invoice.pk}/retry-cae/')
        self.assertEqual(response.status_code, 403)

    def test_retry_requires_afip_enabled(self):
        #Sin la integración configurada el reintento no tiene sentido: 503.
        invoice     =   self._invoice()
        client      =   APIClient()
        client.force_authenticate(user = User.objects.create_user('admin', is_staff = True))
        response    =   client.post(f'/api/invoices-admin/{invoice.pk}/retry-cae/')
        self.assertEqual(response.status_code, 503)

    @override_settings(AFIP = AFIP_ON)
    def test_retry_grants_cae(self):
        invoice     =   self._invoice()
        client      =   APIClient()
        client.force_authenticate(user = User.objects.create_user('admin', is_staff = True))
        with patch('AdminApp.domains.invoices.services.afip.authorize_invoice', return_value = AFIP_RESULT):
            response    =   client.post(f'/api/invoices-admin/{invoice.pk}/retry-cae/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cae'], '72456789012345')
        #El comprobante público usa el número fiscal de ARCA, no el interno.
        self.assertEqual(response.data['comprobante'], '0001-00000007')
        self.assertEqual(response.data['afip_status'], 'ok')


#=========================================
# PENTEST: secretos fiscales en reposo + fuga de datos
#=========================================
import os as _os
from AdminApp.domains.invoices.services import afip as _afip, vault as _vault

_PEM = '-----BEGIN PRIVATE KEY-----\nMIIBVgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\n'


def _ring(*kids):
    import base64
    return ','.join(f'{k}:{base64.urlsafe_b64encode(_os.urandom(32)).decode().rstrip("=")}' for k in kids)


class VaultEncryptionTests(TestCase):
    def test_roundtrip_and_ciphertext_hides_plaintext(self):
        with override_settings(SECRETS_MASTER_KEYS = _ring('k1')):
            token   =   _vault.encrypt_secret(_PEM.encode(), 'AFIP_KEY')
            self.assertTrue(token.startswith('enc:v1:k1:'))
            self.assertNotIn('PRIVATE', token)
            self.assertEqual(_vault.decrypt_secret(token, 'AFIP_KEY'), _PEM.encode())

    def test_nonce_is_unique_per_encryption(self):
        with override_settings(SECRETS_MASTER_KEYS = _ring('k1')):
            self.assertNotEqual(_vault.encrypt_secret(b'x', 'AFIP_KEY'), _vault.encrypt_secret(b'x', 'AFIP_KEY'))

    def test_tampered_ciphertext_is_rejected(self):
        with override_settings(SECRETS_MASTER_KEYS = _ring('k1')):
            token   =   _vault.encrypt_secret(_PEM.encode(), 'AFIP_KEY')
            bad     =   token[:-4] + ('AAAA' if not token.endswith('AAAA') else 'BBBB')
            with self.assertRaises(_vault.VaultError):
                _vault.decrypt_secret(bad, 'AFIP_KEY')

    def test_blob_cannot_be_replayed_in_another_field(self):
        #AAD = purpose: la clave privada cifrada no sirve como AFIP_CERT.
        with override_settings(SECRETS_MASTER_KEYS = _ring('k1')):
            token   =   _vault.encrypt_secret(_PEM.encode(), 'AFIP_KEY')
            with self.assertRaises(_vault.VaultError):
                _vault.decrypt_secret(token, 'AFIP_CERT')

    def test_key_rotation_keeps_old_blobs_readable(self):
        ring1   =   _ring('k1')
        with override_settings(SECRETS_MASTER_KEYS = ring1):
            old     =   _vault.encrypt_secret(b'secreto', 'AFIP_KEY')
        with override_settings(SECRETS_MASTER_KEYS = _ring('k2') + ',' + ring1):
            self.assertEqual(_vault.decrypt_secret(old, 'AFIP_KEY'), b'secreto')
            rotated =   _vault.rotate_secret(old, 'AFIP_KEY')
            self.assertTrue(rotated.startswith('enc:v1:k2:'))
        with override_settings(SECRETS_MASTER_KEYS = _ring('k2')):
            with self.assertRaises(_vault.VaultError):
                _vault.decrypt_secret(old, 'AFIP_KEY')

    def test_short_master_key_is_rejected(self):
        with override_settings(SECRETS_MASTER_KEYS = 'k1:AAAA'):
            with self.assertRaises(_vault.VaultError):
                _vault.encrypt_secret(b'x', 'AFIP_KEY')

    @override_settings(DEBUG = False)
    def test_plaintext_private_key_refused_in_production(self):
        with self.assertRaises(AfipError):
            _afip._read_pem(_PEM, 'AFIP_KEY')

    @override_settings(DEBUG = False)
    def test_encrypted_private_key_is_accepted_in_production(self):
        with override_settings(SECRETS_MASTER_KEYS = _ring('k1')):
            token   =   _vault.encrypt_secret(_PEM.encode(), 'AFIP_KEY')
            self.assertEqual(_afip._read_pem(token, 'AFIP_KEY'), _PEM.encode())


class AfipErrorScrubTests(TestCase):
    def test_scrub_removes_pem_token_path_and_cuit(self):
        raw     =   (f'fallo {_PEM} token="{"A" * 40}" en C:/secrets/afip/clave.key '
                     'cuit 20123456789 /etc/ssl/private/afip.key')
        clean   =   _afip.scrub(raw)
        for leaked in ('PRIVATE KEY', 'A' * 40, 'secrets', '20123456789', '/etc/ssl'):
            self.assertNotIn(leaked, clean)

    @override_settings(AFIP = {'enabled': True, 'env': 'testing', 'cuit': '20123456789', 'cert': 'x', 'key': 'x'})
    def test_stored_afip_error_never_contains_secrets(self):
        profile     =   _profile('leak')
        payment     =   _payment(profile, ref = 'leak-1')
        invoice     =   IssueInvoiceQuery(payment)
        boom        =   AfipError(f'SOAP fault {_PEM} sign={"Z" * 50}')
        with patch.object(_afip, 'authorize_invoice', side_effect = boom):
            RequestCaeQuery(invoice)
        invoice.refresh_from_db()
        self.assertEqual(invoice.afip_status, Invoice.AfipStatus.ERROR)
        self.assertNotIn('PRIVATE KEY', invoice.afip_error)
        self.assertNotIn('Z' * 50, invoice.afip_error)
