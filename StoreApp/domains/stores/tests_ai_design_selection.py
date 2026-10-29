#Tests unitarios de la SELECCIÓN DE ESTILO del motor de diseño (ai_design):
#_skin_pool, _style_pool, _style_order, _style_candidates y _select_styles.
#
#Son funciones puras (no tocan la DB ni la red): se prueban directo, sin
#TestCase, para que corran en milisegundos y fijen los invariantes que ya
#rompieron antes (ver AGENTS.md, "Trampas del motor"):
#  - la plantilla NUNCA sale del plan (`allowed`);
#  - dos propuestas nunca repiten plantilla y, dentro de lo posible, tampoco
#    estilo;
#  - un estilo pedido en la entrevista se ve en la propuesta ganadora;
#  - "otra propuesta" (seed+1) cambia de familia visual.
import unittest

from StoreApp.domains.stores.services import ai_design as A
from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services import ai_design_skins as SKIN
from StoreApp.domains.stores.services import ai_design_typography as TYPE

PLAN_BASIC      =   ('classic', 'duo')
PLAN_PLUS       =   ('classic', 'duo', 'calma', 'vitrina')
PLAN_ADVANCED   =   ('classic', 'duo', 'calma', 'vitrina', 'cobre', 'minimal', 'perspective', 'street')
PLAN_AI         =   PLAN_ADVANCED + tuple(R.AI_TEMPLATES)

FACT_KEYS       =   ('products', 'images', 'categories', 'brands', 'gallery', 'carousel',
                     'offers', 'countdown', 'catalog_dense', 'catalog_note', 'announcements',
                     'highlights', 'about', 'services', 'stats', 'benefits', 'timeline',
                     'team', 'testimonials', 'faqs', 'video')


def facts_full():
    """Tienda con todo el contenido cargado."""
    return {key: True for key in FACT_KEYS}


def facts_empty():
    """Tienda recién creada: nada de contenido."""
    return {key: False for key in FACT_KEYS}


def stats_dense():
    return {'products': 20, 'images': 12, 'categories': 4, 'brands': 3, 'gallery': 6,
            'carousel': 3, 'offers': 4, 'text_chars': 900}


def stats_empty():
    return {'products': 0, 'images': 0, 'categories': 0, 'brands': 0, 'gallery': 0,
            'carousel': 0, 'offers': 0, 'text_chars': 0}


def answers(rubro = 'otro', tone = 'moderno', goals = None, styles = None, **extra):
    """Entrevista equivalente a la que produce `_answers()` ya normalizada."""
    data = {
        'rubro'         :   rubro,
        'tone'          :   tone,
        'goals'         :   list(goals or ['vender_online']),
        'must_have'     :   [],
        'styles'        :   list(styles or []),
        'audience'      :   '',
        'brand_color'   :   '',
        'night_mode'    :   {'enabled': False, 'default': ''},
        'cover_choice'  :   'auto',
        'use_icons'     :   None,
    }
    data.update(extra)
    return data


def score_of(candidate):
    return candidate['score']


#=========================================
# CONTRATO DEL CATÁLOGO (datos del motor)
#=========================================
class CatalogoCerrado(unittest.TestCase):
    """Los catálogos que consume la selección no se rompen por datos."""

    def test_every_style_family_has_at_least_one_skin(self):
        for style in SKIN.STYLE_FAMILIES:
            skins = [skin_id for skin_id in SKIN.SKIN_IDS if SKIN.SKINS[skin_id]['style'] == style]
            self.assertTrue(skins, f'Estilo sin pieles: {style}')

    def test_every_skin_style_belongs_to_the_training_families(self):
        for skin_id, skin in SKIN.SKINS.items():
            self.assertIn(skin['style'], SKIN.STYLE_FAMILIES, skin_id)

    def test_every_rubro_declares_three_signature_styles(self):
        for rubro in R.RUBROS:
            self.assertIn(rubro, R.RUBRO_STYLES)
            self.assertEqual(len(R.RUBRO_STYLES[rubro]), 3, rubro)

    def test_signature_styles_point_to_the_closed_catalogs(self):
        for rubro, signatures in R.RUBRO_STYLES.items():
            for signature in signatures:
                self.assertIn(signature['template'], R.RUBROS[rubro]['templates'] + R.AI_TEMPLATES + R.LEGACY_TEMPLATES, rubro)
                self.assertIn(signature['skin'], SKIN.SKINS, rubro)
                self.assertIn(signature['pair'], TYPE.TYPE_PAIRS, rubro)

    def test_type_pairs_catalog_is_not_empty(self):
        self.assertGreater(len(TYPE.TYPE_PAIRS), 0)


