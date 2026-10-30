"""
Tests del render de DesignPattern contra los datos de la tienda.

Contrato: variables de texto escapadas, fragmentos de lista armados por el
backend, tema del estilo traducido a `--ds-*` y endpoint público.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Category, Product
from StoreApp.domains.design.models import DesignPattern, DesignStyle
from StoreApp.domains.design.services import (
    build_store_context,
    pattern_for_template,
    render_store_pattern,
    theme_css,
)
from StoreApp.domains.stores.models import Store, StoreCustomization

PATTERN_URL = '/api/stores/public/mi-tienda/pattern/'


def _store(slug = 'mi-tienda', **customization):
    province    =   Province.objects.create(name_province = 'Mendoza')
    zipcode     =   ZipCode.objects.create(zipcode = '5500')
    city        =   City.objects.create(name_city = 'Mendoza', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = f'duenio-{slug}', email = f'{slug}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   '27123456',
        province        =   province,
        city            =   city,
        email_verified  =   True,
        phone           =   '1100000001',
        business_name   =   'Almacén Don Pedro',
    )
    store       =   Store.objects.create(user = profile, slug = slug, is_published = True)
    StoreCustomization.objects.create(
        store           =   store,
        display_name    =   'Don Pedro',
        description     =   'Almacén de barrio',
        whatsapp        =   '11 5555-1234',
        accent_custom   =   '#0f766e',
        **customization,
    )
    return store


def _pattern(slug = 'raiz', html = None, **kwargs):
    return DesignPattern.objects.create(
        slug        =   slug,
        nombre      =   slug.title(),
        categoria   =   'general',
        template    =   kwargs.pop('template', slug),
        html        =   html if html is not None else '<h1>{{store_name}}</h1><div>{{products}}</div>',
        css         =   '.x{color:red}',
        js          =   'console.log(1)',
        variables   =   {
            'store_name': {'type': 'text'},
            'products':   {'type': 'list'},
            'services':   {'type': 'list'},
        },
        **kwargs,
    )


class PatternRenderServiceTests(TestCase):
    def setUp(self):
        #La migración deja el catálogo sembrado: cada test crea sus filas.
        DesignPattern.objects.all().delete()

    def test_text_variables_are_escaped(self):
        pattern = _pattern(html = '<h1>{{store_name}}</h1>')
        html    = pattern.render({'store_name': '<script>alert(1)</script>'})
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_undeclared_variable_is_dropped(self):
        pattern = _pattern(html = '<h1>{{secreto}}</h1>')
        self.assertEqual(pattern.render({'secreto': 'x'}), '<h1></h1>')

    def test_list_variable_is_raw_only_when_allowed(self):
        pattern = _pattern(html = '<div>{{products}}</div>')
        html    = pattern.render({}, raw = {'products': '<b>ok</b>'})
        self.assertIn('<b>ok</b>', html)
        escaped = pattern.render({'products': '<b>ok</b>'})
        self.assertIn('&lt;b&gt;', escaped)

    def test_context_uses_store_data(self):
        store           =   _store()
        context, raw    =   build_store_context(store)
        self.assertEqual(context['store_name'], 'Don Pedro')
        self.assertEqual(context['store_initial'], 'D')
        self.assertEqual(context['store_whatsapp_url'], 'https://wa.me/1155551234')
        self.assertEqual(context['store_accent'], '#0f766e')
        self.assertIn('products', raw)

    def test_product_fragment_escapes_and_lists_active_only(self):
        store       =   _store()
        category    =   Category.objects.create(store = store, name = 'Despensa')
        Product.objects.create(store = store, category = category, name = 'Yerba <b>', price = 1500)
        Product.objects.create(store = store, name = 'Oculto', price = 10, is_active = False)
        _, raw      =   build_store_context(store)
        self.assertIn('Yerba &lt;b&gt;', raw['products'])
        self.assertNotIn('Oculto', raw['products'])
        self.assertIn('$1.500', raw['products'])

    def test_empty_catalog_shows_empty_state(self):
        store       =   _store()
        _, raw      =   build_store_context(store)
        self.assertIn('ds-empty', raw['products'])

    def test_theme_css_translates_style_effects(self):
        store           =   _store(site_theme = {
            'style': {'id': 'base', 'effects': {'radius': 'lg', 'shadow': 'soft', 'button_shape': 'pill', 'layout': 'x'}},
        })
        customization   =   store.customization
        css             =   theme_css(customization)
        self.assertIn('--ds-radius:14px', css)
        self.assertIn('--ds-shadow:', css)
        self.assertIn('--ds-radius-btn:999px', css)
        self.assertIn('--ds-accent:#0f766e', css)
        self.assertNotIn('layout', css)

    def test_pattern_resolution_prefers_slug_then_template(self):
        DesignPattern.objects.all().delete()
        other   =   _pattern(slug = 'otro', template = 'raiz')
        self.assertEqual(pattern_for_template('raiz'), other)
        own     =   _pattern(slug = 'raiz', template = 'raiz')
        self.assertEqual(pattern_for_template('raiz'), own)

    def test_render_store_pattern_returns_document(self):
        DesignPattern.objects.all().delete()
        store   =   _store(template = 'raiz')
        _pattern(slug = 'raiz')
        doc     =   render_store_pattern(store)
        self.assertEqual(doc['slug'], 'raiz')
        self.assertIn('Don Pedro', doc['html'])
        self.assertIn('--ds-accent', doc['css'])
        self.assertIn('console.log(1)', doc['js'])
        self.assertTrue(doc['dark'])

    def test_render_store_pattern_none_without_markup(self):
        DesignPattern.objects.all().delete()
        store   =   _store()
        _pattern(slug = 'raiz', html = '')
        self.assertIsNone(render_store_pattern(store))


class PublicPatternEndpointTests(TestCase):
    def setUp(self):
        DesignPattern.objects.all().delete()
        self.store  =   _store()
        _pattern(slug = 'raiz')
        self.client =   APIClient()

    def test_public_endpoint_returns_rendered_pattern(self):
        with patch('StoreApp.domains.stores.views.viewset.profile_has_benefit', return_value = True):
            response = self.client.get(PATTERN_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['slug'], 'raiz')
        self.assertIn('Don Pedro', data['html'])

    def test_unpublished_store_is_404(self):
        self.store.is_published = False
        self.store.save(update_fields = ['is_published'])
        with patch('StoreApp.domains.stores.views.viewset.profile_has_benefit', return_value = True):
            response = self.client.get(PATTERN_URL)
        self.assertEqual(response.status_code, 404)

    def test_store_without_plan_is_404(self):
        with patch('StoreApp.domains.stores.views.viewset.profile_has_benefit', return_value = False):
            response = self.client.get(PATTERN_URL)
        self.assertEqual(response.status_code, 404)
