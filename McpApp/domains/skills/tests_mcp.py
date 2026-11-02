import json

from django.core.management import call_command
from django.test import TestCase

from McpApp.domains.skills.models import DesignModelMcp
from McpApp.mcp_server import handle

"""

End-to-end del protocolo MCP (stdio): el prototipo `McpApp/mcp_client.py`
habla con `mcp_server.handle` por JSON-RPC — estos tests fijan ese contrato
(initialize, tools/list, tools/call, errores y notificaciones).

"""


class McpProtocolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_design_styles', verbosity = 0)

    def _rpc(self, method, params = None, msg_id = 1):
        return handle({'jsonrpc': '2.0', 'id': msg_id, 'method': method, 'params': params or {}})

    def test_initialize_advertises_tools_capability(self):
        response    =   self._rpc('initialize', {
            'protocolVersion'   :   '2024-11-05',
            'capabilities'      :   {},
            'clientInfo'        :   {'name': 'test', 'version': '0'},
        })
        self.assertEqual(response['result']['serverInfo']['name'], 'davent-skills')
        self.assertIn('tools', response['result']['capabilities'])

    def test_tools_list_matches_the_declared_contract(self):
        tools   =   self._rpc('tools/list')['result']['tools']
        names   =   {tool['name'] for tool in tools}
        self.assertEqual(names, {
            'list_design_styles', 'search_design_styles', 'get_design_style',
            'apply_design_style', 'list_design_categories', 'design_catalog_summary',
            'list_design_patterns', 'get_design_pattern', 'propose_design',
        })
        for tool in tools:
            self.assertEqual(tool['inputSchema']['type'], 'object')

    def test_tools_call_returns_json_content_block(self):
        response    =   self._rpc('tools/call', {
            'name'      :   'search_design_styles',
            'arguments' :   {'query': 'neon oscuro', 'limit': 3},
        })
        content     =   response['result']['content']
        self.assertEqual(content[0]['type'], 'text')
        data        =   json.loads(content[0]['text'])
        self.assertEqual(data['styles'][0]['slug'], 'cyberpunk-dark')

    def test_apply_style_delivers_tokens_and_instructions(self):
        response    =   self._rpc('tools/call', {
            'name'      :   'apply_design_style',
            'arguments' :   {'slug': 'cyberpunk-dark'},
        })
        data        =   json.loads(response['result']['content'][0]['text'])
        self.assertEqual(data['tokens_diseno']['primary'], '#00ffcc')
        self.assertIn('instrucciones', data)

    def test_invalid_params_are_a_jsonrpc_error_not_a_crash(self):
        response    =   self._rpc('tools/call', {
            'name'      :   'get_design_style',
            'arguments' :   {'slug': 'no-existe'},
        })
        self.assertEqual(response['error']['code'], -32602)

    def test_unknown_tool_and_method_are_errors(self):
        self.assertEqual(
            self._rpc('tools/call', {'name': 'borrar_todo'})['error']['code'], -32602,
        )
        self.assertEqual(self._rpc('metodo/inventado')['error']['code'], -32601)

    def test_notifications_get_no_response(self):
        self.assertIsNone(handle({
            'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {},
        }))

    def test_propose_design_returns_pattern_and_style(self):
        #El tool corre el MISMO resolve_design del wizard: patrón + estilo
        #del catálogo Design (seed cargado en migraciones del test DB).
        response    =   self._rpc('tools/call', {
            'name'      :   'propose_design',
            'arguments' :   {'rubro': 'gastronomia', 'tone': 'calido', 'must_have': ['whatsapp']},
        })
        data        =   json.loads(response['result']['content'][0]['text'])
        pattern     =   data['pattern']
        self.assertTrue(pattern['slug'])
        self.assertTrue(pattern['template'])
        if data.get('style') is not None:
            self.assertIsInstance(data['style']['tokens'], dict)

    def test_list_and_get_design_patterns(self):
        listed      =   self._rpc('tools/call', {'name': 'list_design_patterns', 'arguments': {'limit': 5}})
        patterns    =   json.loads(listed['result']['content'][0]['text'])['patterns']
        self.assertTrue(patterns)
        self.assertIn('has_markup', patterns[0])
        detail      =   self._rpc('tools/call', {
            'name': 'get_design_pattern', 'arguments': {'slug': patterns[0]['slug']},
        })
        data        =   json.loads(detail['result']['content'][0]['text'])
        self.assertIn('layout', data)
        self.assertIn('tokens', data)

    def test_get_design_pattern_unknown_slug_is_error(self):
        response    =   self._rpc('tools/call', {
            'name': 'get_design_pattern', 'arguments': {'slug': 'no-existe'},
        })
        self.assertEqual(response['error']['code'], -32602)

    def test_seed_data_is_queryable_over_the_protocol(self):
        #El catálogo seed responde por MCP: el prototipo corre contra la
        #base real, no contra fixtures del cliente.
        response    =   self._rpc('tools/call', {
            'name'      :   'list_design_categories',
        })
        data        =   json.loads(response['result']['content'][0]['text'])
        categorias  =   {c['categoria'] for c in data['categories']}
        self.assertIn('moda', categorias)
        self.assertTrue(DesignModelMcp.objects.exists())
