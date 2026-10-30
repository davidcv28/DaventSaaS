"""
Tests de hardening de disponibilidad (auditoría 30/10/2026, bloque 1):

- Huella del cache del catálogo público: SOLO los filtros soportados, para
  que una query string arbitraria no cree entradas nuevas (cache flooding).
- Keys de versión del cache público con TTL y borrado en post_delete.
- Descarga del modelo ONNX: temporal único + os.replace bajo lock entre
  procesos (dos descargas concurrentes no corrompen el archivo).
"""
import hashlib
import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.http import QueryDict
from django.test import TestCase

from StoreApp.domains.stores import public_cache
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services import imaging
from StoreApp.domains.stores.tests import _make_user
from StoreApp.domains.stores.views.viewset import _params_fingerprint


def _request(query : str):
    return type('Req', (), {'query_params': QueryDict(query)})()


class CatalogFingerprintTests(TestCase):
    def test_unknown_params_share_cache_entry(self):
        self.assertEqual(_params_fingerprint(_request('x=1')), _params_fingerprint(_request('x=2')))

    def test_supported_filters_do_not_collide(self):
        self.assertNotEqual(_params_fingerprint(_request('category=1')), _params_fingerprint(_request('category=2')))
        self.assertNotEqual(_params_fingerprint(_request('sort=name')), _params_fingerprint(_request('sort=price_asc')))

    def test_param_order_does_not_change_fingerprint(self):
        self.assertEqual(_params_fingerprint(_request('category=1&brand=2')), _params_fingerprint(_request('brand=2&category=1')))

    def test_huge_q_is_truncated(self):
        huge    =   'a' * 5000
        self.assertEqual(_params_fingerprint(_request(f'q={huge}')), _params_fingerprint(_request('q=' + 'a' * 80)))
        self.assertEqual(len(_params_fingerprint(_request(f'q={huge}'))), 32)


class PublicCacheTtlTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_version_keys_expire(self):
        with patch.object(public_cache, 'cache_add', return_value = True) as add:
            public_cache.bump_public_store(1)
        add.assert_called_once()
        self.assertIsNotNone(add.call_args.kwargs.get('timeout'))
        self.assertGreater(add.call_args.kwargs['timeout'], 0)

    def test_store_delete_forgets_version_key(self):
        _, profile  =   _make_user(verified = True)
        store       =   Store.objects.create(user = profile, slug = 'tienda-cache')
        key     =   public_cache._VERSION_KEY.format(store_id = store.pk)
        cache.set(key, 3)
        store.delete()
        self.assertIsNone(cache.get(key))


class _FakeResponse:
    def __init__(self, payload : bytes):
        self.headers    =   {'Content-Length': str(len(payload))}
        self._payload   =   payload

    def raise_for_status(self):
        return None

    def iter_content(self, size):
        for start in range(0, len(self._payload), size):
            yield self._payload[start:start + size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ModelDownloadTests(TestCase):
    def test_concurrent_downloads_do_not_corrupt_file(self):
        payload =   os.urandom(4096)
        directory   =   tempfile.mkdtemp()
        path        =   os.path.join(directory, 'model.onnx')

        def fake_config(name, default = None, **kwargs):
            if name == 'BG_MODEL_SHA256':
                return hashlib.sha256(payload).hexdigest()
            return default

        errors  =   []
        def worker():
            try:
                imaging._ensure_model(path)
            except Exception as exc:                 # pragma: no cover - falla el assert
                errors.append(exc)

        with patch.object(imaging, 'config', side_effect = fake_config), \
             patch.object(imaging.requests, 'get', side_effect = lambda *a, **k: _FakeResponse(payload)):
            threads =   [threading.Thread(target = worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(30)

        self.assertEqual(errors, [])
        with open(path, 'rb') as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), hashlib.sha256(payload).hexdigest())
        #Ningún temporal a medio escribir queda en el directorio.
        self.assertEqual([name for name in os.listdir(directory) if name.endswith('.part')], [])

    def test_oversized_download_is_rejected(self):
        directory   =   tempfile.mkdtemp()
        path        =   os.path.join(directory, 'model.onnx')
        with patch.object(imaging, 'BG_MODEL_MAX_BYTES', 8), \
             patch.object(imaging, 'config', side_effect = lambda name, default = None, **k: default), \
             patch.object(imaging.requests, 'get', side_effect = lambda *a, **k: _FakeResponse(b'x' * 64)):
            with self.assertRaises(ValueError):
                imaging._ensure_model(path)
        self.assertFalse(os.path.exists(path))
