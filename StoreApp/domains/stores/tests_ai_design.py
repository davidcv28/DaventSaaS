#Tests del motor de diseño automático (ai_design): contrato, invariantes y
#determinismo. Los helpers siguen el patrón de tests.py del dominio (plan +
#suscripción vigente con los beneficios pedidos).

import io
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS, clean_layout_config
from StoreApp.domains.stores.models import Store, StoreCarouselImage, StoreCustomization, StoreGalleryImage, StudioVersion
from StoreApp.domains.stores.site_theme import clean_site_theme
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.services import ai_design_skins as SKIN
from StoreApp.domains.stores.services.ai_design_skins import SKINS, SKIN_IDS, STYLE_FAMILIES
from StoreApp.domains.stores.services.ai_design_typography import (
    BODY_ROLES, FONT_SLUGS, TYPOGRAPHY_ROLES,
    TYPE_CASES, TYPE_LEADING, TYPE_SIZES, TYPE_TRACKING,
)
from StoreApp.domains.stores.services import storage
from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services.ai_design import generate as generate_ai_design
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL  =   '/api/stores/'
AI_URL      =   f'{STORES_URL}ai-design/'
APPLY_URL   =   f'{STORES_URL}ai-design/apply/'
IMAGE_URL   =   f'{STORES_URL}ai-design/image/'


def _grant(profile, **benefits):
    plan    =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username} {profile.pk}')
    for code, value in benefits.items():
        kind        =   Benefit.FLAG if isinstance(value, bool) else Benefit.LIMIT
        benefit     =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': kind})[0]
        PlanBenefit.objects.create(
            plan        =   plan,
            benefit     =   benefit,
            enabled     =   value if kind == Benefit.FLAG else True,
            value       =   None if kind == Benefit.FLAG else value,
        )
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    return plan


def _make_user(username = 'duenio'):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'55{len(username):02d}'[-4:])
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'29{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   True,
        phone           =   f'1122{abs(hash(username)) % 10**8:08d}',
    )
    return user, profile


class AiDesignBase(TestCase):

    def setUp(self):
        cache.clear()

    def _store(self, advanced = True, ai = True, customization = True, products = 0, username = 'duenio', limits = False):
        user, profile   =   _make_user(username)
        extra           =   {'max_gallery_images': 10, 'max_images': 30, 'max_storage_mb': 50} if limits else {}
        _grant(
            profile,
            has_public_link         =   True,
            has_customization       =   customization,
            has_design_plus         =   advanced,
            has_design_advanced     =   advanced,
            has_ai_design           =   ai,
            **extra,
        )
        store   =   Store.objects.create(user = profile, slug = f'tienda-{username}')
        draft   =   StoreCustomization.objects.create(
            store           =   store,
            display_name    =   'Panadería La Espiga',
            site_templates  =   ['landing', 'catalog', 'services'],
        )
        for index in range(products):
            Product.objects.create(store = store, name = f'Producto {index}', price = 100, image_key = f'k{index}')
        return store, draft

    def _client(self, store):
        client  =   APIClient()
        client.force_authenticate(user = store.user.user)
        return client


