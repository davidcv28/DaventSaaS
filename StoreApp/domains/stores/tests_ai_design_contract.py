"""
Suite de CONTRATO del motor de diseño con IA (endpoints /api/stores/ai-design/
y /api/stores/ai-design/apply/).

El contrato está congelado: motor local y determinista, sin llamadas a
servicios de IA, 2-3 propuestas dentro de la whitelist del plan, layout
saneado contra TEMPLATE_BLOCKS y apply que escribe SOLO el borrador.

Esta suite es de QA: no toca código de producción. Si el endpoint todavía
no existe, los tests fallan con 404 (PENDIENTE), no se saltan.
"""
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS, LAYOUT_SURFACES, clean_layout_config
from StoreApp.domains.stores.models import Store, StoreCustomization
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.site_theme import clean_site_theme
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

#Beneficios: la IA de diseño exige personalización + el flag propio.
CUSTOMIZATION       =   ('has_customization',)
AI_DESIGN           =   ('has_ai_design',)
DESIGN_PLUS         =   ('has_design_plus',)
DESIGN_ADVANCED     =   ('has_design_advanced',)

#Bloques cuya existencia depende de datos reales del negocio (BLOCK_GATES):
#sin el dato, el contrato exige enabled=False (nunca una sección vacía).
DATA_DRIVEN_LANDING =   frozenset({
    'announcements', 'highlights', 'categories', 'featured', 'about', 'services',
    'stats', 'benefits', 'offers', 'brands', 'countdown', 'timeline', 'team',
    'gallery', 'testimonials', 'faq', 'video', 'steps', 'compare',
})
DATA_DRIVEN_CATALOG =   frozenset({'note', 'banner', 'promo', 'filters', 'sort'})
DATA_DRIVEN_SERVICES = frozenset({'band', 'steps', 'form', 'faq'})

COPY_MAX            =   {'headline': 140, 'description': 800, 'cta_title': 120, 'cta_text': 280, 'cta_label': 40}

_pk_seq             =   [0]


def _next_pk():
    _pk_seq[0] += 1
    return _pk_seq[0]


def _make_account(*benefit_codes, slug = 'mi-tienda'):
    """Usuario verificado con tienda y plan vigente que habilita `benefit_codes`."""
    n           =   _next_pk()
    province    =   Province.objects.create(name_province = f'Provincia QA {n}')
    zipcode     =   ZipCode.objects.create(zipcode = f'{n:04d}'[-4:])
    city        =   City.objects.create(name_city = f'Ciudad QA {n}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = f'qa{n}', email = f'qa{n}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'29{n:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   True,
        phone           =   f'11{n:08d}',
    )
    plan        =   SuscriptionPlan.objects.create(name = f'Plan QA {n}')
    for code in set(benefit_codes):
        benefit =   Benefit.objects.get_or_create(
            code    =   code,
            defaults =   {'label': code, 'kind': Benefit.FLAG},
        )[0]
        PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    store       =   Store.objects.create(user = profile, slug = f'{slug}-{n}')
    return user, profile, store


def _proposals_of(response):
    return response.json().get('proposals') or []


class _AiDesignBase(TestCase):
    """Cliente autenticado + URLs del router (nunca paths sueltos)."""

    def setUp(self):
        #plan_benefits_of cachea por PK y SQLite reutiliza PKs entre tests.
        cache.clear()
        self.base_url   =   reverse('Stores-list')
        self.gen_url    =   f'{self.base_url}ai-design/'
        self.apply_url  =   f'{self.base_url}ai-design/apply/'

    def _client(self, *codes):
        user, profile, store    =   _make_account(*codes)
        client                  =   APIClient()
        client.force_authenticate(user = user)
        return client, profile, store

    def _premium_client(self):
        return self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED))

    def _generate(self, client, **payload):
        body    =   {'rubro': 'comercio', 'goals': ['vender_online'], 'tone': 'moderno',
                     'audience': 'clientes del barrio', 'must_have': ['catálogo'], **payload}
        return client.post(self.gen_url, body, format = 'json')


