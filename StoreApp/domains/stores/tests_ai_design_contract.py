"""
Suite de CONTRATO v4 del motor de diseño con IA ("Diseñar con IA").

Endpoints:
  POST /api/stores/ai-design/          -> propuestas (motor local, determinista)
  POST /api/stores/ai-design/apply/    -> aplica el borrador Y publica
  POST /api/stores/ai-design/image/    -> fotos del pedido (WebP en galería)
  PATCH /api/stores/customization/     -> site_theme (v2: roles/layout/skin + blocks)

Contrato v4 (engine 'ai-design/4'):
  1) diversidad: 13 rubros con tuplas (template, skin) propias; dentro de una
     generación las 2-3 propuestas difieren en template, skin y par tipográfico;
     seed+1 cambia la familia visual;
  2) fuentes de estilo: con has_ai_design la whitelist suma ai_* y los 20
     legacy; sin el flag, exactamente las del plan;
  3) site_theme v2: typography.roles (13 roles), layout y skin del catálogo;
  4) bloques nuevos (aipricing/aiprocess/aimosaic) solo con has_ai_design y
     props tipadas saneadas (iconos AI_ICONS ∪ gen:<slug>);
  5) apply publica el theme v2 + el layout nuevo (StudioVersion);
  6) regresiones v2/v3: gating, throttle, determinismo, autofill, imágenes,
     brand color, modo noche, portada logo y overrides por contenedor;
  7) la web pública responde 200 con una plantilla legacy y con ai_lumen.

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
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.layout_blocks import (
    AI_ICONS, TEMPLATE_BLOCKS, clean_layout_config,
)
from StoreApp.domains.stores.models import (
    Store, StoreCustomization, StoreGalleryImage, StudioVersion,
)
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services.ai_design import _contrast_ratio
from StoreApp.domains.stores.services.ai_design_skins import (
    SKIN_FAMILIES, SKIN_FAMILY_OF, SKIN_IDS, SKINS, STYLE_FAMILIES,
)
from StoreApp.domains.stores.services.ai_design_typography import (
    FONT_FAMILIES, FONT_KINDS, FONT_SLUGS, TYPE_CASES, TYPE_LEADING,
    QUOTE_DISPLAY_SKINS, TYPE_PAIRS, TYPE_SIZES, TYPE_TRACKING,
    TYPOGRAPHY_ROLES, roles_for, type_pair_signature,
)
from StoreApp.domains.stores.site_theme import SITE_THEME_MAX_BYTES, clean_site_theme
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

#Beneficios: la IA de diseño exige personalización + el flag propio.
CUSTOMIZATION       =   ('has_customization',)
AI_DESIGN           =   ('has_ai_design',)
DESIGN_PLUS         =   ('has_design_plus',)
DESIGN_ADVANCED     =   ('has_design_advanced',)
PUBLIC_LINK         =   ('has_public_link',)

#Cuotas típicas del plan premium (sin ellas, storage/gallery_limit = 0).
PREMIUM_LIMITS      =   {'max_gallery_images': 20, 'max_images': 50, 'max_storage_mb': 200}

#Catálogo del plan (las 6 que ofrece el selector) y los dos exclusivos de IA.
PLAN_TEMPLATES      =   ('classic', 'duo', 'calma', 'vitrina', 'cobre', 'minimal')
STYLE_TEMPLATES     =   frozenset(PLAN_TEMPLATES + R.AI_TEMPLATES + R.LEGACY_TEMPLATES)

#Bloques exclusivos de "Diseñar con IA" (TEMPLATE_BLOCKS[*]['ai_only']).
AI_ONLY_BLOCKS      =   frozenset({
    'aiquote', 'aistrip', 'aicheck', 'aigrid', 'aiband',
    'aipricing', 'aiprocess', 'aimosaic',
})
#Bloques nuevos del contrato v4 (contrato 4).
NEW_AI_BLOCKS       =   ('aipricing', 'aiprocess', 'aimosaic')
AI_BLOCK_STYLE_KEYS =   frozenset({'radius', 'shadow', 'border', 'density', 'surface', 'align', 'accent'})

#Skin: catálogo cerrado de 26 familias (18 del contrato 2 del enunciado +
#las 8 de los estilos de diseño de la v5).
CONTRACT_SKIN_FAMILIES = (
    'glass', 'editorial', 'brutal', 'soft', 'tech', 'warm', 'luxury', 'kinetic',
    'paper', 'neon', 'minimal', 'organic', 'retro', 'corporate', 'playful',
    'mono', 'gradient', 'cinematic',
    'swiss', 'magazine', 'pop', 'aurora', 'craft', 'nostalgia', 'prestige', 'showcase',
)
#Los 13 roles tipográficos del contrato v2.
CONTRACT_ROLES      =   (
    'display', 'h1', 'h2', 'h3', 'body', 'lead', 'eyebrow',
    'label', 'quote', 'price', 'nav', 'button', 'footer',
)
LAYOUT_ENUMS        =   {
    'density'       :   ('compact', 'comfortable', 'spacious'),
    'grid'          :   ('12', 'asym', 'split', 'bento', 'editorial'),
    'hero'          :   ('centered', 'split', 'cinema', 'logo', 'editorial'),
    'gutter'        :   ('sm', 'md', 'lg'),
    'measure'       :   ('narrow', 'normal', 'wide'),
    'radiusScale'   :   ('none', 'sm', 'md', 'lg', 'xl'),
}
ROLE_KEYS           =   frozenset({'font', 'size', 'weight', 'tracking', 'leading', 'case'})

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


def _skin_of(proposal):
    """Piel de la propuesta: `proposal.skin` o, si falta, site_theme.skin."""
    skin    =   proposal.get('skin') or {}
    if not skin:
        skin    =   ((proposal.get('site_theme') or {}).get('skin') or {})
    return skin


def _roles_of(proposal):
    """Roles tipográficos: `proposal.typography_roles` o site_theme.typography.roles."""
    roles   =   proposal.get('typography_roles') or {}
    if not roles:
        roles   =   (((proposal.get('site_theme') or {}).get('typography') or {}).get('roles') or {})
    return roles


def _type_signature_of(proposal):
    roles   =   _roles_of(proposal)
    return (
        (roles.get('display') or {}).get('font'),
        (roles.get('body') or {}).get('font'),
    )


def _layout_of(proposal):
    return proposal.get('layout') or ((proposal.get('site_theme') or {}).get('layout') or {})


def _rubro_payload(rubro, **extra):
    payload =   {'rubro': rubro, 'tone': 'moderno', 'goals': ['mostrar_servicios'],
                 'audience': 'clientes del barrio', 'must_have': ['contact']}
    payload.update(extra)
    return payload


def _theme_from_skin(skin):
    """site_theme v2 completo armado desde una piel del catálogo."""
    return {
        'palette'       :   dict(skin['palette']),
        'containers'    :   dict(skin['containers']),
        'buttons'       :   dict(skin['buttons']),
        'background'    :   dict(skin['background']),
        'motion'        :   dict(skin['motion']),
        'layout'        :   dict(skin['layout']),
        'skin'          :   {'id': skin['id'], 'family': skin['family']},
        'typography'    :   {'roles': roles_for(skin['typography']['pair'], 'moderno', skin['family'])},
    }


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
# 1) DIVERSIDAD (contrato 1 y 8)
#=========================================
class Diversidad(_AiDesignBase):
    """13 rubros, 2-3 propuestas por generación, sin estilos repetidos."""

    def test_the_catalog_has_thirteen_rubros(self):
        self.assertEqual(len(R.RUBROS), 13)
        self.assertEqual(set(R.RUBROS), set(R.RUBRO_STYLES))

    def test_first_proposal_of_every_rubro_has_its_own_template_skin_pair(self):
        client, _, _    =   self._premium_client()
        seen            =   {}
        for rubro in R.RUBROS:
            proposals   =   _proposals_of(self._generate(client, _rubro_payload(rubro)))
            self.assertTrue(proposals, f'{rubro}: el motor no devolvió propuestas')
            first       =   proposals[0]
            skin_id     =   _skin_of(first).get('id')
            self.assertTrue(skin_id, f'{rubro}: la propuesta no declara piel (contrato 7)')
            key         =   (first['template'], skin_id)
            self.assertNotIn(key, seen, f'{rubro} repite el estilo de {seen.get(key)}: {key}')
            seen[key]   =   rubro
        self.assertEqual(len(seen), 13)

    def test_no_template_skin_pair_is_shared_between_rubros(self):
        client, _, _    =   self._premium_client()
        seen            =   {}
        for rubro in R.RUBROS:
            for proposal in _proposals_of(self._generate(client, _rubro_payload(rubro))):
                skin_id =   _skin_of(proposal).get('id')
                self.assertTrue(skin_id, f'{rubro}: propuesta sin piel')
                key     =   (proposal['template'], skin_id)
                self.assertNotIn(key, seen, f'{rubro} comparte {key} con {seen.get(key)}')
                seen[key]   =   rubro

    def test_proposals_of_one_generation_differ_in_template_skin_and_type_pair(self):
        client, _, _    =   self._premium_client()
        for rubro in ('comercio', 'belleza', 'tecnologia'):
            proposals   =   _proposals_of(self._generate(client, _rubro_payload(rubro)))
            self.assertIn(len(proposals), (2, 3), rubro)
            self.assertEqual(len({p['template'] for p in proposals}), len(proposals), rubro)
            self.assertEqual(len({_skin_of(p).get('id') for p in proposals}), len(proposals), rubro)
            self.assertEqual(len({_type_signature_of(p) for p in proposals}), len(proposals), rubro)

    def test_seed_plus_one_changes_the_visual_family(self):
        client, _, _    =   self._premium_client()
        payload         =   _rubro_payload('comercio')
        base            =   _proposals_of(self._generate(client, {**payload, 'seed': 100}))
        other           =   _proposals_of(self._generate(client, {**payload, 'seed': 101}))
        base_family     =   _skin_of(base[0]).get('family')
        other_family    =   _skin_of(other[0]).get('family')
        self.assertTrue(base_family, 'la propuesta base no declara familia de piel')
        self.assertTrue(other_family, 'seed+1 no declara familia de piel')
        self.assertNotEqual(base_family, other_family, 'seed+1 repite la familia visual')

    def test_every_rubro_declares_three_distinct_signature_styles(self):
        pairs_seen  =   set()
        for rubro, styles in R.RUBRO_STYLES.items():
            self.assertEqual(len(styles), 3, rubro)
            self.assertEqual(len({style['pair'] for style in styles}), 3, f'{rubro}: pares repetidos')
            templates   =   [style['template'] for style in styles]
            self.assertTrue(any(template not in R.AI_TEMPLATES for template in templates),
                            f'{rubro}: todos los estilos son ai_*')
            self.assertTrue(any(template in R.LEGACY_TEMPLATES for template in templates),
                            f'{rubro}: ningún estilo legacy')
            for style in styles:
                self.assertIn(style['template'], STYLE_TEMPLATES, f'{rubro}: plantilla fuera del catálogo')
                self.assertIn(style['skin'], SKIN_IDS, f'{rubro}: piel fuera del catálogo')
                self.assertIn(style['pair'], TYPE_PAIRS, f'{rubro}: par tipográfico fuera del catálogo')
                key =   (style['template'], style['skin'])
                self.assertNotIn(key, pairs_seen, f'{rubro} comparte el estilo firma {key}')
                pairs_seen.add(key)

    def test_proposals_declare_skin_variety_and_redesign(self):
        client, _, _    =   self._premium_client()
        proposals       =   _proposals_of(self._generate(client, _rubro_payload('comercio')))
        self.assertIn(len(proposals), (2, 3))
        for proposal in proposals:
            skin        =   proposal.get('skin') or {}
            self.assertEqual(set(skin), {'id', 'family', 'label'}, 'proposal.skin incompleto')
            self.assertIn(skin['id'], SKIN_IDS)
            self.assertEqual(skin['family'], SKIN_FAMILY_OF[skin['id']])
            variety     =   proposal.get('variety') or {}
            self.assertEqual(variety.get('family'), skin['family'])
            self.assertTrue(variety.get('differs_by'), 'variety.differs_by vacío')
            redesign    =   proposal.get('redesign') or {}
            self.assertTrue(redesign.get('surfaces'), 'redesign.surfaces vacío')
            self.assertIs(redesign.get('changed'), True)


#=========================================
# 2) FUENTES DE ESTILO (contrato 2)
#=========================================
class FuentesDeEstilo(_AiDesignBase):
    """Whitelist del plan + ai_* + legacy; el motor nunca se sale de ella."""

    def test_with_ai_design_the_whitelist_covers_plan_ai_and_legacy(self):
        _, profile, _   =   _make_account(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED))
        allowed         =   allowed_templates_of(profile)
        self.assertEqual(len(allowed), len(set(allowed)), 'la whitelist repite plantillas')
        for template in PLAN_TEMPLATES:
            self.assertIn(template, allowed, f'falta la plantilla del plan {template}')
        for template in R.AI_TEMPLATES:
            self.assertIn(template, allowed, f'falta el diseño de IA {template}')
        for template in R.LEGACY_TEMPLATES:
            self.assertIn(template, allowed, f'falta el diseño legacy {template}')

    def test_without_the_flag_the_whitelist_is_exactly_the_plan(self):
        _, profile, _   =   _make_account(*(CUSTOMIZATION + DESIGN_PLUS + DESIGN_ADVANCED))
        self.assertEqual(set(allowed_templates_of(profile)), set(PLAN_TEMPLATES))

    def test_ai_templates_are_allowed_only_with_the_flag(self):
        _, profile_with, _      =   _make_account(*(CUSTOMIZATION + AI_DESIGN))
        _, profile_without, _   =   _make_account(*CUSTOMIZATION)
        for template in R.AI_TEMPLATES:
            self.assertIn(template, allowed_templates_of(profile_with))
            self.assertNotIn(template, allowed_templates_of(profile_without))

    def test_legacy_catalog_is_the_twenty_retired_templates(self):
        self.assertEqual(R.AI_TEMPLATES, ('ai_lumen', 'ai_pulse'))
        self.assertEqual(len(R.LEGACY_TEMPLATES), 20)
        self.assertEqual(set(R.LEGACY_TEMPLATES), set(StoreCustomization.TEMPLATE_RETIRED_MAP))
        self.assertEqual(R.STYLE_SOURCES, ('plan', 'ai', 'legacy'))

    def test_style_source_of_maps_each_source(self):
        self.assertEqual(R.style_source_of('ai_lumen'), 'ai')
        self.assertEqual(R.style_source_of('street'), 'legacy')
        self.assertEqual(R.style_source_of('vitrina'), 'plan')
        for template in PLAN_TEMPLATES + R.AI_TEMPLATES + R.LEGACY_TEMPLATES:
            self.assertIn(R.style_source_of(template), R.STYLE_SOURCES)

    def test_engine_never_returns_a_template_outside_the_whitelist(self):
        for codes in (CUSTOMIZATION + AI_DESIGN,
                      CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED):
            client, profile, _  =   self._client(*codes)
            allowed             =   set(allowed_templates_of(profile))
            for proposal in _proposals_of(self._generate(client)):
                self.assertIn(proposal['template'], allowed)

    def test_proposals_declare_the_matching_style_source(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            self.assertEqual(
                proposal.get('style_source'),
                R.style_source_of(proposal['template']),
                f'style_source incoherente para {proposal["template"]}',
            )

    def test_engine_reports_v4(self):
        client, _, _    =   self._premium_client()
        self.assertEqual(self._generate(client).json()['engine'], 'ai-design/4')


#=========================================
# 3) THEME V2 (contrato 3)
#=========================================
class ThemeV2(_AiDesignBase):
    """typography.roles + layout + skin: catálogo cerrado, rechazo o descarte."""

    def _clean(self, theme):
        return clean_site_theme(theme, has_advanced = True)

    def _roles(self, pair = 'grotesk-clean', tone = 'moderno'):
        return roles_for(pair, tone)

    def test_roles_layout_and_skin_are_accepted(self):
        theme   =   {
            'typography'    :   {'roles': self._roles('serif-editorial', 'serio')},
            'layout'        :   {'density': 'comfortable', 'grid': 'editorial', 'hero': 'editorial',
                                 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
            'skin'          :   {'id': 'editorial-ink', 'family': 'editorial'},
        }
        self.assertEqual(self._clean(theme), theme)

    def test_partial_roles_are_accepted(self):
        body    =   self._roles()['body']
        self.assertEqual(self._clean({'typography': {'roles': {'body': body}}}),
                         {'typography': {'roles': {'body': body}}})

    def test_skin_family_is_derived_from_the_id(self):
        clean   =   self._clean({'skin': {'id': 'glass-noir', 'family': 'brutal'}})
        self.assertEqual(clean['skin'], {'id': 'glass-noir', 'family': 'glass'})

    def test_skin_outside_the_catalog_is_discarded_without_breaking_the_theme(self):
        clean   =   self._clean({'skin': {'id': 'inventada-x'}, 'palette': {'accent': '#123456'}})
        self.assertEqual(clean, {'palette': {'accent': '#123456'}})
        clean   =   self._clean({'skin': {'id': 'editorial-ink', 'family': 'brutal'},
                                 'palette': {'accent': '#123456'}})
        self.assertEqual(clean['skin'], {'id': 'editorial-ink', 'family': 'editorial'})
        #Una sección con forma inválida (no un objeto) sí es 400.
        with self.assertRaises(DRFValidationError):
            self._clean({'skin': 'editorial-ink'})

    def test_unknown_role_is_rejected(self):
        roles   =   self._roles()
        roles['banner'] =   roles['body']
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': roles}})

    def test_font_outside_the_catalog_is_rejected(self):
        roles   =   self._roles()
        roles['display'] =   dict(roles['display'], font = 'comic-sans')
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': roles}})

    def test_weight_must_be_300_to_900_step_100(self):
        for weight in (250, 350, 450, 950, 400.5, True, '700', None):
            roles   =   self._roles()
            roles['h1'] =   dict(roles['h1'], weight = weight)
            with self.assertRaises(DRFValidationError, msg = f'weight {weight!r} aceptado'):
                self._clean({'typography': {'roles': roles}})

    def test_invalid_role_enums_are_rejected(self):
        for key, value in (('size', 'gigante'), ('tracking', 'ancho'),
                           ('leading', 'aereo'), ('case', 'capitalize')):
            roles   =   self._roles()
            roles['h2'] =   dict(roles['h2'], **{key: value})
            with self.assertRaises(DRFValidationError, msg = f'{key}={value!r} aceptado'):
                self._clean({'typography': {'roles': roles}})

    def test_role_with_unknown_key_or_bad_shape_is_rejected(self):
        roles   =   self._roles()
        roles['body'] =   dict(roles['body'], color = '#000000')
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': roles}})
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': {'body': 'md'}}})
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': []}})

    def test_incomplete_role_is_rejected(self):
        role    =   dict(self._roles()['body'])
        role.pop('leading')
        with self.assertRaises(DRFValidationError):
            self._clean({'typography': {'roles': {'body': role}}})

    def test_every_layout_enum_is_accepted(self):
        for key, values in LAYOUT_ENUMS.items():
            for value in values:
                clean   =   self._clean({'layout': {key: value}})
                self.assertEqual(clean, {'layout': {key: value}}, f'layout.{key}={value}')

    def test_invalid_layout_is_rejected(self):
        for payload in ({'grid': 'diagonal'}, {'hero': 'full'}, {'density': 'aireado'},
                        {'gutter': 'xl'}, {'measure': 'enorme'}, {'radiusScale': 'pill'},
                        {'grid': '12', 'inventado': 'x'}):
            with self.assertRaises(DRFValidationError, msg = f'layout {payload} aceptado'):
                self._clean({'layout': payload})

    def test_full_theme_is_idempotent(self):
        theme   =   _theme_from_skin(SKINS['editorial-ink'])
        clean   =   self._clean(theme)
        self.assertEqual(clean, theme)
        self.assertEqual(self._clean(clean), clean)

    def test_max_bytes_is_12288(self):
        self.assertEqual(SITE_THEME_MAX_BYTES, 12288)
        oversized   =   {'typography': {'heading': 'x' * (SITE_THEME_MAX_BYTES + 10)}}
        with self.assertRaises(DRFValidationError):
            self._clean(oversized)


#=========================================
# 4) ROLES TIPOGRÁFICOS (contrato 3 y 4 del enunciado)
#=========================================
class RolesTipograficos(_AiDesignBase):
    """13 roles cerrados, 24 familias y pares con firmas distintas."""

    def test_the_catalog_has_the_thirteen_contract_roles(self):
        self.assertEqual(tuple(TYPOGRAPHY_ROLES), CONTRACT_ROLES)
        self.assertEqual(len(TYPOGRAPHY_ROLES), 13)

    def test_the_font_catalog_has_twenty_four_families(self):
        self.assertEqual(len(FONT_FAMILIES), 24)
        self.assertEqual(len(set(FONT_SLUGS)), 24)
        for slug, meta in FONT_FAMILIES.items():
            self.assertIn(meta['kind'], FONT_KINDS, slug)
            self.assertTrue(meta['label'], slug)

    def test_every_type_pair_uses_catalog_fonts_with_a_distinct_signature(self):
        self.assertEqual(len(TYPE_PAIRS), 24)
        for name, pair in TYPE_PAIRS.items():
            self.assertIn(pair['display'], FONT_SLUGS, name)
            self.assertIn(pair['body'], FONT_SLUGS, name)
        signatures  =   {type_pair_signature(name) for name in TYPE_PAIRS}
        self.assertEqual(len(signatures), len(TYPE_PAIRS), 'dos pares comparten firma (display, body)')

    def test_every_pair_tone_and_skin_expands_to_thirteen_valid_roles(self):
        for name, pair in TYPE_PAIRS.items():
            for tone in R.TONES:
                for family in (None,) + SKIN_FAMILIES:
                    roles   =   roles_for(name, tone, family)
                    label   =   f'{name}/{tone}/{family}'
                    self.assertEqual(set(roles), set(CONTRACT_ROLES), label)
                    for role, value in roles.items():
                        self.assertEqual(set(value), ROLE_KEYS, f'{label}.{role}')
                        self.assertIn(value['font'], FONT_SLUGS, f'{label}.{role}.font')
                        self.assertIn(value['size'], TYPE_SIZES, f'{label}.{role}.size')
                        self.assertIn(value['weight'], range(300, 901, 100), f'{label}.{role}.weight')
                        self.assertIn(value['tracking'], TYPE_TRACKING, f'{label}.{role}.tracking')
                        self.assertIn(value['leading'], TYPE_LEADING, f'{label}.{role}.leading')
                        self.assertIn(value['case'], TYPE_CASES, f'{label}.{role}.case')
                    #Invariantes del contrato.
                    self.assertEqual(roles['body']['size'], 'md', label)
                    self.assertIn(roles['body']['weight'], (400, 500), label)
                    self.assertIn(roles['body']['leading'], ('normal', 'relaxed'), label)
                    self.assertEqual(roles['price']['weight'], 700, label)
                    self.assertEqual(roles['price']['tracking'], 'normal', label)
                    self.assertEqual(roles['eyebrow']['case'], 'upper', label)
                    self.assertEqual(roles['eyebrow']['tracking'], 'wider', label)
                    #Regla de profesionalidad (v4.1): la display manda solo en
                    #display/h1/h2 y en la cita de las pieles de revista; h3 y
                    #el resto de roles van con el cuerpo (una display pesada
                    #en un título chico se lee como un error de maquetado).
                    for role in ('display', 'h1', 'h2'):
                        self.assertEqual(roles[role]['font'], pair['display'], f'{label}.{role}')
                    self.assertEqual(roles['h3']['font'], pair['body'], f'{label}.h3')
                    quote_font = pair['display'] if family in QUOTE_DISPLAY_SKINS else pair['body']
                    self.assertEqual(roles['quote']['font'], quote_font, f'{label}.quote')
                    for role in ('body', 'lead', 'eyebrow', 'label', 'price', 'nav', 'button', 'footer'):
                        self.assertEqual(roles[role]['font'], pair['body'], f'{label}.{role}')

    def test_unknown_pair_falls_back_to_the_default(self):
        self.assertEqual(roles_for('no-existe', 'moderno'), roles_for('grotesk-clean', 'moderno'))

    def test_generated_proposals_declare_the_thirteen_roles(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            roles   =   proposal.get('typography_roles') or {}
            self.assertEqual(set(roles), set(CONTRACT_ROLES), 'proposal.typography_roles incompleto')
            for role, value in roles.items():
                self.assertEqual(set(value), ROLE_KEYS, role)
                self.assertIn(value['font'], FONT_SLUGS, role)
                self.assertIn(value['weight'], range(300, 901, 100), role)

    def test_site_theme_roles_equal_the_proposal_roles(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            theme_roles =   ((proposal.get('site_theme') or {}).get('typography') or {}).get('roles')
            self.assertTrue(theme_roles, 'site_theme.typography.roles ausente (contrato 7)')
            self.assertEqual(theme_roles, proposal.get('typography_roles'))


#=========================================
# 5) LAYOUT Y SKINS (contrato 2 y 9 del enunciado)
#=========================================
class Layout(_AiDesignBase):
    """26 familias de piel, 52 pieles, layout válido y contraste AA."""

    def test_the_skin_catalog_has_the_contract_families(self):
        self.assertEqual(tuple(SKIN_FAMILIES), CONTRACT_SKIN_FAMILIES)
        #v5: 18 del contrato original + las 8 de los estilos de diseño.
        self.assertEqual(len(SKIN_FAMILIES), 26)
        self.assertEqual(len(SKIN_IDS), 52)
        self.assertEqual(set(SKIN_FAMILY_OF), set(SKIN_IDS))

    def test_every_style_of_the_training_has_skins(self):
        """Los 8 estilos del entrenamiento (STYLE_FAMILIES) tienen pieles y
        toda piel declara un estilo del catálogo."""
        self.assertEqual(len(STYLE_FAMILIES), 8)
        for skin_id, skin in SKINS.items():
            self.assertIn(skin['style'], STYLE_FAMILIES, skin_id)
        for style in STYLE_FAMILIES:
            self.assertTrue(
                any(skin['style'] == style for skin in SKINS.values()),
                f'{style}: sin pieles',
            )

    def test_every_skin_id_is_family_variant(self):
        for skin_id, skin in SKINS.items():
            self.assertEqual(skin_id, f'{skin["family"]}-{skin_id.split("-", 1)[1]}')
            self.assertEqual(skin_id, skin['id'])
            self.assertTrue(skin['label'])
            self.assertIn(skin['family'], CONTRACT_SKIN_FAMILIES)

    def test_every_skin_has_a_valid_layout_budget(self):
        for skin_id, skin in SKINS.items():
            self.assertEqual(set(skin['layout']), set(LAYOUT_ENUMS), skin_id)
            for key, value in skin['layout'].items():
                self.assertIn(value, LAYOUT_ENUMS[key], f'{skin_id}.layout.{key}')

    def test_every_skin_composes_into_a_theme_accepted_by_the_sanitizer(self):
        for skin_id, skin in SKINS.items():
            theme   =   _theme_from_skin(skin)
            self.assertEqual(
                clean_site_theme(theme, has_advanced = True),
                theme,
                f'{skin_id}: la piel no compone un site_theme v2 válido',
            )

    def test_every_skin_palette_passes_aa_text_on_background_and_surface(self):
        for skin_id, skin in SKINS.items():
            palette =   skin['palette']
            self.assertGreaterEqual(_contrast_ratio(palette['text'], palette['bg']), 4.5, skin_id)
            self.assertGreaterEqual(_contrast_ratio(palette['text'], palette['surface']), 4.5, skin_id)

    def test_generated_proposals_declare_a_valid_layout(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            layout  =   _layout_of(proposal)
            self.assertTrue(layout, 'la propuesta no declara layout (contrato 7)')
            self.assertEqual(set(layout), set(LAYOUT_ENUMS), 'layout incompleto')
            for key, value in layout.items():
                self.assertIn(value, LAYOUT_ENUMS[key], f'layout.{key}={value}')

    def test_generated_layout_survives_the_sanitizer(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            layout  =   _layout_of(proposal)
            self.assertEqual(clean_site_theme({'layout': layout}, has_advanced = True),
                             {'layout': layout})

    def test_generated_accent_has_aa_on_the_page_background_for_every_rubro(self):
        #Contrato 9: la combinación piel × layout no puede romper AA. El
        #acento es el color de marca de los botones: tiene que leerse sobre
        #el fondo de la página en los 13 rubros, no solo en el default.
        client, _, _    =   self._premium_client()
        for rubro in R.RUBROS:
            for proposal in _proposals_of(self._generate(client, _rubro_payload(rubro))):
                palette =   proposal['site_theme']['palette']
                skin_id =   _skin_of(proposal).get('id')
                self.assertGreaterEqual(
                    _contrast_ratio(palette['accent'], palette['bg']), 4.5,
                    f'{rubro}/{skin_id}: accent {palette["accent"]} sobre bg {palette["bg"]}',
                )


#=========================================
# 6) BLOQUES V4 (contrato 4)
#=========================================
class BloquesV4(_AiDesignBase):
    """aipricing/aiprocess/aimosaic: solo con el flag, props tipadas saneadas."""

    def _clean(self, block_id, props, variant = None):
        block   =   {'id': block_id, 'enabled': True, 'props': props}
        if variant:
            block['variant'] =   variant
        clean   =   clean_layout_config({'landing': {'blocks': [block]}}, True, True)
        return clean['landing']['blocks'][0]

    def test_new_blocks_are_ai_only_and_catalogued(self):
        specs   =   {
            'aipricing' :   (('cards', 'table'), {'title', 'items'}),
            'aiprocess' :   (('steps', 'rail'), {'title', 'items'}),
            'aimosaic'  :   (('mosaic', 'rail'), {'title', 'caption'}),
        }
        for block_id, (variants, props) in specs.items():
            spec    =   TEMPLATE_BLOCKS['landing'][block_id]
            self.assertTrue(spec.get('ai_only'), f'{block_id} no es ai_only')
            self.assertEqual(tuple(spec['variants']), variants, block_id)
            self.assertEqual(set(spec['props']), props, block_id)

    def test_new_blocks_are_dropped_without_the_flag(self):
        layout  =   {'landing': {'blocks': [{'id': block_id, 'enabled': True} for block_id in NEW_AI_BLOCKS]}}
        self.assertEqual(clean_layout_config(layout, True), {})
        self.assertEqual(clean_layout_config(layout, True, False), {})
        kept    =   clean_layout_config(layout, True, True)['landing']['blocks']
        self.assertEqual([block['id'] for block in kept], list(NEW_AI_BLOCKS))

    def test_new_blocks_do_not_persist_without_the_flag(self):
        client, _, store    =   self._client(*(CUSTOMIZATION + DESIGN_PLUS + DESIGN_ADVANCED))
        response            =   client.patch(
            self.custom_url,
            {'layout_config': {'landing': {'blocks': [
                {'id': block_id, 'enabled': True} for block_id in NEW_AI_BLOCKS
            ]}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        customization       =   StoreCustomization.objects.get(store = store)
        dumped              =   json.dumps(customization.layout_config)
        for block_id in NEW_AI_BLOCKS:
            self.assertNotIn(block_id, dumped)

    def test_pricing_rows_are_typed_and_capped(self):
        rows    =   [{'name': f'Plan {i}', 'price': f'${i}00', 'note': 'n' * 120,
                      'items': ['f' * 100] * 8, 'extra': 'x'} for i in range(6)]
        clean   =   self._clean('aipricing', {'title': 't' * 120, 'items': rows})
        self.assertEqual(len(clean['props']['title']), 80)
        self.assertEqual(len(clean['props']['items']), 4)
        for row in clean['props']['items']:
            self.assertEqual(set(row), {'name', 'price', 'note', 'items'})
            self.assertEqual(len(row['note']), 80)
            self.assertEqual(len(row['items']), 5)
            self.assertTrue(all(len(feature) == 60 for feature in row['items']))

    def test_pricing_requires_name_price_and_two_rows(self):
        self.assertNotIn('props', self._clean('aipricing', {'items': [
            {'name': 'Básico', 'price': '$100'}, {'name': 'Sin precio'}, {'price': '$200'}, 'x',
        ]}))
        clean   =   self._clean('aipricing', {'items': [
            {'name': 'Básico', 'price': '$100'}, {'name': 'Pro', 'price': '$200'},
        ]})
        self.assertEqual(len(clean['props']['items']), 2)

    def test_process_requires_three_steps_and_caps_text(self):
        self.assertNotIn('props', self._clean('aiprocess', {'items': [
            {'title': 'Uno'}, {'title': 'Dos'}, {'text': 'sin título'},
        ]}))
        clean   =   self._clean('aiprocess', {'items': [
            {'title': 'T' * 100, 'text': 'x' * 300} for _ in range(6)
        ]})
        self.assertEqual(len(clean['props']['items']), 5)
        for step in clean['props']['items']:
            self.assertEqual(len(step['title']), 60)
            self.assertEqual(len(step['text']), 160)

    def test_mosaic_text_caps_and_variants(self):
        clean   =   self._clean('aimosaic', {'title': 't' * 120, 'caption': 'c' * 300})
        self.assertEqual(len(clean['props']['title']), 80)
        self.assertEqual(len(clean['props']['caption']), 120)
        clean   =   self._clean('aimosaic', {'title': 'Obras'}, variant = 'rail')
        self.assertEqual(clean['variant'], 'rail')
        self.assertNotIn('variant', self._clean('aimosaic', {'title': 'Obras'}, variant = 'diagonal'))

    def test_every_new_block_uses_a_catalog_variant_and_props(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, _rubro_payload('belleza'))):
            for block in _landing_blocks(proposal):
                if block['id'] not in NEW_AI_BLOCKS:
                    continue
                spec    =   TEMPLATE_BLOCKS['landing'][block['id']]
                self.assertTrue(spec.get('ai_only'), block['id'])
                if block.get('variant'):
                    self.assertIn(block['variant'], spec['variants'])
                for key in (block.get('props') or {}):
                    self.assertIn(key, spec['props'], f'{block["id"]}.{key} fuera del catálogo')

    def test_generated_ai_blocks_are_already_sane(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, _rubro_payload('belleza'))):
            for block in _landing_blocks(proposal):
                if block['id'] not in AI_ONLY_BLOCKS:
                    continue
                dumped  =   json.dumps(block.get('props') or {})
                self.assertNotIn('<', dumped)
                self.assertNotIn('>', dumped)
                props   =   block.get('props') or {}
                if block['id'] == 'aipricing':
                    self.assertTrue(2 <= len(props.get('items', [])) <= 4, props)
                    for row in props['items']:
                        self.assertTrue(row.get('name') and row.get('price'), row)
                elif block['id'] == 'aiprocess':
                    self.assertTrue(3 <= len(props.get('items', [])) <= 5, props)
                elif block['id'] == 'aimosaic':
                    self.assertLessEqual(len(props.get('title', '')), 80)
                    self.assertLessEqual(len(props.get('caption', '')), 120)

    def test_generated_icons_are_accepted(self):
        clean   =   self._clean('aistrip', {'items': [
            {'icon': 'gen:cafe-de-especialidad', 'label': 'Café'},
            {'icon': 'gen:a1', 'label': 'Uno'},
        ]})
        icons   =   [item.get('icon') for item in clean['props']['items']]
        self.assertEqual(icons, ['gen:cafe-de-especialidad', 'gen:a1'])
        clean   =   self._clean('aigrid', {'items': [{'title': 'Piezas', 'icon': 'gen:torno'}]})
        self.assertEqual(clean['props']['items'][0]['icon'], 'gen:torno')

    def test_invalid_icons_are_dropped(self):
        for icon in ('gen:', 'gen:con espacio', 'gen:' + 'a' * 25, 'gen:a_b',
                     'gen:ñandu', 'brand:logo', 'no-existe'):
            clean   =   self._clean('aistrip', {'items': [{'icon': icon, 'label': 'Item'}]})
            self.assertNotIn('icon', clean['props']['items'][0], f'{icon} sobrevivió')

    def test_icon_catalog_is_the_lucide_set(self):
        self.assertGreaterEqual(len(AI_ICONS), 110)
        self.assertLess(len(AI_ICONS), 200)
        for icon in ('coffee', 'scissors', 'shopping-bag', 'stethoscope', 'plane', 'palette'):
            self.assertIn(icon, AI_ICONS)
        for icon in AI_ICONS:
            self.assertRegex(icon, r'^[a-z0-9-]+$')

    def test_ai_elements_respect_the_configured_maximum(self):
        client, _, _    =   self._premium_client()
        payload         =   {'rubro': 'belleza', 'tone': 'moderno',
                             'goals': ['dar_confianza', 'mostrar_servicios'],
                             'must_have': ['offers', 'contact', 'faq', 'benefits']}
        for proposal in _proposals_of(self._generate(client, payload)):
            ai_ids  =   [block['id'] for block in _landing_blocks(proposal) if block['id'] in AI_ONLY_BLOCKS]
            self.assertLessEqual(len(ai_ids), R.AI_ELEMENT_MAX, ai_ids)
            self.assertEqual(len(ai_ids), len(set(ai_ids)))

    def test_ai_only_blocks_never_survive_without_the_flag(self):
        layout  =   {'landing': {'blocks': [{'id': block_id, 'enabled': True} for block_id in sorted(AI_ONLY_BLOCKS)]}}
        self.assertEqual(clean_layout_config(layout, True), {})
        self.assertTrue(clean_layout_config(layout, True, True)['landing']['blocks'])

    def test_texts_lists_and_html_are_sanitized(self):
        clean   =   self._clean('aiquote', {'text': 'x' * 400, 'author': 'a' * 120})
        self.assertEqual(len(clean['props']['text']), 160)
        self.assertEqual(len(clean['props']['author']), 40)
        clean   =   self._clean('aicheck', {'items': [{'text': f'Item {i}'} for i in range(9)]})
        self.assertEqual(len(clean['props']['items']), 6)
        clean   =   self._clean('aigrid', {'items': ['x', 42, None, {'title': 'Válido'}]})
        self.assertEqual(clean['props']['items'], [{'title': 'Válido'}])
        clean   =   self._clean('aiquote', {'text': '<b>Hola</b><script>alert(1)</script>'})
        dumped  =   json.dumps(clean['props'])
        self.assertNotIn('<', dumped)
        self.assertNotIn('>', dumped)


#=========================================
# 7) APPLY PUBLICA EN UN SOLO PASO (contrato 5)
#=========================================
class Apply(_AiDesignBase):
    """apply aplica el borrador Y publica theme v2 + layout, con snapshot."""

    PUBLISH_PAYLOAD =   {'rubro': 'belleza', 'tone': 'moderno',
                         'goals': ['dar_confianza', 'mostrar_servicios'],
                         'must_have': ['offers', 'contact', 'faq']}

    def _proposal_and_seed(self, client, payload = None):
        body    =   self._generate(client, payload or self.PUBLISH_PAYLOAD).json()
        return body['seed'], body['proposals'][0]

    def test_apply_publishes_and_reports_success(self):
        client, _, _    =   self._premium_client()
        seed, proposal  =   self._proposal_and_seed(client)
        response        =   self._apply(client, seed, proposal['id'])
        self.assertEqual(response.status_code, 200, response.content[:400])
        body            =   response.json()
        self.assertEqual(body['Exito'], 'Tu web ya está publicada')
        self.assertIs(body['published'], True)
        for key in ('customization', 'storage'):
            self.assertIn(key, body)

    def test_apply_writes_the_published_layout_not_only_the_draft(self):
        client, _, store    =   self._premium_client()
        seed, proposal      =   self._proposal_and_seed(client)
        self.assertEqual(self._apply(client, seed, proposal['id']).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        published           =   customization.layout_config['landing']['blocks']
        self.assertEqual(
            [block['id'] for block in published],
            [block['id'] for block in _landing_blocks(proposal)],
        )
        self.assertTrue({block['id'] for block in published} & AI_ONLY_BLOCKS)
        self.assertEqual(customization.layout_config, customization.layout_config_draft)
        self.assertEqual(customization.site_theme, customization.site_theme_draft)

    def test_apply_publishes_the_template_and_theme_v2(self):
        client, _, store    =   self._premium_client()
        seed, proposal      =   self._proposal_and_seed(client)
        self.assertEqual(self._apply(client, seed, proposal['id']).status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(customization.template, proposal['template'])
        self.assertEqual(customization.site_theme, proposal['site_theme'])
        theme               =   customization.site_theme or {}
        for section in ('typography', 'layout', 'skin'):
            self.assertIn(section, theme, f'el theme publicado no trae {section}')
        self.assertEqual(set(theme['typography']['roles']), set(CONTRACT_ROLES))
        self.assertEqual(theme['skin']['id'], _skin_of(proposal)['id'])
        self.assertEqual(theme['layout'], _layout_of(proposal))

    def test_apply_creates_a_studio_version_with_the_published_snapshot(self):
        client, _, store    =   self._premium_client()
        seed, proposal      =   self._proposal_and_seed(client)
        self.assertEqual(self._apply(client, seed, proposal['id']).status_code, 200)
        versions            =   StudioVersion.objects.filter(store = store)
        self.assertEqual(versions.count(), 1)
        snapshot            =   versions[0].snapshot
        customization       =   StoreCustomization.objects.get(store = store)
        self.assertEqual(snapshot['layout_config'], customization.layout_config)
        self.assertEqual(snapshot['template'], customization.template)

    def test_apply_is_idempotent_for_the_same_seed_and_proposal(self):
        client, _, store    =   self._premium_client()
        seed, proposal      =   self._proposal_and_seed(client)
        first               =   self._apply(client, seed, proposal['id'])
        self.assertEqual(first.status_code, 200)
        customization       =   StoreCustomization.objects.get(store = store)
        published           =   json.dumps(customization.layout_config, sort_keys = True)
        second              =   self._apply(client, seed, proposal['id'])
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
# 8) REGRESIONES v2/v3 (contrato 6 y 7)
#=========================================
class Regresiones(_AiDesignBase):
    """Gating, throttle, determinismo, autofill, copy, imágenes, color, noche,
    portada, overrides por contenedor y web pública."""

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

    def test_every_proposal_declares_the_v4_fields(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client)):
            for key in ('label', 'why', 'template', 'layout_config', 'site_theme',
                        'theme_choice', 'night_mode', 'cover', 'theme', 'theme_toggle',
                        'copy', 'copy_draft', 'image_requests', 'notes',
                        'skin', 'style_source', 'typography_roles', 'layout',
                        'variety', 'redesign'):
                self.assertIn(key, proposal)
            self.assertIn(proposal['cover']['mode'], ('photo', 'logo'))
            self.assertIn(proposal['theme'], ('light', 'dark'))
            self.assertLessEqual(len(proposal['cover']['reason']), 120)

    def test_block_ids_belong_to_the_template_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, Apply.PUBLISH_PAYLOAD)):
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
        for proposal in _proposals_of(self._generate(client, Apply.PUBLISH_PAYLOAD)):
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

    #---- color de marca ----------------------------------------------
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

    def test_accent_has_aa_against_the_page_background(self):
        for brand in (self.BRAND, '#ffff00', ''):
            for proposal in self._proposals({'brand_color': brand}):
                palette =   proposal['site_theme']['palette']
                self.assertGreaterEqual(_contrast_ratio(palette['accent'], palette['bg']), 4.5, palette)

    def test_low_contrast_brand_color_is_adjusted_but_keeps_the_user_source(self):
        for proposal in self._proposals({'brand_color': '#ffff00'}):
            palette =   proposal['site_theme']['palette']
            self.assertEqual(proposal['theme_choice']['source'], 'user')
            self.assertGreaterEqual(_contrast_ratio(palette['accent'], palette['bg']), 4.5)

    def test_invalid_brand_color_is_ignored(self):
        for brand in ('rojo', '#zzzzzz', 'url(x)', '#12345', 'rgb(0,0,0)'):
            for proposal in self._proposals({'brand_color': brand}):
                self.assertEqual(proposal['theme_choice']['source'], 'ai', brand)
                self.assertRegex(proposal['theme_choice']['accent'], r'^#[0-9a-f]{6}$')

    def test_brand_color_is_normalized_to_lowercase_hex(self):
        from StoreApp.domains.stores.services.ai_design import _norm_hex
        self.assertEqual(_norm_hex('#1D4ED8'), self.BRAND)
        for proposal in self._proposals({'brand_color': '#1D4ED8'}):
            self.assertRegex(proposal['theme_choice']['accent'], r'^#[0-9a-f]{6}$')

    #---- modo noche ---------------------------------------------------
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

    def test_disabled_or_invalid_night_mode_keeps_the_toggle_off(self):
        client, _, _    =   self._premium_client()
        for payload in ({'night_mode': {'enabled': False, 'default': 'dark'}},
                        {'night_mode': {'enabled': 'sí', 'default': 'sepia'}},
                        {}):
            for proposal in _proposals_of(self._generate(client, payload)):
                self.assertFalse(proposal['theme_toggle'])
                self.assertFalse(proposal['night_mode']['enabled'])
                self.assertIn(proposal['night_mode']['default'], ('light', 'dark'))
                self.assertIn(proposal['theme'], ('light', 'dark'))

    #---- portada con logo ---------------------------------------------
    def _with_logo(self, store):
        customization           =   StoreCustomization.objects.get_or_create(store = store)[0]
        customization.logo_key  =   'stores/x/logo.webp'
        customization.save(update_fields = ['logo_key'])
        return customization

    def test_logo_choice_uses_logo_hero_and_solid_background(self):
        client, _, store    =   self._premium_client()
        self._with_logo(store)
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'logo'})):
            self.assertEqual(proposal['cover']['mode'], 'logo')
            self.assertEqual(_block_of(proposal, 'hero')['variant'], 'logo')
            self.assertNotEqual(proposal['site_theme']['background']['type'], 'image')

    def test_auto_with_logo_and_without_cover_also_uses_the_logo(self):
        client, _, store    =   self._premium_client()
        self._with_logo(store)
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'auto'})):
            self.assertEqual(proposal['cover']['mode'], 'logo')
            self.assertEqual(_block_of(proposal, 'hero')['variant'], 'logo')

    def test_auto_with_cover_photo_keeps_the_photo(self):
        client, _, store    =   self._premium_client()
        customization       =   self._with_logo(store)
        customization.cover_key =   'stores/x/cover.webp'
        customization.save(update_fields = ['cover_key'])
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'auto'})):
            self.assertEqual(proposal['cover']['mode'], 'photo')
            self.assertNotEqual(_block_of(proposal, 'hero').get('variant'), 'logo')

    def test_photo_choice_ignores_the_logo(self):
        client, _, store    =   self._premium_client()
        self._with_logo(store)
        for proposal in _proposals_of(self._generate(client, {'cover_choice': 'foto'})):
            self.assertEqual(proposal['cover']['mode'], 'photo')
            self.assertNotEqual(_block_of(proposal, 'hero').get('variant'), 'logo')

    #---- overrides por contenedor (site_theme.blocks) ------------------
    ALL_STYLES  =   {'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'spacious',
                     'surface': 'glass', 'align': 'center', 'accent': '#AABBCC'}

    def test_block_overrides_are_accepted_and_normalized(self):
        clean   =   clean_site_theme({'blocks': {'hero': dict(self.ALL_STYLES)}}, has_advanced = True)
        self.assertEqual(clean, {'blocks': {'hero': {
            'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'spacious',
            'surface': 'glass', 'align': 'center', 'accent': '#aabbcc',
        }}})

    def test_unknown_block_id_is_dropped_without_breaking_the_theme(self):
        clean   =   clean_site_theme(
            {'blocks': {'inventado': {'radius': 'xl'}, 'hero': {'radius': 'xl'}},
             'palette': {'accent': '#123456'}},
            has_advanced = True,
        )
        self.assertEqual(clean['blocks'], {'hero': {'radius': 'xl'}})
        self.assertEqual(clean['palette'], {'accent': '#123456'})

    def test_unknown_style_key_inside_a_known_block_is_rejected(self):
        #Contrato del sanitizador: el id desconocido se descarta, pero una
        #clave desconocida dentro de un bloque válido es 400.
        with self.assertRaises(DRFValidationError):
            clean_site_theme({'blocks': {'hero': {'radius': 'xl', 'inventado': 'x'}}},
                             has_advanced = True)

    def test_invalid_block_enum_or_hex_is_rejected(self):
        for styles in ({'align': 'diagonal'}, {'radius': 'gigante'}, {'accent': 'rojo'}):
            with self.assertRaises(DRFValidationError, msg = f'{styles} aceptado'):
                clean_site_theme({'blocks': {'hero': styles}}, has_advanced = True)

    def test_more_than_twelve_blocks_are_rejected(self):
        known   =   list(TEMPLATE_BLOCKS['landing'])[:13]
        self.assertEqual(len(known), 13)
        with self.assertRaises(DRFValidationError):
            clean_site_theme(
                {'blocks': {block_id: {'radius': 'xl'} for block_id in known}},
                has_advanced = True,
            )

    def test_block_section_requires_design_advanced(self):
        payload =   {'blocks': {'hero': {'radius': 'xl'}}}
        self.assertEqual(clean_site_theme(payload, has_plus = True, has_style = True), {})
        self.assertEqual(clean_site_theme(payload, has_style = True), {})
        self.assertTrue(clean_site_theme(payload, has_advanced = True))

    def test_block_section_does_not_persist_without_design_advanced(self):
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

    def test_block_section_persists_with_design_advanced(self):
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

    def test_generated_block_overrides_use_the_closed_catalog(self):
        client, _, _    =   self._premium_client()
        for proposal in _proposals_of(self._generate(client, Apply.PUBLISH_PAYLOAD)):
            blocks  =   (proposal['site_theme'].get('blocks') or {})
            self.assertLessEqual(len(blocks), 12)
            for block_id, styles in blocks.items():
                self.assertIn(block_id, TEMPLATE_BLOCKS['landing'])
                self.assertTrue(set(styles).issubset(AI_BLOCK_STYLE_KEYS), styles)
                self.assertEqual(clean_site_theme(
                    {'blocks': {block_id: styles}},
                    has_plus = True, has_advanced = True, has_style = True,
                )['blocks'][block_id], styles)

    #---- web pública --------------------------------------------------
    def _public_store(self, template):
        client, profile, store  =   self._client(*(PUBLIC_LINK + CUSTOMIZATION + AI_DESIGN))
        store.is_published      =   True
        store.save(update_fields = ['is_published'])
        StoreCustomization.objects.create(store = store, template = template)
        return store

    def test_public_page_renders_the_ai_template_instead_of_falling_back(self):
        store       =   self._public_store('ai_lumen')
        response    =   APIClient().get(reverse('Stores-public', kwargs = {'slug': store.slug}))
        self.assertEqual(response.status_code, 200, response.content[:400])
        body        =   response.json()
        self.assertEqual(body['customization']['template'], 'ai_lumen')
        self.assertIn('ai_lumen', body['allowed_templates'])
        self.assertIn('ai_pulse', body['allowed_templates'])

    def test_public_page_serves_a_legacy_template(self):
        store       =   self._public_store('street')
        response    =   APIClient().get(reverse('Stores-public', kwargs = {'slug': store.slug}))
        self.assertEqual(response.status_code, 200, response.content[:400])
        body        =   response.json()
        self.assertEqual(body['customization']['template'], 'street')
        self.assertIn('street', body['allowed_templates'])
