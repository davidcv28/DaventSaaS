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
from StoreApp.domains.design.models import DesignCategory, DesignPattern
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
    category, _ = DesignCategory.objects.get_or_create(slug = 'general', defaults = {'nombre': 'General'})
    return DesignPattern.objects.create(
        slug        =   slug,
        nombre      =   slug.title(),
        categoria   =   category,
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
        #El número nunca viaja en el documento: el canal enlaza el redirect
        #público (/r/whatsapp/) y se muestra solo por nombre.
        self.assertEqual(context['store_whatsapp_url'], '/api/stores/public/mi-tienda/r/whatsapp/')
        self.assertEqual(context['store_phone'], 'WhatsApp')
        self.assertEqual(context['store_email'], '')
        self.assertNotIn('1155551234', str(context))
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

    def test_render_store_pattern_reports_surfaces_and_product_data(self):
        DesignPattern.objects.all().delete()
        store   =   _store(template = 'raiz')
        Product.objects.create(store = store, name = 'Yerba', price = 1500)
        _pattern(
            slug = 'raiz',
            html = (
                '<div data-surface="landing">{{products}}</div>'
                '<div data-surface="catalog"><div data-ds-products>{{products}}</div></div>'
                '<div data-surface="services">{{services}}</div>'
            ),
        )
        doc = render_store_pattern(store)
        #La tienda del test no tiene página Servicios (sin has_services_site
        #en el plan): su superficie queda fuera del documento y la ruta sigue
        #con la plantilla Vue.
        self.assertEqual(doc['surfaces'], ['catalog', 'landing'])
        self.assertEqual(doc['products_total'], 1)
        self.assertEqual(doc['products_shown'], 24)
        #La tarjeta lleva sus datos: el catálogo filtra y ordena en el navegador.
        self.assertIn('data-cat=', doc['html'])
        self.assertIn('data-price="1500.00"', doc['html'])
        self.assertIn('data-ds-product=', doc['html'])

    def test_product_without_price_asks_to_consult(self):
        DesignPattern.objects.all().delete()
        store   =   _store(template = 'raiz')
        Product.objects.create(store = store, name = 'Sin precio', price = 0)
        _pattern(slug = 'raiz')
        doc = render_store_pattern(store)
        self.assertIn('Consultar', doc['html'])
        self.assertNotIn('$0', doc['html'])

    def test_render_only_builds_fragments_used_by_markup(self):
        store = _store()
        _pattern(slug = 'raiz')
        with patch('StoreApp.domains.design.services.pattern_render._category_fragment') as categories, \
             patch('StoreApp.domains.design.services.pattern_render._gallery_fragment') as gallery:
            render_store_pattern(store)
        categories.assert_not_called()
        gallery.assert_not_called()

    def test_render_store_pattern_none_without_markup(self):
        DesignPattern.objects.all().delete()
        store   =   _store()
        _pattern(slug = 'raiz', html = '')
        self.assertIsNone(render_store_pattern(store))

    def test_disabled_pages_hide_flagged_zones_and_surfaces(self):
        #Las páginas que el dueño apaga en "Qué mostrar" (site_templates)
        #y los toggles show_* se respetan en el documento del diseño:
        #superficie fuera del contrato + regla [data-flag] que apaga la
        #zona marcada (sección, CTA y enlace del menú).
        DesignPattern.objects.all().delete()
        store   =   _store(
            template        = 'raiz',
            site_templates  = ['landing'],
            show_catalog    = False,
            show_contact    = False,
        )
        _pattern(
            slug = 'raiz',
            html = (
                '<a data-flag="catalog">Catálogo</a>'
                '<div data-surface="landing">{{products}}</div>'
                '<div data-surface="catalog">{{products}}</div>'
            ),
        )
        doc = render_store_pattern(store)
        self.assertEqual(doc['surfaces'], ['landing'])
        self.assertIn('[data-flag="catalog"]{display:none!important}', doc['css'])
        self.assertIn('[data-flag="contact"]{display:none!important}', doc['css'])
        self.assertNotIn('ds-empty', doc['html'])

    def test_plans_section_follows_site_templates_and_toggle(self):
        from StoreApp.domains.design.services.pattern_render import _plans_fragment

        store   =   _store(site_templates = ['landing', 'catalog'], show_plans = True)
        custom  =   store.customization
        custom.plans = [{'name': 'Club', 'price': '$10.000'}]
        self.assertEqual(_plans_fragment(store, custom), '')


class ProductReviewFragmentTests(TestCase):
    """Las opiniones de la ficha respetan los toggles del dueño y el plan."""

    def setUp(self):
        DesignPattern.objects.all().delete()
        self.store      =   _store()
        self.product    =   Product.objects.create(store = self.store, name = 'Yerba', price = 1500)
        self.custom     =   self.store.customization

    def _frag(self, has_benefit = True):
        from StoreApp.domains.catalog.models import ProductReview
        from StoreApp.domains.design.services.pattern_render import _reviews_fragment
        ProductReview.objects.create(
            store = self.store, product = self.product,
            is_positive = True, text = 'Muy buena', name = 'Ana', surname = 'Lopez', email = 'a@a.com',
        )
        ProductReview.objects.create(
            store = self.store, product = self.product,
            is_positive = None, text = 'Solo texto', name = 'Juan', surname = 'Paz', email = 'b@b.com',
        )
        with patch('StoreApp.domains.stores.services.profile_has_benefit', return_value = has_benefit):
            return _reviews_fragment(self.store, self.product, self.custom)

    def _flags(self, rate = False, comment = False):
        self.custom.show_reviews  = rate
        self.custom.show_comments = comment

    def test_disabled_by_owner_renders_nothing(self):
        self._flags()
        self.assertEqual(self._frag(), '')

    def test_without_plan_benefit_renders_nothing(self):
        self._flags(rate = True, comment = True)
        self.assertEqual(self._frag(has_benefit = False), '')

    def test_rate_only_hides_comment_text(self):
        self._flags(rate = True)
        frag = self._frag()
        self.assertIn('data-rate="1"', frag)
        self.assertIn('data-comment="0"', frag)
        self.assertIn('ds-rev-list', frag)
        self.assertIn('Ana L.', frag)
        self.assertNotIn('Muy buena', frag)   #texto oculto sin show_comments
        self.assertNotIn('Solo texto', frag)
        self.assertNotIn('Juan', frag)        #reseña sin voto tampoco aparece

    def test_comment_only_shows_text_without_votes(self):
        self._flags(comment = True)
        frag = self._frag()
        self.assertIn('data-rate="0"', frag)
        self.assertIn('data-comment="1"', frag)
        self.assertIn('Muy buena', frag)
        self.assertIn('Solo texto', frag)

    def test_rating_values_need_show_reviews(self):
        from StoreApp.domains.catalog.models import ProductReview
        from StoreApp.domains.design.services.pattern_render import _rating_values
        ProductReview.objects.create(
            store = self.store, product = self.product,
            is_positive = True, name = 'Ana', surname = 'L', email = 'a@a.com',
        )
        ProductReview.objects.create(
            store = self.store, product = self.product,
            is_positive = False, name = 'Juan', surname = 'P', email = 'b@b.com',
        )
        with patch('StoreApp.domains.stores.services.profile_has_benefit', return_value = True):
            self._flags(rate = True)
            avg, count = _rating_values(self.store, self.product, self.custom)
            self.assertEqual((avg, count), ('2.5', '2'))
            self._flags()
            self.assertEqual(_rating_values(self.store, self.product, self.custom), ('', ''))


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

    def test_meta_endpoint_returns_light_envelope(self):
        with patch('StoreApp.domains.stores.views.viewset.profile_has_benefit', return_value = True):
            response = self.client.get(PATTERN_URL, {'meta': 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['slug'], 'raiz')
        self.assertTrue(data['has_html'])
        #El host solo necesita el sobre: el documento lo carga el iframe.
        self.assertNotIn('html', data)
        self.assertNotIn('css', data)
        self.assertNotIn('js', data)

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


class PatternSourceTests(TestCase):
    """
    Los patrones convertidos al contrato de variables tienen su fuente
    editable en `sources/<slug>.html`: el markup se parte en html/css/js y
    las variables declaradas se derivan de los placeholders que usa.
    """

    SLUGS = ('esencial',)

    def test_split_document_returns_three_layers(self):
        from StoreApp.domains.design.services.source_document import split_document
        html, css, js = split_document(
            '<html><head><style>.a{color:red}</style></head>'
            '<body><h1>{{store_name}}</h1><script>var a = 1</script></body></html>'
        )
        self.assertEqual(html, '<h1>{{store_name}}</h1>')
        self.assertIn('.a{color:red}', css)
        self.assertIn('var a = 1', js)

    def test_variables_come_from_the_markup_only(self):
        from StoreApp.domains.design.services.source_document import (
            variables_from_markup,
        )
        variables = variables_from_markup('<h1>{{store_name}}</h1><p>{{no_existe}}</p>')
        self.assertEqual(list(variables), ['store_name'])

    def test_converted_patterns_have_a_ready_source(self):
        from StoreApp.domains.design.services.source_document import load_source
        for slug in self.SLUGS:
            with self.subTest(slug = slug):
                source = load_source(slug)
                self.assertIsNotNone(source, f'falta sources/{slug}.html')
                html, css, js, variables = source
                self.assertIn('store_name', variables)
                self.assertIn('products', variables)
                #Membresías del negocio: la sección Suscripciones de la portada.
                self.assertIn('plans', variables)
                #El estilo solo puede tocar colores/bordes: el diseño usa --ds-*.
                self.assertIn('var(--ds-accent', css)
                #Modo noche explícito: lo controla el interruptor del diseño,
                #no el sistema operativo del visitante.
                self.assertIn('data-ds-theme="dark"', css)
                #Portada, catálogo y servicios son superficies del diseño.
                surfaces = ('landing', 'catalog', 'services')
                for surface in surfaces:
                    self.assertIn(f'data-surface="{surface}"', html)
                self.assertIn('data-ds-products', html)

    def test_converted_patterns_render_and_escape_store_data(self):
        from django.utils.html import escape

        from StoreApp.domains.design.services.source_document import load_source
        for slug in self.SLUGS:
            with self.subTest(slug = slug):
                html, _, _, variables = load_source(slug)
                pattern = DesignPattern(
                    slug = slug, nombre = slug.title(),
                    template = slug, html = html, variables = variables,
                )
                rendered = pattern.render({'store_name': '<b>x</b>'})
                self.assertIn(escape('<b>x</b>'), rendered)
                self.assertNotRegex(rendered, r'\{\{\s*[a-z_]+\s*\}\}')
