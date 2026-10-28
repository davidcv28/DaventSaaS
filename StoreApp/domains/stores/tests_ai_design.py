#Tests del motor de diseño automático (ai_design): contrato, invariantes y
#determinismo. Los helpers siguen el patrón de tests.py del dominio (plan +
#suscripción vigente con los beneficios pedidos).

import io
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS
from StoreApp.domains.stores.models import Store, StoreCarouselImage, StoreCustomization, StoreGalleryImage
from StoreApp.domains.stores.services import allowed_templates_of
from StoreApp.domains.stores.services import storage
from StoreApp.domains.stores.services.ai_design import generate as generate_ai_design
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL  =   '/api/stores/'
AI_URL      =   f'{STORES_URL}ai-design/'
APPLY_URL   =   f'{STORES_URL}ai-design/apply/'
IMAGE_URL   =   f'{STORES_URL}ai-design/image/'


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

    def _store(self, advanced = True, ai = True, customization = True, products = 0, username = 'duenio', limits = False):
        user, profile   =   _make_user(username)
        extra           =   {'max_gallery_images': 10, 'max_images': 30, 'max_storage_mb': 50} if limits else {}
        _grant(
            profile,
            has_public_link         =   True,
            has_customization       =   customization,
            has_design_plus         =   advanced,
            has_design_advanced     =   advanced,
            has_ai_design           =   ai,
            **extra,
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
        self.assertEqual(first.json()['engine'], 'ai-design/2')

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
        #Plan sin has_ai_design ni has_design_plus: la whitelist real queda
        #en el nivel Básico. Se llama al motor directo porque el endpoint
        #responde 403 sin el flag (acá probamos la whitelist, no el gate).
        store, _    =   self._store(advanced = False, ai = False, products = 3)
        data        =   generate_ai_design(store, {})
        allowed     =   set(allowed_templates_of(store.user))
        self.assertEqual(allowed, {'classic', 'duo'})
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
        self.assertIn('testimonials', [item['code'] for item in data['missing']])

    def test_missing_is_list_of_objects(self):
        store, _    =   self._store()
        data        =   self._client(store).post(AI_URL, {}, format = 'json').json()
        self.assertTrue(data['missing'])
        for item in data['missing']:
            self.assertEqual(set(item), {'code', 'label', 'hint', 'action'})
            self.assertTrue(item['code'] and item['label'] and item['action'])

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


class AiDesignV2Tests(AiDesignBase):
    """Ronda 2: diseños exclusivos de IA, copy_draft, autofill y pedido de imágenes."""

    def _generate(self, store, payload = None):
        client  =   self._client(store)
        data    =   {'rubro': 'belleza', 'tone': 'moderno', 'goals': ['mostrar_trabajos']}
        data.update(payload or {})
        return client, client.post(AI_URL, data, format = 'json').json()

    def _apply(self, client, data, autofill = None):
        payload =   {'seed': data['seed'], 'proposal_id': data['proposals'][0]['id']}
        if autofill is not None:
            payload['autofill']   =   autofill
        return client.post(APPLY_URL, payload, format = 'json')

    def test_ai_templates_used_when_plan_allows(self):
        store, _    =   self._store()
        _, data     =   self._generate(store)
        self.assertEqual(data['engine'], 'ai-design/2')
        templates   =   [proposal['template'] for proposal in data['proposals']]
        self.assertTrue(any(template in ('ai_lumen', 'ai_pulse') for template in templates))

    def test_ai_templates_never_outside_plan(self):
        #Sin has_ai_design los ai_* no están en la whitelist del plan y el
        #motor no los devuelve (se llama al motor directo: el endpoint ya
        #responde 403 sin el flag).
        store, _    =   self._store(ai = False)
        data        =   generate_ai_design(store, {'rubro': 'belleza', 'goals': ['mostrar_trabajos']})
        allowed     =   set(allowed_templates_of(store.user))
        self.assertFalse({'ai_lumen', 'ai_pulse'} & allowed)
        for proposal in data['proposals']:
            self.assertIn(proposal['template'], allowed)
            self.assertNotIn(proposal['template'], ('ai_lumen', 'ai_pulse'))

    def test_ai_proposal_uses_bold_blocks_and_look(self):
        store, _    =   self._store()
        _, data     =   self._generate(store)
        proposal    =   next(item for item in data['proposals'] if item['template'] in ('ai_lumen', 'ai_pulse'))
        landing     =   {block['id']: block for block in proposal['layout_config']['landing']['blocks']}
        self.assertIn(landing['hero'].get('variant'), ('cinema', 'editorial', 'full'))
        self.assertEqual(proposal['site_theme']['containers']['surface'], 'glass' if proposal['template'] == 'ai_lumen' else 'flat')
        self.assertTrue(proposal['why'])

    def test_copy_draft_respects_model_limits(self):
        store, _    =   self._store(products = 4)
        _, data     =   self._generate(store)
        for proposal in data['proposals']:
            draft   =   proposal['copy_draft']
            self.assertLessEqual(len(draft.get('about_text', '')), StoreCustomization.about_text.field.max_length)
            self.assertLessEqual(len(draft.get('about_mission', '')), StoreCustomization.about_mission.field.max_length)
            for row in draft.get('faqs', []):
                self.assertLessEqual(len(row['q']), StoreCustomization.FAQ_Q_MAX)
                self.assertLessEqual(len(row['a']), StoreCustomization.FAQ_A_MAX)
            for row in draft.get('services', []):
                self.assertLessEqual(len(row['name']), StoreCustomization.SERVICE_TITLE_MAX)
                self.assertLessEqual(len(row['desc']), StoreCustomization.SERVICE_TEXT_MAX)
            for row in draft.get('steps', []):
                self.assertLessEqual(len(row['title']), StoreCustomization.SERVICE_STEP_TITLE_MAX)
                self.assertLessEqual(len(row['desc']), StoreCustomization.SERVICE_STEP_TEXT_MAX)
            for row in draft.get('announcements', []):
                self.assertLessEqual(len(row['text']), StoreCustomization.ANNOUNCEMENT_TEXT_MAX)

    def test_copy_draft_skips_fields_with_content(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(
            about_text      =   'Texto propio',
            about_mission   =   'Misión propia',
            faqs            =   [{'q': '¿Envían?', 'a': 'Sí'}],
            services        =   [{'icon': 'truck', 'title': 'Envíos', 'text': 'A todo el país'}],
        )
        _, data =   self._generate(store)
        draft   =   data['proposals'][0]['copy_draft']
        for key in ('about_text', 'about_mission', 'faqs', 'services'):
            self.assertNotIn(key, draft)
        self.assertIn('steps', draft)

    def test_autofill_false_keeps_business_fields_empty(self):
        store, customization  =   self._store()
        client, data          =   self._generate(store)
        response              =   self._apply(client, data)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertEqual(customization.about_text, '')
        self.assertEqual(customization.about_mission, '')
        self.assertEqual(customization.faqs, [])
        self.assertEqual(customization.services, [])
        self.assertEqual(customization.service_steps, [])

    def test_autofill_true_writes_only_empty(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(about_mission = 'Misión propia')
        client, data          =   self._generate(store)
        response              =   self._apply(client, data, autofill = True)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        self.assertTrue(customization.about_text)
        self.assertEqual(customization.about_mission, 'Misión propia')
        self.assertTrue(customization.faqs)
        self.assertTrue(customization.services)
        self.assertTrue(customization.service_steps)
        self.assertTrue(customization.announcements)
        #Las filas escritas respetan la forma del modelo (icon/title/text).
        for row in customization.services:
            self.assertEqual(set(row), {'icon', 'title', 'text'})
        for row in customization.faqs:
            self.assertEqual(set(row), {'q', 'a'})

    def test_apply_never_writes_forbidden_business_fields(self):
        store, customization  =   self._store()
        StoreCustomization.objects.filter(pk = customization.pk).update(
            testimonials    =   [{'name': 'Ana', 'detail': 'Clienta', 'text': 'Muy buena atención'}],
            stats           =   [{'value': '+10', 'label': 'Años'}],
            contact_email   =   'hola@negocio.com',
            whatsapp        =   '1122334455',
            hours           =   [{'label': 'Lun a vie', 'value': '9 a 18 h'}],
            catalog_note    =   'Aviso propio',
        )
        before              =   StoreCustomization.objects.get(pk = customization.pk)
        client, data        =   self._generate(store)
        response            =   self._apply(client, data, autofill = True)
        self.assertEqual(response.status_code, 200)
        customization.refresh_from_db()
        for field in ('testimonials', 'stats', 'contact_email', 'whatsapp', 'hours', 'catalog_note'):
            self.assertEqual(getattr(customization, field), getattr(before, field))

    def test_image_requests_only_without_own_images(self):
        store, _    =   self._store()
        _, data     =   self._generate(store)
        proposal    =   data['proposals'][0]
        self.assertTrue(proposal['image_requests'])
        self.assertLessEqual(len(proposal['image_requests']), 2)
        for request in proposal['image_requests']:
            self.assertIn(request['target'], ('cover', 'gallery'))
            self.assertIn(request['min_count'], (2, 3, 4))
            for unlock in request['unlocks']:
                block_id    =   unlock.split(':')[0]
                self.assertIn(block_id, TEMPLATE_BLOCKS['landing'])
        #Con galería propia ya no pide fotos.
        StoreGalleryImage.objects.create(store = store, image_key = 'gallery/1.webp', image_size = 10)
        _, data     =   self._generate(store)
        self.assertEqual(data['proposals'][0]['image_requests'], [])


class AiDesignImageTests(AiDesignBase):
    """POST /api/stores/ai-design/image/: foto del pedido -> galería en WebP."""

    def setUp(self):
        super().setUp()
        self.media      =   tempfile.mkdtemp()
        self.override   =   override_settings(MEDIA_ROOT = self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def _file(self, size = (1400, 900), color = (200, 30, 60), fmt = 'PNG'):
        buffer  =   io.BytesIO()
        Image.new('RGB', size, color).save(buffer, format = fmt)
        buffer.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('foto.png', buffer.read(), content_type = 'image/png')

    def test_upload_creates_webp_gallery_image(self):
        store, _    =   self._store(limits = True)
        client      =   self._client(store)
        with patch.object(storage, 'storage_configured', return_value = False):
            response =  client.post(IMAGE_URL, {'image': self._file(), 'request_id': 'local'}, format = 'multipart')
        self.assertEqual(response.status_code, 200)
        payload     =   response.json()
        self.assertEqual(payload['gallery']['count'], 1)
        image       =   StoreGalleryImage.objects.get(pk = payload['image']['id'])
        self.assertEqual(image.kind, StoreGalleryImage.KIND_GALLERY)
        self.assertEqual(image.position, 0)
        with default_storage.open(image.image_key, 'rb') as handle:
            head    =   handle.read(16)
        #Firma real del archivo guardado: RIFF....WEBP.
        self.assertTrue(head.startswith(b'RIFF'))
        self.assertEqual(head[8:12], b'WEBP')
        self.assertGreater(image.image_size, 0)
        self.assertEqual(payload['image']['url'], f'/media/{image.image_key}')

    def test_upload_without_ai_design_is_403(self):
        store, _    =   self._store(ai = False, limits = True)
        response    =   self._client(store).post(IMAGE_URL, {'image': self._file()}, format = 'multipart')
        self.assertEqual(response.status_code, 403)

    def test_upload_without_file_is_400(self):
        store, _    =   self._store(limits = True)
        response    =   self._client(store).post(IMAGE_URL, {}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_invalid_file_is_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        store, _    =   self._store(limits = True)
        upload      =   SimpleUploadedFile('x.png', b'no soy una imagen', content_type = 'image/png')
        response    =   self._client(store).post(IMAGE_URL, {'image': upload}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_respects_storage_quota(self):
        store, customization  =   self._store(limits = True)
        PlanBenefit.objects.filter(plan__suscription__user = store.user, benefit__code = 'max_storage_mb').update(value = 0)
        with patch.object(storage, 'storage_configured', return_value = False):
            response =  self._client(store).post(IMAGE_URL, {'image': self._file()}, format = 'multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StoreGalleryImage.objects.count(), 0)

    def test_image_throttle_after_limit(self):
        store, _    =   self._store(limits = True)
        client      =   self._client(store)
        codes       =   [
            client.post(IMAGE_URL, {'image': self._file()}, format = 'multipart').status_code
            for _ in range(62)
        ]
        self.assertEqual(codes[0], 200)
        self.assertEqual(codes[-1], 429)