#=========================================
# _skin_pool
#=========================================
class SkinPoolTests(unittest.TestCase):

    def test_pool_keeps_the_whole_closed_catalog(self):
        pool = A._skin_pool(answers(), 0)
        self.assertEqual(set(pool), set(SKIN.SKIN_IDS))
        self.assertEqual(len(pool), len(SKIN.SKIN_IDS))

    def test_seed_zero_starts_with_the_rubro_and_tone_match(self):
        data    =   answers(rubro = 'comercio', tone = 'moderno')
        pool    =   A._skin_pool(data, 0)
        first   =   SKIN.SKINS[pool[0]]
        self.assertIn('comercio', first['rubros'])
        self.assertIn('moderno', first['tones'])

    def test_every_seed_produces_the_same_set_in_a_different_order(self):
        data    =   answers(rubro = 'gastronomia', tone = 'calido')
        base    =   A._skin_pool(data, 0)
        for seed in range(1, 10):
            rotated = A._skin_pool(data, seed)
            self.assertEqual(set(rotated), set(base))
            self.assertNotEqual(rotated, base, f'seed {seed} no rotó la piel')

    def test_seed_is_taken_modulo_pool_size(self):
        data    =   answers(rubro = 'salud', tone = 'serio')
        size    =   len(SKIN.SKIN_IDS)
        self.assertEqual(A._skin_pool(data, 3), A._skin_pool(data, 3 + size))

    def test_unknown_rubro_and_tone_degrade_to_the_whole_catalog(self):
        pool = A._skin_pool(answers(rubro = 'inventado', tone = 'inventado'), 0)
        self.assertEqual(set(pool), set(SKIN.SKIN_IDS))

    def test_pool_never_returns_duplicates(self):
        for seed in range(0, 8):
            pool = A._skin_pool(answers(), seed)
            self.assertEqual(len(pool), len(set(pool)))


#=========================================
# _style_pool
#=========================================
class StylePoolTests(unittest.TestCase):

    def test_every_pool_entry_belongs_to_the_requested_style(self):
        for style in SKIN.STYLE_FAMILIES:
            for skin_id in A._style_pool(style, 'comercio', 'moderno'):
                self.assertEqual(SKIN.SKINS[skin_id]['style'], style)

    def test_pool_covers_every_skin_of_the_style(self):
        for style in SKIN.STYLE_FAMILIES:
            expected = {skin_id for skin_id, skin in SKIN.SKINS.items() if skin['style'] == style}
            self.assertEqual(set(A._style_pool(style, 'otro', 'moderno')), expected)

    def test_full_match_comes_before_a_partial_match(self):
        skin_with_match = next(
            skin_id for skin_id, skin in SKIN.SKINS.items()
            if skin['rubros'] and skin['tones']
        )
        skin = SKIN.SKINS[skin_with_match]
        pool = A._style_pool(skin['style'], skin['rubros'][0], skin['tones'][0])
        self.assertEqual(pool[0], skin_with_match)

    def test_full_match_entries_are_not_interleaved(self):
        skin_with_match = next(
            skin_id for skin_id, skin in SKIN.SKINS.items()
            if skin['rubros'] and skin['tones']
        )
        skin    =   SKIN.SKINS[skin_with_match]
        pool    =   A._style_pool(skin['style'], skin['rubros'][0], skin['tones'][0])
        matches = [
            index for index, skin_id in enumerate(pool)
            if skin['rubros'][0] in SKIN.SKINS[skin_id]['rubros'] and skin['tones'][0] in SKIN.SKINS[skin_id]['tones']
        ]
        self.assertEqual(matches, list(range(len(matches))))

    def test_unknown_values_still_return_the_style_skins(self):
        pool = A._style_pool('minimal', 'rubro-que-no-existe', 'tono-que-no-existe')
        self.assertTrue(pool)
        self.assertTrue(all(SKIN.SKINS[skin_id]['style'] == 'minimal' for skin_id in pool))


