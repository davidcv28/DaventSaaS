"""
Suite de CONTRATO v2 del motor de diseño con IA ("Diseñar con IA").

Endpoints:
  POST /api/stores/ai-design/          -> propuestas (motor local, determinista)
  POST /api/stores/ai-design/apply/    -> borrador (+ autofill opcional)
  POST /api/stores/ai-design/image/    -> fotos del pedido (WebP en galería)

Contrato congelado: cero llamadas de red, layout saneado contra
TEMPLATE_BLOCKS, copy_draft acotado y apply que nunca pisa datos del dueño.

Esta suite es de QA: no toca código de producción. Si un endpoint todavía no
existe, los tests fallan (PENDIENTE), no se saltan.
"""
import json
import socket
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS, LAYOUT_SURFACES, clean_layout_config
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreGalleryImage
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.site_theme import clean_site_theme
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

#Beneficios: la IA de diseño exige personalización + el flag propio.
CUSTOMIZATION       =   ('has_customization',)
AI_DESIGN           =   ('has_ai_design',)
DESIGN_PLUS         =   ('has_design_plus',)
DESIGN_ADVANCED     =   ('has_design_advanced',)
PUBLIC_LINK         =   ('has_public_link',)

#Cuotas típicas del plan premium (sin ellas, storage/gallery_limit = 0).
PREMIUM_LIMITS      =   {'max_gallery_images': 20, 'max_images': 50, 'max_storage_mb': 200}

#Bloques cuya existencia depende de datos reales del negocio (BLOCK_GATES):
#sin el dato, el contrato exige enabled=False (nunca una sección vacía).
DATA_DRIVEN_LANDING =   frozenset({
    'announcements', 'highlights', 'categories', 'featured', 'about', 'services',
    'stats', 'benefits', 'offers', 'brands', 'countdown', 'timeline', 'team',
    'gallery', 'testimonials', 'faq', 'video', 'steps', 'compare',
})
DATA_DRIVEN_CATALOG =   frozenset({'note', 'banner', 'promo', 'filters', 'sort'})
DATA_DRIVEN_SERVICES =  frozenset({'band', 'steps', 'form', 'faq'})

COPY_MAX            =   {'headline': 140, 'description': 800, 'cta_title': 120, 'cta_text': 280, 'cta_label': 40}
DRAFT_MAX           =   {'about_text': 2000, 'about_mission': 400}
FAQ_Q_MAX, FAQ_A_MAX            =   140, 600
SERVICE_NAME_MAX, SERVICE_DESC_MAX = 60, 160
STEP_TITLE_MAX, STEP_DESC_MAX      = 60, 160
ANNOUNCEMENT_MAX    =   120
DRAFT_KEYS          =   frozenset({'about_text', 'about_mission', 'faqs', 'services', 'steps', 'announcements'})
DRAFT_FORBIDDEN     =   frozenset({'testimonials', 'stats', 'prices', 'price', 'contact_email', 'whatsapp',
                                   'instagram', 'tiktok', 'facebook', 'hours', 'phone', 'email'})

_pk_seq             =   [0]


def _next_pk():
    _pk_seq[0] += 1
    return _pk_seq[0]


def _grant(plan, code, value = None, kind = Benefit.FLAG):
    benefit =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': kind})[0]
    if benefit.kind != kind:
        benefit.kind    =   kind
        benefit.save(update_fields = ['kind'])
    PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True, value = value)


def _make_account(*benefit_codes, limits = None, slug = 'mi-tienda'):
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
        _grant(plan, code)
    for code, value in (limits or {}).items():
        _grant(plan, code, value = value, kind = Benefit.LIMIT)
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


def _jpeg_upload(size = (800, 600), quality = 95):
    """JPEG de prueba en memoria (ruido: pesa lo suficiente para comparar WebP)."""
    buffer  =   BytesIO()
    Image.effect_noise(size, 120).convert('RGB').save(buffer, format = 'JPEG', quality = quality)
    body    =   buffer.getvalue()
    return SimpleUploadedFile('foto.jpg', body, content_type = 'image/jpeg'), body


