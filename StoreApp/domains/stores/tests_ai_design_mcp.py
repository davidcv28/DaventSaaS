"""
Suite del wizard "Diseño asistido" -> proxy MCP de estilos.

Endpoint:
  POST /api/stores/ai-design/mcp/  -> {prompt|message, history, seed?} -> propuestas

Contrato:
  1) el pedido viaja como ESTRUCTURA DE DATO (rubro/goals/tone/audience/
     must_have/notes) y se traduce a las respuestas del motor; el texto
     viejo ("Rubro: …") se sigue aceptando;
  2) el MCP decide qué skill aplicar: cada propuesta recibe un estilo
     DISTINTO del catálogo (`mcp_style`) y sus `tokens_diseno` se traducen a
     `site_theme` (paleta, contenedores, tipografía) pasado por
     `clean_site_theme`;
  3) `apply` republica la piel elegida por el MCP (overlay en caché), no la
     del motor;
  4) gates de plan (has_customization + has_ai_design), pedido vacío -> 400 y
     determinismo (mismo pedido = mismo seed; seed+1 = otra tanda).
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from McpApp.domains.skills.models import DesignModelMcp
from StoreApp.domains.stores.models import StoreCustomization
from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services.ai_design_mcp import (
    apply_pattern,
    parse_message,
    pattern_from_components,
)
from StoreApp.domains.stores.tests_ai_design_contract import (
    AI_DESIGN,
    CUSTOMIZATION,
    DESIGN_ADVANCED,
    DESIGN_PLUS,
    PREMIUM_LIMITS,
    _make_account,
)

MESSAGE =   (
    'Rubro: Comida y bebida\n'
    'Objetivo: Vender online, Recibir consultas\n'
    'Tono: Cálido y cercano\n'
    'Audiencia: Personas\n'
    'Imprescindible: Botón de WhatsApp, Horarios\n'
    'Notas: panadería de barrio, hacemos facturas y tortas por encargo.'
)

PROMPT  =   {
    'rubro'     :   'gastronomia',
    'goals'     :   ['vender_online', 'conseguir_consultas'],
    'tone'      :   'calido',
    'audience'  :   'particulares',
    'must_have' :   ['whatsapp', 'hours'],
    'notes'     :   'panadería de barrio, hacemos facturas y tortas por encargo.',
}

TOKENS  =   {
    'primary'       :   '#b4532a',
    'secondary'     :   '#7c8a5a',
    'background'    :   '#fbf3e7',
    'surface'       :   '#fffaf1',
    'text'          :   '#3b2a20',
    'muted'         :   '#8a7565',
    'border'        :   '#ead9c5',
    'font'          :   'Nunito Sans',
    'heading_font'  :   'Playfair Display',
    'radius'        :   '18px',
    'shadow'        :   '0 14px 34px rgba(59,42,32,.10)',
    'source_repo'   :   'bbulakh/tailwind-ecommerce',
    'source_url'    :   'https://github.com/bbulakh/tailwind-ecommerce',
}

#Bloques HTML de una página home de repo: definen el PATRÓN (orden + variantes).
HOME_COMPONENTS =   {
    'header'        :   '<header class="sticky top-0">Tienda</header>',
    'hero'          :   '<section class="px-6 py-24"><div class="grid gap-12 md:grid-cols-2">hero</div></section>',
    'benefits'      :   '<section class="py-16"><div class="grid gap-6 md:grid-cols-3">beneficios</div></section>',
    'featured'      :   '<section class="py-20"><div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">productos</div></section>',
    'testimonials'  :   '<section class="py-16"><blockquote>opinión</blockquote></section>',
    'footer'        :   '<footer>Contacto</footer>',
}


def _seed_styles():
    #Fuentes de repo: son las únicas que el wizard puede elegir.
    DesignModelMcp.objects.create(
        slug = 'bb-minimal-home', nombre = 'Tailwind Ecommerce · Minimal Home', categoria = 'moda',
        tags = ['home', 'azul', 'limpio'],
        tokens_diseno = TOKENS, html_componentes = HOME_COMPONENTS,
    )
    DesignModelMcp.objects.create(
        slug = 'fc-grocery-home', nombre = 'Freshcart · Grocery Home', categoria = 'alimentos',
        tags = ['retail', 'fresco', 'grocery', 'calido'],
        tokens_diseno = {**TOKENS, 'primary': '#0aad0a', 'background': '#f6fbf6', 'radius': '10px'},
        html_componentes = {
            **HOME_COMPONENTS,
            'hero': '<section class="py-20"><div class="grid md:grid-cols-2">hero</div></section>',
            'featured': '<section><div class="grid md:grid-cols-3">productos</div></section>',
        },
    )
    DesignModelMcp.objects.create(
        slug = 'ts-premium-home', nombre = 'Tailstore · Premium Home', categoria = 'general',
        tags = ['moderno', 'swiper', 'premium'],
        tokens_diseno = {**TOKENS, 'primary': '#10b981', 'background': '#ffffff'},
        html_componentes = HOME_COMPONENTS,
    )
    #Preset curado del sistema: NO tiene `source_repo`, así que el wizard no
    #puede elegirlo aunque matchee mejor las palabras del pedido.
    DesignModelMcp.objects.create(
        slug = 'organic-terracotta', nombre = 'Organic Terracotta', categoria = 'alimentos',
        tags = ['calido', 'artesanal', 'organico', 'terracota', 'gastronomia'],
        tokens_diseno = {key: value for key, value in TOKENS.items() if not key.startswith('source_')},
        html_componentes = {'hero': '<section>preset</section>'},
    )


class AiDesignMcpParseTests(TestCase):
    def test_blocks_map_to_engine_answers(self):
        prompt  =   parse_message(MESSAGE)
        self.assertEqual(prompt['rubro'], 'gastronomia')
        self.assertIn('vender_online', prompt['goals'])
        self.assertIn('conseguir_consultas', prompt['goals'])
        self.assertEqual(prompt['tone'], 'calido')
        self.assertEqual(prompt['audience'], 'Personas')
        self.assertIn('whatsapp', prompt['must_have'])
        self.assertIn('hours', prompt['must_have'])
        self.assertIn('panader', prompt['notes'])
        for goal in prompt['goals']:
            self.assertIn(goal, R.GOALS)
        for item in prompt['must_have']:
            self.assertIn(item, R.MUST_HAVE_BLOCKS)

    def test_unknown_text_is_tolerated(self):
        prompt  =   parse_message('Hola, quiero una web linda')
        self.assertEqual(prompt.get('rubro', ''), '')
        self.assertIn('web linda', prompt.get('notes', ''))


class PatternFromRepoTests(TestCase):
    def test_pattern_reads_repo_sections_and_variants(self):
        pattern =   pattern_from_components(HOME_COMPONENTS)
        self.assertEqual(pattern['order'], ['hero', 'benefits', 'featured', 'testimonials'])
        self.assertEqual(pattern['variants']['hero'], 'split')
        self.assertEqual(pattern['variants']['benefits'], 'cards')
        self.assertEqual(pattern['variants']['featured'], 'cols4')

    def test_apply_pattern_reorders_and_keeps_unknown_blocks(self):
        layout  =   {'landing': {'blocks': [
            {'id': 'featured', 'enabled': True, 'order': 0},
            {'id': 'about', 'enabled': True, 'order': 1},
            {'id': 'hero', 'enabled': True, 'order': 2},
            {'id': 'cta', 'enabled': False, 'order': 3},
        ]}}
        out     =   apply_pattern(layout, pattern_from_components(HOME_COMPONENTS))
        ids     =   [block['id'] for block in out['landing']['blocks']]
        self.assertEqual(ids, ['hero', 'featured', 'about', 'cta'])
        self.assertEqual(out['landing']['blocks'][0]['variant'], 'split')
        self.assertEqual(out['landing']['blocks'][1]['variant'], 'cols4')


class AiDesignMcpEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        _seed_styles()
        self.url    =   f'{reverse("Stores-list")}ai-design/mcp/'
        self.apply_url = f'{reverse("Stores-list")}ai-design/apply/'

    def _client(self, *codes):
        user, profile, store    =   _make_account(*codes, limits = PREMIUM_LIMITS)
        client                  =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def _premium(self):
        #Premium: el estilo del MCP entra completo (paleta, contenedores y
        #tipografía). En Estándar el saneo del tema recorta lo premium igual
        #que con cualquier diseño elegido a mano.
        return self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS + DESIGN_ADVANCED))

    def test_structured_prompt_returns_proposals_with_mcp_style(self):
        client, _   =   self._premium()
        response    =   client.post(self.url, {'prompt': PROMPT, 'history': []}, format = 'json')
        self.assertEqual(response.status_code, 200)
        body        =   response.json()
        self.assertTrue(body['proposals'])
        self.assertIsInstance(body['seed'], int)
        self.assertEqual(body['prompt']['rubro'], 'gastronomia')
        self.assertEqual(body['prompt']['tone'], 'calido')
        self.assertTrue(body['mcp']['styles'])
        slugs = {style['slug'] for style in body['mcp']['styles']}
        #Solo fuentes de repo: el preset curado nunca entra.
        self.assertNotIn('organic-terracotta', slugs)
        self.assertTrue(slugs <= {'bb-minimal-home', 'fc-grocery-home', 'ts-premium-home'})
        for proposal in body['proposals']:
            self.assertIn(proposal['mcp_style']['slug'], slugs)
            self.assertIn('palette', proposal['site_theme'])
            self.assertIn('containers', proposal['site_theme'])
            self.assertTrue(proposal['mcp_style']['source_repo'])

    def test_pattern_comes_from_repo_components(self):
        client, _   =   self._premium()
        body        =   client.post(self.url, {'prompt': PROMPT}, format = 'json').json()
        proposal    =   body['proposals'][0]
        pattern     =   proposal['mcp_style']['pattern']
        self.assertEqual(pattern[:3], ['hero', 'benefits', 'featured'])
        blocks      =   proposal['layout_config']['landing']['blocks']
        enabled     =   [block for block in blocks if block.get('enabled') is not False]
        ids         =   [block['id'] for block in enabled]
        self.assertEqual(ids[0], 'hero')
        #Los bloques activos siguen el orden del repo (los que el motor no
        #trae se conservan al final).
        in_pattern  =   [block_id for block_id in ids if block_id in pattern]
        self.assertEqual(in_pattern, [block_id for block_id in pattern if block_id in ids])
        hero        =   next(block for block in enabled if block['id'] == 'hero')
        self.assertEqual(hero.get('variant'), 'split')

    def test_mcp_tokens_land_in_site_theme(self):
        client, _   =   self._premium()
        body        =   client.post(self.url, {'prompt': PROMPT}, format = 'json').json()
        proposal    =   body['proposals'][0]
        style       =   next(s for s in body['mcp']['styles'] if s['slug'] == proposal['mcp_style']['slug'])
        tokens      =   next(s.tokens_diseno for s in DesignModelMcp.objects.all() if s.slug == style['slug'])
        palette     =   proposal['site_theme']['palette']
        self.assertEqual(palette['bg'], tokens['background'])
        self.assertIn(proposal['site_theme']['containers']['radius'], ('none', 'sm', 'md', 'lg', 'xl'))
        self.assertIn(proposal['site_theme']['typography']['heading'], ('playfair-display', 'inter', 'space-grotesk'))

    def test_apply_publishes_the_mcp_style(self):
        client, store   =   self._premium()
        body            =   client.post(self.url, {'prompt': PROMPT}, format = 'json').json()
        proposal        =   body['proposals'][0]
        response        =   client.post(
            self.apply_url,
            {'seed': body['seed'], 'proposal_id': proposal['id']},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        customization   =   StoreCustomization.objects.get(store = store)
        draft           =   customization.site_theme_draft or {}
        self.assertEqual(
            (draft.get('palette') or {}).get('bg'),
            (proposal['site_theme'].get('palette') or {}).get('bg'),
        )
        #El patrón (orden + variantes del repo) también se republica.
        published   =   (customization.layout_config_draft or {}).get('landing', {}).get('blocks') or []
        expected    =   proposal['layout_config']['landing']['blocks']
        self.assertEqual([b['id'] for b in published], [b['id'] for b in expected])

    def test_text_message_still_works(self):
        client, _   =   self._premium()
        response    =   client.post(self.url, {'message': MESSAGE}, format = 'json')
        self.assertEqual(response.status_code, 200)
        body        =   response.json()
        self.assertEqual(body['prompt']['rubro'], 'gastronomia')
        self.assertTrue(body['proposals'])

    def test_same_prompt_is_deterministic_and_seed_changes_tanda(self):
        client, _   =   self._premium()
        first       =   client.post(self.url, {'prompt': PROMPT}, format = 'json').json()
        again       =   client.post(self.url, {'prompt': PROMPT}, format = 'json').json()
        other       =   client.post(self.url, {'prompt': PROMPT, 'seed': first['seed'] + 1}, format = 'json').json()
        self.assertEqual(first['seed'], again['seed'])
        self.assertEqual(
            [p['id'] for p in first['proposals']],
            [p['id'] for p in again['proposals']],
        )
        self.assertNotEqual(first['seed'], other['seed'])

    def test_empty_prompt_is_400(self):
        client, _   =   self._premium()
        response    =   client.post(self.url, {'prompt': {}}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_standard_plan_still_gets_a_skill(self):
        #Estándar tiene has_ai_design pero no diseño avanzado: el skill se
        #elige y viaja en la propuesta, aunque el saneo del tema recorte la
        #paleta premium (misma regla que un diseño elegido a mano).
        client, _   =   self._client(*(CUSTOMIZATION + AI_DESIGN + DESIGN_PLUS))
        response    =   client.post(self.url, {'prompt': PROMPT}, format = 'json')
        self.assertEqual(response.status_code, 200)
        body        =   response.json()
        self.assertTrue(body['mcp']['styles'])
        self.assertTrue(body['proposals'][0]['mcp_style']['slug'])

    def test_requires_customization_benefit(self):
        client, _   =   self._client(*AI_DESIGN)
        response    =   client.post(self.url, {'prompt': PROMPT}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_requires_ai_design_benefit(self):
        client, _   =   self._client(*CUSTOMIZATION)
        response    =   client.post(self.url, {'prompt': PROMPT}, format = 'json')
        self.assertEqual(response.status_code, 403)
