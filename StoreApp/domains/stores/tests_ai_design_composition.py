#Tests de composición del motor "Diseñar con IA" v6 (fase B).
#El rediseño se mide en el layout: ritmo alternado, apertura según objetivo,
#cierre fijo, must_have, densidad por tono y firma distinta por propuesta.
#Todo sobre funciones puras de ai_design (sin base de datos) salvo el caso
#que arma propuestas completas.

import random
import unittest

from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS
from StoreApp.domains.stores.services import ai_design as A
from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services import ai_design_skins as SKIN

RUBROS      =   tuple(R.RUBROS)
GOALS       =   tuple(R.GOAL_RECIPES)
TONES       =   ('serio', 'moderno', 'audaz', 'calido')
#Espejo de PICK_VARIANTS en frontend/src/views/StoreServicesView.vue: la
#variante efectiva del picker cae al default si no está en este set.
#Variantes que el frontend resuelve por catálogo cerrado aunque
#TEMPLATE_BLOCKS no las declare: picker (PICK_VARIANTS en StoreServicesView)
#y steps=rail (las dos formas de bloque "Cómo funciona" ya existen).
FRONTEND_VARIANTS           =   {
    'picker': ('cards', 'list', 'bento', 'tabs', 'timeline', 'packages'),
    'steps':  ('rail',),
}
_CLOSERS                    =   frozenset({'cta', 'contact'})


def answers(rubro = 'comercio', goal = 'vender_online', tone = 'moderno', must_have = None):
    return {
        'rubro':        rubro,
        'goals':        [goal],
        'tone':         tone,
        'must_have':    list(must_have or ()),
        'styles':       [],
        'brand_color':  None,
        'primary_goal': goal,
        'second_goal':  None,
    }


def facts(empty = None):
    """Tienda con todo cargado; `empty` apaga los hechos pedidos."""
    data    =   {
        'products': True, 'images': True, 'categories': True, 'brands': True,
        'gallery': True, 'carousel': True, 'offers': True, 'countdown': True,
        'catalog_dense': True, 'catalog_note': True, 'announcements': True,
        'highlights': True, 'about': True, 'services': True, 'stats': True,
        'benefits': True, 'timeline': True, 'team': True, 'testimonials': True,
        'faqs': True, 'video': True, 'steps': True, 'service_form': True,
        'compare': True, 'contact': True, 'logo': True, 'cover': True,
    }
    for key in (empty or ()):
        data[key]  =   False
    return data


def landing_blocks(surface_layout):
    #_build_surface devuelve la superficie sola; _layout el dict completo.
    if 'landing' in surface_layout:
        surface_layout  =   surface_layout['landing']
    return surface_layout['blocks']


def shown_with_goal(ids):
    """Bloques que cuentan como secciones: desde la prueba social, el cierre
    (las fotos que quedan al final no son sección)."""
    stop    =   next(
        (position for position, block_id in enumerate(ids) if block_id in R.SOCIAL_BLOCKS or block_id in _CLOSERS),
        len(ids),
    )
    return ids[:stop]


def composition(layout):
    return {
        surface: [(block['id'], block.get('variant'), bool(block.get('enabled')))
                  for block in section['blocks']]
        for surface, section in layout.items()
    }