class _AiDesignBase(TestCase):
    """Cliente autenticado + URLs del router (nunca paths sueltos)."""

    def setUp(self):
        #plan_benefits_of cachea por PK y SQLite reutiliza PKs entre tests.
        cache.clear()
        self.base_url   =   reverse('Stores-list')
        self.gen_url    =   f'{self.base_url}ai-design/'
        self.apply_url  =   f'{self.base_url}ai-design/apply/'
        self.image_url  =   f'{self.base_url}ai-design/image/'

    def _client(self, *codes, limits = None):
        user, profile, store    =   _make_account(*codes, limits = limits)
        client                  =   APIClient()
        client.force_authenticate(user = user)
        return client, profile, store

    def _premium_client(self, limits = None):
        return self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED),
                            limits = PREMIUM_LIMITS if limits is None else limits)

    def _generate(self, client, **payload):
        body    =   {'rubro': 'comercio', 'goals': ['vender_online'], 'tone': 'moderno',
                     'audience': 'clientes del barrio', 'must_have': ['catálogo'], **payload}
        return client.post(self.gen_url, body, format = 'json')

    def _first_proposal(self, client):
        body    =   self._generate(client).json()
        return body['seed'], body['proposals'][0]['id']


#=========================================
# GENERACIÓN
#=========================================
class AiDesignGenerationTests(_AiDesignBase):
    """Forma de la respuesta v2: motor, propuestas, layout saneado y copy acotado."""

    def test_returns_between_two_and_three_proposals(self):
        client, _, _    =   self._premium_client()
        response        =   self._generate(client)
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn(len(_proposals_of(response)), (2, 3))

    def test_response_reports_engine_v2_seed_and_missing(self):
        client, _, _    =   self._premium_client()
        body            =   self._generate(client).json()
        self.assertEqual(body['engine'], 'ai-design/2')
        self.assertIsInstance(body['seed'], int)
        self.assertIsInstance(body['missing'], list)

    def test_proposal_ids_are_unique_and_labels_distinct(self):
        client, _, _    =   self._premium_client()
        proposals       =   _proposals_of(self._generate(client))
        ids             =   [p['id'] for p in proposals]
        labels          =   [p['label'] for p in proposals]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(labels), len(set(labels)))

    def test_every_proposal_declares_label_why_notes_and_copy_draft(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertTrue(proposal['label'])
            self.assertLessEqual(len(proposal['label']), 32)
            self.assertTrue(proposal['why'])
            self.assertLessEqual(len(proposal['why']), 160)
            self.assertIsInstance(proposal['notes'], list)
            self.assertTrue(all(isinstance(note, str) for note in proposal['notes']))
            self.assertIsInstance(proposal['copy_draft'], dict)
            self.assertIsInstance(proposal['image_requests'], list)

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

    def test_block_ids_belong_to_the_template_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for surface, value in proposal['layout_config'].items():
                for block in value['blocks']:
                    self.assertIn(block['id'], TEMPLATE_BLOCKS[surface])

    def test_locked_blocks_are_always_enabled(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for surface, value in proposal['layout_config'].items():
                for block in value['blocks']:
                    if TEMPLATE_BLOCKS[surface][block['id']].get('locked'):
                        self.assertTrue(block['enabled'], f'{surface}.{block["id"]} locked apagado')

    def test_premium_blocks_are_omitted_without_design_advanced(self):
        client, _, _    =   self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS))
        for proposal in _proposals_of(self._generate(client)):
            for surface, value in proposal['layout_config'].items():
                for block in value['blocks']:
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
            for surface, value in proposal['layout_config'].items():
                for block in value['blocks']:
                    if block['id'] in gated.get(surface, frozenset()) and not TEMPLATE_BLOCKS[surface][block['id']].get('locked'):
                        self.assertFalse(block['enabled'], f'{surface}.{block["id"]} sin datos pero enabled=true')

    def test_layout_config_is_idempotent_under_the_sanitizer(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertEqual(
                clean_layout_config(proposal['layout_config'], True),
                proposal['layout_config'],
            )

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
# MISSING (qué datos faltan, como objetos accionables)
#=========================================
class AiDesignMissingTests(_AiDesignBase):
    """`missing` es [{code,label,hint,action}] y refleja los datos reales."""

    def _missing(self, client):
        body    =   self._generate(client).json()
        return body['missing']

    def test_missing_items_are_actionable_objects(self):
        client, _, _    =   self._premium_client()
        items           =   self._missing(client)
        self.assertIsInstance(items, list)
        self.assertTrue(items, 'tienda vacía: debería reportar faltantes')
        codes           =   [item['code'] for item in items]
        self.assertEqual(len(codes), len(set(codes)))
        for item in items:
            self.assertEqual(set(item), {'code', 'label', 'hint', 'action'})
            for key in ('code', 'label', 'hint', 'action'):
                self.assertIsInstance(item[key], str, key)
            self.assertTrue(item['code'])
            self.assertTrue(item['label'])
            self.assertTrue(item['action'])

    def test_missing_drops_entries_once_the_data_exists(self):
        client, _, store    =   self._premium_client()
        customization       =   StoreCustomization.objects.get_or_create(store = store)[0]
        self.assertIn('about', [item['code'] for item in self._missing(client)])
        customization.about_text    =   'Somos un taller de barrio con veinte años de oficio.'
        customization.save(update_fields = ['about_text'])
        self.assertNotIn('about', [item['code'] for item in self._missing(client)])


#=========================================
# COPY DRAFT (borradores de datos del negocio, acotados)
#=========================================
class AiDesignCopyDraftTests(_AiDesignBase):
    """copy_draft respeta topes y NUNCA inventa testimonios, cifras ni contacto."""

    def _drafts(self, client):
        return [proposal['copy_draft'] for proposal in _proposals_of(self._generate(client))]

    def test_draft_only_uses_allowed_business_keys(self):
        client, _, _    =   self._premium_client()
        for draft in self._drafts(client):
            self.assertTrue(set(draft).issubset(DRAFT_KEYS), set(draft) - DRAFT_KEYS)
            self.assertFalse(set(draft) & DRAFT_FORBIDDEN)

    def test_draft_respects_the_text_limits(self):
        client, _, _    =   self._premium_client()
        for draft in self._drafts(client):
            self.assertLessEqual(len(draft.get('about_text', '')), DRAFT_MAX['about_text'])
            self.assertLessEqual(len(draft.get('about_mission', '')), DRAFT_MAX['about_mission'])
            for row in draft.get('faqs', []):
                self.assertEqual(set(row), {'q', 'a'})
                self.assertLessEqual(len(row['q']), FAQ_Q_MAX)
                self.assertLessEqual(len(row['a']), FAQ_A_MAX)
            for row in draft.get('services', []):
                self.assertEqual(set(row), {'name', 'desc'})
                self.assertLessEqual(len(row['name']), SERVICE_NAME_MAX)
                self.assertLessEqual(len(row['desc']), SERVICE_DESC_MAX)
            for row in draft.get('steps', []):
                self.assertEqual(set(row), {'title', 'desc'})
                self.assertLessEqual(len(row['title']), STEP_TITLE_MAX)
                self.assertLessEqual(len(row['desc']), STEP_DESC_MAX)
            for row in draft.get('announcements', []):
                self.assertEqual(set(row), {'text'})
                self.assertLessEqual(len(row['text']), ANNOUNCEMENT_MAX)

    def test_draft_skips_fields_the_owner_already_filled(self):
        client, _, store    =   self._premium_client()
        StoreCustomization.objects.create(
            store       =   store,
            about_text  =   'Mi historia real',
            services    =   [{'title': 'Corte', 'text': 'Con turno'}],
        )
        for draft in self._drafts(client):
            self.assertNotIn('about_text', draft)
            self.assertNotIn('services', draft)


#=========================================
# IMAGE REQUESTS (pedido de fotos)
#=========================================
class AiDesignImageRequestsTests(_AiDesignBase):
    """Los pedidos de fotos declaran target cerrado y una cantidad razonable."""

    def _requests(self, client):
        return [item for proposal in _proposals_of(self._generate(client))
                for item in proposal['image_requests']]

    def test_requests_declare_closed_target_and_min_count(self):
        client, _, _    =   self._premium_client()
        requests        =   self._requests(client)
        self.assertTrue(requests, 'tienda sin fotos: debería pedir imágenes')
        for item in requests:
            self.assertIn(item['target'], ('cover', 'gallery'))
            self.assertGreaterEqual(item['min_count'], 2)
            self.assertLessEqual(item['min_count'], 4)
            self.assertTrue(item['id'])
            self.assertTrue(item['label'])
            self.assertTrue(item['hint'])

    def test_no_requests_when_the_store_already_has_photos(self):
        client, _, store    =   self._premium_client()
        StoreGalleryImage.objects.create(store = store, image_key = 'stores/x/gallery/a.webp', image_size = 10, position = 0)
        for proposal in _proposals_of(self._generate(client)):
            self.assertEqual(proposal['image_requests'], [])


#=========================================
# APPLY / AUTOFILL
#=========================================
class AiDesignApplyTests(_AiDesignBase):
    """apply escribe el borrador; autofill rellena SOLO campos de negocio vacíos."""

    def _apply(self, client, seed, proposal_id, **extra):
        return client.post(self.apply_url, {'seed': seed, 'proposal_id': proposal_id, **extra}, format = 'json')

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

    def test_apply_without_autofill_leaves_business_fields_untouched(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.about_text, '')
        self.assertEqual(customization.about_mission, '')
        self.assertEqual(customization.faqs, [])
        self.assertEqual(customization.services, [])
        self.assertEqual(customization.service_steps, [])
        self.assertEqual(customization.announcements, [])

    def test_autofill_false_behaves_like_absent(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid, autofill = False).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.about_text, '')
        self.assertEqual(customization.faqs, [])
        self.assertEqual(customization.services, [])

    def test_autofill_true_fills_only_empty_business_fields(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid, autofill = True).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertTrue(customization.about_text)
        self.assertLessEqual(len(customization.about_text), DRAFT_MAX['about_text'])
        self.assertTrue(customization.about_mission)
        self.assertTrue(customization.faqs)
        self.assertEqual(set(customization.faqs[0]), {'q', 'a'})
        self.assertTrue(customization.services)
        self.assertEqual(set(customization.services[0]), {'icon', 'title', 'text'})
        self.assertTrue(customization.service_steps)
        self.assertEqual(set(customization.service_steps[0]), {'icon', 'title', 'text'})
        self.assertTrue(customization.announcements)
        self.assertEqual(set(customization.announcements[0]), {'icon', 'text'})
        #Datos que el motor no puede inventar: siguen vacíos.
        self.assertEqual(customization.testimonials, [])
        self.assertEqual(customization.stats, [])
        self.assertEqual(customization.contact_email, '')
        self.assertEqual(customization.whatsapp, '')
        self.assertEqual(customization.hours, [])

    def test_autofill_never_overwrites_content_written_by_the_owner(self):
        client, profile, store  =   self._premium_client()
        services                =   [{'icon': 'scissors', 'title': 'Corte', 'text': 'Con turno'}]
        faqs                    =   [{'q': '¿Abren?', 'a': 'Sí'}]
        steps                   =   [{'icon': 'check', 'title': 'Reservá', 'text': 'Por WhatsApp'}]
        announcements           =   [{'icon': 'megaphone', 'text': 'Cerramos el lunes'}]
        stats                   =   [{'value': '10', 'label': 'años'}]
        testimonials            =   [{'name': 'Ana', 'text': 'Genial'}]
        hours                   =   [{'label': 'Lun a vie', 'value': '9 a 18'}]
        StoreCustomization.objects.create(
            store           =   store,
            headline        =   'Mi titular',
            description     =   'Mi descripción',
            about_text      =   'Mi historia',
            about_mission   =   'Mi misión',
            cta_title       =   'Mi cierre',
            cta_text        =   'Texto del cierre',
            cta_label       =   'Escribinos',
            services        =   services,
            faqs            =   faqs,
            service_steps   =   steps,
            announcements   =   announcements,
            stats           =   stats,
            testimonials    =   testimonials,
            hours           =   hours,
            contact_email   =   'hola@mitienda.com',
            whatsapp        =   '5491112345678',
        )
        seed, pid       =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid, autofill = True).status_code, 200)
        customization   =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.headline, 'Mi titular')
        self.assertEqual(customization.description, 'Mi descripción')
        self.assertEqual(customization.about_text, 'Mi historia')
        self.assertEqual(customization.about_mission, 'Mi misión')
        self.assertEqual(customization.cta_title, 'Mi cierre')
        self.assertEqual(customization.cta_text, 'Texto del cierre')
        self.assertEqual(customization.cta_label, 'Escribinos')
        self.assertEqual(customization.services, services)
        self.assertEqual(customization.faqs, faqs)
        self.assertEqual(customization.service_steps, steps)
        self.assertEqual(customization.announcements, announcements)
        self.assertEqual(customization.stats, stats)
        self.assertEqual(customization.testimonials, testimonials)
        self.assertEqual(customization.hours, hours)
        self.assertEqual(customization.contact_email, 'hola@mitienda.com')
        self.assertEqual(customization.whatsapp, '5491112345678')

    def test_unknown_proposal_id_is_rejected(self):
        client, _, _    =   self._premium_client()
        seed, _         =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, 'no-existe').status_code, 400)

    def test_apply_is_idempotent_for_the_same_seed_and_proposal(self):
        #Sin autofill: el autofill cambia los datos del negocio y, por diseño,
        #el motor recalcula distinto con datos nuevos. La idempotencia del
        #contrato es sobre el mismo {seed, proposal_id} sin mutar el negocio.
        client, _, _    =   self._premium_client()
        seed, pid       =   self._first_proposal(client)
        first           =   self._apply(client, seed, pid).json()['customization']
        second          =   self._apply(client, seed, pid).json()['customization']
        for field in ('layout_config_draft', 'site_theme_draft', 'template_draft', 'headline',
                      'description', 'cta_title', 'cta_text', 'cta_label'):
            self.assertEqual(first.get(field), second.get(field), field)


