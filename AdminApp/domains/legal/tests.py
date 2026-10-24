"""
Tests de seguridad del dominio legal.

La denuncia pública es AllowAny (cada create dispara un correo al buzón
legal: por eso tiene throttle propio y validación estricta), pero la
gestión y lectura de denuncias es exclusiva del staff.
"""
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from AdminApp.domains.legal.models import ContentReport

REPORTS_URL =   '/api/content-reports/'


def _payload(**overrides):
    payload     =   {
        'reporter_name'     :   'Juan Denunciante',
        'reporter_email'    :   'denunciante@gmail.com',
        'kind'              :   'COPYRIGHT',
        'reported_url'      :   'https://davent.com.ar/tienda-trucha',
        'original_work'     :   'Foto de producto registrada',
        'description'       :   'Esta tienda publica mis fotos sin autorización comercial.',
        'good_faith'        :   True,
    }
    payload.update(overrides)
    return payload


class ContentReportCreateTests(TestCase):
    """Alta pública de denuncias: validación completa, mail al buzón legal."""

    def setUp(self):
        #Throttle 'content_report' sobre cache locmem compartido: sin el
        #reset, los creates de otros tests agotan el cupo por IP -> 429.
        cache.clear()

    def test_valid_report_created_and_notified(self):
        response        =   APIClient().post(REPORTS_URL, _payload(), format = 'json')
        self.assertEqual(response.status_code, 201)
        report          =   ContentReport.objects.get()
        self.assertIsNone(report.reported_by)
        self.assertEqual(len(mail.outbox), 1)

    def test_copyright_requires_original_work(self):
        response        =   APIClient().post(REPORTS_URL, _payload(original_work = ''), format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ContentReport.objects.exists())

    def test_illegal_kind_without_original_work_ok(self):
        response        =   APIClient().post(
            REPORTS_URL, _payload(kind = 'ILLEGAL', original_work = ''), format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_good_faith_declaration_required(self):
        response        =   APIClient().post(REPORTS_URL, _payload(good_faith = False), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_url_must_be_http(self):
        response        =   APIClient().post(REPORTS_URL, _payload(reported_url = 'ftp://x.com'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_short_description_rejected(self):
        response        =   APIClient().post(REPORTS_URL, _payload(description = 'muy corta'), format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_reporter_name_letters_only(self):
        response        =   APIClient().post(REPORTS_URL, _payload(reporter_name = 'Ju4n H4cker'), format = 'json')
        self.assertEqual(response.status_code, 400)


class ContentReportAccessTests(TestCase):
    """Lectura y gestión de denuncias: solo staff (datos del denunciante)."""

    def setUp(self):
        cache.clear()

    def _report(self):
        return ContentReport.objects.create(
            reporter_name   =   'Juan Denunciante',
            reporter_email  =   'denunciante@gmail.com',
            kind            =   'COPYRIGHT',
            reported_url    =   'https://davent.com.ar/x',
            original_work   =   'Obra',
            description     =   'Descripción suficientemente larga de la denuncia.',
            good_faith      =   True,
        )

    def test_anonymous_cannot_list_reports(self):
        self._report()
        response        =   APIClient().get(REPORTS_URL)
        self.assertEqual(response.status_code, 401)

    def test_non_staff_cannot_list_reports(self):
        self._report()
        user            =   User.objects.create_user(username = 'cliente', password = 'x')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.get(REPORTS_URL)
        self.assertEqual(response.status_code, 403)

    def test_staff_can_list_and_update(self):
        report          =   self._report()
        admin           =   User.objects.create_user(username = 'admin', password = 'x', is_staff = True)
        client          =   APIClient()
        client.force_authenticate(user = admin)
        response        =   client.get(REPORTS_URL)
        self.assertEqual(response.status_code, 200)
        response        =   client.patch(
            f'{REPORTS_URL}{report.pk}/', {'status': 'RESOLVED', 'admin_notes': 'Verificado'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, 'RESOLVED')
