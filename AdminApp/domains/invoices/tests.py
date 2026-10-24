"""
Tests de seguridad del dominio invoices.

La factura se emite solo con el pago acreditado, es idempotente por pago
(OneToOne) y la numeración es secuencial por tipo/punto de venta bajo
lock — dos emisiones concurrentes no pisan el correlativo.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from AdminApp.domains.invoices.models import Invoice, TypeInvoice
from AdminApp.domains.invoices.services import IssueInvoiceQuery
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
