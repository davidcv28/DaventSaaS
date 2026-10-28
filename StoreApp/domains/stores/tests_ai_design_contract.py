"""
Suite de CONTRATO v3 del motor de diseño con IA ("Diseñar con IA").

Endpoints:
  POST /api/stores/ai-design/          -> propuestas (motor local, determinista)
  POST /api/stores/ai-design/apply/    -> aplica el borrador Y publica
  POST /api/stores/ai-design/image/    -> fotos del pedido (WebP en galería)
  PATCH /api/stores/customization/     -> site_theme (sección `blocks`)

Contrato v3 (engine 'ai-design/3'):
  1) bloques solo-IA (aiquote/aistrip/aicheck/aigrid/aiband) solo con
     has_ai_design + props tipadas saneadas;
  2) color de marca con AA, o paleta elegida por la IA;
  3) modo noche (theme_toggle);
  4) portada con logo;
  5) overrides por contenedor (site_theme.blocks) con rechazo silencioso;
  6) apply publica en un solo paso (layout PUBLICADO + StudioVersion);
  7) web pública con ai_lumen/ai_pulse y hero 'logo';
  8) regresiones v2 (gating, throttle, determinismo, autofill, imágenes).

Esta suite es de QA: no toca código de producción. Si el contrato todavía no
está implementado, los tests fallan (PENDIENTE), no se saltan.
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
from StoreApp.domains.stores.layout_blocks import AI_ICONS, TEMPLATE_BLOCKS, clean_layout_config
from StoreApp.domains.stores.models import (
    Store, StoreCustomization, StoreGalleryImage, StudioVersion,
)
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.services.ai_design import _contrast_ratio
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

#Bloques exclusivos de "Diseñar con IA" (TEMPLATE_BLOCKS[*]['ai_only']).
AI_ONLY_BLOCKS      =   frozenset({'aiquote', 'aistrip', 'aicheck', 'aigrid', 'aiband'})
AI_BLOCK_STYLE_KEYS =   frozenset({'radius', 'shadow', 'border', 'density', 'surface', 'align', 'accent'})

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


def _landing_blocks(proposal):
    return proposal['layout_config']['landing']['blocks']


def _block_of(proposal, block_id):
    return next(block for block in _landing_blocks(proposal) if block['id'] == block_id)


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
        self.custom_url =   f'{self.base_url}customization/'

    def _client(self, *codes, limits = None):
        user, profile, store    =   _make_account(*codes, limits = limits)
        client                  =   APIClient()
        client.force_authenticate(user = user)
        return client, profile, store

    def _premium_client(self, limits = None):
        return self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED),
                            limits = PREMIUM_LIMITS if limits is None else limits)

    def _generate(self, client, payload = None):
        body    =   {'rubro': 'comercio', 'goals': ['vender_online'], 'tone': 'moderno',
                     'audience': 'clientes del barrio', 'must_have': ['catálogo']}
        body.update(payload or {})
        return client.post(self.gen_url, body, format = 'json')

    def _first_proposal(self, client, payload = None):
        body    =   self._generate(client, payload).json()
        return body['seed'], body['proposals'][0]['id']

    def _apply(self, client, seed, proposal_id, **extra):
        return client.post(self.apply_url, {'seed': seed, 'proposal_id': proposal_id, **extra}, format = 'json')


#=========================================
# 1) ELEMENTOS SOLO-IA
#=========================================
class ElementosIA(_AiDesignBase):
    """Los bloques ai_only existen solo con has_ai_design y salen saneados."""

    #Entrevista que dispara varios elementos: confianza (aiquote),
    #precios (aicheck), servicios (aigrid) y datos de contacto (aistrip).
    ELEMENTS_PAYLOAD =   {'rubro': 'belleza', 'tone': 'moderno',
                          'goals': ['dar_confianza', 'mostrar_servicios'],
                          'must_have': ['offers', 'contact', 'faq']}

    def test_engine_reports_v3(self):
        client, _, _    =   self._premium_client()
        body            =   self._generate(client).json()
        self.assertEqual(body['engine'], 'ai-design/3')

    def test_ai_only_blocks_appear_with_the_flag(self):
        client, _, _    =   self._premium_client()
        proposals       =   _proposals_of(self._generate(client, self.ELEMENTS_PAYLOAD))
        self.assertIn(len(proposals), (2, 3))
        for proposal in proposals:
            ids     =   {block['id'] for block in _landing_blocks(proposal)}
            self.assertTrue(ids & AI_ONLY_BLOCKS, 'sin bloques solo-IA en la propuesta')
            self.assertTrue(ids & {'aiquote', 'aigrid'}, ids)

    def test_ai_only_blocks_never_survive_without_the_flag(self):
        #El saneador es el punto único de descarte (editor + motor).
        layout  =   {'landing': {'blocks': [{'id': block_id, 'enabled': True} for block_id in sorted(AI_ONLY_BLOCKS)]}}
        self.assertEqual(clean_layout_config(layout, True), {})
        self.assertTrue(clean_layout_config(layout, True, True)['landing']['blocks'])

    def test_generation_never_returns_ai_blocks_for_a_plan_without_the_flag(self):
        #Sin has_ai_design el endpoint está cerrado (403): no hay forma de
        #recibir bloques ai_only. La whitelist del PATCH también los descarta.
        client, _, store    =   self._client(*(CUSTOMIZATION + DESIGN_PLUS + DESIGN_ADVANCED))
        self.assertEqual(self._generate(client, self.ELEMENTS_PAYLOAD).status_code, 403)
        response            =   client.patch(
            self.custom_url,
            {'layout_config': {'landing': {'blocks': [{'id': 'aiquote', 'enabled': True}]}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        store.refresh_from_db()
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertNotIn('aiquote', json.dumps(customization.layout_config))

    def test_every_ai_block_uses_the_catalog_variant_and_props(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, self.ELEMENTS_PAYLOAD)):
            for block in _landing_blocks(proposal):
                if block['id'] not in AI_ONLY_BLOCKS:
                    continue
                spec    =   TEMPLATE_BLOCKS['landing'][block['id']]
                self.assertTrue(spec.get('ai_only'), block['id'])
                if block.get('variant'):
                    self.assertIn(block['variant'], spec['variants'])
                for key in (block.get('props') or {}):
                    self.assertIn(key, spec['props'], f'{block["id"]}.{key} fuera del catálogo')

    def test_ai_elements_respect_the_maximum_of_three(self):
        client, _, _    =   self._premium_client()
        payload         =   dict(self.ELEMENTS_PAYLOAD)
        payload['must_have'] = ['offers', 'contact', 'faq', 'benefits']
        for proposal in _proposals_of(self._generate(client, payload)):
            ai_ids  =   [block['id'] for block in _landing_blocks(proposal) if block['id'] in AI_ONLY_BLOCKS]
            self.assertLessEqual(len(ai_ids), 3, ai_ids)
            self.assertEqual(len(ai_ids), len(set(ai_ids)))

    def test_layout_config_is_idempotent_under_the_sanitizer(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, self.ELEMENTS_PAYLOAD)):
            self.assertEqual(
                clean_layout_config(proposal['layout_config'], True, True),
                proposal['layout_config'],
            )


#=========================================
# 2) PROPS TIPADAS SANEADAS
#=========================================
class PropsSaneadas(_AiDesignBase):
    """Iconos del catálogo, textos recortados, listas al tope y sin HTML."""

    def _clean(self, block_id, props, variant = None):
        block   =   {'id': block_id, 'enabled': True, 'props': props}
        if variant:
            block['variant'] =   variant
        clean   =   clean_layout_config({'landing': {'blocks': [block]}}, True, True)
        return clean['landing']['blocks'][0]

    def test_unknown_icon_is_dropped_and_known_icon_kept(self):
        clean   =   self._clean('aistrip', {'items': [
            {'icon': 'no-existe', 'label': 'Sin icono'},
            {'icon': 'coffee', 'label': 'Con icono'},
        ]})
        items   =   clean['props']['items']
        self.assertNotIn('icon', items[0])
        self.assertEqual(items[1]['icon'], 'coffee')

    def test_texts_are_truncated_to_their_caps(self):
        clean   =   self._clean('aiquote', {'text': 'x' * 400, 'author': 'a' * 120})
        self.assertEqual(len(clean['props']['text']), 160)
        self.assertEqual(len(clean['props']['author']), 40)
        clean   =   self._clean('aiband', {'title': 't' * 200, 'text': 'x' * 400, 'label': 'l' * 120})
        self.assertEqual(len(clean['props']['title']), 80)
        self.assertEqual(len(clean['props']['text']), 160)
        self.assertEqual(len(clean['props']['label']), 40)

    def test_lists_are_truncated_to_their_maximum(self):
        strip   =   self._clean('aistrip', {'items': [{'label': f'Item {i}'} for i in range(8)]})
        self.assertEqual(len(strip['props']['items']), 4)
        check   =   self._clean('aicheck', {'items': [{'text': f'Item {i}'} for i in range(9)]})
        self.assertEqual(len(check['props']['items']), 6)
        grid    =   self._clean('aigrid', {'items': [{'title': f'Item {i}'} for i in range(9)]})
        self.assertEqual(len(grid['props']['items']), 6)

    def test_non_dict_items_are_discarded(self):
        clean   =   self._clean('aicheck', {'items': ['texto suelto', 42, None, {'text': 'Válido'}]})
        self.assertEqual(clean['props']['items'], [{'text': 'Válido'}])
        clean   =   self._clean('aigrid', {'items': ['x', {'title': 'Válido'}]})
        self.assertEqual(clean['props']['items'], [{'title': 'Válido'}])

    def test_item_fields_are_truncated(self):
        clean   =   self._clean('aigrid', {'items': [{'title': 't' * 100, 'text': 'x' * 300}]})
        item    =   clean['props']['items'][0]
        self.assertEqual(len(item['title']), 40)
        self.assertEqual(len(item['text']), 90)

    def test_no_html_in_any_value(self):
        clean   =   self._clean('aiquote', {
            'text': '<b>Hola</b><script>alert(1)</script>',
            'author': '<i>Ana</i>',
        })
        dumped  =   json.dumps(clean['props'])
        self.assertNotIn('<', dumped)
        self.assertNotIn('>', dumped)
        clean   =   self._clean('aigrid', {'items': [{'title': '<b>T</b>', 'text': '<img src=x>'}]})
        dumped  =   json.dumps(clean['props'])
        self.assertNotIn('<', dumped)
        self.assertNotIn('>', dumped)

    def test_unknown_props_and_variants_are_dropped(self):
        clean   =   self._clean('aiquote', {'text': 'Hola', 'inventado': 'x'}, variant = 'diagonal')
        self.assertEqual(clean['props'], {'text': 'Hola'})
        self.assertNotIn('variant', clean)
        clean   =   self._clean('aiquote', {'text': 'Hola'}, variant = 'split')
        self.assertEqual(clean['variant'], 'split')

    def test_block_without_usable_props_has_no_props_key(self):
        clean   =   self._clean('aicheck', {'items': [], 'title': '<b></b>'})
        self.assertNotIn('props', clean)

    def test_every_ai_icon_in_the_catalog_is_accepted(self):
        clean   =   self._clean('aistrip', {'items': [
            {'icon': icon, 'label': f'Item {index}'} for index, icon in enumerate(sorted(AI_ICONS))
        ][:4]})
        for item in clean['props']['items']:
            self.assertIn(item['icon'], AI_ICONS)

    def test_generated_props_are_already_sane(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, ElementosIA.ELEMENTS_PAYLOAD)):
            for block in _landing_blocks(proposal):
                if block['id'] not in AI_ONLY_BLOCKS or not block.get('props'):
                    continue
                dumped  =   json.dumps(block['props'])
                self.assertNotIn('<', dumped)
                self.assertNotIn('>', dumped)
                if block['id'] == 'aiquote':
                    self.assertLessEqual(len(block['props'].get('text', '')), 160)
                    self.assertLessEqual(len(block['props'].get('author', '')), 40)


#=========================================
# 3) COLOR DE MARCA
#=========================================
class Color(_AiDesignBase):
    """brand_color válido manda (con AA); inválido se ignora."""

    BRAND   =   '#1d4ed8'

    def _proposals(self, payload):
        client, _, _    =   self._premium_client()
        return _proposals_of(self._generate(client, payload))

    def test_valid_brand_color_sets_the_palette_accent(self):
        #El color del dueño manda: accent == brand siempre que el hex ya
        #cumpla AA sobre el fondo del look. Si no (look oscuro), el motor lo
        #aclara para no romper AA — el source sigue siendo 'user'.
        for proposal in self._proposals({'brand_color': self.BRAND}):
            palette =   proposal['site_theme']['palette']
            choice  =   proposal['theme_choice']
            self.assertEqual(choice['source'], 'user')
            self.assertEqual(palette['accent'], choice['accent'])
            if _contrast_ratio(self.BRAND, palette['bg']) >= 4.5:
                self.assertEqual(choice['accent'], self.BRAND)
            else:
                self.assertGreaterEqual(_contrast_ratio(choice['accent'], palette['bg']), 4.5)

    def test_brand_color_is_normalized_to_lowercase_hex(self):
        from StoreApp.domains.stores.services.ai_design import _norm_hex
        self.assertEqual(_norm_hex('#1D4ED8'), '#1d4ed8')
        self.assertEqual(_norm_hex('#1D4ED8'), self.BRAND)
        for proposal in self._proposals({'brand_color': '#1D4ED8'}):
            self.assertEqual(proposal['theme_choice']['accent'],
                             proposal['site_theme']['palette']['accent'])
            self.assertRegex(proposal['theme_choice']['accent'], r'^#[0-9a-f]{6}$')

    def test_accent_has_aa_against_the_page_background(self):
        for proposal in self._proposals({'brand_color': self.BRAND}):
            palette =   proposal['site_theme']['palette']
            self.assertGreaterEqual(_contrast_ratio(palette['accent'], palette['bg']), 4.5, palette)

    def test_low_contrast_brand_color_is_adjusted_but_keeps_the_user_source(self):
        #Contrato: el color manda SIEMPRE que no rompa AA. Si el hex crudo no
        #alcanza sobre el fondo del look, el motor lo corrige (documentado en
        #_palette_from_brand) y sigue declarando source='user'.
        brand = '#ffff00'
        for proposal in self._proposals({'brand_color': brand}):
            palette =   proposal['site_theme']['palette']
            self.assertEqual(proposal['theme_choice']['source'], 'user')
            self.assertGreaterEqual(_contrast_ratio(palette['accent'], palette['bg']), 4.5)

    def test_invalid_brand_color_is_ignored(self):
        for brand in ('rojo', '#zzzzzz', 'url(x)', '#12345', 'rgb(0,0,0)'):
            for proposal in self._proposals({'brand_color': brand}):
                self.assertEqual(proposal['theme_choice']['source'], 'ai', brand)
                self.assertRegex(proposal['theme_choice']['accent'], r'^#[0-9a-f]{6}$')

    def test_without_brand_color_the_ai_chooses(self):
        for proposal in self._proposals({'brand_color': ''}):
            self.assertEqual(proposal['theme_choice']['source'], 'ai')

    def test_ai_choice_accent_is_aa_on_the_background(self):
        for proposal in self._proposals({}):
            palette =   proposal['site_theme']['palette']
            self.assertGreaterEqual(_contrast_ratio(palette['accent'], palette['bg']), 4.5, palette)


#=========================================
# 4) MODO NOCHE
#=========================================
class ModoNoche(_AiDesignBase):
    """night_mode.enabled => theme_toggle en la web + default respetado."""

    def test_enabled_dark_sets_theme_and_toggle(self):
        client, _, store    =   self._premium_client()
        proposals           =   _proposals_of(self._generate(
            client, {'night_mode': {'enabled': True, 'default': 'dark'}}))
        for proposal in proposals:
            self.assertEqual(proposal['night_mode'], {'enabled': True, 'default': 'dark'})
            self.assertEqual(proposal['theme'], 'dark')
            self.assertTrue(proposal['theme_toggle'])
        seed    =   self._generate(client, {'night_mode': {'enabled': True, 'default': 'dark'}}).json()['seed']
        self.assertEqual(self._apply(client, seed, proposals[0]['id']).status_code, 200)
        customization   =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.theme, 'dark')
        self.assertTrue(customization.theme_toggle)

    def test_enabled_light_keeps_light_default(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(
                client, {'night_mode': {'enabled': True, 'default': 'light'}})):
            self.assertEqual(proposal['theme'], 'light')
            self.assertTrue(proposal['theme_toggle'])
            self.assertEqual(proposal['night_mode'], {'enabled': True, 'default': 'light'})

    def test_disabled_keeps_the_toggle_off(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(
                client, {'night_mode': {'enabled': False, 'default': 'dark'}})):
            self.assertFalse(proposal['theme_toggle'])
            self.assertFalse(proposal['night_mode']['enabled'])
            self.assertIn(proposal['theme'], ('light', 'dark'))

    def test_absent_night_mode_keeps_the_toggle_off(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertFalse(proposal['theme_toggle'])
            self.assertFalse(proposal['night_mode']['enabled'])

    def test_invalid_night_mode_values_fall_back(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(
                client, {'night_mode': {'enabled': 'sí', 'default': 'sepia'}})):
            self.assertFalse(proposal['theme_toggle'])
            self.assertIn(proposal['night_mode']['default'], ('light', 'dark'))

    def test_apply_persists_theme_toggle(self):
        client, _, store    =   self._premium_client()
        body                =   self._generate(client, {'night_mode': {'enabled': True, 'default': 'dark'}}).json()
        self.assertEqual(self._apply(client, body['seed'], body['proposals'][0]['id']).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertTrue(customization.theme_toggle)
        self.assertEqual(customization.theme, 'dark')


#=========================================
# 5) PORTADA CON LOGO
#=========================================
class Portada(_AiDesignBase):
    """cover_choice 'logo' (o 'auto' sin foto + con logo) => hero logo."""

    def _with_logo(self, client, store):
        customization           =   StoreCustomization.objects.get_or_create(store = store)[0]
        customization.logo_key  =   'stores/x/logo.webp'
        customization.save(update_fields = ['logo_key'])
        return customization

    def test_logo_choice_uses_logo_hero_and_solid_background(self):
        client, _, store    =   self._premium_client()
        self._with_logo(client, store)
        proposals           =   _proposals_of(self._generate(client, {'cover_choice': 'logo'}))
        for proposal in proposals:
            self.assertEqual(proposal['cover']['mode'], 'logo')
            self.assertEqual(_block_of(proposal, 'hero')['variant'], 'logo')
            self.assertNotEqual(proposal['site_theme']['background']['type'], 'image')

    def test_auto_with_logo_and_without_cover_also_uses_the_logo(self):
        client, _, store    =   self._premium_client()
        self._with_logo(client, store)
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'auto'})):
            self.assertEqual(proposal['cover']['mode'], 'logo')
            self.assertEqual(_block_of(proposal, 'hero')['variant'], 'logo')
            self.assertNotEqual(proposal['site_theme']['background']['type'], 'image')

    def test_auto_with_cover_photo_keeps_the_photo(self):
        client, _, store    =   self._premium_client()
        customization       =   self._with_logo(client, store)
        customization.cover_key =   'stores/x/cover.webp'
        customization.save(update_fields = ['cover_key'])
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'auto'})):
            self.assertEqual(proposal['cover']['mode'], 'photo')
            self.assertNotEqual(_block_of(proposal, 'hero').get('variant'), 'logo')

    def test_photo_choice_ignores_the_logo(self):
        client, _, store    =   self._premium_client()
        self._with_logo(client, store)
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'foto'})):
            self.assertEqual(proposal['cover']['mode'], 'photo')
            self.assertNotEqual(_block_of(proposal, 'hero').get('variant'), 'logo')

    def test_public_page_serves_the_logo_hero(self):
        client, profile, store  =   self._client(*(PUBLIC_LINK + CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED))
        store.is_published      =   True
        store.save(update_fields = ['is_published'])
        StoreCustomization.objects.create(
            store           =   store,
            template        =   'ai_lumen',
            layout_config   =   {'landing': {'blocks': [
                {'id': 'hero', 'enabled': True, 'order': 0, 'variant': 'logo'},
                {'id': 'contact', 'enabled': True, 'order': 1},
            ]}},
        )
        response                =   APIClient().get(reverse('Stores-public', kwargs = {'slug': store.slug}))
        self.assertEqual(response.status_code, 200, response.content[:400])
        body                    =   response.json()
        self.assertEqual(body['customization']['template'], 'ai_lumen')
        hero                    =   next(
            block for block in body['customization']['layout_config']['landing']['blocks']
            if block['id'] == 'hero'
        )
        self.assertEqual(hero['variant'], 'logo')


#=========================================
# 6) OVERRIDES POR CONTENEDOR (site_theme.blocks)
#=========================================
class BlockOverrides(_AiDesignBase):
    """site_theme.blocks: catálogo cerrado, descarte silencioso y tope de 12."""

    ALL_STYLES  =   {'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'spacious',
                     'surface': 'glass', 'align': 'center', 'accent': '#AABBCC'}

    def test_valid_keys_are_accepted_and_normalized(self):
        clean   =   clean_site_theme({'blocks': {'hero': dict(self.ALL_STYLES)}}, has_advanced = True)
        self.assertEqual(clean, {'blocks': {'hero': {
            'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'spacious',
            'surface': 'glass', 'align': 'center', 'accent': '#aabbcc',
        }}})

    def test_unknown_block_id_is_dropped_silently(self):
        clean   =   clean_site_theme(
            {'blocks': {'inventado': {'radius': 'xl'}, 'hero': {'radius': 'xl'}}},
            has_advanced = True,
        )
        self.assertEqual(clean, {'blocks': {'hero': {'radius': 'xl'}}})

    def test_unknown_key_is_dropped_silently_and_the_rest_survives(self):
        #Contrato: la clave inválida se descarta; el bloque y el tema siguen.
        clean   =   clean_site_theme(
            {'blocks': {'hero': {'radius': 'xl', 'inventado': 'x'}},
             'palette': {'accent': '#123456'}},
            has_advanced = True,
        )
        self.assertEqual(clean['blocks']['hero'], {'radius': 'xl'})
        self.assertEqual(clean['palette'], {'accent': '#123456'})

    def test_invalid_enum_is_dropped_silently(self):
        clean   =   clean_site_theme(
            {'blocks': {'hero': {'align': 'diagonal', 'radius': 'xl'}}},
            has_advanced = True,
        )
        self.assertEqual(clean, {'blocks': {'hero': {'radius': 'xl'}}})

    def test_invalid_hex_is_dropped_silently(self):
        clean   =   clean_site_theme(
            {'blocks': {'hero': {'accent': 'rojo', 'surface': 'glass'}}},
            has_advanced = True,
        )
        self.assertEqual(clean, {'blocks': {'hero': {'surface': 'glass'}}})

    def test_more_than_twelve_blocks_are_truncated(self):
        known   =   list(TEMPLATE_BLOCKS['landing'])[:13]
        self.assertEqual(len(known), 13)
        clean   =   clean_site_theme(
            {'blocks': {block_id: {'radius': 'xl'} for block_id in known}},
            has_advanced = True,
        )
        self.assertEqual(len(clean['blocks']), 12)

    def test_section_requires_design_advanced(self):
        payload =   {'blocks': {'hero': {'radius': 'xl'}}}
        self.assertEqual(clean_site_theme(payload, has_plus = True, has_style = True), {})
        self.assertEqual(clean_site_theme(payload, has_style = True), {})
        self.assertTrue(clean_site_theme(payload, has_advanced = True))

    def test_section_does_not_persist_without_design_advanced(self):
        #Estándar + IA: el PATCH se acepta, containers persiste (plus) pero
        #la sección `blocks` (Premium) no llega a la DB.
        client, _, store    =   self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS))
        response            =   client.patch(
            self.custom_url,
            {'site_theme': {'blocks': {'hero': {'radius': 'xl'}},
                            'containers': {'radius': 'xl'}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertNotIn('blocks', customization.site_theme or {})
        self.assertEqual(customization.site_theme.get('containers', {}).get('radius'), 'xl')

    def test_section_persists_with_design_advanced(self):
        client, _, store    =   self._premium_client()
        response            =   client.patch(
            self.custom_url,
            {'site_theme': {'blocks': {'hero': {'radius': 'xl', 'accent': '#aabbcc'}}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.site_theme['blocks']['hero'],
                         {'radius': 'xl', 'accent': '#aabbcc'})

    def test_generated_site_theme_blocks_use_the_closed_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, ElementosIA.ELEMENTS_PAYLOAD)):
            blocks  =   (proposal['site_theme'].get('blocks') or {})
            self.assertLessEqual(len(blocks), 12)
            for block_id, styles in blocks.items():
                self.assertIn(block_id, TEMPLATE_BLOCKS['landing'])
                self.assertTrue(set(styles).issubset(AI_BLOCK_STYLE_KEYS), styles)
                self.assertEqual(clean_site_theme(
                    {'blocks': {block_id: styles}},
                    has_plus = True, has_advanced = True, has_style = True,
                )['blocks'][block_id], styles)


#=========================================
# 7) APPLY PUBLICA EN UN SOLO PASO
#=========================================
class ApplyPublica(_AiDesignBase):
    """apply aplica el borrador Y publica, con snapshot en StudioVersion."""

    PUBLISH_PAYLOAD =   {'rubro': 'belleza', 'tone': 'moderno',
                         'goals': ['dar_confianza', 'mostrar_servicios'],
                         'must_have': ['offers', 'contact', 'faq']}

    def test_apply_publishes_and_reports_success(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client, self.PUBLISH_PAYLOAD)
        response            =   self._apply(client, seed, pid)
        self.assertEqual(response.status_code, 200, response.content[:400])
        body                =   response.json()
        self.assertEqual(body['Exito'], 'Tu web ya está publicada')
        self.assertIs(body['published'], True)
        for key in ('customization', 'storage'):
            self.assertIn(key, body)

    def test_apply_writes_the_published_layout_not_only_the_draft(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client, self.PUBLISH_PAYLOAD)
        proposal            =   _proposals_of(self._generate(client, self.PUBLISH_PAYLOAD))[0]
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        published           =   customization.layout_config['landing']['blocks']
        self.assertEqual(
            [block['id'] for block in published],
            [block['id'] for block in _landing_blocks(proposal)],
        )
        self.assertTrue({block['id'] for block in published} & AI_ONLY_BLOCKS)
        self.assertEqual(customization.layout_config, customization.layout_config_draft)
        self.assertEqual(customization.site_theme, customization.site_theme_draft)

    def test_apply_publishes_the_template_and_theme(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client, self.PUBLISH_PAYLOAD)
        proposal            =   _proposals_of(self._generate(client, self.PUBLISH_PAYLOAD))[0]
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.template, proposal['template'])
        self.assertEqual(customization.site_theme, proposal['site_theme'])

    def test_apply_creates_a_studio_version_with_the_published_snapshot(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client, self.PUBLISH_PAYLOAD)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        versions            =   StudioVersion.objects.filter(store = store)
        self.assertEqual(versions.count(), 1)
        snapshot            =   versions[0].snapshot
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(snapshot['layout_config'], customization.layout_config)
        self.assertEqual(snapshot['template'], customization.template)

    def test_apply_is_idempotent_for_the_same_seed_and_proposal(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client, self.PUBLISH_PAYLOAD)
        first               =   self._apply(client, seed, pid)
        self.assertEqual(first.status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        published           =   json.dumps(customization.layout_config, sort_keys = True)
        second              =   self._apply(client, seed, pid)
        self.assertEqual(second.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(json.dumps(customization.layout_config, sort_keys = True), published)

    def test_unknown_proposal_id_is_rejected(self):
        client, _, _    =   self._premium_client()
        seed, _         =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, 'no-existe').status_code, 400)

    def test_missing_seed_is_rejected(self):
        client, _, _    =   self._premium_client()
        _, pid          =   self._first_proposal(client)
        self.assertEqual(self._apply(client, None, pid).status_code, 400)

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

    def test_apply_never_overwrites_the_owners_published_content(self):
        client, profile, store  =   self._premium_client()
        published               =   StoreCustomization.objects.create(
            store           =   store,
            headline        =   'Mi titular',
            about_text      =   'Mi historia',
            template        =   'classic',
            layout_config   =   {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
            site_theme      =   {'palette': {'primary': '#111111'}},
        )
        seed, pid               =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid).status_code, 200)
        published.refresh_from_db()
        self.assertEqual(published.headline, 'Mi titular')
        self.assertEqual(published.about_text, 'Mi historia')


#=========================================
# 8) REGRESIONES v2
#=========================================
class Regresiones(_AiDesignBase):
    """Gating, throttle, determinismo, autofill, copy, imágenes y plantillas."""

    #---- gating -------------------------------------------------------
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
        self.assertEqual(self._apply(client, 1, 'p1').status_code, 403)

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

    #---- forma / determinismo ----------------------------------------
    def test_returns_between_two_and_three_proposals(self):
        client, _, _    =   self._premium_client()
        response        =   self._generate(client)
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertIn(len(_proposals_of(response)), (2, 3))

    def test_proposal_ids_are_unique_and_labels_distinct(self):
        client, _, _    =   self._premium_client()
        proposals       =   _proposals_of(self._generate(client))
        self.assertEqual(len({p['id'] for p in proposals}), len(proposals))
        self.assertEqual(len({p['label'] for p in proposals}), len(proposals))

    def test_every_proposal_declares_the_v3_fields(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for key in ('label', 'why', 'template', 'layout_config', 'site_theme',
                        'theme_choice', 'night_mode', 'cover', 'theme', 'theme_toggle',
                        'copy', 'copy_draft', 'image_requests', 'notes'):
                self.assertIn(key, proposal)
            self.assertIn(proposal['cover']['mode'], ('photo', 'logo'))
            self.assertIn(proposal['theme'], ('light', 'dark'))
            self.assertLessEqual(len(proposal['cover']['reason']), 120)

    def test_templates_stay_inside_the_plan_whitelist(self):
        for codes in (CUSTOMIZATION + AI_DESIGN,
                      CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED):
            client, profile, _  =   self._client(*codes)
            allowed             =   set(allowed_templates_of(profile))
            for proposal in _proposals_of(self._generate(client)):
                self.assertIn(proposal['template'], allowed)

    def test_ai_templates_are_allowed_only_with_the_flag(self):
        _, profile_with, _      =   _make_account(*(CUSTOMIZATION + AI_DESIGN))
        _, profile_without, _   =   _make_account(*CUSTOMIZATION)
        self.assertIn('ai_lumen', allowed_templates_of(profile_with))
        self.assertIn('ai_pulse', allowed_templates_of(profile_with))
        self.assertNotIn('ai_lumen', allowed_templates_of(profile_without))
        self.assertNotIn('ai_pulse', allowed_templates_of(profile_without))

    def test_block_ids_belong_to_the_template_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, ElementosIA.ELEMENTS_PAYLOAD)):
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
                    self.assertFalse(TEMPLATE_BLOCKS[surface][block['id']].get('premium'),
                                     f'{surface}.{block["id"]} es premium y el plan no lo incluye')

    def test_blocks_without_real_data_are_disabled(self):
        client, _, _    =   self._premium_client()
        gated           =   {'landing': DATA_DRIVEN_LANDING, 'catalog': DATA_DRIVEN_CATALOG,
                             'services': DATA_DRIVEN_SERVICES}
        for proposal in _proposals_of(self._generate(client)):
            for surface, value in proposal['layout_config'].items():
                for block in value['blocks']:
                    if block['id'] in gated.get(surface, frozenset()) and not TEMPLATE_BLOCKS[surface][block['id']].get('locked'):
                        self.assertFalse(block['enabled'], f'{surface}.{block["id"]} sin datos pero enabled=true')

    def test_site_theme_is_idempotent_under_the_sanitizer(self):
        client, _, store    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, ElementosIA.ELEMENTS_PAYLOAD)):
            theme           =   proposal['site_theme']
            self.assertEqual(
                clean_site_theme(theme, has_plus = True, has_advanced = True,
                                 has_style = True, store = store),
                theme,
            )

    def test_same_request_returns_the_same_proposals(self):
        client, _, _    =   self._premium_client()
        first           =   self._generate(client).json()
        second          =   self._generate(client).json()
        self.assertEqual(json.dumps(first, sort_keys = True), json.dumps(second, sort_keys = True))

    def test_explicit_seed_reproduces_the_same_payload(self):
        client, _, _    =   self._premium_client()
        first           =   self._generate(client, {'seed': 12345}).json()
        second          =   self._generate(client, {'seed': 12345}).json()
        self.assertEqual(json.dumps(first, sort_keys = True), json.dumps(second, sort_keys = True))

    def test_generation_makes_no_outbound_network_calls(self):
        client, _, _    =   self._premium_client()
        with patch.object(socket, 'create_connection', side_effect = AssertionError('llamada de red saliente')):
            response    =   self._generate(client)
        self.assertEqual(response.status_code, 200, response.content[:400])

    #---- copy ---------------------------------------------------------
    def test_copy_respects_the_model_max_lengths(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            copy    =   proposal['copy']
            for field, max_len in COPY_MAX.items():
                self.assertIn(field, copy)
                self.assertLessEqual(len(copy[field]), max_len, f'{field} excede {max_len}')

    def test_draft_only_uses_allowed_business_keys(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            draft   =   proposal['copy_draft']
            self.assertTrue(set(draft).issubset(DRAFT_KEYS), set(draft) - DRAFT_KEYS)
            self.assertFalse(set(draft) & DRAFT_FORBIDDEN)

    def test_draft_respects_the_text_limits(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            draft   =   proposal['copy_draft']
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
        self.assertTrue(customization.announcements)
        self.assertEqual(customization.testimonials, [])
        self.assertEqual(customization.stats, [])
        self.assertEqual(customization.contact_email, '')
        self.assertEqual(customization.whatsapp, '')

    def test_autofill_false_behaves_like_absent(self):
        client, _, store    =   self._premium_client()
        seed, pid           =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid, autofill = False).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.about_text, '')
        self.assertEqual(customization.faqs, [])
        self.assertEqual(customization.services, [])

    def test_autofill_never_overwrites_content_written_by_the_owner(self):
        client, profile, store  =   self._premium_client()
        services                =   [{'icon': 'scissors', 'title': 'Corte', 'text': 'Con turno'}]
        faqs                    =   [{'q': '¿Abren?', 'a': 'Sí'}]
        steps                   =   [{'icon': 'check', 'title': 'Reservá', 'text': 'Por WhatsApp'}]
        announcements           =   [{'icon': 'megaphone', 'text': 'Cerramos el lunes'}]
        StoreCustomization.objects.create(
            store           =   store,
            about_text      =   'Mi historia',
            about_mission   =   'Mi misión',
            services        =   services,
            faqs            =   faqs,
            service_steps   =   steps,
            announcements   =   announcements,
            contact_email   =   'hola@mitienda.com',
            whatsapp        =   '5491112345678',
        )
        seed, pid       =   self._first_proposal(client)
        self.assertEqual(self._apply(client, seed, pid, autofill = True).status_code, 200)
        customization   =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.about_text, 'Mi historia')
        self.assertEqual(customization.about_mission, 'Mi misión')
        self.assertEqual(customization.services, services)
        self.assertEqual(customization.faqs, faqs)
        self.assertEqual(customization.service_steps, steps)
        self.assertEqual(customization.announcements, announcements)
        self.assertEqual(customization.contact_email, 'hola@mitienda.com')
        self.assertEqual(customization.whatsapp, '5491112345678')

    #---- pedido de fotos ---------------------------------------------
    def test_image_requests_declare_closed_target_and_min_count(self):
        client, _, _    =   self._premium_client()
        requests        =   [item for proposal in _proposals_of(self._generate(client))
                             for item in proposal['image_requests']]
        self.assertTrue(requests, 'tienda sin fotos: debería pedir imágenes')
        for item in requests:
            self.assertIn(item['target'], ('cover', 'gallery'))
            self.assertGreaterEqual(item['min_count'], 2)
            self.assertLessEqual(item['min_count'], 4)

    def test_no_requests_when_the_store_already_has_photos(self):
        client, _, store    =   self._premium_client()
        StoreGalleryImage.objects.create(store = store, image_key = 'stores/x/gallery/a.webp', image_size = 10, position = 0)
        for proposal in _proposals_of(self._generate(client)):
            self.assertEqual(proposal['image_requests'], [])

    #---- imágenes -----------------------------------------------------
    @staticmethod
    def _local_storage():
        return patch('StoreApp.domains.stores.services.storage.storage_configured', return_value = False)

    def _upload(self, client, request_id = 'local', upload = None):
        if upload is None:
            upload, _ = _jpeg_upload()
        return client.post(self.image_url, {'image': upload, 'request_id': request_id}, format = 'multipart')

    def test_upload_stores_a_webp_gallery_image(self):
        client, _, store    =   self._premium_client()
        upload, original    =   _jpeg_upload()
        with self._local_storage():
            response        =   self._upload(client, upload = upload)
        self.assertEqual(response.status_code, 200, response.content[:400])
        body                =   response.json()
        self.assertIn('Exito', body)
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
        self.assertLess(len(stored), len(original))

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
        upload          =   SimpleUploadedFile('foto.jpg', b'no es imagen', content_type = 'image/jpeg')
        for index in range(60):
            response    =   self._upload(client, request_id = 'x', upload = upload)
            self.assertEqual(response.status_code, 400, f'call {index + 1}: {response.content[:200]}')
        self.assertEqual(self._upload(client, request_id = 'x', upload = upload).status_code, 429)

    #---- web pública --------------------------------------------------
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
        self.assertIn('ai_pulse', body['allowed_templates'])
