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
    StudioVersion,
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
        #El catálogo se apaga sacando 'catalog' de site_templates (el flag
        #show_catalog queda derivado: el serializer lo sincroniza y el
        #payload público lo expone desde el set efectivo).
        StoreCustomization.objects.create(
            store               =   store,
            show_catalog        =   show_catalog,
            site_templates      =   ['landing', 'catalog'] if show_catalog else ['landing'],
        )

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


class PublicEndpointsIgnoreStaleTokenTests(TestCase):
    """
    DRF autentica antes de evaluar permisos: con un Bearer vencido las
    acciones públicas (AllowAny) devolvían 401 y ensuciaban la consola de la
    web de tienda. Sin autenticadores en esas acciones el token rancio se
    ignora y el visitante anónimo lee igual.
    """

    def setUp(self):
        _, profile     =   _make_user(verified = True)
        _grant(profile, has_public_link = True, has_product_comments = True)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        StoreCustomization.objects.create(
            store               =   Store.objects.get(slug = 'mi-tienda'),
            show_catalog        =   True,
            show_reviews        =   True,
            show_contact        =   True,
            site_templates      =   ['landing', 'catalog'],
        )

    def _get(self, path):
        return APIClient().get(path, HTTP_AUTHORIZATION = 'Bearer token-vencido')

    def test_public_store_ok_with_stale_bearer(self):
        self.assertEqual(self._get(f'{STORES_URL}public/mi-tienda/').status_code, 200)

    def test_public_catalog_ok_with_stale_bearer(self):
        self.assertEqual(self._get(f'{STORES_URL}public/mi-tienda/catalog/').status_code, 200)

    def test_contact_captcha_ok_with_stale_bearer(self):
        self.assertEqual(self._get(f'{STORES_URL}public/mi-tienda/contact/captcha/').status_code, 200)

    def test_review_captcha_ok_with_stale_bearer(self):
        self.assertEqual(self._get(f'{STORES_URL}public/mi-tienda/reviews/captcha/').status_code, 200)

    def test_protected_endpoint_still_rejects_stale_bearer(self):
        #El corte de auth es solo para acciones públicas: el panel sigue 401.
        self.assertEqual(self._get(f'{STORES_URL}stats/').status_code, 401)


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
        response    =   self._client(premium = True).patch(f'{STORES_URL}customization/', {'template': 'cobre'}, format = 'json')
        self.assertEqual(response.data['customization']['template'], 'cobre')
        self.assertIn('cover', response.data['customization'])


