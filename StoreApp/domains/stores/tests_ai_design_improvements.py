#Tests de la fase 1 de credibilidad (docs/ORQUESTACION_MEJORA_DISENO_IA.md):
#must_have real (0.1), audience/content_hint (0.2), score con información
#(0.3), secciones que no mienten (2.5) y telemetría del funnel (5.1).

from StoreApp.domains.stores.models import AiDesignEvent
from StoreApp.domains.stores.services.ai_design import _layout_signature
from StoreApp.domains.stores.tests_ai_design import AI_URL, AiDesignBase

EVENT_URL   =   '/api/stores/ai-design/event/'


class AiDesignPhaseOneBase(AiDesignBase):

    def _proposals(self, store, payload):
        response    =   self._client(store).post(AI_URL, payload, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:400])
        return response.json()

    def _landing(self, proposal):
        return {block['id']: block for block in proposal['layout_config']['landing']['blocks']}


class MustHaveTests(AiDesignPhaseOneBase):

    def test_whatsapp_turns_on_contact_and_cta(self):
        store, draft   =   self._store(products = 2)
        draft.whatsapp =   '1122334455'
        draft.save()
        data    =   self._proposals(store, {'goals': ['conseguir_consultas'], 'must_have': ['whatsapp']})
        landing =   self._landing(data['proposals'][0])
        self.assertTrue(landing['contact']['enabled'])
        self.assertTrue(landing['cta']['enabled'])
        self.assertTrue(any('Botón de WhatsApp' in note for note in data['proposals'][0]['notes']))
        self.assertFalse(any('whatsapp' in note for note in data['proposals'][0]['notes']))

    def test_prices_maps_to_offers(self):
        store, draft   =   self._store(products = 3)
        from StoreApp.domains.catalog.models import Product
        Product.objects.filter(store = store).update(offer_price = 80)
        draft.show_offers   =   True
        draft.save()
        data    =   self._proposals(store, {'goals': ['vender_online'], 'must_have': ['prices']})
        landing =   self._landing(data['proposals'][0])
        self.assertTrue(landing['offers']['enabled'])

    def test_request_without_data_stays_off_and_explains(self):
        store, _    =   self._store(products = 0)
        data        =   self._proposals(store, {'goals': ['dar_confianza'], 'must_have': ['hours', 'faqs']})
        proposal    =   data['proposals'][0]
        landing     =   self._landing(proposal)
        self.assertFalse(landing['contact']['enabled'])
        self.assertFalse(landing['faq']['enabled'])
        notes       =   ' '.join(proposal['notes'])
        self.assertIn('Pediste', notes)
        self.assertIn('falta el dato', notes)
        #Nunca ids crudos de bloque en las notas.
        self.assertNotIn('faq,', notes)

    def test_hours_alone_keeps_contact_honest(self):
        store, draft    =   self._store(products = 0)
        draft.hours     =   [{'day': 'Lunes', 'open': '09:00', 'close': '18:00'}]
        draft.save()
        data        =   self._proposals(store, {'goals': ['conseguir_consultas'], 'must_have': ['hours']})
        proposal    =   data['proposals'][0]
        self.assertTrue(self._landing(proposal)['contact']['enabled'])
        self.assertTrue(any('Horarios' in note for note in proposal['notes']))

    def test_map_variant_only_with_real_address(self):
        store, draft    =   self._store(products = 0)
        draft.show_location =   True
        draft.whatsapp      =   '1122334455'
        draft.save()
        profile =   store.user
        profile.address =   'Av. Siempreviva 742'
        profile.save()
        data        =   self._proposals(store, {'goals': ['conseguir_consultas'], 'must_have': ['map']})
        self.assertEqual(self._landing(data['proposals'][0])['contact']['variant'], 'map')


class HonestSectionsTests(AiDesignPhaseOneBase):

    def test_long_headline_switches_hero_variant(self):
        store, draft    =   self._store(products = 2)
        draft.headline  =   'Panadería artesanal con masa madre y productos de estación'
        draft.save()
        data    =   self._proposals(store, {'goals': ['vender_online'], 'rubro': 'gastronomia'})
        for proposal in data['proposals']:
            self.assertNotEqual(self._landing(proposal)['hero'].get('variant'), 'centered', proposal['id'])

    def test_stats_block_needs_real_rows(self):
        store, draft    =   self._store(products = 2)
        draft.stats     =   [{}]
        draft.save()
        data    =   self._proposals(store, {'goals': ['dar_confianza']})
        self.assertFalse(self._landing(data['proposals'][0])['stats']['enabled'])

    def test_aipricing_never_offered_with_one_product(self):
        store, _    =   self._store(products = 1)
        data        =   self._proposals(store, {'goals': ['vender_online'], 'accept_extras': True})
        for proposal in data['proposals']:
            self.assertNotIn('aipricing', proposal['offered_blocks'])


