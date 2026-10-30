"""
Suite del wizard "Diseño asistido" -> proxy MCP de estilos.

Endpoint:
  POST /api/stores/ai-design/mcp/  -> {message, history, seed?} -> propuestas

Contrato:
  1) el mensaje acumulado ("Rubro: … / Objetivo: … / Tono: …") se traduce a
     las respuestas del motor (rubro/objetivos/tono/audiencia/imprescindible);
  2) la respuesta usa el MISMO contrato que `ai-design/` (proposals + seed +
     missing + checks), así el ajuste fino y `apply` siguen funcionando;
  3) gates de plan (has_customization + has_ai_design) y mensaje vacío -> 400;
  4) determinismo: mismo mensaje = mismo seed; seed+1 = otra tanda.
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from StoreApp.domains.stores.services import ai_design_recipes as R
from StoreApp.domains.stores.services.ai_design_mcp import parse_message
from StoreApp.domains.stores.tests_ai_design_contract import (
    AI_DESIGN,
    CUSTOMIZATION,
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


class AiDesignMcpParseTests(TestCase):
    def test_blocks_map_to_engine_answers(self):
        payload =   parse_message(MESSAGE)
        self.assertEqual(payload['rubro'], 'gastronomia')
        self.assertIn('vender_online', payload['goals'])
        self.assertIn('conseguir_consultas', payload['goals'])
        self.assertEqual(payload['tone'], 'calido')
        self.assertEqual(payload['audience'], 'Personas')
        self.assertIn('whatsapp', payload['must_have'])
        self.assertIn('hours', payload['must_have'])
        self.assertIn('panader', payload['content_hint'])
        for goal in payload['goals']:
            self.assertIn(goal, R.GOALS)
        for item in payload['must_have']:
            self.assertIn(item, R.MUST_HAVE_BLOCKS)

    def test_unknown_text_is_tolerated(self):
        payload =   parse_message('Hola, quiero una web linda')
        self.assertEqual(payload.get('rubro', ''), '')
        self.assertIn('web linda', payload.get('content_hint', ''))


class AiDesignMcpEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url    =   f'{reverse("Stores-list")}ai-design/mcp/'

    def _client(self, *codes):
        user, profile, store    =   _make_account(*codes, limits = PREMIUM_LIMITS)
        client                  =   APIClient()
        client.force_authenticate(user = user)
        return client, store

    def _premium(self):
        return self._client(*(CUSTOMIZATION + AI_DESIGN))

    def test_returns_proposals_with_engine_contract(self):
        client, _ =   self._premium()
        response  =   client.post(self.url, {'message': MESSAGE, 'history': []}, format = 'json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['proposals'])
        self.assertIsInstance(body['seed'], int)
        self.assertIn('missing', body)
        self.assertIn('checks', body)
        self.assertEqual(body['parsed']['rubro'], 'gastronomia')
        self.assertEqual(body['echo'], MESSAGE)

    def test_same_message_is_deterministic_and_seed_changes_tanda(self):
        client, _ =   self._premium()
        first     =   client.post(self.url, {'message': MESSAGE}, format = 'json').json()
        again     =   client.post(self.url, {'message': MESSAGE}, format = 'json').json()
        other     =   client.post(self.url, {'message': MESSAGE, 'seed': first['seed'] + 1}, format = 'json').json()
        self.assertEqual(first['seed'], again['seed'])
        self.assertEqual(
            [p['id'] for p in first['proposals']],
            [p['id'] for p in again['proposals']],
        )
        self.assertNotEqual(first['seed'], other['seed'])

    def test_empty_message_is_400(self):
        client, _ =   self._premium()
        response  =   client.post(self.url, {'message': '   '}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_requires_customization_benefit(self):
        client, _ =   self._client(*AI_DESIGN)
        response  =   client.post(self.url, {'message': MESSAGE}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_requires_ai_design_benefit(self):
        client, _ =   self._client(*CUSTOMIZATION)
        response  =   client.post(self.url, {'message': MESSAGE}, format = 'json')
        self.assertEqual(response.status_code, 403)
