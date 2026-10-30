"""Tests de aceptación del Agente C — Tipografía v6 ("Diseñar con IA").

Cubre §6.2 del brief:
- test_type_pairs_are_distinct_and_valid: firmas (display, body) únicas y display ≠ body.
- test_typography_roles_within_scale: rangos de escala, pesos reales y tracking
  para las 52 pieles × 4 tonos.
- test_typography_roles_travel_in_proposal: typography.roles viaja en la propuesta
  y styleColors.fonts coincide con el modo.

Cubre además §6.1-5/§6.1-6 (aire tipográfico y tracking publicado):
- la piel declara los aires que admite y su par canónico siempre entra;
- la matriz "firma" de los rubros nunca viola ese aire;
- `resolve_pair()` rota dentro del aire (editorial jamás cae en cartel/mono);
- el `letterSpacing`/`weightHeading` publicados salen del rol h1, no de un fijo.
"""
import random

from django.test import TestCase

from StoreApp.domains.stores.services.ai_design_recipes import RUBRO_STYLES
from StoreApp.domains.stores.services.ai_design_skins import (
    SKIN_FAMILIES,
    SKIN_IDS,
    SKINS,
    type_pair_of,
)
from StoreApp.domains.stores.services.ai_design_typography import (
    BODY_ROLES,
    FONT_SLUGS,
    PAIR_VOICES,
    QUOTE_DISPLAY_SKINS,
    SKIN_TYPE_VOICES,
    TRACKING_EM,
    TYPE_CASES,
    TYPE_LEADING,
    TYPE_PAIRS,
    TYPE_SIZES,
    TYPE_TRACKING,
    TYPE_VOICES,
    compatible_pairs,
    pair_is_consistent,
    resolve_pair,
    roles_for,
    tracking_css,
    type_pair_signature,
    voice_of_pair,
)

#Los 4 tonos del contrato (claves de _TONE_ROLES).
TONES = ('calido', 'serio', 'moderno', 'audaz')
#Familias editoriales: la voz de revista nunca grita ni programa.
EDITORIAL_FAMILIES = (
    'editorial', 'magazine', 'paper', 'nostalgia', 'warm', 'craft', 'organic',
    'luxury', 'prestige', 'aurora', 'cinematic',
)


class TypePairsAreDistinctAndValidTests(TestCase):
    """§C.1 / §6.2-1: 24 pares, firmas (display, body) únicas, display ≠ body."""

    def test_pairs_have_unique_signatures_and_display_neq_body(self):
        signatures = set()
        for name, pair in TYPE_PAIRS.items():
            display, body = pair['display'], pair['body']
            self.assertIsInstance(display, str)
            self.assertIsInstance(body, str)
            self.assertIn(display, FONT_SLUGS, f'{name}: display fuera de catálogo')
            self.assertIn(body, FONT_SLUGS, f'{name}: body fuera de catálogo')
            self.assertNotEqual(display, body, f'{name}: display repite el body')
            sig = (display, body)
            self.assertNotIn(sig, signatures, f'{name}: firma duplicada {sig}')
            signatures.add(sig)
        self.assertEqual(len(signatures), len(TYPE_PAIRS))

    def test_type_pair_signature_is_stable(self):
        for name in TYPE_PAIRS:
            self.assertEqual(type_pair_signature(name),
                             (TYPE_PAIRS[name]['display'], TYPE_PAIRS[name]['body']))
        self.assertEqual(type_pair_signature('no-existe'),
                         type_pair_signature('grotesk-clean'))


