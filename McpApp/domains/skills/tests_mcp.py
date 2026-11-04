import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from McpApp.domains.skills.models import DesignModelMcp
from McpApp.mcp_server import handle
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.models import Store

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
            'list_design_patterns', 'get_design_pattern',
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


MCP_URL =   '/api/mcp/'


def _user_with_store(username, trial = False):
    user        =   User.objects.create_user(username = username, password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(user = user, business_name = f'Negocio {username}')
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {username}', is_trial = trial)
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    store       =   Store.objects.create(user = profile, slug = f'tienda-{username}')
    return user, store


class McpUserToolsTests(TestCase):
    """
    Reglas del MCP de usuario: ciego a la DB general — las tools my_*
    solo leen datos del usuario en sesión (el user lo inyecta el
    transporte, jamás los arguments) y exigen plan vigente no-trial.
    """

    def _rpc_http(self, client, method, params = None):
        return client.post(
            MCP_URL,
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}},
            format = 'json',
        )

    def setUp(self):
        self.user_a, self.store_a   =   _user_with_store('ana')
        self.user_b, self.store_b   =   _user_with_store('beto')
        self.user_trial, _          =   _user_with_store('tri', trial = True)
        Product.objects.create(store = self.store_a, name = 'Zapatilla roja', price = 100)
        Product.objects.create(store = self.store_a, name = 'Camisa azul', price = 50, is_active = False)
        Product.objects.create(store = self.store_b, name = 'Zapatilla secreta de Beto', price = 999)
        self.client_a   =   APIClient()
        self.client_a.force_authenticate(user = self.user_a)
        self.client_trial   =   APIClient()
        self.client_trial.force_authenticate(user = self.user_trial)

    #=========================================
    # GATE: sesión + plan pago vigente
    #=========================================
    def test_stdio_never_exposes_user_data(self):
        #El transporte stdio no inyecta user: las tools personales ni se
        #listan ni corren — el agente local queda ciego a la DB de clientes.
        tools   =   handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['result']['tools']
        self.assertFalse(any(t['name'].startswith('my_') for t in tools))
        response    =   handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                'params': {'name': 'my_store_summary', 'arguments': {}}})
        self.assertEqual(response['error']['code'], -32602)

    def test_anonymous_cannot_call_user_tools(self):
        response    =   self._rpc_http(APIClient(), 'tools/call', {'name': 'my_plan_summary'})
        self.assertIn(response.status_code, (401, 403))

    def test_trial_plan_is_denied(self):
        response    =   self._rpc_http(self.client_trial, 'tools/call', {'name': 'my_store_summary'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], -32602)

    def test_trial_does_not_see_user_tool_schemas(self):
        response    =   self._rpc_http(self.client_trial, 'tools/list')
        names       =   {t['name'] for t in response.data['result']['tools']}
        self.assertFalse(any(n.startswith('my_') for n in names))

    #=========================================
    # AISLAMIENTO: solo datos del usuario en sesión
    #=========================================
    def test_my_store_summary_returns_own_store(self):
        response    =   self._rpc_http(self.client_a, 'tools/call', {'name': 'my_store_summary'})
        data        =   json.loads(response.data['result']['content'][0]['text'])
        self.assertEqual(data['store']['slug'], 'tienda-ana')
        self.assertEqual(data['store']['products_total'], 2)
        self.assertEqual(data['store']['products_active'], 1)

    def test_search_my_products_is_scoped_to_session(self):
        response    =   self._rpc_http(self.client_a, 'tools/call', {
            'name'      :   'search_my_products',
            'arguments' :   {'query': 'zapatilla'},
        })
        products    =   json.loads(response.data['result']['content'][0]['text'])['products']
        names       =   {p['name'] for p in products}
        self.assertEqual(names, {'Zapatilla roja'})
        self.assertNotIn('Zapatilla secreta de Beto', names)

    def test_foreign_ids_in_arguments_are_ignored(self):
        #Aunque el cliente mande ids/slugs ajenos en arguments, la tool
        #sigue atada al usuario en sesión: no hay pivote por parámetro.
        response    =   self._rpc_http(self.client_a, 'tools/call', {
            'name'      :   'my_store_summary',
            'arguments' :   {'user_id': self.user_b.id, 'store': 'tienda-beto', 'slug': 'tienda-beto'},
        })
        data        =   json.loads(response.data['result']['content'][0]['text'])
        self.assertEqual(data['store']['slug'], 'tienda-ana')

    def test_my_plan_summary_returns_own_plan(self):
        response    =   self._rpc_http(self.client_a, 'tools/call', {'name': 'my_plan_summary'})
        data        =   json.loads(response.data['result']['content'][0]['text'])
        self.assertEqual(data['plan']['name'], 'Plan ana')
