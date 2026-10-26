"""
Tests de seguridad del dominio stores.

El claim del slug exige correo verificado (anti-abuso del plan de prueba).
"""
from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.models import (
    Store, StoreCarouselImage, StoreCustomization, StoreDailyVisit, StoreGalleryImage,
)
from StoreApp.domains.stores.services import contact as contact_service
from StoreApp.domains.stores.services import storage
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

STORES_URL = '/api/stores/'


def _grant(profile, **benefits):
    """Plan + suscripción vigente de 30 días con los beneficios pedidos.

    bool → flag habilitado/deshabilitado; int|None → limit con ese valor
    (None = ilimitado)."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username} {profile.pk}')
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


def _make_named_user(username, verified = True, email = None):
    """Segundo usuario del caso (el _make_user de arriba repite credenciales)."""
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'55{len(username):02d}'[-4:])
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = email or f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'29{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   verified,
        #El claim exige celular cargado (ancla anti-abuso del alta social).
        phone           =   f'1122{abs(hash(username)) % 10**8:08d}',
    )
    return user, profile


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
        phone           =   '1100000001',
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

    def test_claim_blocked_without_phone(self):
        #Alta social: el email queda verificado por el provider pero el
        #celular (ancla anti-abuso) se completa aparte — sin él, 403.
        user, profile   =   _make_user(verified = True)
        profile.phone   =   None
        profile.save(update_fields = ['phone'])
        response        =   self._claim(user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('celular', response.json()['detail'])


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
        for key in ('classic', 'perspective', 'duo'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_basic_discards_plus_and_advanced_templates(self):
        client, _       =   self._client()
        for key in ('street', 'promo', 'terminal', 'lookbook', 'cobre', 'minimal', 'boutique'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_standard_picks_plus_templates(self):
        client, _       =   self._client('has_design_plus')
        for key in ('street', 'promo'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_standard_discards_advanced_template(self):
        client, _       =   self._client('has_design_plus')
        for key in ('terminal', 'lookbook', 'cobre', 'minimal', 'boutique'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_premium_picks_any_template(self):
        client, _       =   self._client('has_design_plus', 'has_design_advanced')
        for key in ('classic', 'perspective', 'duo', 'street', 'promo', 'terminal', 'lookbook', 'cobre', 'minimal', 'boutique'):
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
        self.assertEqual(response.data['allowed_templates'], ['classic', 'perspective', 'duo', 'bloque', 'street', 'promo'])

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


class SlugSecurityTests(TestCase):
    """
    El slug es la identidad pública de la web: formato cerrado, lista de
    palabras reservadas (rutas del sistema/frontend), normalización a
    minúsculas y unicidad también al renombrar.
    """

    def _client(self):
        user, _     =   _make_user(verified = True)
        client      =   APIClient()
        client.force_authenticate(user = user)
        return client

    def test_reserved_slug_rejected(self):
        response    =   self._client().post(STORES_URL, {'slug': 'admin'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_slug_format_rejected(self):
        client      =   self._client()
        for slug in ('mi tienda!', 'a', '-roto', 'slug__mal'):
            response    =   client.post(STORES_URL, {'slug': slug}, format = 'json')
            self.assertEqual(response.status_code, 400, slug)

    def test_slug_normalized_to_lowercase(self):
        response    =   self._client().post(STORES_URL, {'slug': 'MiTienda'}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Store.objects.get().slug, 'mitienda')

    def test_second_store_rejected(self):
        client      =   self._client()
        self.assertEqual(client.post(STORES_URL, {'slug': 'tienda-uno'}, format = 'json').status_code, 201)
        self.assertEqual(client.post(STORES_URL, {'slug': 'tienda-dos'}, format = 'json').status_code, 400)

    def test_rename_to_taken_slug_rejected(self):
        _, profile2     =   _make_named_user('otro.dueño')
        Store.objects.create(user = profile2, slug = 'ocupado')
        client          =   self._client()
        client.post(STORES_URL, {'slug': 'libre'}, format = 'json')
        store           =   Store.objects.get(slug = 'libre')
        response        =   client.put(f'{STORES_URL}{store.pk}/', {'slug': 'ocupado'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        store.refresh_from_db()
        self.assertEqual(store.slug, 'libre')

    def test_slug_available_endpoint(self):
        client      =   self._client()
        cases       =   {'admin': 'reserved', 'NO!!': 'invalid', 'mi-web': None}
        for slug, reason in cases.items():
            response    =   client.get(f'{STORES_URL}slug-available/', {'slug': slug})
            self.assertEqual(response.data['reason'], reason, slug)
        client.post(STORES_URL, {'slug': 'mi-web'}, format = 'json')
        response    =   client.get(f'{STORES_URL}slug-available/', {'slug': 'mi-web'})
        self.assertEqual(response.data['reason'], 'taken')


class PublicStoreAccessTests(TestCase):
    """
    Fail-closed de la web pública: 404 sin publicar, bloqueada, sin
    suscripción vigente o sin el flag has_public_link — y el serializer
    público no expone datos internos (contact_email, dirección sin mapa).
    """

    def _setup(self, published = True, blocked = False, suscription = True, **benefits):
        _, profile      =   _make_user(verified = True)
        if suscription:
            _grant(profile, has_public_link = True, **benefits)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda', is_published = published, is_blocked = blocked)
        StoreCustomization.objects.create(store = store, contact_email = 'privado@tienda.com')
        return store

    def test_public_404_when_blocked(self):
        self._setup(blocked = True)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 404)

    def test_public_404_when_unpublished(self):
        self._setup(published = False)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 404)

    def test_public_404_without_suscription(self):
        self._setup(suscription = False)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 404)

    def test_public_404_without_public_link_benefit(self):
        #Plan vigente pero sin el flag: el link público es un beneficio.
        _, profile      =   _make_user(verified = True)
        plan            =   SuscriptionPlan.objects.create(name = 'Plan sin link')
        Suscription.objects.create(
            user = profile, plan_suscription = plan,
            end_date = timezone.now() + timedelta(days = 30),
            status = Suscription.STATUS_ACTIVE,
        )
        Store.objects.create(user = profile, slug = 'mi-tienda')
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 404)

    def test_public_payload_hides_contact_email(self):
        #contact_email es el buzón del formulario: no se publica en el HTML.
        self._setup()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('contact_email', response.data['customization'])

    def test_location_hidden_without_map_benefit(self):
        store           =   self._setup()
        custom          =   store.customization
        custom.show_location    =   True
        custom.save()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertIsNone(response.data['location_address'])

    def test_catalog_404_without_public_link(self):
        self._setup(suscription = False)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/').status_code, 404)

    def test_catalog_price_filters_defensive(self):
        #Regresión: min_price=1e999 desbordaba Decimal y daba 500; ahora el
        #parseo es defensivo y los inválidos/extremos no rompen el catálogo.
        self._setup()
        for bound in ('1e999', 'abc', '-5'):
            response    =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/', {'min_price': bound})
            self.assertEqual(response.status_code, 200, bound)

    def test_catalog_unknown_sort_falls_back(self):
        #El orden es whitelist: un sort desconocido no inyecta order_by.
        self._setup()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/catalog/', {'sort': 'drop_table'})
        self.assertEqual(response.status_code, 200)


class CaptchaTests(TestCase):
    """
    Captcha propio del formulario de contacto: challenge firmado con el
    HASH de la respuesta (nunca la respuesta), edad máxima, tiempo mínimo
    anti-bot y comparación timing-safe.
    """

    def _answer(self, slug, challenge_id):
        payload     =   signing.loads(challenge_id, salt = contact_service.CAPTCHA_SALT)
        return str(next(
            answer for answer in range(2, 19)
            if contact_service._answer_hash(slug, answer) == payload['h']
        ))

    def test_valid_challenge_verifies(self):
        challenge   =   contact_service.issue_captcha('mi-tienda')
        answer      =   self._answer('mi-tienda', challenge['challenge_id'])
        with patch('time.time', return_value = timezone.now().timestamp() + 4):
            self.assertTrue(contact_service.verify_captcha('mi-tienda', challenge['challenge_id'], answer))

    def test_wrong_answer_rejected(self):
        challenge   =   contact_service.issue_captcha('mi-tienda')
        with patch('time.time', return_value = timezone.now().timestamp() + 4):
            self.assertFalse(contact_service.verify_captcha('mi-tienda', challenge['challenge_id'], 'zzz'))

    def test_tampered_challenge_rejected(self):
        challenge   =   contact_service.issue_captcha('mi-tienda')
        self.assertFalse(contact_service.verify_captcha('mi-tienda', challenge['challenge_id'] + 'x', '5'))

    def test_challenge_bound_to_slug(self):
        challenge   =   contact_service.issue_captcha('mi-tienda')
        answer      =   self._answer('mi-tienda', challenge['challenge_id'])
        with patch('time.time', return_value = timezone.now().timestamp() + 4):
            self.assertFalse(contact_service.verify_captcha('otra-tienda', challenge['challenge_id'], answer))

    def test_too_fast_submission_rejected(self):
        #El captcha exige un mínimo de segundos desde que se emitió: un bot
        #que responde al instante se frena sin llegar a comparar el hash.
        challenge   =   contact_service.issue_captcha('mi-tienda')
        answer      =   self._answer('mi-tienda', challenge['challenge_id'])
        self.assertFalse(contact_service.verify_captcha('mi-tienda', challenge['challenge_id'], answer))

    def test_expired_challenge_rejected(self):
        challenge   =   contact_service.issue_captcha('mi-tienda')
        answer      =   self._answer('mi-tienda', challenge['challenge_id'])
        with patch('time.time', return_value = timezone.now().timestamp() + 700):
            self.assertFalse(contact_service.verify_captcha('mi-tienda', challenge['challenge_id'], answer))


class ContactFormTests(TestCase):
    """
    Formulario público "Contáctanos": honeypot de éxito falso para bots,
    captcha obligatorio y mail al dueño (o al contact_email elegido).
    """

    URL     =   f'{STORES_URL}public/mi-tienda/contact/'

    def setUp(self):
        #Throttle 'store_contact' sobre cache compartido: reset por test.
        cache.clear()

    def _setup(self):
        _, profile      =   _make_user(verified = True)
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        StoreCustomization.objects.create(store = store)
        return store

    def _payload(self, **overrides):
        payload     =   {
            'name'              :   'Visitante',
            'email'             :   'visitante@gmail.com',
            'message'           :   'Hola, ¿tienen stock del producto?',
            'challenge_id'      :   'x',
            'captcha_answer'    :   '5',
        }
        payload.update(overrides)
        return payload

    def test_honeypot_returns_fake_success_without_sending(self):
        self._setup()
        response        =   APIClient().post(self.URL, self._payload(website = 'http://spam.com'), format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_valid_message_reaches_owner(self):
        store           =   self._setup()
        with patch('StoreApp.domains.stores.views.viewset.verify_captcha', return_value = True):
            response    =   APIClient().post(self.URL, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [store.user.user.email])
        self.assertEqual(mail.outbox[0].reply_to, ['visitante@gmail.com'])

    def test_bad_captcha_rejected_without_sending(self):
        self._setup()
        with patch('StoreApp.domains.stores.views.viewset.verify_captcha', return_value = False):
            response    =   APIClient().post(self.URL, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_disabled_section_returns_404(self):
        store           =   self._setup()
        store.customization.show_contact    =   False
        store.customization.save()
        response        =   APIClient().post(self.URL, self._payload(), format = 'json')
        self.assertEqual(response.status_code, 404)


class VisitCounterTests(TestCase):
    """
    Contador de visitas: una fila por tienda/día, dedupe best-effort por
    hash(IP+UA) y métricas del panel solo con el beneficio has_stats.
    """

    def _setup(self, **benefits):
        _, profile      =   _make_user(verified = True)
        _grant(profile, has_public_link = True, **benefits)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        return profile

    def test_same_visitor_counts_once_per_day(self):
        self._setup()
        client      =   APIClient()
        client.get(f'{STORES_URL}public/mi-tienda/')
        client.get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(StoreDailyVisit.objects.get().count, 1)

    def test_distinct_visitor_counts_again(self):
        self._setup()
        client      =   APIClient()
        client.get(f'{STORES_URL}public/mi-tienda/', HTTP_USER_AGENT = 'Bot/1.0')
        client.get(f'{STORES_URL}public/mi-tienda/', HTTP_USER_AGENT = 'Bot/2.0')
        self.assertEqual(StoreDailyVisit.objects.get().count, 2)

    def test_xff_first_hop_spoofing_dedupes_by_last(self):
        #Regresión: confiar el primer X-Forwarded-For dejaba inflar el
        #contador cambiando solo el primer hop (spoofeable por el visitante).
        self._setup()
        client      =   APIClient()
        client.get(f'{STORES_URL}public/mi-tienda/', HTTP_X_FORWARDED_FOR = '1.1.1.1, 9.9.9.9')
        client.get(f'{STORES_URL}public/mi-tienda/', HTTP_X_FORWARDED_FOR = '2.2.2.2, 9.9.9.9')
        self.assertEqual(StoreDailyVisit.objects.get().count, 1)

    def test_stats_forbidden_without_benefit(self):
        profile     =   self._setup()
        client      =   APIClient()
        client.force_authenticate(user = profile.user)
        response    =   client.get(f'{STORES_URL}stats/')
        self.assertEqual(response.status_code, 403)

    def test_stats_ok_with_benefit(self):
        profile     =   self._setup(has_stats = True)
        APIClient().get(f'{STORES_URL}public/mi-tienda/')
        client      =   APIClient()
        client.force_authenticate(user = profile.user)
        response    =   client.get(f'{STORES_URL}stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['today'], 1)
        self.assertEqual(response.data['total'], 1)


class ImageOrderTests(TestCase):
    """
    Reorden del carrusel/galería: ids desconocidos se ignoran, duplicados
    se desduplican y los no listados quedan al final sin posiciones rotas.
    """

    def _setup(self, model, count = 3):
        user, profile   =   _make_user(verified = True)
        #Carrusel pide has_design_advanced; galería, has_customization.
        _grant(profile, has_customization = True, has_design_advanced = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        images          =   [model.objects.create(store = store, image_key = f'k{i}', position = i) for i in range(count)]
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, images

    def test_subset_order_appends_unlisted_without_dupes(self):
        client, images  =   self._setup(StoreCarouselImage)
        third           =   images[2]
        response        =   client.patch(f'{STORES_URL}customization/carousel/order/', {'order': [third.pk]}, format = 'json')
        self.assertEqual(response.status_code, 200)
        positions       =   sorted(
            StoreCarouselImage.objects.values_list('position', flat = True)
        )
        self.assertEqual(positions, [0, 1, 2])
        third.refresh_from_db()
        self.assertEqual(third.position, 0)

    def test_duplicate_and_unknown_ids_are_ignored(self):
        client, images  =   self._setup(StoreGalleryImage)
        first, second   =   images[0], images[1]
        response        =   client.patch(
            f'{STORES_URL}customization/gallery/order/',
            {'order': [first.pk, first.pk, 999999, second.pk]},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        positions       =   sorted(
            StoreGalleryImage.objects.values_list('position', flat = True)
        )
        self.assertEqual(positions, [0, 1, 2])
        first.refresh_from_db()
        self.assertEqual(first.position, 0)


class StorageQuotaTests(TestCase):
    """
    Cuotas de imágenes bajo lock: el rechequeo de cupos dentro de la
    transacción cierra la carrera check→put→consume entre uploads
    concurrentes (regresión TOCTOU).
    """

    def _store(self, **benefits):
        _, profile      =   _make_user(verified = True)
        _grant(profile, has_customization = True, **benefits)
        return Store.objects.create(user = profile, slug = 'mi-tienda')

    @staticmethod
    def _fake_upload():
        upload          =   Mock()
        upload.size     =   100
        return upload

    def _patches(self, key = 'fake-key'):
        return (
            patch.object(storage, 'storage_configured', return_value = True),
            patch.object(storage, 'validate_image_file', return_value = ''),
            patch.object(storage, 'normalize_image', return_value = (b'x' * 100, 'webp', 'image/webp')),
            patch.object(storage, '_put_object', return_value = key),
            patch.object(storage, '_delete_object', return_value = None),
        )

    def test_gallery_limit_rechecked_under_lock_cleans_orphan(self):
        #Simula la carrera que cerró el fix TOCTOU: entre el fast path y el
        #select_for_update otro request ganó el último cupo — el objeto ya
        #subido a R2 debe borrarse para no quedar huérfano.
        store           =   self._store(max_gallery_images = 1, max_images = None, max_storage_mb = None)
        def _race_winner(*args, **kwargs):
            StoreGalleryImage.objects.create(store = store, image_key = 'other', image_size = 100, position = 0)
            return 'fake-key'
        cfg, val, norm, put, delete   =   self._patches()
        with cfg, val, norm, \
             patch.object(storage, '_put_object', side_effect = _race_winner), \
             delete as delete_mock:
            with self.assertRaises(ValueError):
                storage.upload_gallery_image(store, self._fake_upload())
        delete_mock.assert_called_once_with('fake-key')
        self.assertEqual(StoreGalleryImage.objects.count(), 1)

    def test_delete_gallery_image_frees_bytes(self):
        store           =   self._store(max_gallery_images = 5, max_images = None, max_storage_mb = None)
        cfg, val, norm, put, delete   =   self._patches()
        with cfg, val, norm, put, delete:
            image       =   storage.upload_gallery_image(store, self._fake_upload())
            store.refresh_from_db()
            self.assertGreater(store.storage_used_bytes, 0)
            storage.delete_gallery_image(image)
            store.refresh_from_db()
        self.assertEqual(store.storage_used_bytes, 0)

    def test_storage_bytes_limit_blocks_upload(self):
        #Cupo de MB del plan: un upload que lo supera se rechaza antes de subir.
        store           =   self._store(max_storage_mb = 0, max_gallery_images = None, max_images = None)
        cfg, val, norm, put, delete   =   self._patches()
        with cfg, val, norm, put, delete:
            with self.assertRaises(ValueError):
                storage.upload_gallery_image(store, self._fake_upload())


class DecompressionBombTests(TestCase):
    """Imágenes gigantes de píxeles: Pillow corta por MAX_IMAGE_PIXELS."""

    def test_oversized_image_rejected(self):
        from StoreApp.domains.stores.services import imaging
        buffer      =   BytesIO()
        Image.new('RGB', (400, 300), (200, 30, 30)).save(buffer, format = 'PNG')
        buffer.seek(0)
        original    =   Image.MAX_IMAGE_PIXELS
        try:
            #Bajo el umbral para el test: 400x300 > 2x el límite parcheado.
            Image.MAX_IMAGE_PIXELS    =   100
            with self.assertRaises(ValueError):
                imaging.normalize_image(buffer, 'gallery')
        finally:
            Image.MAX_IMAGE_PIXELS    =   original


class ChatbotTests(TestCase):
    """Chatbot de la web pública: solo Premium lo configura (has_chatbot)."""

    def _client(self, chatbot = False):
        user, profile   =   _make_user(verified = True)
        _grant(profile, has_customization = True, has_chatbot = chatbot)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def test_patch_forbidden_without_benefit(self):
        response    =   self._client().patch(
            f'{STORES_URL}chatbot/', {'is_enabled': True}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_qa_pairs_are_sanitized(self):
        qa          =   [{'q': '¿Envían?', 'a': 'A todo el país'}] * 15 + [{'q': 'incompleta'}]
        response    =   self._client(chatbot = True).patch(
            f'{STORES_URL}chatbot/', {'is_enabled': True, 'qa': qa}, format = 'json')
        self.assertEqual(response.status_code, 200)
        pairs       =   response.data['chatbot']['qa']
        self.assertEqual(len(pairs), 12)
        self.assertTrue(all('a' in pair for pair in pairs))


class BlockModerationTests(TestCase):
    """Moderación: block/unblock solo staff; la web bloqueada da 404."""

    def _setup(self):
        user, profile   =   _make_user(verified = True)
        _grant(profile, has_public_link = True)
        store           =   Store.objects.create(user = profile, slug = 'mi-tienda')
        admin           =   User.objects.create_user(username = 'adminx', password = 'Xq7#mP2vL9bT', is_staff = True)
        admin_client    =   APIClient()
        admin_client.force_authenticate(user = admin)
        return user, store, admin_client

    def test_block_forbidden_for_non_staff(self):
        user, store, _  =   self._setup()
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(f'{STORES_URL}{store.pk}/block/', {}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_blocked_store_public_404(self):
        _, store, admin_client    =   self._setup()
        response        =   admin_client.post(f'{STORES_URL}{store.pk}/block/', {'reason': 'fraude'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        store.refresh_from_db()
        self.assertTrue(store.is_blocked)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 404)

    def test_unblock_restores_public(self):
        _, store, admin_client    =   self._setup()
        admin_client.post(f'{STORES_URL}{store.pk}/block/', {}, format = 'json')
        admin_client.post(f'{STORES_URL}{store.pk}/unblock/', {}, format = 'json')
        store.refresh_from_db()
        self.assertFalse(store.is_blocked)
        self.assertEqual(APIClient().get(f'{STORES_URL}public/mi-tienda/').status_code, 200)


class PremiumFieldsGatingTests(TestCase):
    """
    Campos premium del diseño: sin has_design_advanced se descartan del
    PATCH (no 403, no se guardan) — igual que show_location sin mapa.
    """

    def _client(self, **benefits):
        user, profile   =   _make_user(verified = True)
        _grant(profile, has_customization = True, **benefits)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def test_advanced_fields_discarded_without_premium(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'accent': 'rose', 'name_font': 'oswald'},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['accent'], 'indigo')
        self.assertEqual(custom['name_font'], 'inter')

    def test_show_location_discarded_without_map_benefit(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/', {'show_location': True}, format = 'json')
        self.assertFalse(response.data['customization']['show_location'])
