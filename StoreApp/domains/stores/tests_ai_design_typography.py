# -*- coding: utf-8 -*-
"""Tests de aceptación del Agente C — Tipografía v6 ("Diseñar con IA").

Cubre §6.2 del brief:
- test_type_pairs_are_distinct_and_valid: firmas (display, body) únicas y display ≠ body.
- test_typography_roles_within_scale: rangos de escala, pesos reales y tracking
  para las 52 pieles × 4 tonos.
- test_typography_roles_travel_in_proposal: typography.roles viaja en la propuesta
  y styleColors.fonts coincide con el modo.
"""
from django.test import TestCase

from StoreApp.domains.stores.services.ai_design_typography import (
    BODY_ROLES, FONT_SLUGS, TYPE_CASES, TYPE_LEADING, TYPE_SIZES, TYPE_TRACKING,
    TYPE_PAIRS, QUOTE_DISPLAY_SKINS, roles_for, type_pair_signature,
)
from StoreApp.domains.stores.services.ai_design_skins import SKINS, SKIN_IDS

#Los 4 tonos del contrato (claves de _TONE_ROLES).
TONES = ('calido', 'serio', 'moderno', 'audaz')


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