class TypographyRolesWithinScaleTests(TestCase):
    SIZE_RANK = {size: i for i, size in enumerate(
        ('xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', 'display'))}

    def test_roles_cover_thirteen_and_values_in_enums(self):
        roles = roles_for('grotesk-clean', 'serio')
        self.assertEqual(set(roles), set(BODY_ROLES) | {'display', 'h1', 'h2', 'h3', 'quote'})
        for role, values in roles.items():
            self.assertIn(values['font'], FONT_SLUGS, f'{role}: font fuera de catálogo')
            self.assertIn(values['size'], TYPE_SIZES, f'{role}: size fuera de rango')
            self.assertIn(values['weight'], (300, 400, 500, 600, 700, 800, 900),
                          f'{role}: peso fuera de rango')
            self.assertIn(values['tracking'], TYPE_TRACKING, f'{role}: tracking fuera de rango')
            self.assertIn(values['leading'], TYPE_LEADING, f'{role}: leading fuera de rango')
            self.assertIn(values['case'], TYPE_CASES, f'{role}: case fuera de rango')

    def test_scale_respects_ratio_and_hierarchy(self):
        roles = roles_for('serif-editorial', 'calido')
        rank = lambda r: self.SIZE_RANK[roles[r]['size']]
        self.assertGreater(rank('display'), rank('h1'))
        self.assertGreater(rank('h1'), rank('h2'))
        self.assertGreater(rank('h2'), rank('h3'))
        self.assertGreater(rank('h3'), rank('body'))
        self.assertEqual(roles['body']['size'], 'md')
        self.assertLessEqual(roles['body']['weight'], 500)
        self.assertIn(roles['body']['leading'], ('normal', 'relaxed'))
        self.assertEqual(roles['price']['weight'], 700)
        self.assertEqual(roles['price']['tracking'], 'normal')
        self.assertEqual(roles['eyebrow']['case'], 'upper')
        self.assertEqual(roles['eyebrow']['tracking'], 'wider')

    def test_tracking_no_negative_in_body(self):
        roles = roles_for('condensed-bold', 'audaz')
        for role in BODY_ROLES:
            self.assertIn(roles[role]['tracking'], ('normal', 'wide', 'wider'), role)
        self.assertIn(roles['display']['tracking'], ('tighter', 'tight', 'normal'))
        self.assertIn(roles['h1']['tracking'], ('tighter', 'tight', 'normal'))

    def test_weights_are_real_for_every_family(self):
        from StoreApp.domains.stores.services.ai_design_typography import FONT_WEIGHTS
        for name, pair in TYPE_PAIRS.items():
            for font in (pair['display'], pair['body']):
                low, high = FONT_WEIGHTS[font]
                roles = roles_for(name, 'serio')
                used = [r for r in roles if roles[r]['font'] == font]
                for role in used:
                    self.assertGreaterEqual(roles[role]['weight'], low,
                                            f'{name}/{role}: {font} {roles[role]["weight"]} < {low}')
                    self.assertLessEqual(roles[role]['weight'], high,
                                            f'{name}/{role}: {font} {roles[role]["weight"]} > {high}')

    def test_52_skins_x_4_tones_roles_within_scale(self):
        for skin_id in SKIN_IDS:
            skin = SKINS[skin_id]
            pair = skin['typography']['pair'] if 'pair' in skin['typography'] else None
            if pair not in TYPE_PAIRS:
                pair = 'grotesk-clean'
            for tone in TONES:
                roles = roles_for(pair, tone, skin['family'])
                self.assertEqual(set(roles), set(BODY_ROLES) | {'display', 'h1', 'h2', 'h3', 'quote'},
                                 f'{skin_id}/{tone}: roles incompletos')
                self.assertEqual(len({roles[r]['font'] for r in BODY_ROLES}), 1,
                                 f'{skin_id}/{tone}: dos familias de cuerpo')
                self.assertLessEqual(roles['body']['weight'], 500,
                                     f'{skin_id}/{tone}: body demasiado pesado')
                self.assertEqual(roles['price']['weight'], 700)
                self.assertEqual(roles['eyebrow']['case'], 'upper')
                self.assertEqual(roles['eyebrow']['tracking'], 'wider')
                for role in BODY_ROLES:
                    self.assertIn(roles[role]['tracking'], ('normal', 'wide', 'wider'),
                                  f'{skin_id}/{tone}/{role}: tracking negativo en cuerpo')
                for role in ('display', 'h1', 'h2'):
                    self.assertEqual(roles[role]['font'], TYPE_PAIRS[pair]['display'],
                                     f'{skin_id}/{tone}/{role}: no usa familia de display')
                for role, values in roles.items():
                    self.assertIn(values['size'], TYPE_SIZES)
                    self.assertIn(values['leading'], TYPE_LEADING)
                    self.assertIn(values['case'], TYPE_CASES)

    def test_skin_pair_mandates_air(self):
        for skin_id in SKIN_IDS:
            skin = SKINS[skin_id]
            family = skin['family']
            pair = skin['typography']['pair']
            self.assertIn(pair, TYPE_PAIRS, f'{skin_id}: par fuera del catálogo')
            roles = roles_for(pair, 'serio', family)
            if family == 'editorial':
                self.assertEqual(pair, 'serif-editorial')
                self.assertEqual(roles['display']['font'], 'fraunces')
                self.assertEqual(roles['body']['font'], 'inter')
            if family in ('minimal', 'swiss', 'corporate', 'tech', 'glass', 'neon',
                          'gradient', 'kinetic', 'showcase'):
                self.assertNotIn(TYPE_PAIRS[pair]['body'],
                                 ('playfair-display', 'cinzel', 'cormorant-garamond',
                                  'libre-baskerville', 'dm-serif-display', 'lora'))


