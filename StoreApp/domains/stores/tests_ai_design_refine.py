#Tests del flujo de 4 pantallas (docs/ORQUESTACION_MEJORA_DISENO_IA.md,
#fase 2-3): prefill de la entrevista, tesis por propuesta, ajuste sin
#rehacer la tanda (`refine`) y lista de chequeo de la web publicada.

from StoreApp.domains.stores.services.ai_design_typography import TYPE_PAIRS
from StoreApp.domains.stores.tests_ai_design import AI_URL, AiDesignBase

PREFILL_URL =   '/api/stores/ai-design/prefill/'
REFINE_URL  =   '/api/stores/ai-design/refine/'
APPLY_URL   =   '/api/stores/ai-design/apply/'


class AiDesignRefineBase(AiDesignBase):

    def _generate(self, store, payload = None):
        response    =   self._client(store).post(AI_URL, payload or {'goals': ['vender_online']}, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:400])
        return response.json()

    def _refine(self, store, data, proposal_id = 'p1', constraints = None):
        return self._client(store).post(
            REFINE_URL,
            {'seed': data['seed'], 'proposal_id': proposal_id, 'constraints': constraints or {}},
            format = 'json',
        )


class PrefillTests(AiDesignRefineBase):

    def test_prefill_returns_what_the_engine_already_knows(self):
        store, draft   =   self._store(products = 3)
        draft.description   =   'Pan de masa madre'
        draft.save()
        response    =   self._client(store).get(PREFILL_URL)
        self.assertEqual(response.status_code, 200, response.content[:400])
        data        =   response.json()
        self.assertEqual(data['name'], 'Panadería La Espiga')
        self.assertEqual(data['slug'], store.slug)
        self.assertIn(data['rubro'], ('comercio', 'gastronomia', 'otro'))
        self.assertTrue(data['goals'])
        self.assertEqual(data['counts']['products'], 3)
        self.assertIn('photos', data['counts'])
        self.assertIn('categories', data['counts'])

    def test_prefill_requires_the_benefit(self):
        store, _   =   self._store(ai = False)
        self.assertEqual(self._client(store).get(PREFILL_URL).status_code, 403)


class ThesisTests(AiDesignRefineBase):

    def test_every_proposal_has_a_thesis(self):
        store, _    =   self._store(products = 8)
        data        =   self._generate(store)
        for proposal in data['proposals']:
            thesis  =   proposal['thesis']
            self.assertTrue(thesis['label'])
            self.assertTrue(thesis['line'])
            self.assertIn(thesis['goal'], ('vender_online', 'mostrar_servicios', 'conseguir_consultas',
                                           'dar_confianza', 'mostrar_trabajos'))

    def test_thesis_follows_the_opening_block(self):
        #La tesis sale de lo que la landing muestra primero, no del índice.
        store, _    =   self._store(products = 8)
        data        =   self._generate(store)
        for proposal in data['proposals']:
            landing =   [block['id'] for block in proposal['layout_config']['landing']['blocks']
                         if block.get('enabled') and block['id'] != 'hero'][:4]
            expected    =   {
                'featured': 'vender', 'offers': 'vender', 'categories': 'vender', 'highlights': 'vender',
                'services': 'servicios', 'steps': 'servicios',
                'gallery': 'trabajos', 'aimosaic': 'trabajos',
            }
            first   =   next((expected[block] for block in landing if block in expected), None)
            if first:
                self.assertEqual(proposal['thesis']['id'], first)


class ChecksTests(AiDesignRefineBase):

    def test_checks_are_honest(self):
        store, draft   =   self._store(products = 0)
        data           =   self._generate(store)
        checks         =   {item['key']: item for item in data['checks']}
        self.assertEqual(set(checks), {'contact', 'cover', 'description', 'photos', 'hours', 'products'})
        #Tienda vacía: todo pendiente y con la sección que lo resuelve.
        self.assertFalse(checks['products']['ok'])
        self.assertEqual(checks['products']['action'], 'catalog')
        self.assertFalse(checks['contact']['ok'])
        self.assertTrue(checks['contact']['hint'])
        draft.whatsapp  =   '1122334455'
        draft.save()
        data            =   self._generate(store)
        checks          =   {item['key']: item for item in data['checks']}
        self.assertTrue(checks['contact']['ok'])