class AlternatingRhythmTests(unittest.TestCase):

    def test_two_image_blocks_are_never_adjacent(self):
        #La portada no es una sección: el hero puede ir con una foto pegada.
        #Entre DOS SECCIONES de foto grande va siempre un bloque de texto o de
        #datos, y la portada desdoblada (hero / foto / texto / foto) separa el
        #par que abre. Con el objetivo en foto la portada abre con sus fotos
        #(mostrar_trabajos: galería + vitrina, el gesto del brief).
        for rubro in RUBROS:
            for goal in GOALS:
                for rot in (0, 1, 2, 3):
                    layout  =   A._build_surface('landing', facts(), answers(rubro, goal), random.Random(rot), rot)
                    ids     =   [block['id'] for block in landing_blocks(layout) if block['enabled']]
                    for previous, current, following in zip(ids[1:], ids[2:], ids[3:]):
                        #Dos secciones de foto grande seguidas: nunca.
                        self.assertFalse(
                            previous in R.IMAGE_BLOCKS and current in R.IMAGE_BLOCKS,
                            f'{rubro}/{goal}/{rot}: {previous} y {current} seguidos',
                        )
                        #Tres fotos juntas solo como portada doblada.
                        self.assertTrue(
                            current not in R.IMAGE_BLOCKS or following not in R.IMAGE_BLOCKS or previous == 'hero',
                            f'{rubro}/{goal}/{rot}: tira sin portada {previous}/{current}/{following}',
                        )
                    #Si la tira de la portada choca (hero + dos fotos), la
                    #sección que sigue es texto o datos reales: nunca prueba
                    #social, cierre ni contacto como relleno.
                    first   =   next(
                        (position for position, block_id in enumerate(ids) if block_id not in R.IMAGE_BLOCKS and block_id != 'hero'),
                        len(ids),
                    )
                    if first > 2:
                        self.assertNotIn(ids[first], R.SOCIAL_BLOCKS | _CLOSERS, f'{rubro}/{goal}/{rot}')

    def test_post_process_keeps_every_block(self):
        blocks  =   [
            {'id': 'hero', 'enabled': True},
            {'id': 'featured', 'enabled': True},
            {'id': 'gallery', 'enabled': True},
            {'id': 'aimosaic', 'enabled': True},
            {'id': 'about', 'enabled': True},
            {'id': 'stats', 'enabled': True},
            {'id': 'cta', 'enabled': True},
        ]
        ordered =   [block['id'] for block in A._alternate_rhythm(blocks)]
        self.assertEqual(sorted(ordered), sorted(block['id'] for block in blocks))
        #Con dos textos reales, las tres fotos quedan separadas (foto, texto,
        #foto, texto, foto) y el cierre sigue al final.
        self.assertEqual(ordered, ['hero', 'featured', 'about', 'gallery', 'stats', 'aimosaic', 'cta'])
        self.assertEqual(ordered[-1], 'cta')
        for previous, current in zip(ordered[1:], ordered[2:]):
            self.assertFalse(previous in R.IMAGE_BLOCKS and current in R.IMAGE_BLOCKS, f'{previous}/{current}')

    def test_closer_is_never_used_as_separator(self):
        blocks  =   [
            {'id': 'featured', 'enabled': True},
            {'id': 'gallery', 'enabled': True},
            {'id': 'newsletter', 'enabled': True},
            {'id': 'testimonials', 'enabled': True},
            {'id': 'cta', 'enabled': True},
            {'id': 'contact', 'enabled': True},
        ]
        ordered =   [block['id'] for block in A._alternate_rhythm(blocks)]
        self.assertEqual(ordered[-2:], ['cta', 'contact'])
        #El separador es el texto libre (newsletter), nunca la prueba social
        #ni el cierre; el resto conserva su orden.
        self.assertEqual(ordered, ['featured', 'newsletter', 'gallery', 'testimonials', 'cta', 'contact'])

    def test_opening_pair_split_with_a_real_text(self):
        #mostrar_trabajos abre con la galería como portada: la vitrina que la
        #sigue ya no queda suelta, la separa un texto real (nunca la prueba
        #social ni el cierre).
        layout  =   A._build_surface('landing', facts(), answers('comercio', 'mostrar_trabajos'), random.Random(0), 0)
        ids     =   [block['id'] for block in landing_blocks(layout)]
        self.assertEqual(ids[:2], ['hero', 'gallery'])
        self.assertIn('featured', ids)
        self.assertNotIn(ids[2], R.IMAGE_BLOCKS | R.SOCIAL_BLOCKS | _CLOSERS)

    def test_image_block_without_a_text_block_goes_last(self):
        blocks  =   [
            {'id': 'featured', 'enabled': True},
            {'id': 'gallery', 'enabled': True},
            {'id': 'aimosaic', 'enabled': True},
        ]
        ordered =   [block['id'] for block in A._alternate_rhythm(blocks)]
        #Sin ningún texto que pueda separar (tres fotos seguidas y nada más) el
        #orden se conserva y no se inventa una sección.
        self.assertEqual(ordered, ['featured', 'gallery', 'aimosaic'])