class TypographyRolesTravelInProposalTests(TestCase):
    """§6.2-3: typography.roles viaja en la propuesta y styleColors.fonts coincide con el modo."""

    def test_roles_travel_in_site_theme_typography(self):
        roles = roles_for('serif-editorial', 'moderno', 'editorial')
        theme = {'typography': {'heading': 'dm-serif-display', 'body': 'dm-sans',
                                'scale': 'balanced', 'weightHeading': 700,
                                'letterSpacing': '-0.02em', 'roles': roles}}
        self.assertIn('roles', theme['typography'])
        self.assertEqual(set(theme['typography']['roles']),
                         set(BODY_ROLES) | {'display', 'h1', 'h2', 'h3', 'quote'})
        self.assertIn(theme['typography']['heading'], FONT_SLUGS)
        self.assertIn(theme['typography']['body'], FONT_SLUGS)

    def test_style_colors_fonts_match_mode(self):
        from StoreApp.domains.stores.services.ai_design import _style_colors
        palette = {'accent': '#4f46e5', 'bg': '#ffffff', 'surface': '#f8fafc',
                   'text': '#0f172a', 'muted': '#5b6678', 'secondary': '#1e1b4b',
                   'primary': '#4f46e5', 'ink': '#0f172a', 'ink_2': '#334155'}
        for mode in ('light', 'dark'):
            sc = _style_colors(palette, palette['accent'])
            self.assertIn(mode, sc, f'falta modo {mode} en styleColors')
            self.assertIn('fonts', sc[mode], f'falta fonts en styleColors.{mode}')
            fonts = sc[mode]['fonts']
            for key in ('heading', 'body', 'muted', 'link'):
                self.assertIn(key, fonts, f'falta fonts.{key} en modo {mode}')

    def test_quote_uses_display_only_for_display_skins(self):
        #§C.7: en pieles de revista (QUOTE_DISPLAY_SKINS) la cita usa la familia
        #de display; en el resto usa la de cuerpo (nunca una tercera familia).
        for skin_id, skin in SKINS.items():
            family     =   skin['family']
            pair_name  =   skin['typography']['pair'] if 'pair' in skin['typography'] else None
            if pair_name not in TYPE_PAIRS:
                pair_name  =   'grotesk-clean'
            pair       =   TYPE_PAIRS[pair_name]
            roles      =   roles_for(pair_name, 'serio', family)
            expected   =   pair['display'] if family in QUOTE_DISPLAY_SKINS else pair['body']
            self.assertEqual(roles['quote']['font'], expected,
                             f'{skin_id}/{family}: quote usa {roles["quote"]["font"]}, esperaba {expected}')


