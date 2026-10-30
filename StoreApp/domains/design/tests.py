"""
Tests del dominio design.

Catálogo de patrones (HTML/CSS/JS) y estilos (tokens): lectura
autenticada, escritura staff, filtros y visibilidad de solo activos.
"""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from StoreApp.domains.design.models import DesignPattern, DesignStyle

STYLES_URL      =   '/api/design/styles/'
PATTERNS_URL    =   '/api/design/patterns/'
CATALOG_URL     =   '/api/design/catalog/'


def _user(username, staff = False):
    return User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT', is_staff = staff)


class DesignCatalogTests(TestCase):
    def setUp(self):
        #La migración 0003 deja el catálogo cargado: estos tests prueban la
        #API con sus propias filas, así que parten de tablas vacías.
        DesignPattern.objects.all().delete()
        DesignStyle.objects.all().delete()
        self.owner  =   _user('owner')
        self.admin  =   _user('admin', staff = True)
        self.client =   APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user = user)

    @staticmethod
    def _rows(response):
        return response.json()['results']

    def _style(self, slug = 'minimal', active = True):
        return DesignStyle.objects.create(
            slug = slug, nombre = slug.title(), categoria = 'minimal',
            tokens = {'primary': '#111111'}, tags = ['claro'], is_active = active,
        )

    def _pattern(self, slug = 'hero-split', active = True, style = None, tags = ('hero',)):
        return DesignPattern.objects.create(
            slug = slug, nombre = slug.title(), categoria = 'landing',
            html = '<section>hola</section>', css = '.x{}', js = '',
            tokens = {'radius': '8px'}, tags = list(tags), style = style,
            is_active = active,
        )

    #LECTURA
    def test_anonymous_cannot_read(self):
        response = self.client.get(PATTERNS_URL)
        self.assertEqual(response.status_code, 401)

    def test_list_only_active_for_owner(self):
        self._pattern('activo')
        self._pattern('apagado', active = False)
        self._auth(self.owner)
        response = self.client.get(PATTERNS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['slug'] for p in self._rows(response)], ['activo'])

    def test_staff_sees_inactive(self):
        self._pattern('activo')
        self._pattern('apagado', active = False)
        self._auth(self.admin)
        response = self.client.get(PATTERNS_URL)
        self.assertEqual(len(self._rows(response)), 2)

    def test_list_hides_code_and_detail_returns_it(self):
        self._pattern('hero-split')
        self._auth(self.owner)
        row = self._rows(self.client.get(PATTERNS_URL))[0]
        self.assertNotIn('html', row)
        detail = self.client.get(f'{PATTERNS_URL}hero-split/').json()
        self.assertEqual(detail['html'], '<section>hola</section>')
        self.assertEqual(detail['css'], '.x{}')

    def test_filters(self):
        style = self._style()
        self._pattern('hero-split', style = style)
        self._pattern('otro', active = False, tags = ())
        self._auth(self.admin)
        self.assertEqual(len(self._rows(self.client.get(f'{PATTERNS_URL}?categoria=landing'))), 2)
        self.assertEqual(len(self._rows(self.client.get(f'{PATTERNS_URL}?q=split'))), 1)
        self.assertEqual(len(self._rows(self.client.get(f'{PATTERNS_URL}?tag=hero'))), 1)
        self.assertEqual(self.client.get(f'{PATTERNS_URL}hero-split/').json()['style'], 'minimal')

    #ESCRITURA
    def test_owner_cannot_write(self):
        self._auth(self.owner)
        response = self.client.post(PATTERNS_URL, {'slug': 'x', 'nombre': 'X', 'categoria': 'landing'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_staff_creates_pattern_and_style(self):
        self._auth(self.admin)
        style = self.client.post(STYLES_URL, {
            'slug': 'minimal', 'nombre': 'Minimal', 'categoria': 'minimal',
            'tokens': {'primary': '#111111'}, 'tags': ['claro'],
        }, format = 'json')
        self.assertEqual(style.status_code, 201)
        pattern = self.client.post(PATTERNS_URL, {
            'slug': 'hero-split', 'nombre': 'Hero Split', 'categoria': 'landing',
            'html': '<section></section>', 'css': '.x{}', 'js': 'console.log(1)',
            'style': 'minimal', 'tags': ['hero'],
        }, format = 'json')
        self.assertEqual(pattern.status_code, 201, pattern.content)
        self.assertEqual(DesignPattern.objects.get(slug = 'hero-split').style.slug, 'minimal')

    def test_invalid_tokens_rejected(self):
        self._auth(self.admin)
        response = self.client.post(STYLES_URL, {
            'slug': 'roto', 'nombre': 'Roto', 'categoria': 'minimal', 'tokens': ['no', 'dict'],
        }, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_duplicate_slug_rejected(self):
        self._style()
        self._auth(self.admin)
        response = self.client.post(STYLES_URL, {'slug': 'minimal', 'nombre': 'Otro', 'categoria': 'minimal'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class DesignCatalogDefaultsTests(TestCase):
    def setUp(self):
        DesignPattern.objects.all().delete()
        DesignStyle.objects.all().delete()
        self.client =   APIClient()

    def test_catalog_is_public(self):
        response = self.client.get(CATALOG_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('pattern', response.json())
        self.assertIn('styles', response.json())

    def test_defaults_public(self):
        self.assertEqual(self.client.get(f'{STYLES_URL}default/').status_code, 404)
        DesignStyle.objects.create(slug = 'base', nombre = 'Base', categoria = 'general', is_default = True)
        DesignPattern.objects.create(slug = 'raiz', nombre = 'Raíz', categoria = 'general', is_default = True)
        style = self.client.get(f'{STYLES_URL}default/')
        pattern = self.client.get(f'{PATTERNS_URL}default/')
        self.assertEqual(style.status_code, 200)
        self.assertEqual(style.json()['slug'], 'base')
        self.assertEqual(pattern.status_code, 200)
        self.assertEqual(pattern.json()['slug'], 'raiz')
        catalog = self.client.get(CATALOG_URL).json()
        self.assertEqual(catalog['style']['slug'], 'base')
        self.assertEqual(catalog['pattern']['slug'], 'raiz')

    def test_seed_catalog_idempotent(self):
        call_command('seed_design_catalog', verbosity = 0)
        call_command('seed_design_catalog', verbosity = 0)
        self.assertTrue(DesignStyle.objects.filter(slug = 'base', is_default = True).exists())
        self.assertTrue(DesignPattern.objects.filter(slug = 'raiz', is_default = True).exists())
        self.assertEqual(DesignStyle.objects.filter(is_default = True).count(), 1)
        self.assertEqual(DesignPattern.objects.filter(is_default = True).count(), 1)
        self.assertGreaterEqual(DesignStyle.objects.count(), 20)
        self.assertEqual(DesignPattern.objects.count(), 12)
        pattern = DesignPattern.objects.get(slug = 'raiz')
        self.assertIn('data-block="hero"', pattern.html)
        #Un patrón puede traer su propio markup: no se pisa con el esqueleto.
        daven = DesignPattern.objects.get(slug = 'daven-indumentaria')
        self.assertIn('dvn-stage', daven.html)
        self.assertNotIn('data-block=', daven.html)
        self.assertTrue(pattern.layout.get('landing'))
        self.assertTrue(DesignStyle.objects.get(slug = 'base').tokens.get('palette'))
