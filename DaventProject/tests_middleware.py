"""
Tests de middlewares transversales (auditoría 30/10/2026, bloque 4):
X-Request-ID, Retry-After en 429, noindex de /api/ y cap de body.
"""
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from DaventProject.middleware import RequestIdMiddleware


def _middleware(status = 200, headers = None):
    def get_response(request):
        response    =   HttpResponse('ok', status = status)
        for name, value in (headers or {}).items():
            response[name] = value
        return response
    return RequestIdMiddleware(get_response)


class RequestIdMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory    =   RequestFactory()

    def test_generates_and_echoes_request_id(self):
        response    =   _middleware()(self.factory.get('/api/x/'))
        self.assertTrue(response.headers.get('X-Request-ID'))
        self.assertEqual(len(response.headers['X-Request-ID']), 32)

    def test_accepts_valid_incoming_id(self):
        request     =   self.factory.get('/api/x/', HTTP_X_REQUEST_ID = 'abc-123')
        response    =   _middleware()(request)
        self.assertEqual(response.headers['X-Request-ID'], 'abc-123')

    def test_rejects_invalid_incoming_id(self):
        request     =   self.factory.get('/api/x/', HTTP_X_REQUEST_ID = '<script>')
        response    =   _middleware()(request)
        self.assertNotEqual(response.headers['X-Request-ID'], '<script>')

    def test_429_gets_retry_after(self):
        response    =   _middleware(status = 429)(self.factory.get('/api/x/'))
        self.assertEqual(response.headers['Retry-After'], '60')

    def test_429_keeps_existing_retry_after(self):
        response    =   _middleware(status = 429, headers = {'Retry-After': '900'})(self.factory.get('/api/x/'))
        self.assertEqual(response.headers['Retry-After'], '900')

    def test_api_gets_noindex(self):
        response    =   _middleware()(self.factory.get('/api/stores/'))
        self.assertIn('noindex', response.headers['X-Robots-Tag'])

    def test_non_api_has_no_noindex(self):
        response    =   _middleware()(self.factory.get('/'))
        self.assertNotIn('X-Robots-Tag', response.headers)

    def test_oversized_body_is_rejected(self):
        request     =   self.factory.generic('POST', '/api/x/', CONTENT_LENGTH = str(11 * 1024 * 1024))
        response    =   _middleware()(request)
        self.assertEqual(response.status_code, 413)