class TypeAirCoherenceTests(TestCase):
    """§6.1-6: la piel manda el aire; el par solo rota dentro de ese aire."""

    def test_every_pair_and_family_declares_a_known_air(self):
        self.assertEqual(set(PAIR_VOICES), set(TYPE_PAIRS),
                         'la tabla de aires no cubre exactamente el catálogo de pares')
        for name, voice in PAIR_VOICES.items():
            self.assertIn(voice, TYPE_VOICES, f'{name}: aire desconocido {voice}')
        self.assertEqual(set(SKIN_TYPE_VOICES), set(SKIN_FAMILIES),
                         'la tabla de aires no cubre exactamente las familias de piel')
        for family, voices in SKIN_TYPE_VOICES.items():
            self.assertTrue(voices, f'{family}: no admite ningún aire')
            self.assertTrue(voices <= set(TYPE_VOICES), f'{family}: aire fuera del contrato')

    def test_every_skin_starts_with_a_pair_of_its_own_air(self):
        #SKIN_TYPE_PAIR (lo que usa el motor, `type_pair_of`) no puede sacar a
        #la piel de su propio aire: la web arrancaría con una tipografía que
        #su familia no admite.
        for skin_id in SKIN_IDS:
            family = SKINS[skin_id]['family']
            pair = type_pair_of(skin_id)
            self.assertIn(pair, TYPE_PAIRS, f'{skin_id}: par fuera del catálogo')
            self.assertTrue(pair_is_consistent(pair, family),
                            f'{skin_id}/{family}: {pair} ({voice_of_pair(pair)}) no es de su aire')

    def test_rubro_signature_matrix_respects_the_skin_air(self):
        #La matriz de cada rubro es contenido firmado: si un combo violara el
        #aire, el motor lo estaría rotando en silencio (la tarjeta diría una
        #cosa y la web publicaría otra).
        for rubro, rows in RUBRO_STYLES.items():
            for row in rows:
                family = SKINS[row['skin']]['family']
                self.assertTrue(
                    pair_is_consistent(row['pair'], family),
                    f'{rubro}: {row["skin"]} ({family}) con {row["pair"]} ({voice_of_pair(row["pair"])})',
                )

    def test_editorial_families_never_take_a_poster_or_mono_voice(self):
        for family in EDITORIAL_FAMILIES:
            for name in TYPE_PAIRS:
                if voice_of_pair(name) in ('poster', 'mono'):
                    self.assertFalse(pair_is_consistent(name, family),
                                     f'{family}: admite {name} ({voice_of_pair(name)})')

    def test_compatible_pairs_is_never_empty_and_stays_in_the_catalog(self):
        for family in SKIN_FAMILIES:
            pool = compatible_pairs(family)
            self.assertTrue(pool, f'{family}: sin pares compatibles')
            for name in pool:
                self.assertIn(name, TYPE_PAIRS, family)
                self.assertTrue(pair_is_consistent(name, family), f'{family}/{name}')