class OpeningRuleTests(unittest.TestCase):

    def test_first_content_block_comes_from_the_goal_group(self):
        for rubro in RUBROS:
            for goal in GOALS:
                opening =   R.GOAL_RECIPES[goal]['opening']
                for rot in (0, 1, 2, 3):
                    layout  =   A._build_surface('landing', facts(), answers(rubro, goal), random.Random(rot), rot)
                    content =   [block for block in landing_blocks(layout) if block['enabled']]
                    #El hero abre; el primer bloque habilitado después tiene
                    #que salir del grupo del objetivo.
                    first   =   next((block for block in content if block['id'] != 'hero'), None)
                    self.assertIn(first['id'], opening, f'{rubro}/{goal}/{rot}: abre con {first["id"]}')

    def test_goal_recipe_respected_with_dense_data(self):
        #Con el juego completo de datos (y sin ellos) la apertura del objetivo
        #sale primero: no depende del rubro ni del tono.
        for rubro in RUBROS:
            for goal in GOALS:
                opening =   R.GOAL_RECIPES[goal]['opening']
                for tone in TONES:
                    layout  =   A._build_surface('landing', facts(), answers(rubro, goal, tone), random.Random(0), 0)
                    content =   [block for block in landing_blocks(layout) if block['enabled'] and block['id'] != 'hero']
                    self.assertIn(content[0]['id'], opening, f'{rubro}/{goal}/{tone}: {content[0]["id"]}')

    def test_missing_opening_data_never_invents_a_block(self):
        layout  =   A._build_surface(
            'landing', facts(empty = ('categories', 'offers')), answers('comercio', 'vender_online'), random.Random(0), 0,
        )
        ids     =   [block['id'] for block in landing_blocks(layout)]
        self.assertIn('categories', ids)
        by_id   =   {block['id']: block for block in landing_blocks(layout)}
        self.assertFalse(by_id['categories']['enabled'])
        self.assertFalse(by_id['offers']['enabled'])

    def test_must_have_wins_over_the_opening(self):
        layout  =   A._build_surface(
            'landing', facts(), answers('comercio', 'vender_online', must_have = ['faq']), random.Random(0), 0,
        )
        content =   [block['id'] for block in landing_blocks(layout) if block['enabled']]
        #must_have sube al frente (después del hero); la apertura del objetivo
        #sigue existiendo en el layout aunque no sea la primera.
        self.assertEqual(content[1], 'faq')


