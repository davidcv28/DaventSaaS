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

    def test_permissions_policy_on_every_response(self):
        #También en JSON: la política no es solo del HTML.
        response    =   self.client.get('/api/config/')
        policy      =   response.headers.get('Permissions-Policy', '')
        self.assertIn('microphone=()', policy)
        self.assertIn('camera=(self)', policy)
        self.assertEqual(response.headers.get('X-Permitted-Cross-Domain-Policies'), 'none')

    def test_admin_is_not_indexable(self):
        response    =   self.client.get(self.admin_url)
        self.assertIn('noindex', response.headers.get('X-Robots-Tag', ''))


class ClientIpTests(TestCase):
    def test_xff_uses_last_hop_not_client_supplied_first(self):
        from django.test import RequestFactory
        from DaventProject.middleware import client_ip
        request =   RequestFactory().get('/', HTTP_X_FORWARDED_FOR = '1.2.3.4, 5.6.7.8')
        self.assertEqual(client_ip(request), '5.6.7.8')

    def test_xff_ignored_without_trusted_proxy(self):
        from django.test import RequestFactory, override_settings
        from DaventProject.middleware import client_ip
        request =   RequestFactory().get('/', HTTP_X_FORWARDED_FOR = '1.2.3.4', REMOTE_ADDR = '9.9.9.9')
        with override_settings(REST_FRAMEWORK = {**settings.REST_FRAMEWORK, 'NUM_PROXIES': 0}):
            self.assertEqual(client_ip(request), '9.9.9.9')

    def test_garbage_xff_falls_back_to_remote_addr(self):
        from django.test import RequestFactory
        from DaventProject.middleware import client_ip
        request =   RequestFactory().get('/', HTTP_X_FORWARDED_FOR = 'not-an-ip', REMOTE_ADDR = '9.9.9.9')
        self.assertEqual(client_ip(request), '9.9.9.9')


class AdminLoginRateLimitTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.login_url  =   f'/{settings.ADMIN_URL.strip("/")}/login/'

    def test_login_post_is_throttled_with_retry_after(self):
        from DaventProject.middleware import AdminLoginRateLimitMiddleware
        limit       =   AdminLoginRateLimitMiddleware.LIMIT
        codes       =   []
        for _ in range(limit + 1):
            response    =   self.client.post(self.login_url, {'username': 'x', 'password': 'y'})
            codes.append(response.status_code)
        self.assertEqual(codes[-1], 429)
        self.assertEqual(response.headers.get('Retry-After'), str(AdminLoginRateLimitMiddleware.WINDOW_SECONDS))


def _html_response(policy):
    from django.http import HttpResponse
    response    =   HttpResponse('<html></html>')
    response['Content-Security-Policy'] =   policy
    return response