class AiDesignGenerateTests(AiDesignBase):

    def test_deterministic_same_payload_same_json(self):
        store, _    =   self._store(products = 5)
        client      =   self._client(store)
        payload     =   {'rubro': 'comercio', 'tone': 'moderno', 'goals': ['vender_online']}
        first       =   client.post(AI_URL, payload, format = 'json')
        second      =   client.post(AI_URL, payload, format = 'json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(first.json()['engine'], 'ai-design/7')

    def test_two_or_three_proposals_distinct(self):
        store, _    =   self._store(products = 8)
        data        =   self._client(store).post(AI_URL, {'rubro': 'gastronomia'}, format = 'json').json()
        self.assertIn(len(data['proposals']), (2, 3))
        ids         =   [proposal['id'] for proposal in data['proposals']]
        self.assertEqual(ids, [f'p{index}' for index in range(1, len(ids) + 1)])
        #Dos propuestas nunca son la misma: cambia la plantilla o, si se
        #repite (plan con una sola), el orden/variante de los bloques.
        shapes      =   [
            (proposal['template'], tuple((block['id'], block.get('variant')) for block in proposal['layout_config']['landing']['blocks']))
            for proposal in data['proposals']
        ]
        self.assertEqual(len(shapes), len(set(shapes)))

    def test_block_ids_always_in_whitelist(self):
        store, _    =   self._store(products = 6)
        data        =   self._client(store).post(AI_URL, {'rubro': 'arte', 'tone': 'audaz'}, format = 'json').json()
        for proposal in data['proposals']:
            for surface, config in proposal['layout_config'].items():
                self.assertIn(surface, TEMPLATE_BLOCKS)
                for block in config['blocks']:
                    self.assertIn(block['id'], TEMPLATE_BLOCKS[surface])
                    spec    =   TEMPLATE_BLOCKS[surface][block['id']]
                    if block.get('variant'):
                        self.assertIn(block['variant'], spec.get('variants', ()))

    def test_locked_blocks_stay_enabled(self):
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        for proposal in data['proposals']:
            catalog =   {block['id']: block for block in proposal['layout_config']['catalog']['blocks']}
            services =  {block['id']: block for block in proposal['layout_config']['services']['blocks']}
            self.assertTrue(catalog['grid']['enabled'])
            self.assertTrue(services['picker']['enabled'])

    def test_premium_block_dropped_without_design_advanced(self):
        store, _    =   self._store(advanced = False, products = 4)
        StoreCarouselImage.objects.create(store = store, image_key = 'carousel/1.webp')
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        for proposal in data['proposals']:
            ids     =   [block['id'] for block in proposal['layout_config']['catalog']['blocks']]
            self.assertNotIn('banner', ids)

    def test_template_outside_plan_never_returned(self):
        #Plan sin has_ai_design ni has_design_plus: la whitelist real queda
        #en el nivel Básico. Se llama al motor directo porque el endpoint
        #responde 403 sin el flag (acá probamos la whitelist, no el gate).
        store, _    =   self._store(advanced = False, ai = False, products = 3)
        data        =   generate_ai_design(store, {})
        allowed     =   set(allowed_templates_of(store.user))
        self.assertEqual(allowed, {'raiz', 'alimentos'})
        for proposal in data['proposals']:
            self.assertIn(proposal['template'], allowed)

    def test_blocks_without_data_are_disabled(self):
        #Tienda vacía: sin testimonios, sin FAQs, sin galería.
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        landing     =   {block['id']: block for block in data['proposals'][0]['layout_config']['landing']['blocks']}
        for block_id in ('testimonials', 'faq', 'gallery', 'stats'):
            if block_id in landing:
                self.assertFalse(landing[block_id]['enabled'])
        self.assertIn('testimonials', [item['code'] for item in data['missing']])

    def test_missing_is_list_of_objects(self):
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        self.assertTrue(data['missing'])
        for item in data['missing']:
            self.assertEqual(set(item), {'code', 'label', 'hint', 'action'})
            self.assertTrue(item['code'] and item['label'] and item['action'])

    def test_hero_first_and_contact_last(self):
        store, _    =   self._store(products = 6)
        data        =   self._client(store).post(AI_URL, {'goals': ['vender_online']}, format = 'json').json()
        blocks      =   [block['id'] for block in data['proposals'][0]['layout_config']['landing']['blocks']]
        self.assertEqual(blocks[0], 'hero')
        self.assertEqual(blocks[-1], 'contact')


def _aa(a, b):
    """WCAG 2.1 (misma fórmula que site_theme._contrast_ratio)."""
    def channel(value):
        s   =   value / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    def lum(hex_value):
        h   =   hex_value.lstrip('#')
        return sum(
            weight * channel(int(h[index:index + 2], 16))
            for weight, index in ((0.2126, 0), (0.7152, 2), (0.0722, 4))
        )
    la, lb  =   lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class AiDesignSkinAndContrastTests(AiDesignBase):
    """v6: el look que elige el motor llega a la web publicada y el texto se
    lee (AA en los cinco pares, claro y oscuro)."""

    def _proposals(self, store, payload = None):
        return self._client(store).post(AI_URL, payload or {'rubro': 'gastronomia'}, format = 'json').json()['proposals']

    def test_every_proposal_ships_style_skin_and_style_colors(self):
        store, _    =   self._store(products = 6)
        for proposal in self._proposals(store):
            theme   =   proposal['site_theme']
            self.assertIn('skin', theme)
            self.assertIn(theme['skin']['id'], SKIN_IDS)
            self.assertEqual(theme['style']['id'], SKIN.SKIN_STYLE_PRESET[proposal['skin']['family']])
            self.assertTrue(theme['typography']['roles'])
            self.assertEqual(set(theme['styleColors']), {'light', 'dark'})

    def test_style_colors_pass_aa_in_both_modes(self):
        store, _    =   self._store(products = 6)
        for proposal in self._proposals(store):
            for mode, style_set in proposal['site_theme']['styleColors'].items():
                fonts       =   style_set['fonts']
                containers  =   style_set['containers']
                self.assertGreaterEqual(_aa(fonts['heading'], containers['bg']), 4.5, f'{mode} heading/bg')
                self.assertGreaterEqual(_aa(fonts['muted'], containers['bg']), 4.5, f'{mode} muted/bg')
                self.assertGreaterEqual(_aa(fonts['heading'], containers['surface']), 4.5, f'{mode} heading/surface')
                self.assertGreaterEqual(_aa(fonts['muted'], containers['surface']), 4.5, f'{mode} muted/surface')
                self.assertGreaterEqual(_aa(containers['onSurface'], containers['surface']), 4.5, f'{mode} onSurface')

    def test_brand_accent_keeps_white_text_aa_on_band_and_buttons(self):
        store, _    =   self._store(products = 3)
        #Acento claro del dueño: la banda del hero y el botón sólido pintan
        #texto blanco, así que la tinta tiene que corregirse.
        for accent in ('#facc15', '#a7f3d0', '#ffffff'):
            proposal    =   self._proposals(store, {'brand_color': accent})[0]
            ink         =   proposal['site_theme']['palette']['secondary']
            self.assertGreaterEqual(_aa('#ffffff', ink), 4.5, accent)

    def test_basic_plan_still_gets_skin_and_style_colors(self):
        store, _    =   self._store(advanced = False, ai = False, products = 3)
        data        =   generate_ai_design(store, {})
        for proposal in data['proposals']:
            theme   =   proposal['site_theme']
            self.assertIn(theme['skin']['id'], SKIN_IDS)
            self.assertIn('styleColors', theme)
            #El resto del tema sigue reservado al plan.
            self.assertNotIn('background', theme)
            self.assertNotIn('buttons', theme)

    def test_apply_publishes_skin_and_style_colors(self):
        store, _    =   self._store(products = 4)
        client      =   self._client(store)
        data        =   client.post(AI_URL, {'rubro': 'indumentaria'}, format = 'json').json()
        proposal    =   data['proposals'][0]
        response    =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': proposal['id']}, format = 'json')
        self.assertEqual(response.status_code, 200, response.content)
        draft   =   StoreCustomization.objects.get(store = store)
        for theme in (draft.site_theme, draft.site_theme_draft):
            self.assertEqual(theme['skin']['id'], proposal['site_theme']['skin']['id'])
            self.assertIn('styleColors', theme)
            self.assertEqual(theme['style']['id'], proposal['site_theme']['style']['id'])
        public  =   APIClient().get(f'{STORES_URL}public/{store.slug}/')
        self.assertEqual(public.status_code, 200)
        theme   =   public.json()['customization']['site_theme']
        self.assertEqual(theme['skin']['id'], proposal['site_theme']['skin']['id'])
        self.assertIn('styleColors', theme)

    def test_proposals_differ_in_layout_not_only_color(self):
        store, _    =   self._store(products = 8)
        proposals   =   self._proposals(store, {'rubro': 'gastronomia', 'goals': ['vender_online']})
        self.assertGreaterEqual(len(proposals), 2)
        signatures  =   [
            (proposal['template'], tuple(
                (block['id'], block.get('variant'))
                for surface in ('landing', 'catalog', 'services')
                for block in proposal['layout_config'][surface]['blocks']
            ))
            for proposal in proposals
        ]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_requested_style_wins_and_unknown_style_is_ignored(self):
        store, _    =   self._store(products = 4)
        data        =   self._client(store).post(
            AI_URL, {'styles': ['luxury', 'no-existe']}, format = 'json'
        )
        self.assertEqual(data.status_code, 200)
        self.assertEqual(data.json()['proposals'][0]['variety']['style'], 'luxury')

    def test_five_contrast_pairs_pass_aa_across_the_whole_catalog(self):
        """A.3: los 5 pares × 2 modos × 52 pieles × 8 estilos.

        El motor no emite la paleta cruda de la piel: la pasa por `_theme`
        (acento del catálogo de la piel, tinta de banda, neutros calmados y
        `styleColors`). Se verifica lo que de verdad llega a la web.
        """
        import random as _random
        from StoreApp.domains.stores.services import ai_design as A
        answers =   {
            'tone': 'moderno', 'brand_color': None, 'night_mode': None,
            'goals': ['vender_online'], 'must_have': [],
        }
        checked     =   0
        seen_styles =   set()
        for skin_id, skin in SKINS.items():
            seen_styles.add(skin['style'])
            for index, accent in enumerate(skin['accents']):
                theme, _    =   A._theme(skin, 'grotesk-clean', answers, _random.Random(0), index)
                palette     =   theme['palette']
                surface     =   palette.get('surface') or palette['bg']
                pairs       =   {
                    'text/bg'           :   (palette['text'], palette['bg']),
                    'muted/bg'          :   (palette['muted'], palette['bg']),
                    'text/surface'      :   (palette['text'], surface),
                    'muted/surface'     :   (palette['muted'], surface),
                    'white/band'        :   ('#ffffff', palette['secondary']),
                    'accent/bg'         :   (palette['accent'], palette['bg']),
                    'accent/surface'    :   (palette['accent'], surface),
                }
                for label, (fg, bg) in pairs.items():
                    self.assertGreaterEqual(
                        _aa(fg, bg), 4.5, f'{skin_id} {accent} {label}: {fg} sobre {bg}'
                    )
                for mode, style_set in theme['styleColors'].items():
                    containers  =   style_set['containers']
                    fonts       =   style_set['fonts']
                    self.assertGreaterEqual(_aa(fonts['heading'], containers['bg']), 4.5, f'{skin_id} {mode} heading/bg')
                    self.assertGreaterEqual(_aa(fonts['heading'], containers['surface']), 4.5, f'{skin_id} {mode} heading/surface')
                    self.assertGreaterEqual(_aa(fonts['muted'], containers['bg']), 4.5, f'{skin_id} {mode} muted/bg')
                    self.assertGreaterEqual(_aa(fonts['muted'], containers['surface']), 4.5, f'{skin_id} {mode} muted/surface')
                    self.assertGreaterEqual(_aa(fonts['link'], containers['bg']), 4.5, f'{skin_id} {mode} link/bg')
                    self.assertGreaterEqual(_aa(containers['onSurface'], containers['surface']), 4.5, f'{skin_id} {mode} onSurface')
                checked += 1
        self.assertEqual(checked, len(SKIN_IDS) * 3)
        self.assertEqual(len(seen_styles), 8)

    def test_surface_stays_within_eight_percent_of_the_background(self):
        """A.1-3: un card blanco puro sobre papel crema se ve \"pegado\".

        El motor compone el tema con la superficie calmada; la paleta cruda
        de la piel es el presupuesto de origen, no lo que se publica.
        """
        import random as _random
        from StoreApp.domains.stores.services import ai_design as A
        answers =   {'tone': 'moderno', 'brand_color': None, 'night_mode': None,
                     'goals': ['vender_online'], 'must_have': []}
        for skin_id, skin in SKINS.items():
            theme, _    =   A._theme(skin, 'grotesk-clean', answers, _random.Random(0), 0)
            palette     =   theme['palette']
            span        =   max(_aa(palette['text'], palette['bg']) - 1, 0.001)
            delta       =   abs(_aa(palette['surface'], palette['bg']) - 1) / span
            self.assertLessEqual(delta, 0.08, f'{skin_id}: superficie a >8 % del fondo')

    def test_brand_color_palette_passes_aa_on_bg_and_surface(self):
        """A.3/A.4: el acento del dueño no puede degradar los neutros.

        Los pares de la paleta se verifican también sobre los cards: un muted
        que solo se midió contra el fondo puede quedar al borde sobre la
        superficie (era el caso de `brutal-concrete` con marca clara).
        """
        import random as _random
        from StoreApp.domains.stores.services import ai_design as A
        answers =   {'tone': 'moderno', 'brand_color': None, 'night_mode': None,
                     'goals': ['vender_online'], 'must_have': []}
        for skin_id, skin in SKINS.items():
            for brand in ('#facc15', '#a7f3d0', '#ffffff', '#000000', '#ff4d00'):
                answers['brand_color']  =   brand
                theme, _    =   A._theme(skin, 'grotesk-clean', answers, _random.Random(0), 0)
                palette     =   theme['palette']
                surface     =   palette['surface']
                pairs       =   {
                    'text/bg'       :   (palette['text'], palette['bg']),
                    'muted/bg'      :   (palette['muted'], palette['bg']),
                    'text/surface'  :   (palette['text'], surface),
                    'muted/surface' :   (palette['muted'], surface),
                    'accent/bg'     :   (palette['accent'], palette['bg']),
                    'accent/surface':   (palette['accent'], surface),
                    'white/band'    :   ('#ffffff', palette['secondary']),
                }
                for label, (fg, bg) in pairs.items():
                    self.assertGreaterEqual(
                        _aa(fg, bg), 4.5, f'{skin_id} {brand} {label}: {fg} sobre {bg}'
                    )

    def test_dark_set_is_not_the_light_one_inverted(self):
        """A.1-5: en oscuro el fondo baja de 0.1 y la superficie se despega
        hacia arriba (≥ 1.08×), no se hunde en el fondo."""
        import random as _random
        from StoreApp.domains.stores.services import ai_design as A
        answers =   {'tone': 'moderno', 'brand_color': None, 'night_mode': None,
                     'goals': ['vender_online'], 'must_have': []}
        for skin_id, skin in SKINS.items():
            theme, _    =   A._theme(skin, 'grotesk-clean', answers, _random.Random(0), 0)
            dark        =   theme['styleColors']['dark']['containers']
            bg_lum      =   A._luminance(dark['bg'])
            surface_lum =   A._luminance(dark['surface'])
            self.assertLess(bg_lum, 0.1, f'{skin_id}: el modo oscuro no es oscuro')
            self.assertGreaterEqual(
                surface_lum, bg_lum * 1.08,
                f'{skin_id}: la superficie oscura se hunde en el fondo',
            )

    def test_emitted_themes_survive_the_sanitizer_for_every_skin(self):
        """El motor emite sets que ya pasan: `_v_style_set` no puede dar 400."""
        import random as _random
        from StoreApp.domains.stores.services import ai_design as A
        answers =   {'tone': 'serio', 'brand_color': None, 'night_mode': None,
                     'goals': ['dar_confianza'], 'must_have': []}
        for skin_id, skin in SKINS.items():
            theme, _    =   A._theme(skin, 'serif-editorial', answers, _random.Random(1), 0)
            #Sin tienda no hay plan: la sección `style` se OMITE (nunca null).
            self.assertNotIn('style', theme, skin_id)
            clean       =   clean_site_theme(theme, has_advanced = True)
            self.assertEqual(clean['styleColors'], theme['styleColors'], skin_id)
            self.assertEqual(clean['palette']['surface'], theme['palette']['surface'], skin_id)

    def test_style_preset_is_always_a_known_preset_the_plan_can_carry(self):
        """A.4: style.id sale del mapeo explícito y su plantilla entra en el plan."""
        from StoreApp.domains.stores.services.ai_design_skins import STYLE_PRESET_TEMPLATES
        store, _    =   self._store(products = 3)
        allowed     =   set(allowed_templates_of(store.user))
        for proposal in generate_ai_design(store, {})['proposals']:
            style   =   proposal['site_theme']['style']
            self.assertEqual(style['id'], SKIN.SKIN_STYLE_PRESET[proposal['skin']['family']])
            self.assertIn(STYLE_PRESET_TEMPLATES[style['id']], allowed, proposal['skin']['family'])

    def test_proposals_are_scored_and_explain_what_changed(self):
        store, _    =   self._store(products = 6)
        for proposal in self._proposals(store):
            score   =   proposal['score']
            self.assertEqual(set(score), {'contrast', 'harmony', 'hierarchy', 'fit', 'total', 'issues'})
            self.assertEqual(score['contrast'], 100, proposal['id'])
            self.assertTrue(score['total'] >= 80)
            look    =   proposal['look']
            self.assertGreaterEqual(len(look['changed']), 3)
            self.assertEqual(look['accent'], proposal['site_theme']['palette']['accent'])
            self.assertIn(look['mode'], ('light', 'dark'))
            self.assertEqual(look['structure']['landing'][0], 'hero')

    def test_basic_plan_never_gets_skin_outside_level(self):
        #La piel sobrevive al plan Básico, pero la plantilla sigue siendo de
        #su nivel: la piel es un presupuesto visual, no una plantilla.
        store, _    =   self._store(advanced = False, ai = False)
        allowed     =   set(allowed_templates_of(store.user))
        for proposal in generate_ai_design(store, {})['proposals']:
            self.assertIn(proposal['template'], allowed)
            self.assertIn(proposal['site_theme']['skin']['id'], SKIN_IDS)


class AiDesignGateTests(AiDesignBase):

    def test_403_without_customization(self):
        store, _    =   self._store(customization = False)
        response    =   self._client(store).post(AI_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_403_without_ai_design(self):
        store, _    =   self._store(ai = False)
        response    =   self._client(store).post(AI_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_403_apply_without_ai_design(self):
        store, _    =   self._store(ai = False)
        response    =   self._client(store).post(APPLY_URL, {'seed': 1, 'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_throttle_after_limit(self):
        store, _    =   self._store()
        client      =   self._client(store)
        codes       =   [client.post(AI_URL, {}, format = 'json').status_code for _ in range(21)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(codes[0], 200)


class AiDesignApplyTests(AiDesignBase):

    def _generate(self, client, payload = None):
        return client.post(AI_URL, payload or {'rubro': 'comercio', 'goals': ['vender_online']}, format = 'json').json()

    def test_apply_publishes_in_one_step(self):
        store, customization  =   self._store(products = 5)
        client                =   self._client(store)
        data                  =   self._generate(client)
        proposal              =   data['proposals'][0]
        published             =   {
            'layout_config' :   {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
            'site_theme'    :   {'palette': {'primary': '#111111'}},
            'template'      :   'classic',
        }
        StoreCustomization.objects.filter(pk = customization.pk).update(
            layout_config = published['layout_config'],
            site_theme    = published['site_theme'],
            template      = published['template'],
            about_text    = 'Texto propio del dueño',
        )
        versions_before =   StudioVersion.objects.filter(store = store).count()
        response    =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': proposal['id']}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['published'])
        customization.refresh_from_db()
        #Publica en el mismo paso: lo publicado ya tiene el layout nuevo.
        self.assertEqual(customization.layout_config, customization.layout_config_draft)
        self.assertEqual(customization.site_theme, customization.site_theme_draft)
        self.assertEqual(customization.template, proposal['template'])
        self.assertEqual(customization.template_draft, proposal['template'])
        self.assertEqual(customization.about_text, 'Texto propio del dueño')
        self.assertEqual(
            [block['id'] for block in customization.layout_config['landing']['blocks']],
            [block['id'] for block in proposal['layout_config']['landing']['blocks']],
        )
        self.assertEqual(StudioVersion.objects.filter(store = store).count(), versions_before + 1)

    def test_apply_fills_only_empty_copy(self):
        store, customization  =   self._store(products = 3)
        customization.headline = 'Titular propio'
        customization.save(update_fields = ['headline'])
        client                =   self._client(store)
        data                  =   self._generate(client)
        response              =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': data['proposals'][0]['id']}, format = 'json')
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.headline, 'Titular propio')
        self.assertTrue(customization.cta_label)

    def test_apply_unknown_proposal_is_400(self):
        store, _    =   self._store()
        client      =   self._client(store)
        data        =   self._generate(client)
        response    =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': 'p9'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_apply_missing_seed_is_400(self):
        store, _    =   self._store()
        response    =   self._client(store).post(APPLY_URL, {'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class AiDesignV2Tests(AiDesignBase):
    """Ronda 2: diseños exclusivos de IA, copy_draft, autofill y pedido de imágenes."""

    def _generate(self, store, payload = None):
        client  =   self._client(store)
        data    =   {'rubro': 'belleza', 'tone': 'moderno', 'goals': ['mostrar_trabajos']}
        data.update(payload or {})
        return client, client.post(AI_URL, data, format = 'json').json()

    def _apply(self, client, data, autofill = None):
        payload =   {'seed': data['seed'], 'proposal_id': data['proposals'][0]['id']}
        if autofill is not None:
            payload['autofill']   =   autofill
        return client.post(APPLY_URL, payload, format = 'json')

    def test_ai_templates_used_when_plan_allows(self):
        store, _    =   self._store()
        _, data     =   self._generate(store)
        self.assertEqual(data['engine'], 'ai-design/7')
        #El motor ya no tiene diseños exclusivos: todas las propuestas son
        #del catálogo público y declaran fuente de estilo 'plan'.
        sources     =   {proposal['style_source'] for proposal in data['proposals']}
        self.assertEqual(sources, {'plan'})
        self.assertEqual(set(allowed_templates_of(store.user)), {'raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad'})

    def test_ai_templates_never_outside_plan(self):
        #Sin has_ai_design los ai_* no están en la whitelist del plan y el
        #motor no los devuelve (se llama al motor directo: el endpoint ya
        #responde 403 sin el flag).
        store, _    =   self._store(ai = False)
        data        =   generate_ai_design(store, {'rubro': 'belleza', 'goals': ['mostrar_trabajos']})
        allowed     =   set(allowed_templates_of(store.user))
        self.assertFalse({'ai_lumen', 'ai_pulse'} & allowed)
        for proposal in data['proposals']:
            self.assertIn(proposal['template'], allowed)
            self.assertNotIn(proposal['template'], ('ai_lumen', 'ai_pulse'))

    def test_ai_proposal_uses_bold_blocks_and_look(self):
        store, customization    =   self._store(products = 8)
        customization.about_text =   'Somos una marca con historia. ' * 12
        customization.services   =   [{'title': f'Servicio {index}', 'text': 'Detalle'} for index in range(3)]
        customization.save()
        for index in range(3):
            StoreGalleryImage.objects.create(store = store, image_key = f'gg{index}', position = index)
        _, data     =   self._generate(store)
        #v7: el motor propone solo los 6 diseños del catálogo, con la piel
        #compuesta por el rubro y el tono.
        proposal    =   data['proposals'][0]
        self.assertIn(proposal['template'], ('raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad'))
        landing     =   {block['id']: block for block in proposal['layout_config']['landing']['blocks']}
        self.assertIn(landing['hero'].get('variant'), ('full', 'split', 'centered', 'cinema', 'editorial'))
        #Los contenedores los dicta la PIEL elegida, no la plantilla.
        self.assertEqual(
            proposal['site_theme']['containers']['surface'],
            SKINS[proposal['skin']['id']]['containers']['surface'],
        )
        self.assertTrue(proposal['why'])

    def test_copy_draft_respects_model_limits(self):
        store, _    =   self._store(products = 4)
        _, data     =   self._generate(store)
        for proposal in data['proposals']:
            draft   =   proposal['copy_draft']
            self.assertLessEqual(len(draft.get('about_text', '')), StoreCustomization.about_text.field.max_length)
            self.assertLessEqual(len(draft.get('about_mission', '')), StoreCustomization.about_mission.field.max_length)
            for row in draft.get('faqs', []):
                self.assertLessEqual(len(row['q']), StoreCustomization.FAQ_Q_MAX)
                self.assertLessEqual(len(row['a']), StoreCustomization.FAQ_A_MAX)
            for row in draft.get('services', []):
                self.assertLessEqual(len(row['name']), StoreCustomization.SERVICE_TITLE_MAX)
                self.assertLessEqual(len(row['desc']), StoreCustomization.SERVICE_TEXT_MAX)
            for row in draft.get('steps', []):
                self.assertLessEqual(len(row['title']), StoreCustomization.SERVICE_STEP_TITLE_MAX)
                self.assertLessEqual(len(row['desc']), StoreCustomization.SERVICE_STEP_TEXT_MAX)
            for row in draft.get('announcements', []):
                self.assertLessEqual(len(row['text']), StoreCustomization.ANNOUNCEMENT_TEXT_MAX)

    def test_copy_draft_skips_fields_with_content(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(
            about_text      =   'Texto propio',
            about_mission   =   'Misión propia',
            faqs            =   [{'q': '¿Envían?', 'a': 'Sí'}],
            services        =   [{'icon': 'truck', 'title': 'Envíos', 'text': 'A todo el país'}],
        )
        _, data =   self._generate(store)
        draft   =   data['proposals'][0]['copy_draft']
        for key in ('about_text', 'about_mission', 'faqs', 'services'):
            self.assertNotIn(key, draft)
        self.assertIn('steps', draft)

    def test_autofill_false_keeps_business_fields_empty(self):
        store, customization  =   self._store()
        client, data          =   self._generate(store)
        response              =   self._apply(client, data)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.about_text, '')
        self.assertEqual(customization.about_mission, '')
        self.assertEqual(customization.faqs, [])
        self.assertEqual(customization.services, [])
        self.assertEqual(customization.service_steps, [])

    def test_autofill_true_writes_only_empty(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(about_mission = 'Misión propia')
        client, data          =   self._generate(store)
        response              =   self._apply(client, data, autofill = True)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertTrue(customization.about_text)
        self.assertEqual(customization.about_mission, 'Misión propia')
        self.assertTrue(customization.faqs)
        self.assertTrue(customization.services)
        self.assertTrue(customization.service_steps)
        self.assertTrue(customization.announcements)
        #Las filas escritas respetan la forma del modelo (icon/title/text).
        for row in customization.services:
            self.assertEqual(set(row), {'icon', 'title', 'text'})
        for row in customization.faqs:
            self.assertEqual(set(row), {'q', 'a'})

    def test_apply_never_writes_forbidden_business_fields(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(
            testimonials    =   [{'name': 'Ana', 'detail': 'Clienta', 'text': 'Muy buena atención'}],
            stats           =   [{'value': '+10', 'label': 'Años'}],
            contact_email   =   'hola@negocio.com',
            whatsapp        =   '1122334455',
            hours           =   [{'label': 'Lun a vie', 'value': '9 a 18 h'}],
            catalog_note    =   'Aviso propio',
        )
        before              =   StoreCustomization.objects.get(pk = customization.pk)
        client, data        =   self._generate(store)
        response            =   self._apply(client, data, autofill = True)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        for field in ('testimonials', 'stats', 'contact_email', 'whatsapp', 'hours', 'catalog_note'):
            self.assertEqual(getattr(customization, field), getattr(before, field))

    def test_image_requests_only_without_own_images(self):
        store, _    =   self._store()
        _, data     =   self._generate(store)
        proposal    =   data['proposals'][0]
        self.assertTrue(proposal['image_requests'])
        self.assertLessEqual(len(proposal['image_requests']), 2)
        for request in proposal['image_requests']:
            self.assertIn(request['target'], ('cover', 'gallery'))
            self.assertIn(request['min_count'], (2, 3, 4))
            for unlock in request['unlocks']:
                block_id    =   unlock.split(':')[0]
                self.assertIn(block_id, TEMPLATE_BLOCKS['landing'])
        #Con galería propia ya no pide fotos.
        StoreGalleryImage.objects.create(store = store, image_key = 'gallery/1.webp', image_size = 10)
        _, data     =   self._generate(store)
        self.assertEqual(data['proposals'][0]['image_requests'], [])


class AiDesignImageTests(AiDesignBase):
    """POST /api/stores/ai-design/image/: foto del pedido -> galería en WebP."""

    def setUp(self):
        super().setUp()
        self.media      =   tempfile.mkdtemp()
        self.override   =   override_settings(MEDIA_ROOT = self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def _file(self, size = (1400, 900), color = (200, 30, 60), fmt = 'PNG'):
        buffer  =   io.BytesIO()
        Image.new('RGB', size, color).save(buffer, format = fmt)
        buffer.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('foto.png', buffer.read(), content_type = 'image/png')

    def test_upload_creates_webp_gallery_image(self):
        store, _    =   self._store(limits = True)
        client      =   self._client(store)
        with patch.object(storage, 'storage_configured', return_value = False):
            response =  client.post(IMAGE_URL, {'image': self._file(), 'request_id': 'local'}, format = 'multipart')
        self.assertEqual(response.status_code, 200)
        payload     =   response.json()
        self.assertEqual(payload['gallery']['count'], 1)
        image       =   StoreGalleryImage.objects.get(pk = payload['image']['id'])
        self.assertEqual(image.kind, StoreGalleryImage.KIND_GALLERY)
        self.assertEqual(image.position, 0)
        with default_storage.open(image.image_key, 'rb') as handle:
            head    =   handle.read(16)
        #Firma real del archivo guardado: RIFF....WEBP.
        self.assertTrue(head.startswith(b'RIFF'))
        self.assertEqual(head[8:12], b'WEBP')
        self.assertGreater(image.image_size, 0)
        self.assertEqual(payload['image']['url'], f'/media/{image.image_key}')

    def test_upload_without_ai_design_is_403(self):
        store, _    =   self._store(ai = False, limits = True)
        response    =   self._client(store).post(IMAGE_URL, {'image': self._file()}, format = 'multipart')
        self.assertEqual(response.status_code, 403)

    def test_upload_without_file_is_400(self):
        store, _    =   self._store(limits = True)
        response    =   self._client(store).post(IMAGE_URL, {}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_invalid_file_is_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        store, _    =   self._store(limits = True)
        upload      =   SimpleUploadedFile('x.png', b'no soy una imagen', content_type = 'image/png')
        response    =   self._client(store).post(IMAGE_URL, {'image': upload}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_respects_storage_quota(self):
        store, customization  =   self._store(limits = True)
        PlanBenefit.objects.filter(plan__suscription__user = store.user, benefit__code = 'max_storage_mb').update(value = 0)
        with patch.object(storage, 'storage_configured', return_value = False):
            response =  self._client(store).post(IMAGE_URL, {'image': self._file()}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StoreGalleryImage.objects.count(), 0)

    def test_image_throttle_after_limit(self):
        store, _    =   self._store(limits = True)
        client      =   self._client(store)
        codes       =   [
            client.post(IMAGE_URL, {'image': self._file()}, format = 'multipart').status_code
            for _ in range(62)
        ]
        self.assertEqual(codes[0], 200)
        self.assertEqual(codes[-1], 429)


class AiDesignV3Tests(AiDesignBase):
    """Ronda 3: elementos solo-IA, color de marca, modo noche, portada con
    logo, overrides por contenedor y publicación en el mismo apply."""

    def _generate(self, store, payload = None):
        data    =   {'rubro': 'belleza', 'tone': 'moderno', 'goals': ['dar_confianza']}
        data.update(payload or {})
        response    =   self._client(store).post(AI_URL, data, format = 'json')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_ai_only_blocks_need_ai_design(self):
        with_ai, _  =   self._store(username = 'con-ai')
        payload     =   {'goals': ['dar_confianza', 'mostrar_servicios'], 'must_have': ['contact', 'faq', 'offers']}
        proposals   =   self._generate(with_ai, payload)['proposals']
        ids_ai      =   {
            block['id']
            for proposal in proposals
            for block in proposal['layout_config']['landing']['blocks']
        }
        self.assertTrue(ids_ai & {'aiquote', 'aicheck', 'aigrid', 'aistrip', 'aiband'})
        #Sin has_ai_design el saneador descarta los bloques ai_only.
        layout  =   {'landing': {'blocks': [{'id': 'aiquote', 'props': {'text': 'Hola'}}]}}
        self.assertEqual(clean_layout_config(layout, True), {})
        self.assertTrue(clean_layout_config(layout, True, True))

    def test_typed_props_are_sanitized(self):
        layout  =   {'landing': {'blocks': [{
            'id'        :   'aigrid',
            'variant'   :   'grid3',
            'props'     :   {
                'title' :   'X' * 120,
                'items' :   [{'icon': 'no-existe', 'title': 'T' * 60, 'text': 't' * 200}]
                            + [{'title': f'Item {index}'} for index in range(8)],
            },
        }]}}
        clean   =   clean_layout_config(layout, True, True)['landing']['blocks'][0]['props']
        self.assertEqual(len(clean['title']), 80)
        self.assertEqual(len(clean['items']), 6)
        self.assertNotIn('icon', clean['items'][0])
        self.assertEqual(len(clean['items'][0]['title']), 40)
        self.assertEqual(len(clean['items'][0]['text']), 90)

    def test_site_theme_blocks_are_closed_catalog(self):
        clean   =   clean_site_theme(
            {'blocks': {'hero': {'radius': 'xl', 'align': 'center', 'accent': '#AABBCC'}, 'inventado': {'radius': 'xl'}}},
            has_advanced = True,
        )
        self.assertEqual(clean, {'blocks': {'hero': {'radius': 'xl', 'align': 'center', 'accent': '#aabbcc'}}})
        from rest_framework import serializers
        with self.assertRaises(serializers.ValidationError):
            clean_site_theme({'blocks': {'hero': {'align': 'diagonal'}}}, has_advanced = True)
        with self.assertRaises(serializers.ValidationError):
            clean_site_theme({'blocks': {'hero': {'accent': 'rojo'}}}, has_advanced = True)
        with self.assertRaises(serializers.ValidationError):
            clean_site_theme({'blocks': {'hero': {'inventado': 'x'}}}, has_advanced = True)
        with self.assertRaises(serializers.ValidationError):
            clean_site_theme({'blocks': {f'hero{i}': {'radius': 'xl'} for i in range(13)}}, has_advanced = True)
        self.assertEqual(clean_site_theme({'blocks': {'hero': {'radius': 'xl'}}}, has_plus = True), {})

    def test_brand_color_sets_accent_with_aa(self):
        store, _    =   self._store()
        data        =   self._generate(store, {'brand_color': '#1d4ed8'})
        from StoreApp.domains.stores.services.ai_design import _contrast_ratio, _palette_from_brand
        for proposal in data['proposals']:
            self.assertEqual(proposal['theme_choice']['source'], 'user')
            accent  =   proposal['theme_choice']['accent']
            self.assertEqual(proposal['site_theme']['palette']['accent'], accent)
            self.assertGreaterEqual(_contrast_ratio(accent, proposal['site_theme']['palette']['bg']), 4.5)
        palette =   _palette_from_brand('#1d4ed8', {'primary': '#000000', 'secondary': '#000000', 'accent': '#000000',
                                                    'bg': '#fdf6f0', 'surface': '#ffffff', 'text': '#1c1917',
                                                    'muted': '#78716c', 'border': '#e7ded4'})
        self.assertEqual(palette['accent'], '#1d4ed8')

    def test_invalid_brand_color_is_ignored(self):
        store, _    =   self._store()
        data        =   self._generate(store, {'brand_color': 'no-es-un-color'})
        for proposal in data['proposals']:
            self.assertEqual(proposal['theme_choice']['source'], 'ai')

    def test_night_mode_sets_theme_and_toggle(self):
        store, customization    =   self._store()
        data                    =   self._generate(store, {'night_mode': {'enabled': True, 'default': 'dark'}})
        for proposal in data['proposals']:
            self.assertEqual(proposal['night_mode'], {'enabled': True, 'default': 'dark'})
            self.assertEqual(proposal['theme'], 'dark')
            self.assertTrue(proposal['theme_toggle'])
        response    =   self._client(store).post(
            APPLY_URL,
            {'seed': data['seed'], 'proposal_id': data['proposals'][0]['id']},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.theme, 'dark')
        self.assertTrue(customization.theme_toggle)

    def test_cover_logo_uses_logo_hero_and_solid_background(self):
        store, customization    =   self._store()
        customization.logo_key  =   'stores/1/logo.webp'
        customization.save(update_fields = ['logo_key'])
        data                    =   self._generate(store, {'cover_choice': 'logo'})
        for proposal in data['proposals']:
            self.assertEqual(proposal['cover']['mode'], 'logo')
            hero    =   next(block for block in proposal['layout_config']['landing']['blocks'] if block['id'] == 'hero')
            self.assertEqual(hero['variant'], 'logo')
            self.assertNotEqual(proposal['site_theme']['background']['type'], 'image')

    def test_apply_publishes_ai_layout(self):
        store, customization    =   self._store()
        data                    =   self._generate(store, {'goals': ['dar_confianza', 'mostrar_servicios']})
        proposal                =   data['proposals'][0]
        response                =   self._client(store).post(
            APPLY_URL,
            {'seed': data['seed'], 'proposal_id': proposal['id']},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['published'])
        customization.refresh_from_db()
        self.assertEqual(
            [block['id'] for block in customization.layout_config['landing']['blocks']],
            [block['id'] for block in proposal['layout_config']['landing']['blocks']],
        )
        self.assertTrue(StudioVersion.objects.filter(store = store).exists())

#=========================================
# RONDA 4 — VARIEDAD REAL: PLANTILLAS RETIRADAS, 18 PIELES Y TIPOGRAFÍA POR ROL
#=========================================
def _contrast(a, b):
    """WCAG 2.1 (misma fórmula que site_theme._contrast_ratio)."""
    def channel(value):
        s = value / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    def lum(hex_value):
        h = hex_value.lstrip('#')
        r, g, b = (int(h[index:index + 2], 16) for index in (0, 2, 4))
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class AiDesignV4Tests(AiDesignBase):
    """Motor v4: terna (plantilla, piel, par tipográfico) con diversidad
    obligatoria, site_theme v2 (roles + layout + skin) y rediseño completo."""

    RUBROS  =   ('comercio', 'gastronomia', 'indumentaria', 'servicios_profesionales',
                 'salud', 'belleza', 'construccion', 'tecnologia', 'educacion',
                 'turismo', 'mascotas', 'arte', 'seguridad', 'otro')

    def _generate(self, store, payload = None):
        data        =   {'tone': 'moderno', 'goals': ['vender_online']}
        data.update(payload or {})
        response    =   self._client(store).post(AI_URL, data, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:400])
        return response.json()

    def test_engine_reports_v4(self):
        store, _    =   self._store()
        self.assertEqual(self._generate(store, {'rubro': 'comercio'})['engine'], 'ai-design/7')

    def test_each_rubro_opens_with_a_design_and_skin_from_the_catalog(self):
        #La apertura siempre sale del catálogo real de 6 y declara su piel.
        store, _    =   self._store()
        for rubro in self.RUBROS:
            proposal    =   self._generate(store, {'rubro': rubro})['proposals'][0]
            self.assertIn(proposal['template'], ('raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad'), rubro)
            self.assertTrue(proposal['skin']['id'], rubro)

    def test_proposals_differ_in_template_skin_and_type_pair(self):
        store, _    =   self._store(products = 8)
        proposals   =   self._generate(store, {'rubro': 'comercio'})['proposals']
        self.assertIn(len(proposals), (2, 3))
        self.assertEqual(len({proposal['template'] for proposal in proposals}), len(proposals))
        self.assertEqual(len({proposal['skin']['id'] for proposal in proposals}), len(proposals))
        #Los estilos también difieren (el invariante que sostiene la
        #variedad de la generación).
        self.assertEqual(len({proposal['variety']['style'] for proposal in proposals}), len(proposals))
        for proposal in proposals:
            self.assertEqual(proposal['variety']['differs_by'], ['template', 'skin', 'type-pair'])

    def test_all_proposals_come_from_the_six_designs(self):
        store, _    =   self._store()
        templates   =   set()
        for rubro in self.RUBROS:
            for proposal in self._generate(store, {'rubro': rubro})['proposals']:
                self.assertEqual(proposal['style_source'], 'plan')
                templates.add(proposal['template'])
        self.assertEqual(templates, {'raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad'})

    def test_rubro_seguridad_proposes_the_security_design(self):
        #El rubro nuevo entra al entrenamiento: la matriz firma incluye
        #'seguridad' y la generación la propone (la semilla rota el orden de
        #la cabeza, así que se recorren varias). Sigue siendo determinista.
        store, _    =   self._store()
        seen        =   set()
        for seed in range(6):
            data    =   self._generate(store, {'rubro': 'seguridad', 'seed': seed})
            seen.update(proposal['template'] for proposal in data['proposals'])
            again   =   self._generate(store, {'rubro': 'seguridad', 'seed': seed})
            self.assertEqual(data, again)
            for proposal in data['proposals']:
                self.assertIn(proposal['skin']['id'], SKIN_IDS)
        self.assertIn('seguridad', seen)
        self.assertTrue(seen <= set(allowed_templates_of(store.user)))

    def test_standard_plan_never_gets_advanced_designs(self):
        #Estándar = base + plus (4 diseños); circuito/seguridad quedan fuera.
        _, profile =   _make_user('estandar')
        _grant(
            profile,
            has_public_link     =   True,
            has_customization   =   True,
            has_design_plus     =   True,
            has_ai_design       =   True,
        )
        store       =   Store.objects.create(user = profile, slug = 'tienda-estandar')
        StoreCustomization.objects.create(store = store, site_templates = ['landing', 'catalog', 'services'])
        allowed     =   set(allowed_templates_of(store.user))
        self.assertEqual(allowed, {'raiz', 'alimentos', 'trama', 'boutique'})
        data        =   self._client(store).post(AI_URL, {'rubro': 'seguridad'}, format = 'json').json()
        self.assertTrue(data['proposals'])
        for proposal in data['proposals']:
            self.assertIn(proposal['template'], allowed)
            self.assertNotIn(proposal['template'], ('circuito', 'seguridad'))

    def test_legacy_and_ai_templates_never_without_the_flag(self):
        store, _    =   self._store(ai = False)
        self.assertEqual(self._client(store).post(AI_URL, {'rubro': 'comercio'}, format = 'json').status_code, 403)
        allowed     =   allowed_templates_of(store.user)
        self.assertNotIn('perspective', allowed)
        self.assertNotIn('ai_lumen', allowed)

    def test_allowed_templates_grow_with_the_flag(self):
        premium, _  =   self._store()
        self.assertEqual(set(allowed_templates_of(premium.user)), {'raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad'})
        basic, _    =   self._store(advanced = False, username = 'basico')
        self.assertEqual(set(allowed_templates_of(basic.user)), {'raiz', 'alimentos'})

    def test_typography_roles_cover_the_thirteen_roles(self):
        store, _    =   self._store()
        proposal    =   self._generate(store, {'rubro': 'belleza'})['proposals'][0]
        roles       =   proposal['typography_roles']
        self.assertEqual(set(roles), set(TYPOGRAPHY_ROLES))
        for role, values in roles.items():
            self.assertIn(values['font'], FONT_SLUGS)
            self.assertIn(values['size'], TYPE_SIZES)
            self.assertIn(values['tracking'], TYPE_TRACKING)
            self.assertIn(values['leading'], TYPE_LEADING)
            self.assertIn(values['case'], TYPE_CASES)
            self.assertIn(values['weight'], (300, 400, 500, 600, 700, 800, 900))
        #Cuerpo legible y precios con peso alto: reglas del contrato.
        self.assertLessEqual(roles['body']['weight'], 500)
        self.assertEqual(roles['price']['weight'], 700)
        self.assertEqual(roles['eyebrow']['case'], 'upper')
        self.assertEqual(roles['eyebrow']['tracking'], 'wider')
        #Nunca dos familias de cuerpo distintas.
        self.assertEqual(len({roles[role]['font'] for role in BODY_ROLES}), 1)

    def test_skin_palettes_pass_aa(self):
        for skin_id, skin in SKINS.items():
            palette =   skin['palette']
            self.assertGreaterEqual(_contrast(palette['text'], palette['bg']), 4.5, skin_id)
            self.assertGreaterEqual(_contrast(palette['muted'], palette['bg']), 4.5, skin_id)

    def test_skin_catalog_is_closed_and_composed(self):
        #26 familias desde la v5: las 18 del contrato + las 8 de los estilos.
        self.assertEqual(len({skin['family'] for skin in SKINS.values()}), 26)
        self.assertEqual(len({skin['style'] for skin in SKINS.values()}), 8, 'los 8 estilos deben tener pieles')
        for skin_id, skin in SKINS.items():
            self.assertTrue(skin_id.startswith(f"{skin['family']}-"), skin_id)
            self.assertIn(skin['layout']['grid'], ('12', 'asym', 'split', 'bento', 'editorial'))
            self.assertIn(skin['layout']['hero'], ('centered', 'split', 'cinema', 'logo', 'editorial'))

    def test_proposals_declare_their_design_style(self):
        """v5: cada propuesta declara el estilo del entrenamiento y la
        generación ofrece estilos distintos (no tres variantes del mismo)."""
        store, _        =   self._store(products = 8)
        for rubro in ('comercio', 'belleza', 'tecnologia'):
            proposals   =   self._generate(store, {'rubro': rubro})['proposals']
            styles      =   [proposal['variety'].get('style') for proposal in proposals]
            self.assertEqual(len(styles), len(set(styles)), f'{rubro}: estilos repetidos {styles}')
            for proposal, style in zip(proposals, styles):
                self.assertIn(style, STYLE_FAMILIES)
                self.assertEqual(style, SKINS[proposal['skin']['id']]['style'])
                self.assertTrue(proposal['variety'].get('style_label'))

    def test_requested_styles_are_prioritized_but_never_imposed(self):
        store, _        =   self._store(products = 8)
        proposals       =   self._generate(store, {'rubro': 'comercio', 'styles': ['luxury']})['proposals']
        styles          =   [proposal['variety']['style'] for proposal in proposals]
        self.assertIn('luxury', styles)
        #Un plan/plantilla que no permite un estilo nunca rompe la respuesta.
        unknown =   self._generate(store, {'rubro': 'comercio', 'styles': ['inventado']})['proposals']
        self.assertTrue(all(proposal['variety']['style'] in STYLE_FAMILIES for proposal in unknown))

    def test_site_theme_v2_accepts_roles_layout_and_skin(self):
        clean   =   clean_site_theme({
            'typography': {'roles': {'body': {'font': 'inter', 'size': 'md', 'weight': 400,
                                              'tracking': 'normal', 'leading': 'relaxed', 'case': 'none'}}},
            'layout': {'density': 'compact', 'grid': 'bento', 'hero': 'cinema',
                       'gutter': 'sm', 'measure': 'wide', 'radiusScale': 'lg'},
            'skin': {'id': 'editorial-ink', 'family': 'glass'},
        }, has_advanced = True)
        self.assertEqual(clean['typography']['roles']['body']['font'], 'inter')
        self.assertEqual(clean['layout']['grid'], 'bento')
        self.assertEqual(clean['skin'], {'id': 'editorial-ink', 'family': 'editorial'})

    def test_site_theme_v2_rejects_invalid_roles(self):
        base    =   {'font': 'inter', 'size': 'md', 'weight': 400, 'tracking': 'normal',
                     'leading': 'normal', 'case': 'none'}
        for role, override in (
            ('inventado', {}),
            ('body', {'font': 'comic-sans'}),
            ('body', {'size': 'gigante'}),
            ('body', {'weight': 450}),
            ('body', {'weight': 1000}),
            ('body', {'tracking': 'wideee'}),
            ('body', {'leading': 'apretado'}),
            ('body', {'case': 'capitalize'}),
            ('body', {'inventado': 1}),
        ):
            with self.assertRaises(Exception, msg = f'{role} {override}'):
                clean_site_theme({'typography': {'roles': {role: {**base, **override}}}}, has_advanced = True)

    def test_site_theme_v2_rejects_invalid_layout(self):
        for layout in ({'grid': 'masonry'}, {'hero': 'video'}, {'density': 'tight'},
                       {'gutter': 'xl'}, {'measure': 'huge'}, {'radiusScale': 'pill'}):
            with self.assertRaises(Exception, msg = layout):
                clean_site_theme({'layout': layout}, has_advanced = True)

    def test_site_theme_v2_discards_unknown_skin(self):
        self.assertEqual(clean_site_theme({'skin': {'id': 'inventada-1', 'family': 'glass'}}, has_advanced = True), {})
        self.assertEqual(clean_site_theme({'skin': {'family': 'glass'}}, has_advanced = True), {})

    def test_site_theme_v2_is_gated_by_the_plan(self):
        payload =   {'layout': {'grid': 'bento'}, 'skin': {'id': 'editorial-ink'},
                     'typography': {'roles': {'body': {'font': 'inter', 'size': 'md', 'weight': 400,
                                                       'tracking': 'normal', 'leading': 'normal', 'case': 'none'}}}}
        plus    =   clean_site_theme(payload, has_plus = True)
        self.assertNotIn('layout', plus)
        self.assertNotIn('typography', plus)
        #v6: la piel es presupuesto visual básico y viaja con el estilo (en
        #todos los planes con diseño); el resto del tema sigue gateado.
        skincare    =   {'skin': {'id': 'editorial-ink', 'family': 'editorial'}}
        self.assertEqual(plus['skin'], skincare['skin'])
        self.assertEqual(clean_site_theme(payload, has_style = True), skincare)
        self.assertEqual(clean_site_theme(payload), {})

    def test_redesign_covers_landing_catalog_and_services(self):
        store, _    =   self._store(products = 6)
        for proposal in self._generate(store, {'rubro': 'tecnologia'})['proposals']:
            self.assertEqual(proposal['redesign']['surfaces'], ['landing', 'catalog', 'services'])
            self.assertTrue(proposal['redesign']['changed'])
            self.assertEqual(set(proposal['layout_config']), {'landing', 'catalog', 'services'})
            self.assertIn('skin', proposal['site_theme'])
            self.assertIn('layout', proposal['site_theme'])

    def test_apply_publishes_theme_v2_and_new_blocks(self):
        store, customization    =   self._store(products = 3)
        customization.service_steps =   [
            {'title': f'Paso {index}', 'text': f'Explicación {index}'} for index in range(3)
        ]
        customization.save(update_fields = ['service_steps'])
        for index in range(4):
            StoreGalleryImage.objects.create(store = store, image_key = f'g{index}', position = index)
        data        =   self._generate(store, {'rubro': 'comercio', 'goals': ['vender_online'],
                                               'must_have': ['contact', 'faq']})
        proposal    =   data['proposals'][0]
        response    =   self._client(store).post(
            APPLY_URL, {'seed': data['seed'], 'proposal_id': proposal['id']}, format = 'json',
        )
        self.assertEqual(response.status_code, 200, response.content[:400])
        customization.refresh_from_db()
        self.assertIn(customization.site_theme['skin']['id'], SKIN_IDS)
        self.assertIn('roles', customization.site_theme['typography'])
        self.assertIn('layout', customization.site_theme)
        landing     =   [block['id'] for block in customization.layout_config['landing']['blocks']]
        self.assertTrue({'aiprocess', 'aipricing', 'aimosaic'} & set(landing), landing)

    def test_new_blocks_respect_their_props(self):
        store, customization    =   self._store(products = 3)
        customization.service_steps =   [{'title': f'Paso {index}', 'text': 'x' * 300} for index in range(6)]
        customization.save(update_fields = ['service_steps'])
        data        =   self._generate(store, {'rubro': 'comercio', 'goals': ['vender_online'],
                                               'must_have': ['contact', 'faq']})
        for proposal in data['proposals']:
            for block in proposal['layout_config']['landing']['blocks']:
                if block['id'] not in ('aiprocess', 'aipricing', 'aimosaic') or not block.get('enabled'):
                    continue
                self.assertIn(block['id'], proposal['offered_blocks'], block)
                spec    =   TEMPLATE_BLOCKS['landing'][block['id']]
                self.assertTrue(spec['ai_only'])
                if block.get('variant'):
                    self.assertIn(block['variant'], spec['variants'])
                for key in (proposal['offered_blocks'][block['id']].get('props') or {}):
                    self.assertIn(key, spec['props'])
                #v6: el contenido REAL del extra lo arma el motor y viaja en
                #`offered_blocks` (apply lo prende sin props del cliente).
                props   =   proposal['offered_blocks'][block['id']].get('props')
                self.assertTrue(props, block)
                if block['id'] == 'aiprocess':
                    self.assertLessEqual(len(props['items']), 5)
                    self.assertLessEqual(len(props['items'][0]['text']), 160)
                if block['id'] == 'aipricing':
                    self.assertLessEqual(len(props['items']), 4)
                    self.assertGreaterEqual(len(props['items']), 2)

    def test_generated_icons_are_accepted(self):
        layout  =   {'landing': {'blocks': [{'id': 'aigrid', 'props': {
            'items': [{'icon': 'gen:llave-inglesa', 'title': 'A'}, {'icon': 'gen:Mal Slug', 'title': 'B'},
                      {'icon': 'nope', 'title': 'C'}],
        }}]}}
        items   =   clean_layout_config(layout, True, True)['landing']['blocks'][0]['props']['items']
        self.assertEqual(items[0]['icon'], 'gen:llave-inglesa')
        self.assertNotIn('icon', items[1])
        self.assertNotIn('icon', items[2])


class AiDesignExtrasTests(AiDesignBase):
    """Fase D (v6): la IA ofrece elementos extra y el dueño acepta o rechaza."""

    def _store_with_material(self, **kwargs):
        store, customization    =   self._material(products = 4, **kwargs)
        customization.services  =   [{'icon': 'package', 'title': f'Servicio {index}', 'text': 'Detalle'} for index in range(3)]
        customization.service_steps =   [{'title': f'Paso {index + 1}', 'text': 'Cómo lo hacemos'} for index in range(3)]
        customization.benefits  =   [{'text': f'Beneficio {index}'} for index in range(3)]
        customization.testimonials =   [{'name': 'Ana', 'detail': 'Clienta', 'text': 'Muy buena atención'}]
        customization.whatsapp  =   '1122334455'
        customization.save()
        for index in range(5):
            StoreGalleryImage.objects.create(store = store, image_key = f'e{index}', position = index)
        return store, customization

    def _material(self, products = 0, **kwargs):
        return self._store(products = products, **kwargs)

    def _generate(self, store, payload = None):
        data    =   {'rubro': 'comercio', 'tone': 'moderno', 'goals': ['vender_online', 'mostrar_servicios']}
        data.update(payload or {})
        response    =   self._client(store).post(AI_URL, data, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:300])
        return response.json()

    def _ai_blocks(self, proposal):
        return {block['id']: block for block in proposal['layout_config']['landing']['blocks'] if block['id'] in R.AI_ELEMENT_ORDER}

    def test_every_proposal_ships_the_extras_section(self):
        store, _    =   self._store_with_material()
        data    =   self._generate(store)
        for proposal in data['proposals']:
            extras  =   proposal['extras']
            self.assertEqual(set(extras), {'offered', 'applied', 'skipped'})
            self.assertLessEqual(len(extras['applied']), R.AI_ELEMENT_MAX)
            self.assertTrue(extras['offered'], proposal['label'])
            #Contrato §2.2: `offered` son los extras con su bloque y `applied`
            #son ids de bloque REALES de TEMPLATE_BLOCKS (todos ai_only).
            for item in proposal['extras_items']:
                self.assertIn(item['kind'], R.AI_ELEMENT_ORDER)
                self.assertEqual(item['block_id'], item['kind'])
                self.assertTrue(item['label'] and item['why'] and item['needs'])
                self.assertEqual(item['block']['id'], item['kind'])
                self.assertTrue(TEMPLATE_BLOCKS['landing'][item['block']['id']]['ai_only'])
            self.assertEqual(set(extras['applied']), {item['kind'] for item in proposal['extras_items'] if item['block']['enabled']})
            self.assertEqual(set(proposal['offered_blocks']), {item['kind'] for item in proposal['extras_items']})
            self.assertIn('score', proposal)

    def test_accept_extras_false_offers_but_does_not_apply(self):
        store, _    =   self._store_with_material()
        data    =   self._generate(store, {'accept_extras': False})
        for proposal in data['proposals']:
            self.assertTrue(proposal['extras']['offered'], proposal['extras'])
            self.assertEqual(proposal['extras']['applied'], [])
            #Ninguno se prende: la tarjeta los ofrece para sumarlos a mano.
            for item in proposal['extras_items']:
                self.assertFalse(item['block']['enabled'], item['kind'])
            #Un extra no aplicado nunca viaja prendido en el layout.
            for block in self._ai_blocks(proposal).values():
                self.assertFalse(block['enabled'], block['id'])

    def test_accept_extras_absent_keeps_applying(self):
        store, _    =   self._store_with_material()
        data    =   self._generate(store)
        self.assertTrue(any(proposal['extras']['applied'] for proposal in data['proposals']))

    def test_extras_input_wins_priority_and_is_capped(self):
        store, _    =   self._store_with_material()
        data    =   self._generate(store, {'extras': ['aimosaic', 'aipricing', 'no-existe', 'aiquote',
                                                     'aistrip', 'aigrid', 'aiband']})
        for proposal in data['proposals']:
            applied =   proposal['extras']['applied']
            self.assertLessEqual(len(applied), R.AI_ELEMENT_MAX)
            self.assertEqual(applied[:2], ['aimosaic', 'aipricing'], applied)

    def test_extras_require_ai_flag(self):
        store, _    =   self._store_with_material(ai = False)
        data    =   generate_ai_design(store, {'rubro': 'comercio', 'goals': ['vender_online']})
        for proposal in data['proposals']:
            self.assertEqual(proposal['extras']['offered'], [])
            self.assertEqual(proposal['extras']['applied'], [])
            self.assertTrue(proposal['extras']['skipped'])
            self.assertEqual(self._ai_blocks(proposal), {})

    def test_extras_offered_items_follow_the_contract(self):
        #Contrato §2.2: `extras.offered` son OBJETOS con su bloque ai_only,
        #el "para qué" y qué datos reales usa (lo que pinta la tarjeta).
        store, _    =   self._store_with_material()
        data        =   self._generate(store)
        for proposal in data['proposals']:
            self.assertTrue(proposal['extras']['offered'], proposal['label'])
            for item in proposal['extras']['offered']:
                self.assertEqual(item['id'], f'extra-{item["kind"][2:]}')
                self.assertIn(item['kind'], R.AI_ELEMENT_ORDER)
                self.assertTrue(item['label'] and item['why'] and item['needs'])
                self.assertTrue(TEMPLATE_BLOCKS['landing'][item['block']['id']]['ai_only'])
                self.assertEqual(item['block']['id'], item['kind'])

    def test_extras_respect_data_gates(self):
        #Sin pasos ni galería no se ofrecen aiprocess ni aimosaic (nunca
        #inventan precios, pasos ni fotos).
        store, _    =   self._store(products = 0)
        data        =   self._generate(store, {'goals': ['vender_online']})
        for proposal in data['proposals']:
            kinds   =   {item['kind'] for item in proposal['extras']['offered']}
            self.assertNotIn('aiprocess', kinds)
            self.assertNotIn('aimosaic', kinds)
            self.assertNotIn('aipricing', kinds)



    def test_apply_with_rejected_extra_disables_block(self):
        store, customization    =   self._store_with_material()
        data                    =   self._generate(store)
        proposal                =   next(item for item in data['proposals'] if item['extras']['applied'])
        applied                 =   proposal['extras']['applied']
        dropped                 =   applied[0]
        kept                    =   applied[1:]
        offered                 =   [item['kind'] for item in proposal['extras_items']]
        response                =   self._client(store).post(APPLY_URL, {
            'seed'          :   data['seed'],
            'proposal_id'   :   proposal['id'],
            'extras'        :   {'offered': offered, 'applied': kept},
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:300])
        customization.refresh_from_db()
        landing =   {block['id']: block for block in customization.layout_config['landing']['blocks']}
        #El rechazado sigue en el layout (para prenderlo después) pero apagado.
        self.assertIn(dropped, landing)
        self.assertFalse(landing[dropped]['enabled'])
        for kind in kept:
            self.assertTrue(landing[kind]['enabled'])

    def test_apply_with_skip_extras_turns_them_all_off(self):
        store, customization    =   self._store_with_material()
        data                    =   self._generate(store)
        proposal                =   next(item for item in data['proposals'] if item['extras']['applied'])
        response                =   self._client(store).post(APPLY_URL, {
            'seed': data['seed'], 'proposal_id': proposal['id'], 'skip_extras': True,
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:300])
        customization.refresh_from_db()
        landing =   {block['id']: block for block in customization.layout_config['landing']['blocks']}
        #Apagados, pero presentes en el borrador para prenderlos después.
        self.assertFalse({k for k, v in landing.items() if v.get('enabled')} & set(R.AI_ELEMENT_ORDER))

    def test_apply_can_turn_on_an_offered_extra(self):
        store, customization    =   self._store_with_material()
        data                    =   self._generate(store, {'accept_extras': False})
        proposal                =   data['proposals'][0]
        offered                 =   [item['kind'] for item in proposal['extras_items']]
        self.assertTrue(offered)
        chosen                  =   offered[0]
        response                =   self._client(store).post(APPLY_URL, {
            'seed': data['seed'], 'proposal_id': proposal['id'],
            'extras': {'offered': offered, 'applied': [chosen]},
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:300])
        customization.refresh_from_db()
        stored  =   {block['id']: block for block in customization.layout_config_draft['landing']['blocks']}
        self.assertIn(chosen, stored)
        self.assertTrue(stored[chosen]['enabled'])
        #El contenido sale del motor (nunca props enviadas por el cliente).
        self.assertEqual(stored[chosen].get('props'), proposal['offered_blocks'][chosen].get('props'))
        #Elegir un extra no apaga el resto de la portada.
        enabled =   {block['id'] for block in customization.layout_config_draft['landing']['blocks'] if block['enabled']}
        self.assertIn('hero', enabled)
        if chosen != 'aipricing':
            self.assertFalse(stored['aipricing']['enabled'])
