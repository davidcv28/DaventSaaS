"""
Catch-all de la SPA empaquetada.

Un asset faltante (/assets/x.css) tiene que ser un 404 real: si cae en el
catch-all, CommonMiddleware (APPEND_SLASH) lo redirige a /assets/x.css/ y el
browser recibe index.html con MIME text/html ("Refused to apply style").
"""
import importlib
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import clear_url_caches

import DaventProject.urls as project_urls


class SpaCatchAllTests(TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        dist = Path(self._tmp.name)
        (dist / 'index.html').write_text('<html></html>')
        self._override = override_settings(FRONTEND_DIST = dist)
        self._override.enable()
        importlib.reload(project_urls)
        clear_url_caches()

    def tearDown(self):
        self._override.disable()
        importlib.reload(project_urls)
        clear_url_caches()
        self._tmp.cleanup()

    def test_missing_asset_is_404(self):
        self.assertEqual(self.client.get('/assets/no-existe.css').status_code, 404)

    def test_missing_asset_with_appended_slash_is_404(self):
        self.assertEqual(self.client.get('/assets/no-existe.css/').status_code, 404)

    def test_missing_media_file_is_404(self):
        self.assertEqual(self.client.get('/media/no-existe.webp').status_code, 404)

    def test_spa_route_still_serves_index(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertEqual(response['Cache-Control'], 'no-store')
