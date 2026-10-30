from django.core.management import call_command
from django.test import TestCase

from McpApp.domains.skills.models import DesignModelMcp
from McpApp.domains.skills.services import call_tool, get_design_style, search_design_styles

"""
Tests del dominio skills y del contrato MCP.
"""


class DesignStyleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_design_styles', verbosity = 0)

    def test_seed_creates_twenty_styles(self):
        self.assertEqual(DesignModelMcp.objects.count(), 20)

    def test_slug_is_unique(self):
        with self.assertRaises(Exception):
            DesignModelMcp.objects.create(
                slug = 'cyberpunk-dark', nombre = 'Duplicado', categoria = 'tecnologia',
            )

    def test_style_has_components_and_tokens(self):
        style = get_design_style('cyberpunk-dark')
        self.assertIsNotNone(style)
        self.assertIn('hero', style.html_componentes)
        self.assertEqual(style.tokens_diseno['primary'], '#00ffcc')
        self.assertIn('neon', style.tags)

    def test_search_ranks_exact_style_first(self):
        rows = search_design_styles('neon oscuro', limit = 3)
        self.assertEqual(rows[0].slug, 'cyberpunk-dark')

    def test_mcp_tools_contract(self):
        data = call_tool('list_design_categories')
        self.assertTrue(any(c['categoria'] == 'moda' for c in data['categories']))

    def test_mcp_apply_style_returns_instructions(self):
        data = call_tool('apply_design_style', {'slug': 'minimal-nordic'})
        self.assertIn('instrucciones', data)
        self.assertEqual(data['tokens_diseno']['primary'], '#2f6f6b')

    def test_mcp_unknown_slug_raises(self):
        with self.assertRaises(ValueError):
            call_tool('get_design_style', {'slug': 'no-existe'})
