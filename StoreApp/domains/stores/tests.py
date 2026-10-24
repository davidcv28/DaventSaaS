"""
Tests de seguridad del dominio stores.

El claim del slug exige correo verificado (anti-abuso del plan de prueba).
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.models import Store, StoreCustomization
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL = '/api/stores/'


def _make_user(verified):
    province    =   Province.objects.create(name_province = 'Mendoza')
    zipcode     =   ZipCode.objects.create(zipcode = '5500')
    city        =   City.objects.create(name_city = 'Mendoza', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = 'duenio', email = 'duenio@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   '27123456',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
    )
    return user, profile


class StoreClaimVerificationTests(TestCase):

    def _claim(self, user):
        client  =   APIClient()
        client.force_authenticate(user = user)
        return client.post(STORES_URL, {'slug': 'mi-tienda', 'is_published': False}, format = 'json')

    def test_claim_blocked_without_verified_email(self):
        user, _     =   _make_user(verified = False)
        response    =   self._claim(user)
        self.assertEqual(response.status_code, 403)

    def test_claim_allowed_with_verified_email(self):
        user, _     =   _make_user(verified = True)
        response    =   self._claim(user)
        self.assertEqual(response.status_code, 201)


class StoreCatalogToggleTests(TestCase):
    """
    Catálogo opcional (customization.show_catalog): apagado, el endpoint
    público del catálogo devuelve 404 y la web queda como vidriera — sin
    borrar productos ni bloquear la gestión del panel.
    """

    def _make_store(self, show_catalog):
        _, profile      =   _make_user(verified = True)
        plan            =   SuscriptionPlan.objects.create(name = 'Plan test')
        benefit         =   Benefit.objects.create(code = 'has_public_link', label = 'Link público', kind = Benefit.FLAG)
        PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        StoreCustomization.objects.create(store = store, show_catalog = show_catalog)

    def test_public_catalog_ok_when_enabled(self):
        self._make_store(show_catalog = True)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/')
        self.assertEqual(response.status_code, 200)

    def test_public_catalog_404_when_disabled(self):
        self._make_store(show_catalog = False)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/')
        self.assertEqual(response.status_code, 404)

    def test_public_store_still_ok_when_catalog_disabled(self):
        #Solo se apaga la página Catálogo: la web pública sigue respondiendo.
        self._make_store(show_catalog = False)
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['customization']['show_catalog'])


class StoreListMineTests(TestCase):
    """
    El listado /stores/ de un staff trae todas las webs (panel admin); con
    ?mine=1 trae solo la suya, para que el panel de usuario no tome la web
    de otro cliente como propia (y todo PATCH diera 404).
    """

    def _setup(self):
        _, owner_profile    =   _make_user(verified = True)
        Store.objects.create(user = owner_profile, slug = 'cliente')
        admin               =   User.objects.create_user(username = 'admin', email = 'admin@gmail.com', password = 'Xq7#mP2vL9bT', is_staff = True)
        client              =   APIClient()
        client.force_authenticate(user = admin)
        return client

    def test_staff_list_returns_all_stores(self):
        client      =   self._setup()
        response    =   client.get(STORES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results'] if isinstance(response.data, dict) else response.data), 1)

    def test_staff_list_mine_excludes_other_users_stores(self):
        client      =   self._setup()
        response    =   client.get(STORES_URL, {'mine': 1})
        self.assertEqual(response.status_code, 200)
        rows        =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 0)


class ImageNormalizationTests(TestCase):
    """Procesado automático de imágenes (galería/decoración/producto)."""

    @staticmethod
    def _upload(size, mode = 'RGB', color = (200, 30, 30), fmt = 'PNG'):
        import io
        from PIL import Image
        buffer  =   io.BytesIO()
        Image.new(mode, size, color).save(buffer, format = fmt)
        buffer.seek(0)
        return buffer

    def test_gallery_clamps_extreme_ratio_and_outputs_webp(self):
        import io
        from PIL import Image
        from StoreApp.domains.stores.services.imaging import normalize_image
        body, ext, content_type =   normalize_image(self._upload((4000, 500)), 'gallery')
        width, height           =   Image.open(io.BytesIO(body)).size
        self.assertEqual((ext, content_type), ('webp', 'image/webp'))
        self.assertLessEqual(width, 1600)
        self.assertLessEqual(width / height, 16 / 9 + 0.02)

    def test_product_flattens_transparency_on_white(self):
        import io
        from PIL import Image
        from StoreApp.domains.stores.services.imaging import normalize_image
        body, _, _  =   normalize_image(self._upload((300, 300), 'RGBA', (0, 0, 0, 0)), 'product')
        pixel       =   Image.open(io.BytesIO(body)).convert('RGB').getpixel((10, 10))
        self.assertTrue(all(channel >= 250 for channel in pixel))

    def test_invalid_file_is_rejected(self):
        import io
        from StoreApp.domains.stores.services.imaging import normalize_image
        with self.assertRaises(ValueError):
            normalize_image(io.BytesIO(b'no soy una imagen'), 'gallery')

    def test_cover_crops_portrait_to_square_and_caps_size(self):
        import io
        from PIL import Image
        from StoreApp.domains.stores.services.imaging import normalize_image
        body, ext, _    =   normalize_image(self._upload((1000, 3000)), 'cover')
        width, height   =   Image.open(io.BytesIO(body)).size
        self.assertEqual(ext, 'webp')
        self.assertLessEqual(width / height, 1.01)
        body, _, _      =   normalize_image(self._upload((5000, 2000)), 'cover')
        self.assertLessEqual(max(Image.open(io.BytesIO(body)).size), 2200)

    def test_logo_keeps_transparency_and_outputs_webp(self):
        import io
        from PIL import Image
        from StoreApp.domains.stores.services.imaging import normalize_image
        body, ext, content_type =   normalize_image(self._upload((1600, 1600), 'RGBA', (10, 20, 30, 0)), 'logo')
        out                     =   Image.open(io.BytesIO(body))
        self.assertEqual((ext, content_type), ('webp', 'image/webp'))
        self.assertLessEqual(max(out.size), 800)
        self.assertIn('A', out.getbands())
        self.assertLess(out.getpixel((5, 5))[3], 16)

    def test_carousel_behaves_like_cover(self):
        import io
        from PIL import Image
        from StoreApp.domains.stores.services.imaging import normalize_image
        body, ext, _    =   normalize_image(self._upload((1000, 3000)), 'carousel')
        width, height   =   Image.open(io.BytesIO(body)).size
        self.assertEqual(ext, 'webp')
        self.assertLessEqual(width / height, 1.01)


class StoreCoverGatingTests(TestCase):
    """Imagen de portada: solo con has_design_advanced (Plan premium)."""

    def _client(self, premium = False, plus = False):
        _, profile      =   _make_user(verified = True)
        plan            =   SuscriptionPlan.objects.create(name = 'Plan test')
        codes           =   ['has_public_link', 'has_customization']
        if plus:
            codes.append('has_design_plus')
        if premium:
            codes +=  ['has_design_plus', 'has_design_advanced']
        for code in set(codes):
            benefit     =   Benefit.objects.create(code = code, label = code, kind = Benefit.FLAG)
            PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client

    def test_cover_upload_forbidden_without_premium(self):
        response    =   self._client(premium = False).post(f'{STORES_URL}customization/cover/', {}, format = 'multipart')
        self.assertEqual(response.status_code, 403)

    def test_cover_delete_forbidden_without_premium(self):
        response    =   self._client(premium = False).delete(f'{STORES_URL}customization/cover/')
        self.assertEqual(response.status_code, 403)

    def test_cover_upload_requires_file_with_premium(self):
        response    =   self._client(premium = True).post(f'{STORES_URL}customization/cover/', {}, format = 'multipart')
        self.assertEqual(response.status_code, 400)

    def test_premium_template_saved_with_premium(self):
        response    =   self._client(premium = True).patch(f'{STORES_URL}customization/', {'template': 'street'}, format = 'json')
        self.assertEqual(response.data['customization']['template'], 'street')
        self.assertIn('cover', response.data['customization'])


class StoreTemplateGatingTests(TestCase):
    """
    Plantillas de portada por nivel de plan: Básico elige Clásico o
    Perspectiva, Estándar (has_design_plus) suma Urbano y Publicidad y
    Premium (has_design_advanced) todo el catálogo. Un diseño fuera del
    nivel se descarta del PATCH igual que los campos premium y la web
    pública fuerza 'classic' si el guardado deja de estar permitido.
    """

    def _client(self, *benefit_codes):
        _, profile      =   _make_user(verified = True)
        plan            =   SuscriptionPlan.objects.create(name = 'Plan test')
        for code in set(('has_public_link', 'has_customization') + benefit_codes):
            benefit     =   Benefit.objects.create(code = code, label = code, kind = Benefit.FLAG)
            PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client, store

    def test_basic_picks_base_templates(self):
        client, _       =   self._client()
        for key in ('classic', 'perspective'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_basic_discards_plus_and_advanced_templates(self):
        client, _       =   self._client()
        for key in ('street', 'promo', 'terminal'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_standard_picks_plus_templates(self):
        client, _       =   self._client('has_design_plus')
        for key in ('street', 'promo'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_standard_discards_advanced_template(self):
        client, _       =   self._client('has_design_plus')
        response        =   client.patch(f'{STORES_URL}customization/', {'template': 'terminal'}, format = 'json')
        self.assertEqual(response.data['customization']['template'], 'classic')

    def test_premium_picks_any_template(self):
        client, _       =   self._client('has_design_plus', 'has_design_advanced')
        for key in ('classic', 'perspective', 'street', 'promo', 'terminal'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_removed_template_is_discarded(self):
        #'atelier' salió del catálogo: no está en allowed_templates, así
        #que el PATCH la descarta como a un diseño fuera del nivel.
        client, _       =   self._client('has_design_plus', 'has_design_advanced')
        response        =   client.patch(f'{STORES_URL}customization/', {'template': 'atelier'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['template'], 'classic')

    def test_public_payload_lists_allowed_templates(self):
        client, store   =   self._client('has_design_plus')
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.data['allowed_templates'], ['classic', 'perspective', 'street', 'promo'])

    def test_downgraded_template_is_not_persisted(self):
        #Con el plan vigente guarda 'street'; si el beneficio se pierde, el
        #payload público ya no lo lista (el frontend fuerza 'classic').
        client, store   =   self._client('has_design_plus')
        client.patch(f'{STORES_URL}customization/', {'template': 'street'}, format = 'json')
        PlanBenefit.objects.filter(benefit__code = 'has_design_plus').delete()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertNotIn('street', response.data['allowed_templates'])
        self.assertEqual(response.data['customization']['template'], 'street')


class MarketingFieldsTests(TestCase):
    """
    Secciones de marketing de la portada ("Mi empresa"): las listas JSON se
    sanea en el serializer — filas incompletas fuera, textos recortados,
    iconos fuera del catálogo caen al default y section_order solo admite
    claves conocidas completándose con el orden base.
    """

    def _client(self, with_plan = True):
        _, profile      =   _make_user(verified = True)
        if with_plan:
            plan        =   SuscriptionPlan.objects.create(name = 'Plan test')
            for code in ('has_public_link', 'has_customization'):
                benefit =   Benefit.objects.create(code = code, label = code, kind = Benefit.FLAG)
                PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
            Suscription.objects.create(
                user                =   profile,
                plan_suscription    =   plan,
                end_date            =   timezone.now() + timedelta(days = 30),
                status              =   Suscription.STATUS_ACTIVE,
            )
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = profile.user)
        return client

    def test_marketing_patch_forbidden_without_plan(self):
        response    =   self._client(with_plan = False).patch(f'{STORES_URL}customization/', {'services': []}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_services_are_sanitized(self):
        payload     =   [
            {'icon': 'truck', 'title': 'Envíos', 'text': 'A todo el país'},
            {'icon': 'no-existe', 'title': 'Garantía', 'text': '30 días'},
            {'icon': 'star', 'title': '', 'text': 'sin título'},
            {'icon': 'star', 'title': 'Solo título'},
            'basura',
        ]
        response    =   self._client().patch(f'{STORES_URL}customization/', {'services': payload}, format = 'json')
        services    =   response.data['customization']['services']
        self.assertEqual(len(services), 2)
        self.assertEqual(services[0]['icon'], 'truck')
        self.assertEqual(services[1]['icon'], 'package')

    def test_lists_are_truncated_and_clipped(self):
        payload     =   {
            'stats'         :   [{'value': f'+{i}', 'label': f'Cifra {i}'} for i in range(10)],
            'testimonials'  :   [{'name': 'Ana', 'detail': 'x' * 200, 'text': 'Muy buena atención'}],
            'faqs'          :   [{'q': '¿Envían?', 'a': 'Sí, a todo el país'}, {'q': 'incompleta'}],
            'hours'         :   [{'label': 'Lun a vie', 'value': '9 a 18 h'}],
        }
        response    =   self._client().patch(f'{STORES_URL}customization/', payload, format = 'json')
        custom      =   response.data['customization']
        self.assertEqual(len(custom['stats']), 4)
        self.assertEqual(len(custom['testimonials'][0]['detail']), 80)
        self.assertEqual(len(custom['faqs']), 1)
        self.assertEqual(custom['hours'], [{'label': 'Lun a vie', 'value': '9 a 18 h'}])

    def test_section_order_filters_and_completes(self):
        response    =   self._client().patch(
            f'{STORES_URL}customization/',
            {'section_order': ['faq', 'inventada', 'about', 'faq']},
            format = 'json',
        )
        order       =   response.data['customization']['section_order']
        self.assertEqual(order[:2], ['faq', 'about'])
        self.assertEqual(len(order), 7)
        self.assertNotIn('inventada', order)

    def test_non_list_payload_rejected(self):
        response    =   self._client().patch(f'{STORES_URL}customization/', {'faqs': 'no-es-lista'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_public_payload_exposes_marketing_fields(self):
        client      =   self._client()
        client.patch(
            f'{STORES_URL}customization/',
            {'services': [{'icon': 'truck', 'title': 'Envíos', 'text': 'A todo el país'}], 'cta_title': 'Escribinos'},
            format = 'json',
        )
        response    =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        custom      =   response.data['customization']
        self.assertEqual(custom['services'][0]['title'], 'Envíos')
        self.assertEqual(custom['cta_title'], 'Escribinos')