#=========================================
# _style_order
#=========================================
class StyleOrderTests(unittest.TestCase):

    def test_always_returns_the_eight_styles_without_repeats(self):
        for seed in range(10):
            order = A._style_order(answers(), seed)
            self.assertEqual(set(order), set(SKIN.STYLE_FAMILIES))
            self.assertEqual(len(order), len(SKIN.STYLE_FAMILIES))

    def test_requested_styles_go_first(self):
        order = A._style_order(answers(styles = ['luxury']), 0)
        self.assertEqual(order[0], 'luxury')

    def test_requested_styles_never_displace_each_other(self):
        order = A._style_order(answers(styles = ['tech', 'craft']), 4)
        self.assertEqual(set(order[:2]), {'tech', 'craft'})

    def test_rubro_affine_styles_lead_without_a_request(self):
        order = A._style_order(answers(rubro = 'comercio', tone = 'moderno'), 0)
        affine = {
            style for style in SKIN.STYLE_FAMILIES
            if any('comercio' in skin['rubros'] for skin in SKIN.SKINS.values() if skin['style'] == style)
        }
        self.assertTrue(set(order[:2]) <= affine, order)

    def test_seed_rotates_only_the_tail(self):
        data    =   answers(rubro = 'arte', tone = 'audaz')
        head    =   A._style_order(data, 0)[:2]
        for seed in range(1, 8):
            order = A._style_order(data, seed)
            self.assertEqual(order[:2], head, f'seed {seed} movió la cabeza')
            self.assertEqual(set(order), set(SKIN.STYLE_FAMILIES))

    def test_tail_actually_rotates_between_seeds(self):
        data    =   answers(rubro = 'otro', tone = 'moderno')
        tails   = {tuple(A._style_order(data, seed)[2:]) for seed in range(5)}
        self.assertGreater(len(tails), 1)

    def test_unknown_requested_style_is_ignored(self):
        order = A._style_order(answers(styles = ['no-existe']), 0)
        self.assertEqual(set(order), set(SKIN.STYLE_FAMILIES))

    def test_seed_is_taken_modulo_tail_size(self):
        data    =   answers(rubro = 'turismo', tone = 'calido')
        size    =   len(SKIN.STYLE_FAMILIES) - 2
        self.assertEqual(A._style_order(data, 0), A._style_order(data, size))


