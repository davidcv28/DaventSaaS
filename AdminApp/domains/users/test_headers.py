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


class LoginLockoutTests(TestCase):
    """
    Lockout por CUENTA+IP (además del throttle por IP): el credential stuffing
    rota IPs. La key incluye la IP — un lockout solo por username permitía
    DoS dirigido (10 passwords erróneos bloqueaban la cuenta de cualquiera).
    Backoff progresivo: 5 fallos → 429 corto, 10 → 429 largo.
    """
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        from AdminApp.domains.users.views.auth_views import _login_fail_key
        self.key    =   _login_fail_key
        self.url    =   '/api/token/'

    def _login(self, username, password, ip = '10.0.0.1'):
        return self.client.post(self.url, {'username': username, 'password': password}, format = 'json', REMOTE_ADDR = ip)

    def test_locked_username_and_ip_is_rejected_before_checking_credentials(self):
        from django.core.cache import cache

        from AdminApp.domains.users.views.auth_views import (
            LOGIN_FAIL_LIMIT,
            LOGIN_FAIL_WINDOW,
        )
        cache.set(self.key('victima', '10.0.0.1'), LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW)
        response    =   self._login('victima', 'x')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers.get('Retry-After'), str(LOGIN_FAIL_WINDOW))

    def test_soft_backoff_after_five_failures(self):
        from django.core.cache import cache

        from AdminApp.domains.users.views.auth_views import (
            LOGIN_FAIL_SOFT_LIMIT,
            LOGIN_FAIL_SOFT_WINDOW,
        )
        cache.set(self.key('victima', '10.0.0.1'), LOGIN_FAIL_SOFT_LIMIT)
        response    =   self._login('victima', 'x')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers.get('Retry-After'), str(LOGIN_FAIL_SOFT_WINDOW))

    def test_distributed_failures_do_not_lock_the_account(self):
        #10 IPs × 1 fallo: cada contador queda en 1, la cuenta no se bloquea
        #para la IP legítima (la víctima entra con su password correcta).
        from django.contrib.auth.models import User
        User.objects.create_user(username = 'victima', email = 'v@example.com', password = 'ClaveSegura-2026!')
        for index in range(10):
            response    =   self._login('victima', 'incorrecta', ip = f'10.0.0.{index + 1}')
            self.assertEqual(response.status_code, 401)
        response    =   self._login('victima', 'ClaveSegura-2026!', ip = '10.0.0.99')
        self.assertEqual(response.status_code, 200)

    def test_failed_login_counts_and_success_clears(self):
        from django.contrib.auth.models import User
        from django.core.cache import cache
        User.objects.create_user(username = 'cliente', email = 'c@example.com', password = 'ClaveSegura-2026!')
        self._login('cliente', 'incorrecta')
        self.assertEqual(cache.get(self.key('cliente', '10.0.0.1')), 1)
        self._login('cliente', 'ClaveSegura-2026!')
        self.assertIsNone(cache.get(self.key('cliente', '10.0.0.1')))

    def test_username_is_hashed_in_cache_keys(self):
        self.assertNotIn('victima', self.key('victima', '10.0.0.1'))
        self.assertEqual(self.key('Victima', '10.0.0.1'), self.key('victima', '10.0.0.1'))
        self.assertNotEqual(self.key('victima', '10.0.0.1'), self.key('victima', '10.0.0.2'))