class RefineTests(AiDesignRefineBase):

    def test_refine_keeps_the_tanda_and_changes_only_the_typography(self):
        store, _    =   self._store(products = 6)
        data        =   self._generate(store)
        original    =   data['proposals'][0]
        response    =   self._refine(store, data, 'p1', {'typography': 'serif-classic'})
        self.assertEqual(response.status_code, 200, response.content[:400])
        refined     =   response.json()['proposal']
        self.assertEqual(refined['id'], original['id'])
        self.assertEqual(refined['template'], original['template'])
        self.assertEqual(refined['skin']['id'], original['skin']['id'])
        #Misma composición, otra tipografía.
        self.assertEqual(refined['look']['structure'], original['look']['structure'])
        self.assertEqual(refined['look']['fonts']['pair'], 'serif-classic')
        self.assertNotEqual(refined['look']['fonts']['pair'], original['look']['fonts']['pair'])

    def test_refine_color_and_air(self):
        store, _    =   self._store(products = 4)
        data        =   self._generate(store)
        response    =   self._refine(store, data, 'p1', {'color': '#c2410c', 'air': 'spacious'})
        self.assertEqual(response.status_code, 200, response.content[:400])
        refined     =   response.json()['proposal']
        self.assertEqual(refined['look']['density'], 'spacious')
        self.assertEqual(refined['theme_choice']['source'], 'user')
        #El acento del dueño se ajusta para AA sobre el fondo de la piel
        #elegida (que depende de la semilla): el hex exacto no es invariante
        #entre corridas, sí lo es que sea una elección 'user' con acento.
        self.assertTrue(refined['theme_choice']['accent'])

    def test_refine_without_constraints_restores_the_original(self):
        store, _    =   self._store(products = 4)
        data        =   self._generate(store)
        original    =   data['proposals'][0]
        self._refine(store, data, 'p1', {'typography': 'serif-classic', 'color': '#c2410c'})
        restored    =   self._refine(store, data, 'p1', {})
        self.assertEqual(restored.status_code, 200, restored.content[:400])
        proposal    =   restored.json()['proposal']
        self.assertEqual(proposal['look']['fonts']['pair'], original['look']['fonts']['pair'])
        self.assertEqual(proposal['look']['accent'], original['look']['accent'])

    def test_refine_is_deterministic(self):
        store, _    =   self._store(products = 4)
        data        =   self._generate(store)
        constraints =   {'typography': 'serif-classic', 'air': 'comfortable', 'color': '#0f766e'}
        first       =   self._refine(store, data, 'p1', constraints)
        second      =   self._refine(store, data, 'p1', constraints)
        self.assertEqual(first.json(), second.json())

    def test_refine_without_a_cached_run_is_400(self):
        store, _    =   self._store(products = 4)
        response    =   self._client(store).post(
            REFINE_URL, {'seed': 123, 'proposal_id': 'p1', 'constraints': {}}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_apply_publishes_the_refined_proposal(self):
        store, _    =   self._store(products = 4)
        data        =   self._generate(store)
        refined     =   self._refine(store, data, 'p1', {'color': '#c2410c', 'air': 'spacious'})
        self.assertEqual(refined.status_code, 200, refined.content[:400])
        response    =   self._client(store).post(
            APPLY_URL, {'seed': data['seed'], 'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:400])
        customization   =   response.json()['customization']
        #Lo publicado es EXACTO lo que mostró el refine (el acento del dueño
        #puede ajustarse para AA según la piel de la semilla).
        self.assertEqual(
            customization['site_theme']['palette']['accent'].lower(),
            refined.json()['proposal']['theme_choice']['accent'].lower(),
        )

    def test_unknown_typography_is_ignored(self):
        store, _    =   self._store(products = 4)
        data        =   self._generate(store)
        response    =   self._refine(store, data, 'p1', {'typography': 'no-existe'})
        self.assertEqual(response.status_code, 200, response.content[:400])
        self.assertEqual(response.json()['applied'], [])
        self.assertIn(response.json()['proposal']['look']['fonts']['pair'], TYPE_PAIRS)
