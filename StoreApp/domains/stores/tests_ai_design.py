#Tests del motor de diseño automático (ai_design): contrato, invariantes y
#determinismo. Los helpers siguen el patrón de tests.py del dominio (plan +
#suscripción vigente con los beneficios pedidos).

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS
from StoreApp.domains.stores.models import Store, StoreCarouselImage, StoreCustomization
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL  =   '/api/stores/'
AI_URL      =   f'{STORES_URL}ai-design/'
APPLY_URL   =   f'{STORES_URL}ai-design/apply/'


def _grant(profile, **benefits):
    plan    =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username} {profile.pk}')
    for code, value in benefits.items():
        kind        =   Benefit.FLAG if isinstance(value, bool) else Benefit.LIMIT
        benefit     =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': kind})[0]
        PlanBenefit.objects.create(
            plan        =   plan,
            benefit     =   benefit,
            enabled     =   value if kind == Benefit.FLAG else True,
            value       =   None if kind == Benefit.FLAG else value,
        )
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    return plan


def _make_user(username = 'duenio'):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'55{len(username):02d}'[-4:])
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'29{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   True,
        phone           =   f'1122{abs(hash(username)) % 10**8:08d}',
    )
    return user, profile


class AiDesignBase(TestCase):

    def setUp(self):
        cache.clear()

    def _store(self, advanced = True, ai = True, customization = True, products = 0, username = 'duenio'):
        user, profile   =   _make_user(username)
        _grant(
            profile,
            has_public_link         =   True,
            has_customization       =   customization,
            has_design_plus         =   advanced,
            has_design_advanced     =   advanced,
            has_ai_design           =   ai,
        )
        store   =   Store.objects.create(user = profile, slug = f'tienda-{username}')
        draft   =   StoreCustomization.objects.create(
            store           =   store,
            display_name    =   'Panadería La Espiga',
            site_templates  =   ['landing', 'catalog', 'services'],
        )
        for index in range(products):
            Product.objects.create(store = store, name = f'Producto {index}', price = 100, image_key = f'k{index}')
        return store, draft

    def _client(self, store):
        client  =   APIClient()
        client.force_authenticate(user = store.user.user)
        return client