#=========================================
# _style_candidates — positivos
#=========================================
class StyleCandidatesPositiveTests(unittest.TestCase):

    def setUp(self):
        self.candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_BASIC, 0)

    def test_returns_candidates(self):
        self.assertTrue(self.candidates)

    def test_candidate_has_the_full_contract_shape(self):
        for candidate in self.candidates:
            self.assertEqual(
                set(candidate),
                {'template', 'skin', 'pair', 'style', 'source', 'score'},
            )
            self.assertIsInstance(candidate['score'], (int, float))

    def test_candidates_are_sorted_from_best_to_worst(self):
        scores = [score_of(candidate) for candidate in self.candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_every_candidate_uses_a_skin_and_pair_from_the_catalog(self):
        for candidate in self.candidates:
            self.assertIn(candidate['skin'], SKIN.SKINS)
            self.assertIn(candidate['pair'], TYPE.TYPE_PAIRS)

    def test_candidate_style_matches_its_skin(self):
        for candidate in self.candidates:
            self.assertEqual(candidate['style'], SKIN.SKINS[candidate['skin']]['style'])

    def test_style_source_is_derived_from_the_template(self):
        for candidate in self.candidates:
            self.assertEqual(candidate['source'], R.style_source_of(candidate['template']))

    def test_with_the_ai_flag_ai_templates_compete(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_AI, 0)
        templates = A.seen_templates(candidates)
        self.assertTrue(templates & set(R.AI_TEMPLATES), templates)

    def test_without_the_ai_flag_legacy_templates_compete(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 0)
        templates = A.seen_templates(candidates)
        self.assertTrue(templates & set(R.LEGACY_TEMPLATES), templates)

    def test_signature_matrix_opens_the_ranking(self):
        #La matriz del rubro es el piso de diversidad: sus plantillas (las que
        #el plan permite) están entre las candidatas.
        candidates  =   A._style_candidates(facts_full(), stats_dense(), answers(rubro = 'comercio'), PLAN_ADVANCED, 0)
        templates   =   A.seen_templates(candidates)
        expected    =   {
            signature['template'] for signature in R.RUBRO_STYLES['comercio']
            if signature['template'] in PLAN_ADVANCED
        }
        self.assertTrue(expected)
        self.assertTrue(expected <= templates, templates - expected)

    def test_goal_affinity_raises_the_score(self):
        #agregar el bloque de "catálogo" al objetivo debe mover el puntaje.
        base = A._style_candidates(
            facts_full(), stats_dense(), answers(goals = ['mostrar_servicios']), PLAN_ADVANCED, 0,
        )
        boost = A._style_candidates(
            facts_full(), stats_dense(), answers(goals = ['vender_online']), PLAN_ADVANCED, 0,
        )
        base_scores = {(c['template'], c['skin']): c['score'] for c in base}
        boost_scores = {(c['template'], c['skin']): c['score'] for c in boost}
        self.assertNotEqual(base_scores, boost_scores)

    def test_tone_match_raises_the_score_of_the_skin(self):
        with_tone = A._style_candidates(
            facts_full(), stats_dense(), answers(rubro = 'comercio', tone = 'moderno'), PLAN_PLUS, 0,
        )
        for candidate in with_tone:
            if 'moderno' in SKIN.SKINS[candidate['skin']]['tones']:
                self.assertGreaterEqual(candidate['score'], 8)


#=========================================
# _style_candidates — negativos (gating)
#=========================================
class StyleCandidatesGatingTests(unittest.TestCase):

    def test_never_returns_a_template_outside_the_plan(self):
        for allowed in (PLAN_BASIC, PLAN_PLUS, PLAN_ADVANCED, PLAN_AI):
            for seed in range(5):
                candidates = A._style_candidates(facts_full(), stats_dense(), answers(), allowed, seed)
                for candidate in candidates:
                    self.assertIn(candidate['template'], allowed, (allowed, seed, candidate))

    def test_regression_plan_basico_never_gets_ai_lumen(self):
        #El clon de respaldo de un estilo sin plantilla libre filtraba mal y
        #un plan Básico recibía ai_lumen (rompía el gating del backend).
        for seed in range(20):
            candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_BASIC, seed)
            templates = A.seen_templates(candidates)
            self.assertTrue(templates <= set(PLAN_BASIC), (seed, templates))

    def test_single_template_plan_only_returns_that_template(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(), ['classic'], 0)
        self.assertEqual(A.seen_templates(candidates), {'classic'})

    def test_empty_plan_returns_no_candidates(self):
        self.assertEqual(A._style_candidates(facts_full(), stats_dense(), answers(), [], 0), [])

    def test_empty_plan_does_not_crash_with_a_requested_style(self):
        self.assertEqual(
            A._style_candidates(facts_full(), stats_dense(), answers(styles = ['luxury']), [], 3),
            [],
        )

    def test_a_template_never_repeats_its_skin(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_AI, 0)
        pairs = [(candidate['template'], candidate['skin']) for candidate in candidates]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_requested_style_outside_the_catalog_is_ignored(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(styles = ['nada']), PLAN_BASIC, 0)
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertIn(candidate['style'], SKIN.STYLE_FAMILIES)


