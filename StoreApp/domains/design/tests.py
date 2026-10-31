"""
Tests del dominio design.

Catálogo de patrones (HTML/CSS/JS) y estilos (tokens): lectura
autenticada, escritura staff, filtros y visibilidad de solo activos.
"""
import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from StoreApp.domains.design.models import DesignPattern, DesignStyle

STYLES_URL      =   '/api/design/styles/'
PATTERNS_URL    =   '/api/design/patterns/'
CATALOG_URL     =   '/api/design/catalog/'
SEED_FILE       =   Path(__file__).resolve().parent / 'seed_data.json'


def _seed_data():
    return json.loads(SEED_FILE.read_text(encoding = 'utf-8'))


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
        self.assertEqual(DesignPattern.objects.count(), len(_seed_data()['patterns']))
        pattern = DesignPattern.objects.get(slug = 'raiz')
        self.assertIn('data-block="hero"', pattern.html)
        #Los arquetipos del formato viejo ya no forman parte del catálogo.
        self.assertFalse(DesignPattern.objects.filter(slug = 'mercado-libre').exists())
        self.assertTrue(pattern.layout.get('landing'))
        self.assertTrue(DesignStyle.objects.get(slug = 'base').tokens.get('palette'))


ICON_URL        =   '/api/design/icon-styles/'


class DesignContractTests(TestCase):
    """Contrato nuevo: estilo limitado, variables de patrón e iconos."""

    def setUp(self):
        self.admin  =   _user('admin2', staff = True)
        self.owner  =   _user('owner2')
        self.client =   APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user = user)

    def test_style_effects_discard_structural_keys(self):
        self._auth(self.admin)
        response = self.client.post(STYLES_URL, {
            'slug': 'contrato', 'nombre': 'Contrato', 'categoria': 'general',
            'effects': {
                'radius': 'pill', 'accent': '#12AB34', 'border_width': 2,
                'shadow': 'soft', 'layout': {'landing': []},
                'template': 'raiz', 'html': '<script>alert(1)</script>',
                'border_width_evil': 9,
            },
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['effects'], {
            'radius': 'pill', 'accent': '#12ab34', 'border_width': 2, 'shadow': 'soft',
        })

    def test_style_effects_reject_invalid_values(self):
        self._auth(self.admin)
        response = self.client.post(STYLES_URL, {
            'slug': 'contrato2', 'nombre': 'Contrato 2', 'categoria': 'general',
            'effects': {'accent': 'red', 'radius': 'huge', 'border_width': 99, 'divider': 'line'},
        }, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['effects'], {'divider': 'line'})

    def test_pattern_variables_and_render(self):
        pattern = DesignPattern.objects.create(
            slug = 'vars', nombre = 'Vars', categoria = 'landing',
            html = '<h1>{{store_name}}</h1><p>{{missing}}</p><script>{{store_name}}</script>',
            variables = {
                'store_name': {'type': 'text', 'label': 'Nombre'},
                'bad key': {'type': 'text'},
                'layout': 'ignored',
            },
        )
        self.assertEqual(list(pattern.variables.keys()), ['store_name'])
        rendered = pattern.render({'store_name': 'Mi <Negocio>'})
        self.assertIn('Mi &lt;Negocio&gt;', rendered)
        self.assertNotIn('<Negocio>', rendered)
        self.assertNotIn('{{', rendered)

    def test_pattern_preview_renders_sample_data(self):
        DesignPattern.objects.create(
            slug = 'prev', nombre = 'Prev', categoria = 'landing',
            html = '<h1>{{store_name}}</h1><div class="grid">{{products}}</div>',
            variables = {
                'store_name': {'type': 'text'},
                'products': {'type': 'list'},
            },
        )
        self._auth(self.owner)
        response = self.client.get('/api/design/patterns/prev/preview/')
        self.assertEqual(response.status_code, 200, response.content)
        html = response.json()['html']
        self.assertNotIn('{{', html)
        self.assertIn('Tu negocio', html)
        self.assertIn('ds-product', html)

    def test_pattern_serializer_sanitizes_variables(self):
        self._auth(self.admin)
        response = self.client.post(PATTERNS_URL, {
            'slug': 'vars-api', 'nombre': 'Vars API', 'categoria': 'landing',
            'html': '<b>{{title}}</b>',
            'variables': {'title': {'type': 'text'}, 'Bad Name': {'type': 'text'}},
            'supports_dark_mode': True,
        }, format = 'json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(list(response.json()['variables'].keys()), ['title'])

    def test_icon_style_sanitizes_paths(self):
        from StoreApp.domains.design.models import DesignIconStyle
        icon_style = DesignIconStyle.objects.create(
            slug = 'test-set', nombre = 'Test', is_default = True,
            icons = {
                'home': {'path': 'M3 3h18v18z'},
                'unknown': {'path': 'M0 0h1v1z'},
                'bad': {'path': '<script>alert(1)</script>'},
            },
        )
        icon_style.refresh_from_db()
        self.assertEqual(list(icon_style.icons.keys()), ['home'])
        self.assertEqual(icon_style.icons['home']['view_box'], '0 0 24 24')

    def test_icon_style_endpoints(self):
        from StoreApp.domains.design.models import DesignIconStyle
        DesignIconStyle.objects.create(slug = 'base-set', nombre = 'Base', is_default = True,
                                       icons = {'home': {'path': 'M3 3h18v18z'}})
        DesignIconStyle.objects.create(slug = 'off-set', nombre = 'Off', is_active = False)
        self.assertEqual(self.client.get(ICON_URL).status_code, 401)
        self._auth(self.owner)
        rows = self.client.get(ICON_URL).json()['results']
        self.assertEqual([r['slug'] for r in rows], ['base-set'])
        default = self.client.get(f'{ICON_URL}default/')
        self.assertEqual(default.status_code, 200)
        self.assertEqual(default.json()['slug'], 'base-set')

    def test_catalog_includes_icon_styles(self):
        from StoreApp.domains.design.models import DesignIconStyle
        DesignIconStyle.objects.create(slug = 'catalog-set', nombre = 'Catálogo', is_default = True)
        data = self.client.get(CATALOG_URL).json()
        self.assertIn('icon_styles', data)
        self.assertEqual(data['default_icon_style']['slug'], 'catalog-set')


class IconStyleSeedTests(TestCase):
    def test_seed_is_idempotent_and_sets_default(self):
        from StoreApp.domains.design.models import DesignIconStyle
        call_command('seed_icon_styles', verbosity = 0)
        call_command('seed_icon_styles', verbosity = 0)
        self.assertEqual(DesignIconStyle.objects.filter(is_default = True).count(), 1)
        self.assertGreaterEqual(DesignIconStyle.objects.count(), 4)
        lineal = DesignIconStyle.objects.get(slug = 'lineal')
        self.assertTrue(lineal.is_default)
        self.assertIn('home', lineal.icons)
        self.assertIn('path', lineal.icons['home'])