class ScoreTests(AiDesignPhaseOneBase):

    def test_score_discriminates_between_stores(self):
        empty, _    =   self._store(products = 1, username = 'vacia')
        rich, draft =   self._store(products = 8, username = 'llena')
        draft.about_text        =   'Panadería de barrio con 20 años de historia.'
        draft.whatsapp          =   '1122334455'
        draft.hours             =   [{'day': 'Lunes', 'open': '09:00', 'close': '18:00'}]
        draft.faqs              =   [{'q': '¿Hacen envíos?', 'a': 'Sí, en la zona.'}]
        draft.testimonials      =   [{'name': 'Ana', 'text': 'Excelente atención.'}]
        draft.save()
        low     =   self._proposals(empty, {'goals': ['vender_online']})['proposals'][0]['score']
        high    =   self._proposals(rich, {'goals': ['vender_online']})['proposals'][0]['score']
        self.assertIsNotNone(low['total'])
        self.assertGreaterEqual(high['total'] - low['total'], 8, (low, high))
        self.assertEqual(set(low['parts']), {'data', 'density', 'copy', 'assets'})
        self.assertTrue(low['todo'])
        self.assertTrue(all(isinstance(item, str) and item for item in low['todo']))

    def test_total_is_none_without_any_signal(self):
        store, _    =   self._store(products = 0)
        score       =   self._proposals(store, {'goals': ['vender_online']})['proposals'][0]['score']
        #La tienda vacía igual tiene copy y layout: el score no puede ser
        #siempre 95-97 ni venir de contraste fijo.
        self.assertNotIn(score['total'], (95, 96, 97))


class CopyInputTests(AiDesignPhaseOneBase):

    def test_audience_changes_description_and_cta(self):
        store, _    =   self._store(products = 2)
        people      =   self._proposals(store, {'goals': ['vender_online'], 'audience': 'particulares'})['proposals'][0]['copy']
        companies   =   self._proposals(store, {'goals': ['vender_online'], 'audience': 'empresas'})['proposals'][0]['copy']
        self.assertNotEqual(people['description'], companies['description'])
        self.assertNotEqual(people['cta_text'], companies['cta_text'])

    def test_content_hint_is_used_and_markup_is_ignored(self):
        store, _    =   self._store(products = 1)
        plain       =   self._proposals(store, {'goals': ['vender_online'], 'content_hint': 'Hacemos pan de masa madre por encargo.'})['proposals'][0]['copy']
        unsafe      =   self._proposals(store, {'goals': ['vender_online'], 'content_hint': '<script>alert(1)</script>'})['proposals'][0]['copy']
        self.assertIn('masa madre', plain['description'])
        self.assertNotIn('script', unsafe['description'])


class TelemetryTests(AiDesignPhaseOneBase):

    def test_event_is_recorded_and_meta_is_sanitized(self):
        store, _    =   self._store(products = 1)
        response    =   self._client(store).post(EVENT_URL, {
            'session'   :   's-1',
            'step'      :   3,
            'action'    :   'step_done',
            'meta'      :   {'tone': 'calido', 'email': 'duenio@gmail.com', 'free': 'texto libre'},
        }, format = 'json')
        self.assertEqual(response.status_code, 200, response.content[:400])
        event   =   AiDesignEvent.objects.get(store = store)
        self.assertEqual(event.action, 'step_done')
        self.assertEqual(event.step, 3)
        self.assertEqual(event.meta, {'tone': 'calido'})

    def test_unknown_action_is_rejected(self):
        store, _    =   self._store(products = 1)
        response    =   self._client(store).post(EVENT_URL, {'action': 'drop-table'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AiDesignEvent.objects.filter(store = store).exists())

    def test_out_of_range_step_is_rejected(self):
        store, _    =   self._store(products = 1)
        response    =   self._client(store).post(EVENT_URL, {'action': 'step_done', 'step': 9}, format = 'json')
        self.assertEqual(response.status_code, 400)


class RegressionGateTests(AiDesignPhaseOneBase):

    def test_same_payload_same_layout_signature(self):
        store, _    =   self._store(products = 4)
        payload     =   {'goals': ['vender_online'], 'must_have': ['faqs']}
        first       =   self._proposals(store, payload)['proposals']
        second      =   self._proposals(store, payload)['proposals']
        self.assertEqual(
            [_layout_signature(item['template'], item['layout_config']) for item in first],
            [_layout_signature(item['template'], item['layout_config']) for item in second],
        )

    def test_must_have_changes_composition(self):
        store, _    =   self._store(products = 4)
        base        =   self._proposals(store, {'goals': ['vender_online']})['proposals'][0]
        asked       =   self._proposals(store, {'goals': ['vender_online'], 'must_have': ['prices']})['proposals'][0]
        self.assertNotEqual(
            _layout_signature(base['template'], base['layout_config']),
            _layout_signature(asked['template'], asked['layout_config']),
        )

    def test_proposals_keep_structure_invariants(self):
        store, _    =   self._store(products = 5)
        data        =   self._proposals(store, {'goals': ['vender_online'], 'must_have': ['whatsapp', 'faqs']})
        signatures  =   set()
        for proposal in data['proposals']:
            blocks      =   proposal['layout_config']['landing']['blocks']
            enabled     =   [block['id'] for block in blocks if block['enabled']]
            self.assertEqual(len(enabled), len(set(enabled)), proposal['id'])
            self.assertEqual(enabled[0], 'hero', proposal['id'])
            self.assertIn(enabled[-1], ('contact', 'cta'), proposal['id'])
            signature   =   _layout_signature(proposal['template'], proposal['layout_config'])
            self.assertNotIn(signature, signatures, proposal['id'])
            signatures.add(signature)