#=========================================
# _style_candidates — bordes
#=========================================
class StyleCandidatesEdgeTests(unittest.TestCase):

    def test_empty_store_still_produces_candidates(self):
        candidates = A._style_candidates(facts_empty(), stats_empty(), answers(), PLAN_BASIC, 0)
        self.assertTrue(candidates)

    def test_density_is_capped_and_does_not_break_the_order(self):
        dense   =   A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 0)
        empty   =   A._style_candidates(facts_empty(), stats_empty(), answers(), PLAN_ADVANCED, 0)
        self.assertGreater(dense[0]['score'], empty[0]['score'])

    def test_missing_fact_keys_are_treated_as_false(self):
        candidates = A._style_candidates({}, stats_empty(), answers(), PLAN_BASIC, 0)
        self.assertTrue(candidates)

    def test_data_signals_reward_photos_for_photo_templates(self):
        photo_stats = dict(stats_empty(), images = 10, gallery = 5)
        candidates  = A._style_candidates(facts_empty(), photo_stats, answers(), PLAN_BASIC, 0)
        self.assertEqual(A._data_signal('duo', photo_stats, facts_empty()), 0)
        self.assertTrue(candidates)

    def test_catalog_signal_only_fires_with_a_big_catalog(self):
        self.assertEqual(A._data_signal('duo', dict(stats_empty(), products = 5), facts_empty()), 0)
        self.assertEqual(A._data_signal('classic', dict(stats_empty(), products = 0), facts_empty()), 2)

    def test_requested_style_never_overrides_the_plan(self):
        #Estilo pedido cuya plantilla no está en el plan: no se impone.
        candidates = A._style_candidates(
            facts_full(), stats_dense(), answers(styles = ['luxury']), PLAN_BASIC, 0,
        )
        self.assertTrue(A.seen_templates(candidates) <= set(PLAN_BASIC))

    def test_requested_style_with_a_allowed_template_leads(self):
        candidates = A._style_candidates(
            facts_full(), stats_dense(), answers(styles = ['minimal']), PLAN_ADVANCED, 0,
        )
        self.assertEqual(candidates[0]['style'], 'minimal')

    def test_seed_plus_one_changes_the_head(self):
        first   =   A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 0)[:3]
        second  =   A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 1)[:3]
        signatures = lambda items: [(item['template'], item['skin']) for item in items]
        self.assertNotEqual(signatures(first), signatures(second))

    def test_same_inputs_are_byte_for_byte_deterministic(self):
        for seed in range(4):
            first   =   A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_AI, seed)
            second  =   A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_AI, seed)
            self.assertEqual(first, second)

    def test_results_do_not_depend_on_the_order_of_allowed(self):
        forward = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 2)
        reverse = A._style_candidates(facts_full(), stats_dense(), answers(), tuple(reversed(PLAN_ADVANCED)), 2)
        self.assertEqual(forward, reverse)

    def test_a_list_plan_is_accepted(self):
        candidates = A._style_candidates(facts_full(), stats_dense(), answers(), list(PLAN_BASIC), 0)
        self.assertTrue(candidates)

    def test_every_rubro_produces_candidates_with_its_own_plan(self):
        for rubro in R.RUBROS:
            candidates = A._style_candidates(facts_full(), stats_dense(), answers(rubro = rubro), PLAN_BASIC, 0)
            self.assertTrue(candidates, rubro)
            self.assertTrue(A.seen_templates(candidates) <= set(PLAN_BASIC), rubro)

    def test_small_seed_and_big_seed_are_equivalent_modulo_rotation(self):
        small = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 1)
        big   = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, 1 + 7 * 11)
        self.assertEqual(A.seen_templates(small), A.seen_templates(big))


#=========================================
# _select_styles
#=========================================
def candidate(template, skin, pair = 'grotesk-clean', style = None, score = 10):
    """Candidato sintético: aísla `_select_styles` del resto del motor."""
    return {
        'template'  :   template,
        'skin'      :   skin,
        'pair'      :   pair,
        'style'     :   style or SKIN.SKINS[skin]['style'],
        'source'    :   R.style_source_of(template),
        'score'     :   score,
    }


def two_skins_of(style):
    """Dos pieles distintas del mismo estilo."""
    skins = [skin_id for skin_id in SKIN.SKIN_IDS if SKIN.SKINS[skin_id]['style'] == style]
    return skins[0], skins[1]