class AiDesignGenerateTests(AiDesignBase):

    def test_deterministic_same_payload_same_json(self):
        store, _    =   self._store(products = 5)
        client      =   self._client(store)
        payload     =   {'rubro': 'comercio', 'tone': 'moderno', 'goals': ['vender_online']}
        first       =   client.post(AI_URL, payload, format = 'json')
        second      =   client.post(AI_URL, payload, format = 'json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(first.json()['engine'], 'ai-design/1')

    def test_two_or_three_proposals_distinct(self):
        store, _    =   self._store(products = 8)
        data        =   self._client(store).post(AI_URL, {'rubro': 'gastronomia'}, format = 'json').json()
        self.assertIn(len(data['proposals']), (2, 3))
        ids         =   [proposal['id'] for proposal in data['proposals']]
        self.assertEqual(ids, [f'p{index}' for index in range(1, len(ids) + 1)])
        #Dos propuestas nunca son la misma: cambia la plantilla o, si se
        #repite (plan con una sola), el orden/variante de los bloques.
        shapes      =   [
            (proposal['template'], tuple((block['id'], block.get('variant')) for block in proposal['layout_config']['landing']['blocks']))
            for proposal in data['proposals']
        ]
        self.assertEqual(len(shapes), len(set(shapes)))

    def test_block_ids_always_in_whitelist(self):
        store, _    =   self._store(products = 6)
        data        =   self._client(store).post(AI_URL, {'rubro': 'arte', 'tone': 'audaz'}, format = 'json').json()
        for proposal in data['proposals']:
            for surface, config in proposal['layout_config'].items():
                self.assertIn(surface, TEMPLATE_BLOCKS)
                for block in config['blocks']:
                    self.assertIn(block['id'], TEMPLATE_BLOCKS[surface])
                    spec    =   TEMPLATE_BLOCKS[surface][block['id']]
                    if block.get('variant'):
                        self.assertIn(block['variant'], spec.get('variants', ()))

    def test_locked_blocks_stay_enabled(self):
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        for proposal in data['proposals']:
            catalog =   {block['id']: block for block in proposal['layout_config']['catalog']['blocks']}
            services =  {block['id']: block for block in proposal['layout_config']['services']['blocks']}
            self.assertTrue(catalog['grid']['enabled'])
            self.assertTrue(services['picker']['enabled'])

    def test_premium_block_dropped_without_design_advanced(self):
        store, _    =   self._store(advanced = False, products = 4)
        StoreCarouselImage.objects.create(store = store, image_key = 'carousel/1.webp')
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        for proposal in data['proposals']:
            ids     =   [block['id'] for block in proposal['layout_config']['catalog']['blocks']]
            self.assertNotIn('banner', ids)

    def test_template_outside_plan_never_returned(self):
        store, _    =   self._store(advanced = False, products = 3)
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        allowed     =   {'classic', 'duo'}
        for proposal in data['proposals']:
            self.assertIn(proposal['template'], allowed)

    def test_blocks_without_data_are_disabled(self):
        #Tienda vacía: sin testimonios, sin FAQs, sin galería.
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        landing     =   {block['id']: block for block in data['proposals'][0]['layout_config']['landing']['blocks']}
        for block_id in ('testimonials', 'faq', 'gallery', 'stats'):
            if block_id in landing:
                self.assertFalse(landing[block_id]['enabled'])
        self.assertIn('testimonials', data['missing'])

    def test_hero_first_and_contact_last(self):
        store, _    =   self._store(products = 6)
        data        =   self._client(store).post(AI_URL, {'goals': ['vender_online']}, format = 'json').json()
        blocks      =   [block['id'] for block in data['proposals'][0]['layout_config']['landing']['blocks']]
        self.assertEqual(blocks[0], 'hero')
        self.assertEqual(blocks[-1], 'contact')


class AiDesignGateTests(AiDesignBase):

    def test_403_without_customization(self):
        store, _    =   self._store(customization = False)
        response    =   self._client(store).post(AI_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_403_without_ai_design(self):
        store, _    =   self._store(ai = False)
        response    =   self._client(store).post(AI_URL, {}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_403_apply_without_ai_design(self):
        store, _    =   self._store(ai = False)
        response    =   self._client(store).post(APPLY_URL, {'seed': 1, 'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_throttle_after_limit(self):
        store, _    =   self._store()
        client      =   self._client(store)
        codes       =   [client.post(AI_URL, {}, format = 'json').status_code for _ in range(21)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(codes[0], 200)


class AiDesignApplyTests(AiDesignBase):

    def _generate(self, client, payload = None):
        return client.post(AI_URL, payload or {'rubro': 'comercio', 'goals': ['vender_online']}, format = 'json').json()

    def test_apply_writes_only_draft(self):
        store, customization  =   self._store(products = 5)
        client                =   self._client(store)
        data                  =   self._generate(client)
        proposal              =   data['proposals'][0]
        published             =   {
            'layout_config' :   {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
            'site_theme'    :   {'palette': {'primary': '#111111'}},
            'template'      :   'classic',
        }
        StoreCustomization.objects.filter(pk = customization.pk).update(
            layout_config = published['layout_config'],
            site_theme    = published['site_theme'],
            template      = published['template'],
            about_text    = 'Texto propio del dueño',
        )
        response    =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': proposal['id']}, format = 'json')
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.layout_config, published['layout_config'])
        self.assertEqual(customization.site_theme, published['site_theme'])
        self.assertEqual(customization.template, published['template'])
        self.assertEqual(customization.about_text, 'Texto propio del dueño')
        self.assertEqual(customization.template_draft, proposal['template'])
        self.assertTrue(customization.layout_config_draft)
        self.assertEqual(
            [block['id'] for block in customization.layout_config_draft['landing']['blocks']],
            [block['id'] for block in proposal['layout_config']['landing']['blocks']],
        )

    def test_apply_fills_only_empty_copy(self):
        store, customization  =   self._store(products = 3)
        customization.headline = 'Titular propio'
        customization.save(update_fields = ['headline'])
        client                =   self._client(store)
        data                  =   self._generate(client)
        response              =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': data['proposals'][0]['id']}, format = 'json')
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.headline, 'Titular propio')
        self.assertTrue(customization.cta_label)

    def test_apply_unknown_proposal_is_400(self):
        store, _    =   self._store()
        client      =   self._client(store)
        data        =   self._generate(client)
        response    =   client.post(APPLY_URL, {'seed': data['seed'], 'proposal_id': 'p9'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_apply_missing_seed_is_400(self):
        store, _    =   self._store()
        response    =   self._client(store).post(APPLY_URL, {'proposal_id': 'p1'}, format = 'json')
        self.assertEqual(response.status_code, 400)
