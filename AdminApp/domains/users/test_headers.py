"""
Tests de cabeceras de seguridad servidas por Django.

La SPA y nginx tienen su propia CSP; este test cubre la capa de respaldo
(middleware de Django + SecurityMiddleware), que es la que protege el admin,
la browsable API y las páginas de error en un deploy sin nginx.
"""
from django.conf import settings
from django.test import TestCase


class SecurityHeadersTests(TestCase):
    def setUp(self):
        self.admin_url  =   f'/{settings.ADMIN_URL.strip("/")}/login/'

    def test_html_response_has_csp_and_hardening_headers(self):
        response    =   self.client.get(self.admin_url)
        self.assertEqual(response.status_code, 200)
        csp         =   response.headers.get('Content-Security-Policy', '')
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertIn("frame-ancestors 'self'", csp)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        #Django usa DENY por default; nginx publica SAMEORIGIN. Ambas bloquean
        #el framing de terceros (la SPA usa frame-ancestors para el dominio).
        self.assertIn(response.headers.get('X-Frame-Options'), ('DENY', 'SAMEORIGIN'))
        self.assertEqual(response.headers.get('Referrer-Policy'), 'same-origin')

    def test_json_response_is_not_given_html_csp(self):
        #Una CSP sobre JSON no protege nada: el middleware solo rellena HTML.
        response    =   self.client.get('/api/config/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Content-Security-Policy', response.headers)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_existing_csp_is_never_overwritten(self):
        #Si una capa previa ya seteó la política, el middleware no la pisa.
        from DaventProject.middleware import ContentSecurityPolicyMiddleware
        middleware  =   ContentSecurityPolicyMiddleware(lambda request: _html_response('default-src \'none\''))
        response    =   middleware(object())
        self.assertEqual(response['Content-Security-Policy'], "default-src 'none'")


def _html_response(policy):
    from django.http import HttpResponse
    response    =   HttpResponse('<html></html>')
    response['Content-Security-Policy'] =   policy
    return response