class ResolvePairTests(TestCase):
    """§6.1-6: el par se corrige al aire de la piel, de forma determinista."""

    def test_resolve_pair_keeps_the_compatible_and_fixes_the_rest(self):
        for skin_id in SKIN_IDS:
            family = SKINS[skin_id]['family']
            for name in TYPE_PAIRS:
                effective = resolve_pair(name, family)
                self.assertIn(effective, TYPE_PAIRS, f'{skin_id}/{family}/{name}')
                self.assertTrue(pair_is_consistent(effective, family),
                                f'{skin_id}/{family}: {name} -> {effective} fuera de aire')
                if pair_is_consistent(name, family):
                    self.assertEqual(effective, name,
                                     f'{skin_id}/{family}: se pisó un par que ya era válido')

    def test_resolve_pair_is_deterministic(self):
        for family in SKIN_FAMILIES:
            for offset in range(4):
                self.assertEqual(resolve_pair('condensed-bold', family, offset),
                                 resolve_pair('condensed-bold', family, offset))

    def test_resolve_pair_rotates_inside_the_air(self):
        #Un par de cartel en piel editorial no cae siempre en el mismo: la
        #semilla reparte diversidad dentro del aire (si no, tres propuestas
        #saldrían con la misma tipografía).
        picks = {resolve_pair('condensed-bold', 'editorial', offset) for offset in range(6)}
        self.assertGreater(len(picks), 1, 'la rotación por aire no diversifica')
        for name in picks:
            self.assertTrue(pair_is_consistent(name, 'editorial'))

    def test_unknown_pair_falls_back_inside_the_air(self):
        for family in SKIN_FAMILIES:
            self.assertTrue(pair_is_consistent(resolve_pair('no-existe', family), family),
                            f'{family}: el fallback se salió del aire')

    def test_without_family_the_pair_is_not_restricted(self):
        #Sin familia (llamadas de bajo nivel) no se restringe: la validación
        #es de coherencia con la piel, no de existencia en el catálogo.
        self.assertFalse(pair_is_consistent('condensed-bold', None))
        self.assertEqual(resolve_pair('condensed-bold', None), 'condensed-bold')

    def test_style_candidates_only_emit_pairs_of_the_skin_air(self):
        #Fin a fin de la selección: es el punto exacto donde antes entraba un
        #par al azar (`pairs[(index * 5 + seed) % len(pairs)]`).
        from StoreApp.domains.stores.services import ai_design as A
        from StoreApp.domains.stores.tests_ai_design_selection import (
            PLAN_BASIC,
            PLAN_PLUS,
            answers,
            facts_empty,
            facts_full,
            stats_dense,
            stats_empty,
        )
        plans = (PLAN_BASIC, PLAN_PLUS)
        for rubro in RUBRO_STYLES:
            for plan in plans:
                for seed in range(2):
                    for fact, stat in ((facts_full(), stats_dense()), (facts_empty(), stats_empty())):
                        for candidate in A._style_candidates(fact, stat, answers(rubro), plan, seed):
                            family = SKINS[candidate['skin']]['family']
                            self.assertTrue(
                                pair_is_consistent(candidate['pair'], family),
                                f'{rubro}/{plan}/seed{seed}: {candidate["skin"]} ({family}) '
                                f'con {candidate["pair"]} ({voice_of_pair(candidate["pair"])})',
                            )


class PublishedTrackingTests(TestCase):
    """§6.1-5: el tracking que se publica sale del rol, no de un valor fijo."""

    def test_tracking_em_covers_the_whole_enum(self):
        for tracking in TYPE_TRACKING:
            self.assertIn(tracking, TRACKING_EM, f'{tracking}: sin valor em para publicar')
            self.assertRegex(TRACKING_EM[tracking], r'^-?\d+(\.\d+)?em$|^0$')
            self.assertEqual(tracking_css(tracking), TRACKING_EM[tracking])
        #Un tracking desconocido no rompe el CSS guardado.
        self.assertEqual(tracking_css('inventado'), '0')

    def test_theme_publishes_h1_tracking_and_weight(self):
        from StoreApp.domains.stores.services import ai_design as A
        answers = {
            'tone': 'serio', 'brand_color': None, 'night_mode': None,
            'goals': ['vender_online'], 'must_have': [],
        }
        for skin_id, skin in SKINS.items():
            pair = skin['typography']['pair']
            theme, _ = A._theme(skin, pair, answers, random.Random(0), 0)
            roles = theme['typography']['roles']
            self.assertEqual(theme['typography']['letterSpacing'],
                             TRACKING_EM[roles['h1']['tracking']],
                             f'{skin_id}: letterSpacing fuera del rol h1')
            self.assertEqual(theme['typography']['weightHeading'], roles['h1']['weight'],
                             f'{skin_id}: weightHeading fuera del rol h1')
            #Lo publicado coincide con la firma del par (tarjeta = web).
            self.assertEqual(theme['typography']['heading'],
                             TYPE_PAIRS[pair]['display'], skin_id)
            self.assertEqual(theme['typography']['body'],
                             TYPE_PAIRS[pair]['body'], skin_id)