class StoreTemplateGatingTests(TestCase):
    """
    Plantillas de portada por nivel de plan — catálogo de 6 (2 por
    nivel): Básico elige classic/duo, Estándar (has_design_plus) suma
    calma/vitrina y Premium (has_design_advanced) cobre/minimal. Los 20
    diseños retirados no están en allowed_templates: un PATCH con ellos
    se descarta igual que uno fuera del nivel, y la mig. 0049 remapeó las
    tiendas que los tenían al más cercano del mismo plan
    (TEMPLATE_RETIRED_MAP).
    """

    def setUp(self):
        # Mismo motivo que el resto de la suite: plan_benefits_of keyea por
        # PK y SQLite las reutiliza — sin limpiar, el plan de un test se
        # filtra al siguiente y el gating de plantillas miente.
        cache.clear()

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
        for key in ('classic', 'duo'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_basic_discards_plus_and_advanced_templates(self):
        client, _       =   self._client()
        for key in ('calma', 'vitrina', 'cobre', 'minimal'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_standard_picks_plus_templates(self):
        client, _       =   self._client('has_design_plus')
        for key in ('calma', 'vitrina'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_standard_discards_advanced_template(self):
        client, _       =   self._client('has_design_plus')
        for key in ('cobre', 'minimal'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_premium_picks_any_template(self):
        client, _       =   self._client('has_design_plus', 'has_design_advanced')
        for key in ('classic', 'duo', 'calma', 'vitrina', 'cobre', 'minimal'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.data['customization']['template'], key)

    def test_removed_template_is_discarded(self):
        #Una clave retirada del catálogo tampoco está en allowed_templates:
        #el PATCH la descarta como a un diseño fuera del nivel (las tiendas
        #que la tenían ya se remapearon en la mig. 0049).
        client, _       =   self._client('has_design_plus', 'has_design_advanced')
        for key in ('shop', 'street', 'aurora', 'diseno-borrado'):
            response    =   client.patch(f'{STORES_URL}customization/', {'template': key}, format = 'json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['customization']['template'], 'classic')

    def test_retired_map_stays_in_tier(self):
        #El mapa de la mig. 0049 solo puede mover una retirada a otra del
        #mismo nivel de plan — nunca cruza de tier ni apunta fuera del
        #catálogo habilitado.
        tiers       =   {}
        for key in StoreCustomization.TEMPLATE_BASE:     tiers[key] = 'base'
        for key in StoreCustomization.TEMPLATE_PLUS:     tiers[key] = 'plus'
        for key in StoreCustomization.TEMPLATE_ADVANCED: tiers[key] = 'advanced'
        old_tiers   =   {
            'perspective': 'base', 'bloque': 'base', 'riso': 'base',
            'street': 'plus', 'promo': 'plus', 'atelier': 'plus', 'circuit': 'plus',
            'mercado': 'plus', 'studio': 'plus', 'arena': 'plus',
            'terminal': 'advanced', 'lookbook': 'advanced', 'shop': 'advanced',
            'boutique': 'advanced', 'signature': 'advanced', 'aurora': 'advanced',
            'terra': 'advanced', 'lab': 'advanced', 'carta': 'advanced', 'proceso': 'advanced',
        }
        self.assertEqual(set(StoreCustomization.TEMPLATE_RETIRED_MAP), set(old_tiers))
        for old, new in StoreCustomization.TEMPLATE_RETIRED_MAP.items():
            self.assertEqual(tiers.get(new), old_tiers[old], f'{old} -> {new}')

    def test_public_payload_lists_allowed_templates(self):
        client, store   =   self._client('has_design_plus')
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertEqual(response.data['allowed_templates'], ['classic', 'duo', 'calma', 'vitrina'])

    def test_downgraded_template_is_not_persisted(self):
        #Con el plan vigente guarda 'vitrina'; si el beneficio se pierde, el
        #payload público ya no lo lista (el frontend fuerza 'classic').
        client, store   =   self._client('has_design_plus')
        client.patch(f'{STORES_URL}customization/', {'template': 'vitrina'}, format = 'json')
        PlanBenefit.objects.filter(benefit__code = 'has_design_plus').delete()
        response        =   APIClient().get(f'{STORES_URL}public/mi-tienda/')
        self.assertNotIn('vitrina', response.data['allowed_templates'])
        self.assertEqual(response.data['customization']['template'], 'vitrina')


class MarketingFieldsTests(TestCase):
    """
    Secciones de marketing de la portada ("Mi empresa"): las listas JSON se
    sanea en el serializer — filas incompletas fuera, textos recortados,
    iconos fuera del catálogo caen al default y section_order solo admite
    claves conocidas completándose con el orden base.
    """

    def setUp(self):
        # El cache de beneficios se keyea por PK y SQLite reutiliza PKs tras
        # el rollback: sin limpiar, el plan de un test se filtra al que corre
        # sin plan y el gate responde 200 en vez de 403.
        cache.clear()

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
        self.assertEqual(len(order), len(StoreCustomization.SECTION_ORDER))
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

    def test_announcements_are_sanitized(self):
        payload     =   [
            {'icon': 'truck', 'text': 'Envíos a todo el país'},
            {'icon': 'no-existe', 'text': 'Cuotas sin interés'},
            {'icon': 'star', 'text': ''},
            'basura',
        ]
        response    =   self._client().patch(f'{STORES_URL}customization/', {'announcements': payload}, format = 'json')
        ann         =   response.data['customization']['announcements']
        self.assertEqual(len(ann), 2)
        self.assertEqual(ann[0]['icon'], 'truck')
        self.assertEqual(ann[1]['icon'], 'megaphone')

    def test_video_url_normalizes_youtube_links(self):
        client      =   self._client()
        cases       =   [
            ('https://www.youtube.com/watch?v=abcDEF123_-', 'https://www.youtube-nocookie.com/embed/abcDEF123_-'),
            ('https://youtu.be/abcDEF123_-?t=30', 'https://www.youtube-nocookie.com/embed/abcDEF123_-'),
            ('https://www.youtube.com/shorts/abcDEF123_-', 'https://www.youtube-nocookie.com/embed/abcDEF123_-'),
            ('https://vimeo.com/123456789', 'https://player.vimeo.com/video/123456789'),
        ]
        for raw, embed in cases:
            response    =   client.patch(f'{STORES_URL}customization/', {'video_url': raw}, format = 'json')
            self.assertEqual(response.data['customization']['video_url'], embed)

    def test_video_url_rejects_other_hosts(self):
        client      =   self._client()
        for raw in ('https://evil.example.com/x', 'javascript:alert(1)', 'https://youtube.com.evil.com/watch?v=abcDEF123_-'):
            response    =   client.patch(f'{STORES_URL}customization/', {'video_url': raw}, format = 'json')
            self.assertEqual(response.status_code, 400, raw)

    def test_extras_are_stored_and_bounded(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'catalog_note': 'Envíos a todo el país', 'footer_text': 'Tienda familiar desde 1998'},
            format = 'json',
        )
        custom      =   response.data['customization']
        self.assertEqual(custom['catalog_note'], 'Envíos a todo el país')
        self.assertEqual(custom['footer_text'], 'Tienda familiar desde 1998')
        too_long    =   client.patch(f'{STORES_URL}customization/', {'footer_text': 'x' * 200}, format = 'json')
        self.assertEqual(too_long.status_code, 400)


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

    def setUp(self):
        # El dedupe de visitas usa cache con hash(IP+UA+fecha): en tests la IP
        # es siempre 127.0.0.1, así que sin limpiar el cache la segunda visita
        # se descarta como duplicada del test anterior y no se crea la fila.
        cache.clear()

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

    def setUp(self):
        # plan_benefits_of keyea por PK y SQLite las reutiliza tras el
        # rollback: sin limpiar, el premium de un test se filtra al otro.
        cache.clear()

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

    def test_popular_font_saved_with_premium(self):
        # El selector del panel solo ofrece las fuentes populares del
        # mercado; el backend acepta el superset de FONT_CHOICES (roboto
        # entró al catálogo con la remisión del picker).
        client      =   self._client(has_design_advanced = True)
        response    =   client.patch(
            f'{STORES_URL}customization/', {'name_font': 'roboto'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['name_font'], 'roboto')

    def test_show_location_discarded_without_map_benefit(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/', {'show_location': True}, format = 'json')
        self.assertFalse(response.data['customization']['show_location'])

class LayoutConfigTests(TestCase):
    """
    Editor de bloques (Diseño web → Bloques): `layout_config` se valida
    contra el catálogo cerrado TEMPLATE_BLOCKS — superficies/ids/variantes/
    props desconocidas se descartan, los bloques premium se quitan sin
    has_design_advanced, los locked quedan siempre prendidos y los textos
    de props se sanea a texto plano acotado. Una config inválida deja el
    campo en {} y la web pública cae al layout por defecto de la plantilla.
    """

    def setUp(self):
        # plan_benefits_of keyea por PK y SQLite las reutiliza tras el
        # rollback de cada TestCase — sin limpiar, el premium de un test se
        # filtra al siguiente y el descarte de bloques miente.
        cache.clear()

    def _client(self, **benefits):
        user, profile   =   _make_user(verified = True)
        _grant(profile, has_customization = True, **benefits)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def test_layout_requires_customization_benefit(self):
        user, profile   =   _make_user(verified = True)
        _grant(profile)
        Store.objects.create(user = profile, slug = 'mi-tienda')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 403)

    def test_valid_layout_is_saved_normalized(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {
                'landing': {'blocks': [
                    {'id': 'about', 'enabled': True, 'order': 1, 'props': {'title': 'Nuestra historia'}},
                    {'id': 'hero', 'enabled': True, 'order': 0},
                    {'id': 'contact', 'enabled': False, 'order': 2},
                ]},
                'catalog': {'blocks': [
                    {'id': 'grid', 'enabled': True},
                    {'id': 'filters', 'enabled': True},
                ]},
            }},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        config      =   response.data['customization']['layout_config']
        landing     =   config['landing']['blocks']
        #El order declarado reordena la lista y se renumera secuencial.
        self.assertEqual([b['id'] for b in landing], ['hero', 'about', 'contact'])
        self.assertEqual([b['order'] for b in landing], [0, 1, 2])
        self.assertEqual(landing[1]['props'], {'title': 'Nuestra historia'})
        self.assertFalse(landing[2]['enabled'])

    def test_unknown_blocks_surfaces_and_variants_are_dropped(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {
                'landing': {'blocks': [
                    {'id': 'hero', 'enabled': True, 'variant': 'full'},
                    {'id': 'no-existe', 'enabled': True},
                    {'id': 'hero', 'enabled': True},
                    {'id': 'stats', 'enabled': True, 'variant': 'inventada'},
                    {'id': 'announcements', 'enabled': True, 'variant': 'static'},
                    'basura', 42, None,
                ]},
                'seccion-inventada': {'blocks': [{'id': 'hero'}]},
                'services': 'no-es-dict',
            }},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        config      =   response.data['customization']['layout_config']
        self.assertNotIn('seccion-inventada', config)
        self.assertNotIn('services', config)
        blocks      =   config['landing']['blocks']
        self.assertEqual([b['id'] for b in blocks], ['hero', 'stats', 'announcements'])
        #variant default no se guarda; inventada se descarta al default.
        self.assertNotIn('variant', blocks[0])
        self.assertNotIn('variant', blocks[1])
        self.assertEqual(blocks[2]['variant'], 'static')

    def test_premium_block_discarded_without_advanced(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'catalog': {'blocks': [
                {'id': 'banner', 'enabled': True},
                {'id': 'filters', 'enabled': True},
            ]}}},
            format = 'json',
        )
        blocks      =   response.data['customization']['layout_config']['catalog']['blocks']
        self.assertEqual([b['id'] for b in blocks], ['filters'])

    def test_premium_block_kept_with_advanced(self):
        client      =   self._client(has_design_advanced = True)
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'catalog': {'blocks': [
                {'id': 'banner', 'enabled': True},
                {'id': 'filters', 'enabled': True},
            ]}}},
            format = 'json',
        )
        blocks      =   response.data['customization']['layout_config']['catalog']['blocks']
        self.assertEqual([b['id'] for b in blocks], ['banner', 'filters'])

    def test_locked_block_cannot_be_disabled(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'catalog': {'blocks': [
                {'id': 'grid', 'enabled': False},
                {'id': 'filters', 'enabled': False},
            ]}}},
            format = 'json',
        )
        blocks      =   response.data['customization']['layout_config']['catalog']['blocks']
        self.assertTrue(blocks[0]['enabled'])
        self.assertFalse(blocks[1]['enabled'])

    def test_props_are_sanitized_and_truncated(self):
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'landing': {'blocks': [
                {'id': 'about', 'enabled': True, 'props': {
                    'title': '<b>Nuestra</b> historia ' + 'x' * 200,
                    'inventada': 'se descarta',
                    'vacia': '   ',
                }},
            ]}}},
            format = 'json',
        )
        block       =   response.data['customization']['layout_config']['landing']['blocks'][0]
        self.assertEqual(set(block['props'].keys()), {'title'})
        self.assertEqual(block['props']['title'], 'Nuestra historia ' + 'x' * (80 - len('Nuestra historia ')))
        self.assertNotIn('<', block['props']['title'])

    def test_invalid_config_falls_back_to_empty(self):
        client      =   self._client()
        for bad in ('texto', [1, 2], 42):
            response    =   client.patch(
                f'{STORES_URL}customization/', {'layout_config': bad}, format = 'json')
            self.assertEqual(response.status_code, 400)
        #Una config con superficies inválidas queda en {} (fail-safe:
        #la web cae al layout por defecto, no guarda basura).
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'landing': 'no-dict', 'pepito': {'blocks': []}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['layout_config'], {})

    def test_invalid_config_returns_readable_message(self):
        #El editor de bloques muestra el 400 tal cual llega — tiene que ser
        #un mensaje entendible en español, no un dump del serializer.
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/', {'layout_config': 'texto'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('objeto', str(response.data['layout_config']))

    def test_oversized_config_rejected(self):
        #Los bytes se cuentan sobre el payload crudo (antes de sanear):
        #un prop gigante pasa el tope aunque el saneo lo truncaría a 80.
        client      =   self._client()
        response    =   client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'landing': {'blocks': [
                {'id': 'about', 'enabled': True, 'props': {'title': 'x' * 9000}},
            ]}}},
            format = 'json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('grande', str(response.data['layout_config']))

    def test_layout_survives_template_switch(self):
        #La config es por superficie, no por plantilla: cambiar de diseño
        #conserva los bloques guardados (el renderer usa los que la
        #plantilla destino soporta).
        client      =   self._client()
        client.patch(
            f'{STORES_URL}customization/',
            {'layout_config': {'landing': {'blocks': [
                {'id': 'contact', 'enabled': True, 'order': 0},
                {'id': 'hero', 'enabled': True, 'order': 1},
            ]}}},
            format = 'json',
        )
        response    =   client.patch(
            f'{STORES_URL}customization/', {'template': 'duo'}, format = 'json')
        config      =   response.data['customization']['layout_config']
        self.assertEqual([b['id'] for b in config['landing']['blocks']], ['contact', 'hero'])