class HierarchyTests(unittest.TestCase):

    def test_contact_is_last_and_hero_first_for_every_combination(self):
        for rubro in RUBROS:
            for goal in GOALS:
                layout  =   A._build_surface('landing', facts(), answers(rubro, goal), random.Random(0), 0)
                ids     =   [block['id'] for block in landing_blocks(layout)]
                self.assertEqual(ids[0], 'hero')
                self.assertEqual(ids[-1], 'contact', f'{rubro}/{goal}')

    def test_social_goes_before_the_cta(self):
        for rubro in RUBROS:
            for goal in GOALS:
                layout  =   A._build_surface('landing', facts(), answers(rubro, goal), random.Random(0), 0)
                ids     =   [block['id'] for block in landing_blocks(layout)]
                if 'cta' not in ids:
                    continue
                for social in ('testimonials', 'brands'):
                    if social in ids:
                        self.assertLess(ids.index(social), ids.index('cta'), f'{rubro}/{goal}/{social}')

    def test_must_have_blocks_land_in_the_first_third(self):
        for rubro in RUBROS:
            layout  =   A._build_surface(
                'landing', facts(), answers(rubro, 'vender_online', must_have = ['faq', 'benefits']), random.Random(0), 0,
            )
            ids =   [block['id'] for block in landing_blocks(layout) if block['enabled']]
            for block_id in ('faq', 'benefits'):
                self.assertIn(block_id, ids)
                self.assertLessEqual(ids.index(block_id), max(1, len(ids) // 3), f'{rubro}/{block_id}')


class DensityTests(unittest.TestCase):

    def test_serious_tone_turns_off_secondary_blocks(self):
        full    =   A._build_surface('landing', facts(), answers('construccion', 'dar_confianza', tone = 'moderno'), random.Random(0), 0)
        calm    =   A._build_surface('landing', facts(), answers('construccion', 'dar_confianza', tone = 'serio'), random.Random(0), 0)
        on_full =   {block['id'] for block in landing_blocks(full) if block['enabled']}
        on_calm =   {block['id'] for block in landing_blocks(calm) if block['enabled']}
        self.assertLess(len(on_calm), len(on_full))
        for block_id in ('team', 'video', 'timeline'):
            if block_id in on_full:
                self.assertNotIn(block_id, on_calm)

    def test_density_never_turns_off_a_block_without_gate(self):
        calm    =   A._build_surface('landing', facts(), answers('salud', 'dar_confianza', tone = 'serio'), random.Random(0), 0)
        by_id   =   {block['id']: block for block in landing_blocks(calm)}
        self.assertTrue(by_id['hero']['enabled'])
        self.assertTrue(by_id['cta']['enabled'])

    def test_bold_tone_keeps_everything(self):
        data    =   A._build_surface('landing', facts(), answers('arte', 'mostrar_trabajos', tone = 'audaz'), random.Random(0), 0)
        ids     =   {block['id'] for block in landing_blocks(data) if block['enabled']}
        self.assertIn('gallery', ids)
        self.assertIn('about', ids)


class VariantCatalogTests(unittest.TestCase):

    def test_every_variant_in_a_layout_exists_in_the_catalog(self):
        for rubro in RUBROS:
            for goal in GOALS:
                layout  =   A._layout(None, facts(), answers(rubro, goal), random.Random(0), 0)
                for surface, section in layout.items():
                    for block in section['blocks']:
                        variants    =   (TEMPLATE_BLOCKS[surface].get(block['id']) or {}).get('variants')
                        if block.get('variant'):
                            self.assertIn(block['variant'], variants or (), f'{surface}/{block["id"]}')

    def test_catalog_and_services_are_designed_too(self):
        #El catálogo y los servicios no son un layout fijo: filtros, grilla,
        #selector y pasos cambian de variante con la piel.
        seen    =   {'filters': set(), 'grid': set(), 'picker': set(), 'steps': set()}
        for skin in SKIN.SKINS.values():
            layout  =   A._layout(None, facts(), answers('comercio', 'vender_online'), random.Random(0), 0)
            A._apply_skin_layout(layout, skin, facts())
            for surface in ('catalog', 'services'):
                for block in layout[surface]['blocks']:
                    if block.get('variant'):
                        seen.setdefault(block['id'], set()).add(block['variant'])
        #Filters y grid (catálogo) y picker (servicios) cambian de variante
        #con la piel; steps suma la forma 'rail' donde la piel la pide.
        for block_id in ('filters', 'grid', 'picker'):
            self.assertGreaterEqual(len(seen.get(block_id, ())), 2, f'{block_id} sin variantes reales')
        self.assertIn('rail', seen.get('steps', ()))

    def test_new_layout_families_are_distinct(self):
        self.assertEqual(set(A._GRID_BY_LAYOUT), set(A._VARIANTS_BY_LAYOUT))
        signatures  =   {layout: tuple(sorted(A._VARIANTS_BY_LAYOUT[layout].items())) for layout in A._VARIANTS_BY_LAYOUT}
        self.assertEqual(len(signatures), len(set(signatures.values())), 'dos layouts comparten firma de bloques')

    def test_new_variant_families_use_real_catalog_ids(self):
        for layout, variants in A._VARIANTS_BY_LAYOUT.items():
            for block_id, variant in variants.items():
                if block_id in FRONTEND_VARIANTS:
                    self.assertIn(variant, FRONTEND_VARIANTS[block_id], f'{layout}/{block_id}')
                    continue
                specs   =   [
                    TEMPLATE_BLOCKS[surface][block_id]
                    for surface in ('landing', 'catalog', 'services')
                    if block_id in TEMPLATE_BLOCKS[surface]
                ]
                self.assertTrue(specs, f'{layout}/{block_id} no existe en el catálogo')
                self.assertTrue(
                    any(variant in (spec.get('variants') or ()) for spec in specs),
                    f'{layout}/{block_id}: variante {variant} fuera del catálogo',
                )


class AntiRepetitionTests(unittest.TestCase):

    def test_rotate_shifts_the_middle_group(self):
        first   =   A._build_surface('landing', facts(), answers('gastronomia', 'vender_online'), random.Random(0), 0)
        second  =   A._build_surface('landing', facts(), answers('gastronomia', 'vender_online'), random.Random(0), 1)
        self.assertNotEqual(
            [block['id'] for block in landing_blocks(first)],
            [block['id'] for block in landing_blocks(second)],
        )

    def test_signature_differs_between_rotations(self):
        signatures  =   set()
        for rot in range(4):
            layout  =   A._layout(None, facts(), answers('gastronomia', 'vender_online'), random.Random(rot), rot)
            signatures.add(A._layout_signature('cobre', layout))
        self.assertEqual(len(signatures), 4)

    def test_alternate_proposals_turn_off_or_move_blocks(self):
        #La segunda propuesta usa el layout alterno de la familia: la firma
        #de variantes cambia aunque la piel sea la misma.
        signatures  =   []
        for alt in (None, SKIN.SKIN_LAYOUT_ALT.get(SKIN.SKINS['editorial-ink']['family'])):
            skin    =   {**SKIN.SKINS['editorial-ink'], 'layout_alt': alt}
            layout  =   A._layout(None, facts(), answers('indumentaria', 'vender_online'), random.Random(0), 0)
            layout  =   A._apply_skin_layout(layout, skin, facts())
            signatures.append(A._layout_signature('cobre', layout))
        self.assertNotEqual(signatures[0], signatures[1])


class GoalRecipeTests(unittest.TestCase):
    """Script de 1200 combinaciones (13 rubros × 5 objetivos × 4 tonos ×
    rotaciones), igual que el criterio de aceptación del brief §5.4."""

    def test_goal_recipe_respected_in_1200_combinations(self):
        total, hits    =   0, 0
        for rubro in RUBROS:
            for goal in GOALS:
                for tone in TONES:
                    #13 × 5 × 4 × 5 rotaciones = 1300 combinaciones.
                    for rot in range(5):
                        total   +=  1
                        layout  =   A._build_surface('landing', facts(), answers(rubro, goal, tone), random.Random(rot), rot)
                        content =   [block for block in landing_blocks(layout) if block['enabled'] and block['id'] != 'hero']
                        if content and content[0]['id'] in R.GOAL_RECIPES[goal]['opening']:
                            hits += 1
        self.assertGreaterEqual(total, 1200)
        ratio   =   hits / total
        self.assertGreaterEqual(ratio, 0.9, f'apertura del objetivo: {ratio:.2%}')

    def test_goal_recipe_contact_last_in_1200_combinations(self):
        for rubro in RUBROS:
            for goal in GOALS:
                for tone in TONES:
                    for rot in (0, 1, 2):
                        layout  =   A._build_surface('landing', facts(), answers(rubro, goal, tone), random.Random(rot), rot)
                        ids     =   [block['id'] for block in landing_blocks(layout)]
                        self.assertEqual(ids[-1], 'contact', f'{rubro}/{goal}/{tone}/{rot}')
                        self.assertEqual(ids[0], 'hero', f'{rubro}/{goal}/{tone}/{rot}')


class PortadaDobladaTests(unittest.TestCase):

    def test_opening_in_photo_folds_the_portada(self):
        #mostrar_trabajos abre con la galería: la portada se dobla (hero +
        #fotos) y el primer texto real las separa, así el par de la portada no
        #queda pegado y la primera sección sigue siendo la del objetivo.
        layout  =   A._build_surface('landing', facts(), answers('comercio', 'mostrar_trabajos'), random.Random(0), 0)
        ids     =   [block['id'] for block in landing_blocks(layout) if block['enabled']]
        self.assertEqual(ids[0], 'hero')
        self.assertIn('gallery', ids[1:3])
        self.assertTrue(all(right in R.IMAGE_BLOCKS for right in ids[1:ids.index('gallery') + 1]))

    def test_alternate_proposal_keeps_the_hero_first(self):
        for rot in (1, 2, 3):
            layout  =   A._build_surface('landing', facts(), answers('gastronomia', 'vender_online'), random.Random(rot), rot)
            ids     =   [block['id'] for block in landing_blocks(layout)]
            self.assertEqual(ids[0], 'hero', f'rot {rot}')
            self.assertEqual(ids[-1], 'contact', f'rot {rot}')