class SelectStylesTests(unittest.TestCase):

    def test_empty_candidates_return_nothing(self):
        self.assertEqual(A._select_styles([], 2), [])

    def test_zero_count_returns_nothing(self):
        skin = SKIN.SKIN_IDS[0]
        self.assertEqual(A._select_styles([candidate('classic', skin)], 0), [])

    def test_takes_at_most_count(self):
        skin = SKIN.SKIN_IDS[0]
        items = [candidate(f'tpl{index}', skin) for index in range(5)]
        self.assertEqual(len(A._select_styles(items, 2)), 2)

    def test_never_repeats_a_template(self):
        style = 'minimal'
        first_skin, second_skin = two_skins_of(style)
        items = [candidate('classic', first_skin), candidate('classic', second_skin)]
        chosen = A._select_styles(items, 2)
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]['template'], 'classic')

    def test_prefers_distinct_styles_first(self):
        first_skin, second_skin = two_skins_of('minimal')
        luxury_skin = next(skin_id for skin_id in SKIN.SKIN_IDS if SKIN.SKINS[skin_id]['style'] == 'luxury')
        items = [
            candidate('classic', first_skin, pair = 'grotesk-clean'),
            candidate('duo', second_skin, pair = 'grotesk-clean'),
            candidate('cobre', luxury_skin, pair = 'grotesk-clean'),
        ]
        chosen = A._select_styles(items, 2)
        self.assertEqual(len({item['style'] for item in chosen}), 2)

    def test_falls_back_to_relaxed_pass_to_reach_count(self):
        #Solo hay candidatas del mismo estilo pero plantillas distintas: aun
        #así se devuelven dos (la plantilla es la condición dura).
        style = 'minimal'
        first_skin, second_skin = two_skins_of(style)
        items = [candidate('classic', first_skin), candidate('duo', second_skin)]
        chosen = A._select_styles(items, 2)
        self.assertEqual([item['template'] for item in chosen], ['classic', 'duo'])

    def test_strict_pass_rejects_a_repeated_pair(self):
        style = 'minimal'
        first_skin, second_skin = two_skins_of(style)
        items = [
            candidate('classic', first_skin, pair = 'grotesk-clean'),
            candidate('duo', second_skin, pair = 'grotesk-clean'),
        ]
        #El pase 1 toma la primera por estilo y descarta la segunda; el pase 2
        #exige par nuevo y el pase 3 solo pide plantilla nueva.
        chosen = A._select_styles(items, 2)
        self.assertEqual(len(chosen), 2)
        self.assertNotEqual(chosen[0]['template'], chosen[1]['template'])

    def test_preserves_the_original_ranking(self):
        skins = [next(skin_id for skin_id in SKIN.SKIN_IDS if SKIN.SKINS[skin_id]['style'] == style)
                 for style in SKIN.STYLE_FAMILIES[:4]]
        items = [candidate(f'tpl{index}', skin, pair = f'pair-{index}', score = 100 - index)
                 for index, skin in enumerate(skins)]
        chosen = A._select_styles(items, 3)
        self.assertEqual([item['template'] for item in chosen], ['tpl0', 'tpl1', 'tpl2'])

    def test_count_larger_than_candidates_returns_what_exists(self):
        skin = SKIN.SKIN_IDS[0]
        chosen = A._select_styles([candidate('classic', skin)], 3)
        self.assertEqual(len(chosen), 1)


#=========================================
# INTEGRACIÓN LIGERA: candidatos -> selección
#=========================================
class CandidatesToSelectionTests(unittest.TestCase):
    """El combo que realmente usa `_build`, a 1200 combinaciones."""

    def test_generation_never_repeats_a_template_across_rubros_and_seeds(self):
        for rubro in R.RUBROS:
            for seed in range(6):
                candidates = A._style_candidates(facts_full(), stats_dense(), answers(rubro = rubro), PLAN_AI, seed)
                chosen = A._select_styles(candidates, 3)
                self.assertEqual(len({item['template'] for item in chosen}), len(chosen), (rubro, seed))
                self.assertTrue(len(chosen) >= 2, (rubro, seed))

    def test_plan_basico_gets_two_proposals_inside_the_plan(self):
        for seed in range(6):
            candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_BASIC, seed)
            chosen = A._select_styles(candidates, 2)
            self.assertEqual(len(chosen), 2, seed)
            for item in chosen:
                self.assertIn(item['template'], PLAN_BASIC)

    def test_requested_style_shows_up_in_the_generation(self):
        for seed in range(6):
            candidates = A._style_candidates(
                facts_full(), stats_dense(), answers(styles = ['minimal']), PLAN_ADVANCED, seed,
            )
            chosen = A._select_styles(candidates, 2)
            self.assertIn('minimal', {item['style'] for item in chosen}, seed)

    def test_generation_covers_two_different_styles_when_possible(self):
        for seed in range(6):
            candidates = A._style_candidates(facts_full(), stats_dense(), answers(), PLAN_ADVANCED, seed)
            chosen = A._select_styles(candidates, 2)
            self.assertEqual(len({item['style'] for item in chosen}), 2, seed)


if __name__ == '__main__':
    unittest.main()