class IdentityFieldsTests(TestCase):
    """
    Identidad visual Premium (accent_custom, logo_scale/logo_mode, overlay y
    punto focal de la portada): validación de formato y rango, descarte sin
    has_design_advanced y aislamiento entre clientes.
    """

    def setUp(self):
        cache.clear()

    def _client(self, username = 'duenio', **benefits):
        user, profile   =   _make_named_user(username)
        _grant(profile, has_customization = True, has_public_link = True, **benefits)
        Store.objects.create(user = profile, slug = f'tienda-{username}')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def _patch(self, client, payload):
        return client.patch(f'{STORES_URL}customization/', payload, format = 'json')

    def test_defaults_do_not_change_existing_stores(self):
        client      =   self._client(has_design_advanced = True)
        custom      =   client.get(f'{STORES_URL}customization/').data
        self.assertEqual(custom['accent_custom'], '')
        self.assertEqual(custom['logo_scale'], 'm')
        self.assertEqual(custom['logo_mode'], 'logo_name')
        self.assertEqual(custom['mono_style'], 'accent')
        self.assertEqual(custom['cover_overlay'], 0)
        self.assertEqual((custom['cover_focus_x'], custom['cover_focus_y']), (50, 50))

    def test_valid_values_saved_with_premium(self):
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {
            'accent_custom': '#1A7F5A', 'logo_scale': 'l', 'logo_mode': 'logo_only',
            'mono_style': 'neutral', 'cover_overlay': 40, 'cover_focus_x': 20, 'cover_focus_y': 80,
        })
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['accent_custom'], '#1a7f5a')
        self.assertEqual((custom['logo_scale'], custom['logo_mode'], custom['mono_style']), ('l', 'logo_only', 'neutral'))
        self.assertEqual((custom['cover_overlay'], custom['cover_focus_x'], custom['cover_focus_y']), (40, 20, 80))

    def test_invalid_hex_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for bad in ('red', '#12345', '#1234567', '#gggggg', '123456', 'javascript:alert(1)'):
            response    =   self._patch(client, {'accent_custom': bad})
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('accent_custom', response.data)

    def test_empty_hex_clears_custom_accent(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'accent_custom': '#1a7f5a'})
        response    =   self._patch(client, {'accent_custom': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['accent_custom'], '')

    def test_overlay_and_focus_ranges(self):
        client      =   self._client(has_design_advanced = True)
        for payload in ({'cover_overlay': 81}, {'cover_overlay': -1}, {'cover_focus_x': 101},
                        {'cover_focus_y': -5}, {'cover_overlay': 'mucho'}):
            response    =   self._patch(client, payload)
            self.assertEqual(response.status_code, 400, payload)
        for payload in ({'cover_overlay': 0}, {'cover_overlay': 80}, {'cover_focus_x': 0}, {'cover_focus_y': 100}):
            self.assertEqual(self._patch(client, payload).status_code, 200, payload)

    def test_invalid_choices_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for payload in ({'logo_scale': 'xl'}, {'logo_mode': 'otro'}, {'mono_style': 'rojo'}):
            self.assertEqual(self._patch(client, payload).status_code, 400, payload)

    def test_discarded_without_premium(self):
        client      =   self._client()
        response    =   self._patch(client, {
            'accent_custom': '#1a7f5a', 'logo_scale': 'l', 'logo_mode': 'logo_only',
            'mono_style': 'neutral', 'cover_overlay': 40, 'cover_focus_x': 20, 'cover_focus_y': 80,
        })
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['accent_custom'], '')
        self.assertEqual((custom['logo_scale'], custom['logo_mode'], custom['mono_style']), ('m', 'logo_name', 'accent'))
        self.assertEqual((custom['cover_overlay'], custom['cover_focus_x'], custom['cover_focus_y']), (0, 50, 50))

    def test_discarded_even_if_value_is_invalid_without_premium(self):
        client      =   self._client()
        self.assertEqual(self._patch(client, {'accent_custom': 'no-es-hex', 'cover_overlay': 999}).status_code, 200)

    def test_public_ignores_values_after_downgrade(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'accent_custom': '#1a7f5a', 'cover_overlay': 40})
        self.assertEqual(APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']['accent_custom'], '#1a7f5a')
        PlanBenefit.objects.filter(benefit__code = 'has_design_advanced').delete()
        cache.clear()
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        self.assertEqual(public['accent_custom'], '')
        self.assertEqual(public['cover_overlay'], 0)

    def test_public_exposes_new_fields(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'logo_scale': 's', 'cover_focus_x': 10})
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        for key in ('accent_custom', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay', 'cover_focus_x', 'cover_focus_y'):
            self.assertIn(key, public)
        self.assertEqual((public['logo_scale'], public['cover_focus_x']), ('s', 10))

    def test_client_cannot_edit_another_customization(self):
        owner       =   self._client('duenio', has_design_advanced = True)
        other       =   self._client('intruso', has_design_advanced = True)
        self._patch(owner, {'accent_custom': '#112233'})
        self._patch(other, {'accent_custom': '#aabbcc', 'cover_overlay': 70})
        mine        =   StoreCustomization.objects.get(store__slug = 'tienda-duenio')
        theirs      =   StoreCustomization.objects.get(store__slug = 'tienda-intruso')
        self.assertEqual((mine.accent_custom, mine.cover_overlay), ('#112233', 0))
        self.assertEqual((theirs.accent_custom, theirs.cover_overlay), ('#aabbcc', 70))

    def test_anonymous_cannot_patch(self):
        self._client(has_design_advanced = True)
        response    =   APIClient().patch(f'{STORES_URL}customization/', {'accent_custom': '#112233'}, format = 'json')
        self.assertIn(response.status_code, (401, 403))


class SiteThemeTests(TestCase):
    """
    Tema visual del Studio (`site_theme`): el backend aplica el contrato
    cerrado de la Fase 0 (secciones/claves/enums, hex, rangos, 4 KB,
    fondos solo con imágenes propias), descarta por plan como `accent`
    (subset plus: radius/density de containers) y la web pública expone
    el tema EFECTIVO del plan vigente.
    """

    def setUp(self):
        # plan_benefits_of keyea por PK y SQLite las reutiliza tras el
        # rollback: sin limpiar, el plan de un test se filtra al siguiente.
        cache.clear()

    def _client(self, username = 'duenio', **benefits):
        user, profile   =   _make_named_user(username)
        _grant(profile, has_customization = True, has_public_link = True, **benefits)
        Store.objects.create(user = profile, slug = f'tienda-{username}')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def _patch(self, client, payload):
        return client.patch(f'{STORES_URL}customization/', payload, format = 'json')

    def _public_theme(self, slug):
        return APIClient().get(f'{STORES_URL}public/{slug}/').data['customization']['site_theme']

    def test_full_theme_saved_normalized_with_advanced(self):
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {'site_theme': {
            'palette': {'primary': '#FFF', 'danger': 'ff0000'},
            'containers': {'radius': 'pill', 'shadow': 'deep', 'border': 'bold', 'density': 'compact', 'surface': 'glass'},
            'typography': {'heading': 'oswald', 'body': 'Georgia, serif', 'scale': 'editorial', 'weightHeading': 700, 'letterSpacing': '-0.02em'},
            'buttons': {'shape': 'square', 'style': 'outline', 'size': 'lg'},
            'background': {'type': 'gradient', 'value': 'linear-gradient(135deg, #fff 0%, #000 100%)', 'overlay': 'soft'},
            'motion': {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'bold'},
            'mobile': {'nav': 'drawer', 'gridCols': 2, 'cardStyle': 'overlay', 'stickyCta': True, 'heroHeight': 'tall'},
        }})
        self.assertEqual(response.status_code, 200)
        theme       =   response.data['customization']['site_theme']
        self.assertEqual(theme['palette'], {'primary': '#ffffff', 'danger': '#ff0000'})
        self.assertEqual(theme['containers'], {'radius': 'pill', 'shadow': 'deep', 'border': 'bold', 'density': 'compact', 'surface': 'glass'})
        self.assertEqual(theme['typography']['weightHeading'], 700)
        self.assertEqual(theme['buttons'], {'shape': 'square', 'style': 'outline', 'size': 'lg'})
        self.assertEqual(theme['background']['type'], 'gradient')
        self.assertEqual(theme['mobile'], {'nav': 'drawer', 'gridCols': 2, 'cardStyle': 'overlay', 'stickyCta': True, 'heroHeight': 'tall'})

    def test_store_without_theme_looks_identical(self):
        #Una tienda sin site_theme se ve idéntica a hoy: {} guardado y
        #{} en el payload público (el frontend resuelve los defaults).
        client      =   self._client(has_design_advanced = True)
        self.assertEqual(client.get(f'{STORES_URL}customization/').data['site_theme'], {})
        self.assertEqual(self._public_theme('tienda-duenio'), {})

    def test_invalid_hex_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for bad in ('rojo', '#12345', '#1234567', '#gggggg', 'rgb(1,2,3)', 'javascript:alert(1)'):
            response    =   self._patch(client, {'site_theme': {'palette': {'primary': bad}}})
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('site_theme', response.data)

    def test_invalid_choices_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for section, key, bad in (
            ('containers', 'radius', 'enorme'),
            ('containers', 'shadow', 'infinita'),
            ('containers', 'border', 'gruesa'),
            ('containers', 'density', 'apretada'),
            ('containers', 'surface', 'espejo'),
            ('typography', 'scale', 'gigante'),
            ('buttons', 'shape', 'hexagonal'),
            ('buttons', 'style', 'neon'),
            ('buttons', 'size', 'xxl'),
            ('background', 'type', 'video'),
            ('background', 'overlay', 'fuerte'),
            ('motion', 'reveal', 'zoom'),
            ('motion', 'hover', 'spin'),
            ('motion', 'intensity', 'brutal'),
            ('mobile', 'nav', 'lateral'),
            ('mobile', 'cardStyle', 'gigante'),
            ('mobile', 'heroHeight', 'inmensa'),
            ('style', 'palette', 'neon'),
        ):
            response    =   self._patch(client, {'site_theme': {section: {key: bad}}})
            self.assertEqual(response.status_code, 400, (section, key, bad))

    def test_unknown_keys_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for payload in (
            {'paleta': {'primary': '#112233'}},
            {'custom_css': 'body{color:red}'},
            {'containers': {'inventada': 'x'}},
            {'palette': {'primario': '#112233'}},
        ):
            response    =   self._patch(client, {'site_theme': payload})
            self.assertEqual(response.status_code, 400, payload)

    def test_not_a_dict_rejected(self):
        client      =   self._client(has_design_advanced = True)
        for bad in ('texto', [1, 2], 42):
            response    =   self._patch(client, {'site_theme': bad})
            self.assertEqual(response.status_code, 400, bad)

    def test_oversized_theme_rejected(self):
        #Los bytes se cuentan sobre el JSON crudo (SITE_THEME_MAX_BYTES, 12 KB
        #desde la v2/v4): un valor gigante no pasa aunque la clave sea válida.
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {'site_theme': {
            'containers': {'radius': 'pill'},
            'palette': {'primary': '#112233', 'text': '#' + 'f' * 20000},
        }})
        self.assertEqual(response.status_code, 400)
        self.assertIn('grande', str(response.data['site_theme']))

    def test_ranges_and_types(self):
        client      =   self._client(has_design_advanced = True)
        for payload in (
            {'typography': {'weightHeading': 99}},
            {'typography': {'weightHeading': 901}},
            {'typography': {'weightHeading': 'ocho'}},
            {'typography': {'weightHeading': True}},
            {'mobile': {'gridCols': 3}},
            {'mobile': {'gridCols': '2'}},
            {'mobile': {'gridCols': True}},
            {'mobile': {'stickyCta': 'si'}},
            {'mobile': {'stickyCta': 1}},
            {'typography': {'letterSpacing': 'ancho'}},
            {'typography': {'heading': 'Inter; color: red'}},
            {'typography': {'heading': '" onmouseover="alert(1)'}},
            {'typography': {'body': 'url(https://evil.com/a.css)'}},
        ):
            response    =   self._patch(client, {'site_theme': payload})
            self.assertEqual(response.status_code, 400, payload)

    def test_font_stack_and_tracking_accepted(self):
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {'site_theme': {'typography': {
            'heading': 'Playfair Display, serif', 'body': 'inter', 'letterSpacing': '-0.05em',
        }}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['site_theme']['typography']['heading'], 'Playfair Display, serif')

    def test_background_value_safe_css_only(self):
        client      =   self._client(has_design_advanced = True)
        #URLs ajenas, javascript:, HTML y CSS libre: rechazados siempre.
        for bad in (
            'https://evil.com/fondo.png',
            'javascript:alert(1)',
            'url(https://evil.com/a.png)',
            'url(/media/x.png)',
            'body { background: red }',
            '"><script>alert(1)</script>',
            'expression(alert(1))',
        ):
            response    =   self._patch(client, {'site_theme': {'background': {'type': 'image', 'value': bad}}})
            self.assertEqual(response.status_code, 400, bad)
        #Degradado propio del catálogo: aceptado.
        response    =   self._patch(client, {'site_theme': {
            'background': {'type': 'mesh', 'value': 'radial-gradient(circle at 20% 30%, #fff 0%, #000 100%)'},
        }})
        self.assertEqual(response.status_code, 200)

    def test_background_accepts_own_image_url(self):
        #Solo las imágenes PROPIAS de la tienda (logo, portada, carrusel,
        #galería) valen como fondo image — las de otro store también 400.
        client      =   self._client(has_design_advanced = True)
        store       =   Store.objects.get(slug = 'tienda-duenio')
        StoreGalleryImage.objects.create(store = store, image_key = 'stores/1/gallery/fondo.webp')
        ajena       =   StoreGalleryImage.objects.create(store = Store.objects.create(user = _make_named_user('ajeno')[1], slug = 'tienda-ajena'), image_key = 'stores/2/gallery/fondo.webp')
        with patch.object(storage, 'object_url', side_effect = lambda key: f'https://cdn.test/{key}'):
            response    =   self._patch(client, {'site_theme': {
                'background': {'type': 'image', 'value': 'https://cdn.test/stores/1/gallery/fondo.webp'},
            }})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['customization']['site_theme']['background']['value'], 'https://cdn.test/stores/1/gallery/fondo.webp')
            response    =   self._patch(client, {'site_theme': {
                'background': {'type': 'image', 'value': f'https://cdn.test/{ajena.image_key}'},
            }})
            self.assertEqual(response.status_code, 400)

    def _style_colors(self, **over):
        #Set completo que pasa AA en ambos modos (mismos valores que deriva
        #el contrato para un preset claro).
        light = {
            'fonts': {'heading': '#0f172a', 'body': '#0f172a', 'muted': '#5b6678', 'link': '#4f46e5'},
            'containers': {'bg': '#f4f6fb', 'surface': '#ffffff', 'border': '#e2e6f0', 'onSurface': '#0f172a'},
        }
        dark = {
            'fonts': {'heading': '#f1f5f9', 'body': '#f1f5f9', 'muted': '#94a3b8', 'link': '#a5b4fc'},
            'containers': {'bg': '#0b1220', 'surface': '#111a2c', 'border': '#243049', 'onSurface': '#f1f5f9'},
        }
        light.update(over.get('light') or {})
        return {'light': light, 'dark': dark}

    def test_basic_saves_only_style_and_colors(self):
        #Plan Básico (has_customization): persiste el estilo elegido y su
        #juego de colores; paleta/tipografía/fondo/movimiento se descartan.
        client      =   self._client()
        response    =   self._patch(client, {'site_theme': {
            'style'         :   {'id': 'corporativo', 'palette': 'warm'},
            'styleColors'   :   self._style_colors(),
            'palette'       :   {'primary': '#112233'},
            'typography'    :   {'heading': 'oswald'},
            'background'    :   {'type': 'gradient', 'value': 'linear-gradient(#fff, #000)'},
            'motion'        :   {'reveal': 'stagger'},
        }})
        self.assertEqual(response.status_code, 200)
        theme       =   response.data['customization']['site_theme']
        self.assertEqual(set(theme), {'style', 'styleColors'})
        self.assertEqual(theme['style'], {'id': 'corporativo', 'palette': 'warm'})
        self.assertEqual(theme['styleColors']['light']['containers']['surface'], '#ffffff')

    def test_basic_style_id_above_plan_is_dropped(self):
        #bento usa la plantilla vitrina (Estándar): el id se descarta pero
        #los colores del estilo sí se guardan.
        client      =   self._client()
        response    =   self._patch(client, {'site_theme': {
            'style': {'id': 'bento'}, 'styleColors': self._style_colors(),
        }})
        self.assertEqual(response.status_code, 200)
        theme       =   response.data['customization']['site_theme']
        self.assertNotIn('style', theme)
        self.assertIn('styleColors', theme)

    def test_basic_advanced_sections_discarded_or_rejected(self):
        #Las secciones avanzadas se descartan en silencio; una sección
        #desconocida o un color inválido del set sí son 400.
        client      =   self._client()
        response    =   self._patch(client, {'site_theme': {'typography': {'heading': 'oswald'}}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['site_theme'], {})
        response    =   self._patch(client, {'site_theme': {'hack': {'<': 'script'}}})
        self.assertEqual(response.status_code, 400)
        bad         =   self._style_colors()
        bad['light']['fonts']['link'] = 'rojo'
        response    =   self._patch(client, {'site_theme': {'styleColors': bad}})
        self.assertEqual(response.status_code, 400)

    def test_basic_style_colors_need_contrast(self):
        client      =   self._client()
        bad         =   self._style_colors()
        bad['light']['fonts']['heading'] = '#fefefe'   # casi blanco sobre blanco
        response    =   self._patch(client, {'site_theme': {'styleColors': bad}})
        self.assertEqual(response.status_code, 400)
        self.assertIn('contraste', str(response.data['site_theme']))

    def test_public_exposes_basic_style(self):
        client      =   self._client()
        self._patch(client, {'site_theme': {
            'style': {'id': 'corporativo'}, 'styleColors': self._style_colors(),
        }})
        theme       =   self._public_theme('tienda-duenio')
        self.assertEqual(theme['style'], {'id': 'corporativo'})
        self.assertIn('styleColors', theme)

    def test_plus_keeps_only_basic_subset(self):
        #has_design_plus (Estándar): solo radius/density de containers; el
        #resto del tema se descarta en silencio como los campos premium.
        client      =   self._client(has_design_plus = True)
        response    =   self._patch(client, {'site_theme': {
            'palette': {'primary': '#112233'},
            'containers': {'radius': 'pill', 'shadow': 'deep', 'density': 'compact'},
            'buttons': {'shape': 'square'},
            'mobile': {'nav': 'drawer'},
        }})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['customization']['site_theme'],
            {'containers': {'radius': 'pill', 'density': 'compact'}},
        )

    def test_plus_still_validates_the_subset(self):
        #La clave admitida se valida igual (radius 'enorme' -> 400); una
        #clave gated con valor inválido se descarta antes de validar (200).
        client      =   self._client(has_design_plus = True)
        response    =   self._patch(client, {'site_theme': {'containers': {'radius': 'enorme'}}})
        self.assertEqual(response.status_code, 400)
        response    =   self._patch(client, {'site_theme': {'containers': {'shadow': 'no-existe'}, 'palette': 'basura'}})
        self.assertEqual(response.status_code, 200)

    def test_saved_premium_values_survive_downgrade(self):
        #Baja a Estándar: lo guardado premium se conserva (como accent) y
        #el PATCH de la básica mergea sin pisarlo — reaparece al volver.
        client      =   self._client(has_design_plus = True, has_design_advanced = True)
        self._patch(client, {'site_theme': {'palette': {'primary': '#112233'}, 'containers': {'radius': 'pill'}}})
        PlanBenefit.objects.filter(benefit__code = 'has_design_advanced').delete()
        cache.clear()
        response    =   self._patch(client, {'site_theme': {'containers': {'radius': 'sm', 'density': 'compact'}}})
        theme       =   response.data['customization']['site_theme']
        self.assertEqual(theme['palette'], {'primary': '#112233'})
        self.assertEqual(theme['containers'], {'radius': 'sm', 'density': 'compact'})

    def test_public_exposes_effective_theme_by_plan(self):
        client      =   self._client(has_design_plus = True, has_design_advanced = True)
        self._patch(client, {'site_theme': {
            'palette': {'primary': '#112233'},
            'containers': {'radius': 'pill', 'shadow': 'deep', 'density': 'compact'},
        }})
        self.assertEqual(self._public_theme('tienda-duenio'), {
            'palette': {'primary': '#112233'},
            'containers': {'radius': 'pill', 'shadow': 'deep', 'density': 'compact'},
        })
        #Baja a Estándar: la web solo ve el subconjunto plus guardado.
        PlanBenefit.objects.filter(benefit__code = 'has_design_advanced').delete()
        cache.clear()
        self.assertEqual(self._public_theme('tienda-duenio'), {'containers': {'radius': 'pill', 'density': 'compact'}})
        #Sin beneficios de diseño: {} — el look vuelve a los defaults.
        PlanBenefit.objects.filter(benefit__code = 'has_design_plus').delete()
        cache.clear()
        self.assertEqual(self._public_theme('tienda-duenio'), {})

    def test_client_cannot_edit_another_theme(self):
        owner       =   self._client('duenio', has_design_advanced = True)
        other       =   self._client('intruso', has_design_advanced = True)
        self._patch(owner, {'site_theme': {'palette': {'primary': '#112233'}}})
        self._patch(other, {'site_theme': {'palette': {'primary': '#aabbcc'}, 'containers': {'radius': 'none'}}})
        mine        =   StoreCustomization.objects.get(store__slug = 'tienda-duenio')
        theirs      =   StoreCustomization.objects.get(store__slug = 'tienda-intruso')
        self.assertEqual(mine.site_theme, {'palette': {'primary': '#112233'}})
        self.assertEqual(theirs.site_theme['palette'], {'primary': '#aabbcc'})

    def test_anonymous_cannot_patch_theme(self):
        self._client(has_design_advanced = True)
        response    =   APIClient().patch(f'{STORES_URL}customization/', {'site_theme': {}}, format = 'json')
        self.assertIn(response.status_code, (401, 403))