#=========================================
# GENERACIÓN
#=========================================
class AiDesignGenerationTests(_AiDesignBase):
    """Forma de la respuesta: 2-3 propuestas, ids/labels únicos y textos acotados."""

    def test_returns_between_two_and_three_proposals(self):
        client, _, _    =   self._premium_client()
        response        =   self._generate(client)
        self.assertEqual(response.status_code, 200, response.content[:400])
        proposals       =   _proposals_of(response)
        self.assertIn(len(proposals), (2, 3))

    def test_proposal_ids_are_unique_and_labels_distinct(self):
        client, _, _    =   self._premium_client()
        proposals       =   _proposals_of(self._generate(client))
        ids             =   [p['id'] for p in proposals]
        labels          =   [p['label'] for p in proposals]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(labels), len(set(labels)))

    def test_response_reports_engine_seed_and_missing(self):
        client, _, _    =   self._premium_client()
        body            =   self._generate(client).json()
        self.assertEqual(body['engine'], 'ai-design/1')
        self.assertIsInstance(body['seed'], int)
        self.assertIsInstance(body['missing'], list)
        self.assertTrue(all(isinstance(item, str) for item in body['missing']))

    def test_every_proposal_declares_label_why_and_notes(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertTrue(proposal['label'])
            self.assertLessEqual(len(proposal['label']), 32)
            self.assertTrue(proposal['why'])
            self.assertLessEqual(len(proposal['why']), 160)
            self.assertIsInstance(proposal['notes'], list)
            self.assertTrue(all(isinstance(note, str) for note in proposal['notes']))

    def test_copy_respects_the_model_max_lengths(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            copy    =   proposal['copy']
            for field, max_len in COPY_MAX.items():
                self.assertIn(field, copy)
                self.assertIsInstance(copy[field], str)
                self.assertLessEqual(len(copy[field]), max_len, f'{field} excede {max_len}')

    def test_templates_stay_inside_the_plan_whitelist(self):
        #Básico: solo classic/duo; Premium: todo el catálogo permitido.
        for codes in (CUSTOMIZATION + AI_DESIGN, CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED):
            client, profile, _  =   self._client(*codes)
            allowed             =   set(allowed_templates_of(profile))
            for proposal in _proposals_of(self._generate(client)):
                self.assertIn(proposal['template'], allowed)

    def test_each_proposal_has_layout_config_for_the_public_surfaces(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            layout      =   proposal['layout_config']
            self.assertIsInstance(layout, dict)
            self.assertTrue(layout, 'layout_config vacío: no hay propuesta que aplicar')
            for surface, value in layout.items():
                self.assertIn(surface, LAYOUT_SURFACES)
                self.assertIsInstance(value.get('blocks'), list)

    def test_site_theme_is_an_object_with_closed_catalog_values(self):
        client, _, store    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            theme           =   proposal['site_theme']
            self.assertIsInstance(theme, dict)
            #Idempotente respecto del saneador: nada fuera del catálogo cerrado.
            self.assertEqual(
                clean_site_theme(theme, has_plus = True, has_advanced = True, has_style = True, store = store),
                theme,
            )


#=========================================
# GATING Y PLAN
#=========================================
class AiDesignGatingTests(_AiDesignBase):
    """El motor exige personalización Y el flag has_ai_design del plan vigente."""

    def test_forbidden_without_customization(self):
        client, _, _    =   self._client(*AI_DESIGN)
        self.assertEqual(self._generate(client).status_code, 403)

    def test_forbidden_without_ai_design_flag(self):
        client, _, _    =   self._client(*CUSTOMIZATION)
        self.assertEqual(self._generate(client).status_code, 403)

    def test_allowed_with_customization_and_ai_design(self):
        client, _, _    =   self._client(*(CUSTOMIZATION + AI_DESIGN))
        self.assertEqual(self._generate(client).status_code, 200)

    def test_requires_authentication(self):
        response    =   APIClient().post(self.gen_url, {}, format = 'json')
        self.assertIn(response.status_code, (401, 403))


#=========================================
# SANITIZACIÓN DEL LAYOUT
#=========================================
class AiDesignSanitizationTests(_AiDesignBase):
    """El layout propuesto ya sale saneado: ids cerrados, locked on, premium filtrado."""

    def _all_blocks(self, proposal):
        for surface, value in proposal['layout_config'].items():
            for block in value['blocks']:
                yield surface, block

    def test_block_ids_belong_to_the_template_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for surface, block in self._all_blocks(proposal):
                self.assertIn(block['id'], TEMPLATE_BLOCKS[surface])

    def test_locked_blocks_are_always_enabled(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for surface, block in self._all_blocks(proposal):
                if TEMPLATE_BLOCKS[surface][block['id']].get('locked'):
                    self.assertTrue(block['enabled'], f'{surface}.{block["id"]} locked apagado')

    def test_premium_blocks_are_omitted_without_design_advanced(self):
        client, _, _    =   self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS))
        for proposal in _proposals_of(self._generate(client)):
            for surface, block in self._all_blocks(proposal):
                self.assertFalse(
                    TEMPLATE_BLOCKS[surface][block['id']].get('premium'),
                    f'{surface}.{block["id"]} es premium y el plan no lo incluye',
                )

    def test_blocks_without_real_data_are_disabled(self):
        #Tienda vacía: sin productos, servicios, faqs, galería ni testimonios.
        client, _, _    =   self._premium_client()
        gated           =   {'landing': DATA_DRIVEN_LANDING, 'catalog': DATA_DRIVEN_CATALOG,
                             'services': DATA_DRIVEN_SERVICES}
        for proposal in _proposals_of(self._generate(client)):
            for surface, block in self._all_blocks(proposal):
                if block['id'] in gated.get(surface, frozenset()) and not TEMPLATE_BLOCKS[surface][block['id']].get('locked'):
                    self.assertFalse(block['enabled'], f'{surface}.{block["id"]} sin datos pero enabled=true')

    def test_layout_config_is_idempotent_under_the_sanitizer(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertEqual(
                clean_layout_config(proposal['layout_config'], True),
                proposal['layout_config'],
            )


#=========================================
# DETERMINISMO
#=========================================
class AiDesignDeterminismTests(_AiDesignBase):
    """Misma entrada => mismo JSON; el motor es local y determinista."""

    def test_same_request_returns_the_same_proposals(self):
        client, _, _    =   self._premium_client()
        first           =   self._generate(client).json()
        second          =   self._generate(client).json()
        self.assertEqual(json.dumps(first, sort_keys = True), json.dumps(second, sort_keys = True))

    def test_explicit_seed_reproduces_the_same_payload(self):
        client, _, _    =   self._premium_client()
        first           =   self._generate(client, seed = 12345).json()
        second          =   self._generate(client, seed = 12345).json()
        self.assertEqual(json.dumps(first, sort_keys = True), json.dumps(second, sort_keys = True))


#=========================================
# APPLY / BORRADOR
#=========================================
class AiDesignApplyTests(_AiDesignBase):
    """apply recalcula server-side y escribe SOLO el borrador, sin pisar datos."""

    def _apply(self, client, seed, proposal_id):
        return client.post(self.apply_url, {'seed': seed, 'proposal_id': proposal_id}, format = 'json')

    def _first_proposal(self, client):
        body    =   self._generate(client).json()
        return body['seed'], body['proposals'][0]['id']

    def test_apply_returns_the_same_shape_as_the_customization_patch(self):
        client, _, _    =   self._premium_client()
        seed, pid       =   self._first_proposal(client)
        response        =   self._apply(client, seed, pid)
        self.assertEqual(response.status_code, 200, response.content[:400])
        body            =   response.json()
        for key in ('Exito', 'customization', 'storage'):
            self.assertIn(key, body)

    def test_apply_writes_only_the_draft_fields(self):
        client, profile, store  =   self._premium_client()
        published               =   StoreCustomization.objects.create(
            store           =   store,
            template        =   'classic',
            layout_config   =   {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
            site_theme      =   {'palette': {'primary': '#111111'}},
        )
        seed, pid               =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        published.refresh_from_db()
        self.assertEqual(published.template, 'classic')
        self.assertEqual(published.layout_config, {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}})
        self.assertEqual(published.site_theme, {'palette': {'primary': '#111111'}})

    def test_apply_writes_the_draft_fields(self):
        client, profile, store  =   self._premium_client()
        seed, pid               =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization           =   StoreCustomization.objects.get(store = store)
        self.assertTrue(customization.layout_config_draft)
        self.assertIn(customization.template_draft, allowed_templates_of(profile))

    def test_copy_never_overwrites_content_written_by_the_owner(self):
        client, profile, store  =   self._premium_client()
        services                =   [{'title': 'Corte', 'text': 'Con turno'}]
        faqs                    =   [{'question': '¿Abren?', 'answer': 'Sí'}]
        stats                   =   [{'value': '10', 'label': 'años'}]
        testimonials            =   [{'name': 'Ana', 'text': 'Genial'}]
        hours                   =   [{'label': 'Lun a vie', 'value': '9 a 18'}]
        StoreCustomization.objects.create(
            store           =   store,
            headline        =   'Mi titular',
            description     =   'Mi descripción',
            about_text      =   'Mi historia',
            cta_title       =   'Mi cierre',
            cta_text        =   'Texto del cierre',
            cta_label       =   'Escribinos',
            services        =   services,
            faqs            =   faqs,
            stats           =   stats,
            testimonials    =   testimonials,
            hours           =   hours,
        )
        seed, pid       =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization   =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.headline, 'Mi titular')
        self.assertEqual(customization.description, 'Mi descripción')
        self.assertEqual(customization.about_text, 'Mi historia')
        self.assertEqual(customization.cta_title, 'Mi cierre')
        self.assertEqual(customization.cta_text, 'Texto del cierre')
        self.assertEqual(customization.cta_label, 'Escribinos')
        self.assertEqual(customization.services, services)
        self.assertEqual(customization.faqs, faqs)
        self.assertEqual(customization.stats, stats)
        self.assertEqual(customization.testimonials, testimonials)
        self.assertEqual(customization.hours, hours)

    def test_copy_fills_only_empty_fields(self):
        client, profile, store  =   self._premium_client()
        seed, pid               =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization           =   StoreCustomization.objects.get(store = store)
        self.assertTrue(customization.headline, 'el titular vacío debería rellenarse')
        self.assertLessEqual(len(customization.headline), COPY_MAX['headline'])
        #about_text está prohibido para el motor: sigue vacío.
        self.assertEqual(customization.about_text, '')

    def test_unknown_proposal_id_is_rejected(self):
        client, _, _    =   self._premium_client()
        seed, _         =   self._first_proposal(client)
        response        =   self._apply(client, seed, 'no-existe')
        self.assertEqual(response.status_code, 400)

    def test_apply_is_idempotent_for_the_same_seed_and_proposal(self):
        client, profile, store  =   self._premium_client()
        seed, pid               =   self._first_proposal(client)
        first                   =   self._apply(client, seed, pid).json()['customization']
        second                  =   self._apply(client, seed, pid).json()['customization']
        for field in ('layout_config_draft', 'site_theme_draft', 'template_draft', 'headline'):
            self.assertEqual(first.get(field), second.get(field), field)


#=========================================
# THROTTLE
#=========================================
class AiDesignThrottleTests(_AiDesignBase):
    """El scope 'ai_design' (20/hour) corta el abuso del motor."""

    def test_generation_is_throttled_after_twenty_calls(self):
        cache.clear()
        client, _, _    =   self._premium_client()
        for index in range(20):
            response    =   self._generate(client)
            self.assertEqual(response.status_code, 200, f'call {index + 1}: {response.content[:200]}')
        self.assertEqual(self._generate(client).status_code, 429)