#=========================================
# IMÁGENES (upload del pedido de fotos)
#=========================================
class AiDesignImageTests(_AiDesignBase):
    """La foto se normaliza a WebP, entra a la galería y respeta cupo/throttle."""

    def _upload(self, client, request_id = 'local', upload = None):
        if upload is None:
            upload, _ = _jpeg_upload()
        return client.post(self.image_url, {'image': upload, 'request_id': request_id}, format = 'multipart')

    @staticmethod
    def _local_storage():
        #En la máquina de QA hay credenciales R2: forzamos MEDIA_ROOT para no
        #escribir objetos reales en el bucket desde la suite.
        return patch('StoreApp.domains.stores.services.storage.storage_configured', return_value = False)

    def test_upload_stores_a_webp_gallery_image(self):
        client, _, store    =   self._premium_client()
        upload, original    =   _jpeg_upload()
        with self._local_storage():
            response        =   self._upload(client, upload = upload)
        self.assertEqual(response.status_code, 200, response.content[:400])
        body                =   response.json()
        self.assertIn('Exito', body)
        self.assertIn('image', body)
        self.assertEqual(body['gallery']['count'], 1)
        image               =   StoreGalleryImage.objects.get(pk = body['image']['id'])
        self.assertEqual(image.store, store)
        self.assertEqual(image.kind, StoreGalleryImage.KIND_GALLERY)
        self.assertTrue(image.image_key.endswith('.webp'), image.image_key)
        from django.core.files.storage import default_storage
        try:
            stored  =   default_storage.open(image.image_key, 'rb').read()
        finally:
            default_storage.delete(image.image_key)
        self.assertTrue(stored.startswith(b'RIFF') and stored[8:12] == b'WEBP')
        self.assertLess(len(stored), len(original), 'el WebP debería pesar menos que el JPEG original')

    def test_invalid_file_is_rejected(self):
        client, _, _    =   self._premium_client()
        upload          =   SimpleUploadedFile('foto.jpg', b'esto no es una imagen', content_type = 'image/jpeg')
        self.assertEqual(self._upload(client, upload = upload).status_code, 400)

    def test_upload_is_rejected_when_the_plan_has_no_storage(self):
        limits          =   {'max_gallery_images': 20, 'max_images': 50, 'max_storage_mb': 0}
        client, _, store    =   self._client(*(CUSTOMIZATION + AI_DESIGN), limits = limits)
        self.assertEqual(self._upload(client).status_code, 400)
        self.assertEqual(StoreGalleryImage.objects.filter(store = store).count(), 0)

    def test_upload_requires_the_ai_design_flag(self):
        client, _, _    =   self._client(*CUSTOMIZATION, limits = PREMIUM_LIMITS)
        self.assertEqual(self._upload(client).status_code, 403)

    def test_upload_requires_authentication(self):
        upload, _       =   _jpeg_upload()
        response        =   APIClient().post(self.image_url, {'image': upload}, format = 'multipart')
        self.assertIn(response.status_code, (401, 403))

    def test_upload_is_throttled(self):
        cache.clear()
        client, _, _    =   self._premium_client()
        #Archivo inválido: corta en validación (sin tocar storage) pero el
        #throttle corre antes, así que el request igual consume cupo.
        upload          =   SimpleUploadedFile('foto.jpg', b'no es imagen', content_type = 'image/jpeg')
        for index in range(60):
            response    =   self._upload(client, request_id = 'x', upload = upload)
            self.assertEqual(response.status_code, 400, f'call {index + 1}: {response.content[:200]}')
        self.assertEqual(self._upload(client, request_id = 'x', upload = upload).status_code, 429)


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

    def test_apply_forbidden_without_ai_design_flag(self):
        client, _, _    =   self._client(*CUSTOMIZATION)
        response        =   client.post(self.apply_url, {'seed': 1, 'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_requires_authentication(self):
        response    =   APIClient().post(self.gen_url, {}, format = 'json')
        self.assertIn(response.status_code, (401, 403))

    def test_generation_is_throttled_after_twenty_calls(self):
        cache.clear()
        client, _, _    =   self._premium_client()
        for index in range(20):
            response    =   self._generate(client)
            self.assertEqual(response.status_code, 200, f'call {index + 1}: {response.content[:200]}')
        self.assertEqual(self._generate(client).status_code, 429)


#=========================================
# DETERMINISMO
#=========================================
class AiDesignDeterminismTests(_AiDesignBase):
    """Misma entrada => mismo JSON; el motor es local (cero red saliente)."""

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

    def test_generation_makes_no_outbound_network_calls(self):
        client, _, _    =   self._premium_client()
        with patch.object(socket, 'create_connection', side_effect = AssertionError('llamada de red saliente')):
            response    =   self._generate(client)
        self.assertEqual(response.status_code, 200, response.content[:400])


#=========================================
# PLANTILLAS EXCLUSIVAS DE IA
#=========================================
class AiDesignTemplatesTests(_AiDesignBase):
    """ai_lumen/ai_pulse solo con has_ai_design, y la web pública los respeta."""

    def test_ai_templates_are_allowed_only_with_the_flag(self):
        _, profile_with, _      =   _make_account(*(CUSTOMIZATION + AI_DESIGN))
        _, profile_without, _   =   _make_account(*CUSTOMIZATION)
        allowed_with            =   set(allowed_templates_of(profile_with))
        allowed_without         =   set(allowed_templates_of(profile_without))
        self.assertIn('ai_lumen', allowed_with)
        self.assertIn('ai_pulse', allowed_with)
        self.assertNotIn('ai_lumen', allowed_without)
        self.assertNotIn('ai_pulse', allowed_without)

    def test_public_page_renders_the_ai_template_instead_of_falling_back(self):
        client, profile, store  =   self._client(*(PUBLIC_LINK + CUSTOMIZATION + AI_DESIGN))
        store.is_published      =   True
        store.save(update_fields = ['is_published'])
        StoreCustomization.objects.create(store = store, template = 'ai_lumen')
        response                =   APIClient().get(reverse('Stores-public', kwargs = {'slug': store.slug}))
        self.assertEqual(response.status_code, 200, response.content[:400])
        body                    =   response.json()
        self.assertEqual(body['customization']['template'], 'ai_lumen')
        self.assertIn('ai_lumen', body['allowed_templates'])
