from django.core.management import call_command
from django.test import TestCase, override_settings

from McpApp.domains.skills.models import DesignModelMcp
from McpApp.domains.skills.services import (
    ask_llm,
    call_tool,
    get_design_style,
    llm_enabled,
    search_design_styles,
)

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


class LlmProviderTests(TestCase):
    """Selección y fallback de proveedores LLM gratuitos."""

    def _response(self, status, payload):
        from unittest.mock import Mock
        response            =   Mock()
        response.status_code =  status
        response.json.return_value = payload
        response.text       =   ''
        return response

    @override_settings(AI_PROVIDER = 'gemini', GEMINI_API_KEY = 'g-key', GROQ_API_KEY = '', OPENROUTER_API_KEY = '', ANTHROPIC_API_KEY = '')
    def test_gemini_parses_candidates(self):
        from unittest.mock import patch
        payload = {'candidates': [{'content': {'parts': [{'text': 'Hola, ¿qué vendés?'}]}}]}
        with patch('McpApp.domains.skills.services.llm.requests.post', return_value = self._response(200, payload)) as post:
            text = ask_llm('system', [{'role': 'user', 'content': 'hola'}])
        self.assertEqual(text, 'Hola, ¿qué vendés?')
        self.assertIn('generativelanguage.googleapis.com', post.call_args[0][0])

    @override_settings(AI_PROVIDER = 'gemini', GEMINI_API_KEY = 'g-key', GROQ_API_KEY = 'q-key', OPENROUTER_API_KEY = '', ANTHROPIC_API_KEY = '')
    def test_falls_back_to_groq_when_gemini_fails(self):
        from unittest.mock import patch
        groq_payload = {'choices': [{'message': {'content': 'Respuesta de Groq'}}]}
        with patch('McpApp.domains.skills.services.llm.requests.post', side_effect = [
            self._response(429, {'error': 'rate limit'}),
            self._response(200, groq_payload),
        ]) as post:
            text = ask_llm('system', [{'role': 'user', 'content': 'hola'}])
        self.assertEqual(text, 'Respuesta de Groq')
        self.assertEqual(post.call_count, 2)

    @override_settings(AI_PROVIDER = '', GEMINI_API_KEY = '', GROQ_API_KEY = '', OPENROUTER_API_KEY = '', ANTHROPIC_API_KEY = '')
    def test_disabled_without_keys(self):
        self.assertFalse(llm_enabled())
        self.assertIsNone(ask_llm('system', [{'role': 'user', 'content': 'hola'}]))