class StudioDraftPublishTests(TestCase):
    """
    Flujo borrador/publicado del Studio: los campos *_draft editan sin
    tocar la web (el draft es invisible en el payload público), publish
    aplica el draft y guarda la versión (últimas 10), discard vuelve al
    publicado y restore recupera un snapshot — todo con has_customization
    y aislado por tienda.
    """

    def setUp(self):
        cache.clear()

    def _client(self, username = 'duenio', **benefits):
        user, profile   =   _make_named_user(username)
        _grant(profile, has_customization = True, has_public_link = True, **benefits)
        Store.objects.create(user = profile, slug = f'tienda-{username}')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client

    def _patch(self, client, payload):
        return client.patch(f'{STORES_URL}customization/', payload, format = 'json')

    def _custom(self, slug = 'tienda-duenio'):
        return StoreCustomization.objects.get(store__slug = slug)

    def test_patch_theme_publishes_and_syncs_draft(self):
        #Guardar el publicado también alinea el borrador: el editor actual
        #deja la web al día en el mismo paso (has_unpublished queda False).
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {'site_theme': {'palette': {'primary': '#112233'}}})
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(custom['site_theme_draft'], custom['site_theme'])
        self.assertFalse(custom['has_unpublished'])

    def test_draft_theme_not_visible_in_public(self):
        #El draft se guarda aparte: la web pública lee solo lo publicado
        #y nunca expone los campos *_draft ni el estado de sincronía.
        client      =   self._client(has_design_advanced = True)
        response    =   self._patch(client, {'site_theme_draft': {'palette': {'primary': '#112233'}}})
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {})
        self.assertEqual(custom['site_theme_draft'], {'palette': {'primary': '#112233'}})
        self.assertTrue(custom['has_unpublished'])
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        self.assertEqual(public['site_theme'], {})
        self.assertNotIn('site_theme_draft', public)
        self.assertNotIn('layout_config_draft', public)
        self.assertNotIn('has_unpublished', public)

    def test_draft_layout_not_visible_in_public(self):
        client      =   self._client()
        response    =   self._patch(client, {'layout_config_draft': {
            'landing': {'blocks': [{'id': 'hero', 'enabled': False, 'order': 0}]},
        }})
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['layout_config'], {})
        self.assertEqual(custom['layout_config_draft']['landing']['blocks'][0]['enabled'], False)
        self.assertTrue(custom['has_unpublished'])
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        self.assertEqual(public['layout_config'], {})

    def test_draft_layout_keeps_premium_gate(self):
        #El borrador corre la misma whitelist que el publicado: el bloque
        #premium se descarta sin has_design_advanced aunque sea draft.
        client      =   self._client()
        response    =   self._patch(client, {'layout_config_draft': {
            'catalog': {'blocks': [{'id': 'banner'}, {'id': 'filters'}]},
        }})
        blocks      =   response.data['customization']['layout_config_draft']['catalog']['blocks']
        self.assertEqual([b['id'] for b in blocks], ['filters'])

    def test_publish_applies_draft_and_creates_version(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {
            'site_theme_draft'      :   {'palette': {'primary': '#112233'}},
            'layout_config_draft'   :   {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
        })
        response    =   client.post(f'{STORES_URL}customization/publish/', {'note': 'primer look'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(custom['layout_config']['landing']['blocks'][0]['id'], 'hero')
        self.assertFalse(custom['has_unpublished'])
        version     =   StudioVersion.objects.get()
        self.assertEqual(version.note, 'primer look')
        self.assertEqual(version.snapshot['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(version.snapshot['template'], custom['template'])
        #La web pública ya muestra lo publicado.
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        self.assertEqual(public['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(public['layout_config']['landing']['blocks'][0]['id'], 'hero')

    def test_discard_reverts_draft_to_published(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'site_theme': {'palette': {'primary': '#112233'}}})
        self._patch(client, {'site_theme_draft': {'palette': {'primary': '#aabbcc'}, 'buttons': {'shape': 'square'}}})
        response    =   client.post(f'{STORES_URL}customization/discard/')
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(custom['site_theme_draft'], custom['site_theme'])
        self.assertFalse(custom['has_unpublished'])
        #Nada quedó publicado de más ni en la web.
        self.assertEqual(self._custom().site_theme, {'palette': {'primary': '#112233'}})

    def test_versions_listed_for_owner(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'site_theme_draft': {'palette': {'primary': '#112233'}}})
        client.post(f'{STORES_URL}customization/publish/', {'note': 'v1'}, format = 'json')
        versions    =   client.get(f'{STORES_URL}customization/versions/').data
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]['note'], 'v1')
        self.assertEqual(versions[0]['snapshot']['site_theme'], {'palette': {'primary': '#112233'}})

    def test_versions_keep_last_ten(self):
        client      =   self._client(has_design_advanced = True)
        for index in range(12):
            client.post(f'{STORES_URL}customization/publish/', {'note': f'v{index}'}, format = 'json')
        self.assertEqual(StudioVersion.objects.count(), StudioVersion.MAX_PER_STORE)
        versions    =   client.get(f'{STORES_URL}customization/versions/').data
        self.assertEqual(len(versions), 10)
        #Quedan las 10 más nuevas (v11 primero, v2 último): v0/v1 se podaron.
        self.assertEqual(versions[0]['note'], 'v11')
        self.assertEqual(versions[-1]['note'], 'v2')

    def test_restore_applies_snapshot(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'site_theme_draft': {'palette': {'primary': '#112233'}}})
        client.post(f'{STORES_URL}customization/publish/', {'note': 'look azul'}, format = 'json')
        version     =   StudioVersion.objects.get()
        self._patch(client, {'site_theme': {'palette': {'primary': '#aabbcc'}, 'mobile': {'nav': 'drawer'}}})
        response    =   client.post(f'{STORES_URL}customization/restore/{version.pk}/')
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(custom['site_theme_draft'], custom['site_theme'])
        self.assertFalse(custom['has_unpublished'])
        #La web vuelve a mostrar la versión restaurada.
        self.assertEqual(APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']['site_theme'], {'palette': {'primary': '#112233'}})

    def test_restore_skips_template_outside_plan(self):
        #Una baja de plan no re-habilita plantillas premium al restaurar:
        #solo se aplica si sigue en la whitelist del plan vigente.
        client      =   self._client()
        store       =   Store.objects.get(slug = 'tienda-duenio')
        version     =   StudioVersion.objects.create(
            store       =   store,
            snapshot    =   {'template': 'cobre', 'site_theme': {'palette': {'primary': '#112233'}}},
        )
        response    =   client.post(f'{STORES_URL}customization/restore/{version.pk}/')
        custom      =   response.data['customization']
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertNotEqual(custom['template'], 'cobre')

    def test_restore_is_isolated_between_stores(self):
        #El restore va por (tienda del dueño, id): una versión ajena da
        #404 — nadie puede restaurar ni conocer el historial de otro.
        owner       =   self._client('duenio', has_design_advanced = True)
        other       =   self._client('intruso', has_design_advanced = True)
        self._patch(owner, {'site_theme_draft': {'palette': {'primary': '#112233'}}})
        owner.post(f'{STORES_URL}customization/publish/')
        version     =   StudioVersion.objects.get()
        response    =   other.post(f'{STORES_URL}customization/restore/{version.pk}/')
        self.assertEqual(response.status_code, 404)
        theirs      =   self._custom('tienda-intruso')
        self.assertEqual(theirs.site_theme, {})
        self.assertEqual(theirs.site_theme_draft, {})

    def test_versions_list_is_isolated_between_stores(self):
        owner       =   self._client('duenio', has_design_advanced = True)
        other       =   self._client('intruso', has_design_advanced = True)
        self._patch(owner, {'site_theme_draft': {'palette': {'primary': '#112233'}}})
        owner.post(f'{STORES_URL}customization/publish/')
        self.assertEqual(other.get(f'{STORES_URL}customization/versions/').data, [])

    def test_studio_endpoints_require_customization_benefit(self):
        user, profile   =   _make_named_user('duenio')
        _grant(profile, has_public_link = True)
        Store.objects.create(user = profile, slug = 'tienda-duenio')
        client          =   APIClient()
        client.force_authenticate(user = user)
        version         =   StudioVersion.objects.create(store = Store.objects.get(slug = 'tienda-duenio'), snapshot = {})
        for method, url in (
            ('post', f'{STORES_URL}customization/publish/'),
            ('post', f'{STORES_URL}customization/discard/'),
            ('post', f'{STORES_URL}customization/restore/{version.pk}/'),
        ):
            self.assertEqual(getattr(client, method)(url).status_code, 403, url)

    def test_studio_endpoints_require_auth(self):
        self._client(has_design_advanced = True)
        for method, url in (
            ('post', f'{STORES_URL}customization/publish/'),
            ('post', f'{STORES_URL}customization/discard/'),
            ('get', f'{STORES_URL}customization/versions/'),
            ('post', f'{STORES_URL}customization/restore/1/'),
        ):
            self.assertIn(getattr(APIClient(), method)(url).status_code, (401, 403), url)

    #===== template_draft (la plantilla también es borrador del Studio) =====

    def test_published_template_syncs_draft(self):
        #Guardar la plantilla publicada alinea su borrador, igual que
        #site_theme/layout_config (el editor clásico sigue de un paso).
        client      =   self._client()
        custom      =   self._patch(client, {'template': 'duo'}).data['customization']
        self.assertEqual(custom['template'], 'duo')
        self.assertEqual(custom['template_draft'], 'duo')
        self.assertFalse(custom['has_unpublished'])

    def test_draft_template_not_visible_in_public(self):
        client      =   self._client()
        response    =   self._patch(client, {'template_draft': 'duo'})
        self.assertEqual(response.status_code, 200)
        custom      =   response.data['customization']
        self.assertEqual(custom['template'], 'classic')
        self.assertEqual(custom['template_draft'], 'duo')
        self.assertTrue(custom['has_unpublished'])
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']
        self.assertEqual(public['template'], 'classic')
        self.assertNotIn('template_draft', public)

    def test_draft_template_keeps_plan_gate(self):
        #El borrador corre la misma whitelist por nivel: 'cobre' es
        #advanced y un plan básico lo descarta en silencio del payload.
        client      =   self._client()
        response    =   self._patch(client, {'template_draft': 'cobre'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customization']['template_draft'], 'classic')
        self.assertFalse(response.data['customization']['has_unpublished'])

    def test_publish_applies_draft_template(self):
        client      =   self._client()
        self._patch(client, {'template_draft': 'duo'})
        response    =   client.post(f'{STORES_URL}customization/publish/')
        custom      =   response.data['customization']
        self.assertEqual(custom['template'], 'duo')
        self.assertEqual(custom['template_draft'], 'duo')
        self.assertFalse(custom['has_unpublished'])
        self.assertEqual(StudioVersion.objects.get().snapshot['template'], 'duo')
        self.assertEqual(APIClient().get(f'{STORES_URL}public/tienda-duenio/').data['customization']['template'], 'duo')

    def test_publish_resolves_draft_template_outside_plan(self):
        #Baja de plan con borrador premium pendiente: publish no lo
        #re-habilita — queda el publicado y el borrador se resuelve a él.
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'template_draft': 'cobre'})
        PlanBenefit.objects.filter(benefit__code = 'has_design_advanced').delete()
        cache.clear()
        response    =   client.post(f'{STORES_URL}customization/publish/')
        custom      =   response.data['customization']
        self.assertEqual(custom['template'], 'classic')
        self.assertEqual(custom['template_draft'], 'classic')
        self.assertFalse(custom['has_unpublished'])

    def test_discard_reverts_draft_template(self):
        client      =   self._client(has_design_plus = True)
        self._patch(client, {'template': 'duo'})
        self._patch(client, {'template_draft': 'vitrina'})
        response    =   client.post(f'{STORES_URL}customization/discard/')
        custom      =   response.data['customization']
        self.assertEqual(custom['template'], 'duo')
        self.assertEqual(custom['template_draft'], 'duo')
        self.assertFalse(custom['has_unpublished'])

    #===== Compartir vista previa (token firmado -> web con el borrador) =====

    def _share(self, client):
        return client.post(f'{STORES_URL}customization/share/')

    def test_share_preview_shows_draft(self):
        #El link temporal muestra el borrador completo del Studio (tema,
        #layout y plantilla) a un visitante anónimo, marcado con preview.
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {
            'site_theme_draft'  :   {'palette': {'primary': '#112233'}},
            'template_draft'    :   'duo',
            'layout_config_draft':  {'landing': {'blocks': [{'id': 'hero', 'enabled': True, 'order': 0}]}},
        })
        data        =   self._share(client).data
        self.assertIn('preview=', data['path'])
        #El path es frontend (/{slug}?preview=t): se re-arma como API.
        url         =   f"{STORES_URL}public/tienda-duenio/?preview={data['token']}"
        public      =   APIClient().get(url)
        self.assertEqual(public.status_code, 200)
        custom      =   public.data['customization']
        self.assertTrue(public.data['preview'])
        self.assertEqual(custom['site_theme'], {'palette': {'primary': '#112233'}})
        self.assertEqual(custom['template'], 'duo')
        self.assertEqual(custom['layout_config']['landing']['blocks'][0]['id'], 'hero')
        self.assertNotIn('template_draft', custom)
        self.assertNotIn('site_theme_draft', custom)

    def test_preview_bad_or_foreign_token_shows_published(self):
        client      =   self._client(has_design_advanced = True)
        self._patch(client, {'site_theme_draft': {'palette': {'primary': '#112233'}}, 'template_draft': 'duo'})
        #Token basura: el visitante ve lo publicado, como si no viniera.
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/?preview=basura').data
        self.assertNotIn('preview', public)
        self.assertEqual(public['customization']['site_theme'], {})
        #Token de otra tienda no habilita el borrador acá.
        other       =   self._client('otra', has_design_advanced = True)
        other_token =   self._share(other).data['token']
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/?preview={other_token}').data
        self.assertNotIn('preview', public)
        self.assertEqual(public['customization']['site_theme'], {})

    def test_preview_tampered_signature_shows_published(self):
        client      =   self._client()
        token       =   self._share(client).data['token']
        tampered    =   token[:-4] + ('AAAA' if token[-4:] != 'AAAA' else 'BBBB')
        public      =   APIClient().get(f'{STORES_URL}public/tienda-duenio/?preview={tampered}').data
        self.assertNotIn('preview', public)

    def test_preview_does_not_count_visit(self):
        #La vista previa es tráfico del dueño/su cliente, no de la web:
        #no suma al contador ni consume el dedupe del visitante.
        client      =   self._client()
        token       =   self._share(client).data['token']
        APIClient().get(f'{STORES_URL}public/tienda-duenio/?preview={token}')
        self.assertFalse(StoreDailyVisit.objects.exists())

    def test_share_requires_customization_benefit(self):
        user, profile   =   _make_named_user('duenio')
        _grant(profile, has_public_link = True)
        Store.objects.create(user = profile, slug = 'tienda-duenio')
        client          =   APIClient()
        client.force_authenticate(user = user)
        self.assertEqual(self._share(client).status_code, 403)

    def test_share_requires_auth(self):
        self.assertIn(APIClient().post(f'{STORES_URL}customization/share/').status_code, (401, 403))


class ObjectUrlPrivacyTests(TestCase):
    """Los adjuntos privados (chat) nunca salen por la URL pública del bucket:
    siempre firma de lectura con vigencia acotada."""

    def test_private_forces_presigned_even_with_public_base(self):
        from StoreApp.domains.stores.services import storage
        client          =   Mock()
        client.generate_presigned_url.return_value = 'https://r2.test/signed'
        with patch.object(storage, 'storage_configured', return_value = True), \
             patch.object(storage, '_public_base', return_value = 'https://cdn.test'), \
             patch.object(storage, '_client', return_value = client):
            self.assertEqual(storage.object_url('chat/1/x.webp', private = True, expires = 3600), 'https://r2.test/signed')
            client.generate_presigned_url.assert_called_once()
            self.assertEqual(client.generate_presigned_url.call_args.kwargs['ExpiresIn'], 3600)
            self.assertEqual(storage.object_url('store/x.webp'), 'https://cdn.test/store/x.webp')
