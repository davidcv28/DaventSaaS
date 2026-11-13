"""
Tests de seguridad del dominio legalpages (PROMPT_MAESTRO §3.5).

Cubre: páginas legales del dueño (IDOR 404, defaults sin persistir,
versión, contenido fijo no editable — el dueño solo publica/oculta),
endpoints públicos (tienda no publicada/bloqueada/sin beneficio → 404,
interpolación fiscal, inyección de texto descartada), flujo de
arrepentimiento (captcha, honeypot, throttle, anti-enumeración,
notificación + email al dueño, bandeja y transiciones con IDOR).
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.notifications.models import Notification
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.legalpages.models import ReturnRequest, StoreLegalPage
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreFiscalProfile
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

BASE_URL    =   '/api/store-legal-pages/'
PUBLIC_URL  =   '/api/stores/public/mi-tienda/legal/'
#CUIT válido (dígito verificador módulo 11) para fiscal_complete=True.
VALID_CUIT  =   '30712345671'


def _grant(profile, *codes):
    """Plan + suscripción vigente con los flags pedidos (reusa la
    suscripción existente si ya tiene una — user es OneToOne)."""
    suscription =   getattr(profile, 'suscription', None)
    plan        =   suscription.plan_suscription if suscription is not None else SuscriptionPlan.objects.create(name = f'Plan {profile.pk}')
    for code in codes:
        benefit =   Benefit.objects.get_or_create(code = code, defaults = {'label': code, 'kind': Benefit.FLAG})[0]
        PlanBenefit.objects.get_or_create(plan = plan, benefit = benefit, defaults = {'enabled': True})
    if suscription is None:
        Suscription.objects.create(
            user                =   profile,
            plan_suscription    =   plan,
            end_date            =   timezone.now() + timedelta(days = 30),
            status              =   Suscription.STATUS_ACTIVE,
        )


def _make_owner(username = 'duenio', slug = 'mi-tienda', ecommerce = True, **store_kwargs):
    """Usuario + perfil + tienda publicada (con has_ecommerce salvo que se pida lo contrario)."""
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(user = user, email_verified = True)
    #plan_benefits_of cachea por PK y SQLite las reutiliza entre tests.
    cache.delete(f'planben:{profile.pk}')
    if ecommerce:
        #El panel legal/devoluciones es superficie de venta online.
        _grant(profile, 'has_ecommerce')
    store       =   Store.objects.create(user = profile, slug = slug, **store_kwargs)
    StoreCustomization.objects.create(store = store)
    return user, profile, store


def _grant_public_link(profile):
    """Plan + suscripción vigente con has_public_link (gate de lo público)."""
    _grant(profile, 'has_public_link')


def _authed(user):
    client      =   APIClient()
    client.force_authenticate(user = user)
    return client


def _captcha_payload(**overrides):
    payload =   {
        'name'              :   'Comprador Prueba',
        'email'             :   'comprador@gmail.com',
        #Decreto 274/2019: documento/teléfono/domicilio obligatorios.
        'document'          :   '30123456',
        'phone'             :   '+5491155551234',
        'address'           :   'Av. Corrientes 1234, CABA',
        'reason'            :   'change_of_mind',
        'details'           :   'Me arrepentí, gracias.',
        'order_ref'         :   'tok_abc123DEF-_456',
        'challenge_id'      :   'x',
        'captcha_answer'    :   '5',
    }
    payload.update(overrides)
    return payload


#=========================================
# PÁGINAS LEGALES — DUEÑO
#=========================================
class LegalPagesOwnerTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_list_requires_auth(self):
        response    =   APIClient().get(BASE_URL)
        self.assertIn(response.status_code, (401, 403))

    def test_owner_without_store_gets_404(self):
        user        =   User.objects.create_user(username = 'sinweb', email = 'sinweb@gmail.com', password = 'Xq7#mP2vL9bT')
        UserProfile.objects.create(user = user, email_verified = True)
        #El perfil existe pero el usuario nunca reclamó su web.
        response    =   _authed(user).get(BASE_URL)
        self.assertEqual(response.status_code, 404)

    def test_owner_without_ecommerce_benefit_403(self):
        #Páginas legales + bandeja de devoluciones: superficie de venta
        #online — un plan sin has_ecommerce responde 403 (la tienda ES
        #suya, lo que falta es el beneficio).
        user, _, _    =   _make_owner('duenio-sin-plan', ecommerce = False)
        client        =   _authed(user)
        self.assertEqual(client.get(BASE_URL).status_code, 403)
        self.assertEqual(client.put(f'{BASE_URL}terms/', {'body': 'x'}, format = 'json').status_code, 403)
        self.assertEqual(client.get(f'{BASE_URL}returns/').status_code, 403)

    def test_list_returns_three_pages_with_defaults(self):
        user, _, store    =   _make_owner()
        response          =   _authed(user).get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        pages             =   response.json()['pages']
        self.assertEqual([p['kind'] for p in pages], ['terms', 'privacy', 'returns'])
        for page in pages:
            self.assertFalse(page['is_published'])
            self.assertFalse(page['persisted'])
            self.assertIsNone(page['updated_at'])
            #Contenido fijo de la plataforma, ya interpolado (sin perfil
            #fiscal los placeholders caen a 'a completar').
            self.assertIn('a completar', page['body'])
            self.assertNotIn('{{', page['body'])
        #Nada se persistió: el default se sirve en memoria.
        self.assertEqual(StoreLegalPage.objects.count(), 0)

    def test_put_publishes_page(self):
        user, _, store    =   _make_owner()
        client            =   _authed(user)
        response          =   client.put(f'{BASE_URL}terms/', {'is_published': True}, format = 'json')
        self.assertEqual(response.status_code, 200)
        page              =   StoreLegalPage.objects.get(store = store, kind = 'terms')
        self.assertEqual(page.version, 1)
        self.assertTrue(page.is_published)
        data              =   response.json()
        self.assertTrue(data['is_published'])
        self.assertTrue(data['persisted'])
        self.assertNotIn('{{', data['body'])

    def test_put_ignores_custom_content(self):
        #El contenido legal es FIJO de la plataforma: body/title que el
        #dueño mande se descartan — no puede escribir que DAVENT es
        #responsable ni publicar textos inválidos.
        user, _, _        =   _make_owner()
        client            =   _authed(user)
        response          =   client.put(
            f'{BASE_URL}terms/',
            {'is_published': True, 'body': 'DAVENT es el vendedor responsable {{cuit}}', 'title': 'Texto trucho'},
            format = 'json',
        )
        self.assertEqual(response.status_code, 200)
        data              =   response.json()
        self.assertNotIn('DAVENT es el vendedor', data['body'])
        self.assertNotIn('Texto trucho', data['title'])
        self.assertEqual(data['title'], 'Términos y condiciones de venta')

    def test_put_twice_bumps_version(self):
        user, _, store    =   _make_owner()
        client            =   _authed(user)
        client.put(f'{BASE_URL}terms/', {'is_published': True}, format = 'json')
        response          =   client.put(f'{BASE_URL}terms/', {'is_published': False}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], 2)
        self.assertFalse(StoreLegalPage.objects.get(store = store, kind = 'terms').is_published)

    def test_put_empty_payload_keeps_state(self):
        user, _, _        =   _make_owner()
        client            =   _authed(user)
        client.put(f'{BASE_URL}terms/', {'is_published': True}, format = 'json')
        response          =   client.put(f'{BASE_URL}terms/', {}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_published'])

    def test_put_invalid_kind_returns_404(self):
        user, _, _        =   _make_owner()
        response          =   _authed(user).put(f'{BASE_URL}foo/', {'is_published': True}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_idor_owner_cannot_touch_other_store_pages(self):
        user_a, _, store_a   =   _make_owner(username = 'duenio-a', slug = 'tienda-a')
        user_b, _, store_b   =   _make_owner(username = 'duenio-b', slug = 'tienda-b')
        _authed(user_a).put(f'{BASE_URL}terms/', {'is_published': True}, format = 'json')
        client_b         =   _authed(user_b)
        #B no ve la publicación de A: su lista muestra defaults ocultas.
        listing          =   client_b.get(BASE_URL).json()['pages']
        terms_b          =   next(p for p in listing if p['kind'] == 'terms')
        self.assertFalse(terms_b['is_published'])
        self.assertFalse(terms_b['persisted'])
        #El PUT de B crea/edita SOLO su tienda.
        client_b.put(f'{BASE_URL}terms/', {'is_published': True}, format = 'json')
        self.assertTrue(StoreLegalPage.objects.get(store = store_a, kind = 'terms').is_published)
        self.assertTrue(StoreLegalPage.objects.get(store = store_b, kind = 'terms').is_published)

    def test_put_returns_path_edits_returns_page(self):
        #'/store-legal-pages/returns/' es bandeja (GET) y página 'returns' (PUT).
        user, _, store    =   _make_owner()
        client            =   _authed(user)
        response          =   client.put(f'{BASE_URL}returns/', {'is_published': True}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['kind'], 'returns')
        page              =   StoreLegalPage.objects.get(store = store, kind = 'returns')
        self.assertTrue(page.is_published)


#=========================================
# PÁGINAS LEGALES — PÚBLICO
#=========================================
class PublicLegalPagesTests(TestCase):

    def setUp(self):
        cache.clear()

    def _setup(self, *, published_store = True, blocked = False, benefit = True, fiscal = True):
        user, profile, store =   _make_owner(is_published = published_store, is_blocked = blocked)
        if benefit:
            _grant_public_link(profile)
        if fiscal:
            StoreFiscalProfile.objects.create(
                store               =   store,
                legal_name          =   'Comercio Demo SA',
                tax_condition       =   'RI',
                cuit                =   VALID_CUIT,
                fiscal_address      =   'Av. Corrientes 1234, CABA',
                point_of_sale       =   '0001',
            )
        return user, profile, store

    def _publish(self, store, kind = 'terms', **kwargs):
        defaults    =   {'is_published': True}
        defaults.update(kwargs)
        return StoreLegalPage.objects.create(store = store, kind = kind, **defaults)

    def test_index_empty_when_nothing_published(self):
        self._setup()
        response    =   APIClient().get(PUBLIC_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pages'], [])

    def test_unpublished_store_returns_404(self):
        self._setup(published_store = False)
        self.assertEqual(APIClient().get(PUBLIC_URL).status_code, 404)
        self.assertEqual(APIClient().get(f'{PUBLIC_URL}terms/').status_code, 404)

    def test_blocked_store_returns_404(self):
        self._setup(blocked = True)
        self.assertEqual(APIClient().get(PUBLIC_URL).status_code, 404)

    def test_store_without_public_link_returns_404(self):
        self._setup(benefit = False)
        self.assertEqual(APIClient().get(PUBLIC_URL).status_code, 404)

    def test_published_page_served_with_interpolated_fiscal(self):
        _, _, store   =   self._setup()
        self._publish(store)
        response      =   APIClient().get(f'{PUBLIC_URL}terms/')
        self.assertEqual(response.status_code, 200)
        data          =   response.json()
        self.assertEqual(data['kind'], 'terms')
        #El contenido es el texto base de la plataforma, interpolado con
        #el perfil fiscal de la tienda.
        self.assertIn('Comercio Demo SA', data['body'])
        self.assertIn(VALID_CUIT, data['body'])
        self.assertNotIn('{{legal_name}}', data['body'])
        self.assertNotIn('{{cuit}}', data['body'])
        self.assertEqual(data['fiscal']['legal_name'], 'Comercio Demo SA')
        self.assertEqual(data['fiscal']['cuit'], VALID_CUIT)
        self.assertEqual(data['fiscal']['point_of_sale'], '0001')
        self.assertTrue(data['fiscal_complete'])
        self.assertEqual(data['version'], 1)

    def test_interpolation_follows_current_fiscal_data(self):
        #Si el dueño corrige sus datos fiscales, la página se actualiza sola.
        _, _, store   =   self._setup()
        self._publish(store)
        profile       =   store.fiscal_profile
        profile.cuit  =   '30712345672'
        #El dígito verificador de este CUIT no valida → fiscal_complete cae.
        profile.save()
        data          =   APIClient().get(f'{PUBLIC_URL}terms/').json()
        self.assertIn('30712345672', data['body'])
        self.assertFalse(data['fiscal_complete'])

    def test_unpublished_page_returns_404(self):
        _, _, store   =   self._setup()
        self._publish(store, is_published = False)
        self.assertEqual(APIClient().get(f'{PUBLIC_URL}terms/').status_code, 404)

    def test_invalid_kind_returns_404(self):
        self._setup()
        self.assertEqual(APIClient().get(f'{PUBLIC_URL}foo/').status_code, 404)

    def test_index_lists_only_published_with_titles(self):
        _, _, store   =   self._setup()
        self._publish(store, 'terms')
        self._publish(store, 'privacy', is_published = False)
        data          =   APIClient().get(PUBLIC_URL).json()['pages']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['kind'], 'terms')
        self.assertEqual(data[0]['title'], 'Términos y condiciones de venta')
        self.assertIn('version', data[0])
        self.assertIn('updated_at', data[0])

    def test_missing_fiscal_profile_marks_incomplete(self):
        _, _, store   =   self._setup(fiscal = False)
        StoreLegalPage.objects.create(store = store, kind = 'terms', is_published = True)
        data          =   APIClient().get(f'{PUBLIC_URL}terms/').json()
        self.assertFalse(data['fiscal_complete'])
        self.assertEqual(data['fiscal']['cuit'], '')
        self.assertIn('a completar', data['body'])

    def test_default_page_never_published_stays_404(self):
        #Aunque exista la tienda, sin fila publicada no hay página que servir.
        self._setup()
        self.assertEqual(APIClient().get(f'{PUBLIC_URL}returns/').status_code, 404)

    def test_custom_content_never_reaches_public(self):
        #Regresión: el dueño no puede inyectar texto — el PUT descarta
        #body/title y la web pública solo sirve el texto base de la
        #plataforma interpolado con los datos fiscales de la tienda.
        user, _, store   =   self._setup()
        _authed(user).put(
            f'{BASE_URL}terms/',
            {'is_published': True, 'body': '<script>alert(1)</script>', 'title': 'Hackeado'},
            format = 'json',
        )
        data          =   APIClient().get(f'{PUBLIC_URL}terms/').json()
        self.assertNotIn('<script>', data['body'])
        self.assertNotIn('Hackeado', data['title'])
        self.assertIn('Comercio Demo SA', data['body'])

    def test_captcha_endpoint(self):
        self._setup()
        response    =   APIClient().get(f'{PUBLIC_URL}captcha/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('challenge_id', response.json())
        self.assertIn('question', response.json())

    def test_captcha_endpoint_404_for_unpublished_store(self):
        self._setup(published_store = False)
        self.assertEqual(APIClient().get(f'{PUBLIC_URL}captcha/').status_code, 404)


#=========================================
# ARREPENTIMIENTO (POST público + bandeja del dueño)
#=========================================
class ReturnRequestTests(TestCase):

    URL         =   f'{PUBLIC_URL}returns/request/'

    def setUp(self):
        cache.clear()
        mail.outbox =   []

    def _setup(self, *, benefit = True, fiscal = True, ecommerce = True):
        user, profile, store =   _make_owner(ecommerce = ecommerce)
        if benefit:
            _grant_public_link(profile)
        if fiscal:
            StoreFiscalProfile.objects.create(store = store, legal_name = 'Comercio SA', cuit = VALID_CUIT, fiscal_address = 'Calle 1', tax_condition = 'RI')
        return user, profile, store

    def test_creates_request_notifies_and_emails_owner(self):
        user, _, store    =   self._setup()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            response    =   APIClient().post(self.URL, _captcha_payload(), format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'ok': True})
        req             =   ReturnRequest.objects.get(store = store)
        self.assertEqual(req.customer_email, 'comprador@gmail.com')
        self.assertEqual(req.name, 'Comprador Prueba')
        self.assertEqual(req.reason, 'change_of_mind')
        self.assertEqual(req.order_ref, 'tok_abc123DEF-_456')
        self.assertEqual(req.document, '30123456')
        self.assertEqual(req.phone, '+5491155551234')
        self.assertEqual(req.address, 'Av. Corrientes 1234, CABA')
        self.assertEqual(req.status, 'new')
        #Notificación in-app al dueño (KIND_SYSTEM).
        notif          =   Notification.objects.get(user = user, kind = Notification.KIND_SYSTEM)
        self.assertIn('Solicitud de devolución', notif.title)
        self.assertIn('Comprador Prueba', notif.body)
        self.assertIn('comprador@gmail.com', notif.body)
        #Email al dueño (contact_email vacío → email de la cuenta).
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        self.assertIn('devolución', mail.outbox[0].subject.lower())

    def test_email_goes_to_contact_email_when_set(self):
        user, _, store    =   self._setup()
        store.customization.contact_email    =   'ventas@tienda.com'
        store.customization.save()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            APIClient().post(self.URL, _captcha_payload(), format = 'json')
        self.assertEqual(mail.outbox[0].to, ['ventas@tienda.com'])

    def test_order_ref_optional(self):
        self._setup()
        payload         =   _captcha_payload()
        payload.pop('order_ref')
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            response    =   APIClient().post(self.URL, payload, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ReturnRequest.objects.get().order_ref, '')

    def test_anti_enumeration_same_response_for_any_order_ref(self):
        #No se revela si el pedido existe: refs válidas, inventadas o
        #vacías reciben la misma respuesta genérica.
        self._setup()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            r1  =   APIClient().post(self.URL, _captcha_payload(order_ref = 'tok_real12345'), format = 'json')
            r2  =   APIClient().post(self.URL, _captcha_payload(order_ref = 'tok_inventado99'), format = 'json')
            r3  =   APIClient().post(self.URL, _captcha_payload(order_ref = ''), format = 'json')
        for r in (r1, r2, r3):
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.json(), {'ok': True})
        self.assertEqual(ReturnRequest.objects.count(), 3)

    def test_unpublished_store_returns_404(self):
        user, _, _        =   _make_owner(is_published = False)
        self.assertEqual(APIClient().post(self.URL, _captcha_payload(), format = 'json').status_code, 404)

    def test_store_without_public_link_returns_404(self):
        self._setup(benefit = False)
        self.assertEqual(APIClient().post(self.URL, _captcha_payload(), format = 'json').status_code, 404)

    def test_store_without_ecommerce_benefit_404(self):
        #La tienda tiene web pública (has_public_link) pero el plan perdió
        #has_ecommerce: una solicitud NUEVA es superficie de venta online
        #→ 404 (el dueño tampoco podría abrir la bandeja).
        self._setup(ecommerce = False)
        response    =   APIClient().post(self.URL, _captcha_payload(), format = 'json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ReturnRequest.objects.count(), 0)

    def test_honeypot_fake_success_without_persisting(self):
        self._setup()
        response        =   APIClient().post(self.URL, _captcha_payload(website = 'http://spam.com'), format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ReturnRequest.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_captcha_rejected(self):
        self._setup()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = False):
            response    =   APIClient().post(self.URL, _captcha_payload(), format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReturnRequest.objects.count(), 0)

    def test_missing_captcha_fields_returns_400(self):
        self._setup()
        payload         =   _captcha_payload()
        payload.pop('challenge_id')
        payload.pop('captcha_answer')
        response        =   APIClient().post(self.URL, payload, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_malformed_payloads_return_400(self):
        self._setup()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            #Email inválido
            self.assertEqual(APIClient().post(self.URL, _captcha_payload(email = 'no-es-mail'), format = 'json').status_code, 400)
            #Motivo fuera de choices
            self.assertEqual(APIClient().post(self.URL, _captcha_payload(reason = 'inventado'), format = 'json').status_code, 400)
            #order_ref con formato inválido (no token_urlsafe)
            self.assertEqual(APIClient().post(self.URL, _captcha_payload(order_ref = 'ref con espacios!!'), format = 'json').status_code, 400)
            #Nombre vacío
            self.assertEqual(APIClient().post(self.URL, _captcha_payload(name = '   '), format = 'json').status_code, 400)
        self.assertEqual(ReturnRequest.objects.count(), 0)

    def test_throttle_after_ten_requests(self):
        self._setup()
        with patch('StoreApp.domains.legalpages.views.views.verify_captcha', return_value = True):
            codes   =   [APIClient().post(self.URL, _captcha_payload(), format = 'json').status_code for _ in range(11)]
        self.assertEqual(codes[:10], [201] * 10)
        self.assertEqual(codes[10], 429)


class ReturnRequestsInboxTests(TestCase):

    def setUp(self):
        cache.clear()

    def _setup(self):
        user, _, store    =   _make_owner()
        return user, store

    def _req(self, store, **kwargs):
        defaults    =   {'customer_email': 'c@gmail.com', 'name': 'Cliente', 'reason': 'defect', 'status': 'new'}
        defaults.update(kwargs)
        return ReturnRequest.objects.create(store = store, **defaults)

    def test_inbox_requires_auth(self):
        self.assertIn(APIClient().get(f'{BASE_URL}returns/').status_code, (401, 403))

    def test_inbox_lists_only_own_requests(self):
        user_a, store_a   =   self._setup()
        user_b, _, store_b   =   _make_owner(username = 'otro', slug = 'otra-tienda')
        self._req(store_a, name = 'De A')
        self._req(store_b, name = 'De B')
        data            =   _authed(user_a).get(f'{BASE_URL}returns/').json()['results']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'De A')
        self.assertEqual(data[0]['reason_display'], 'Producto defectuoso')

    def test_inbox_status_filter_and_bad_status_400(self):
        user, store       =   self._setup()
        self._req(store, status = 'new')
        self._req(store, status = 'approved')
        client          =   _authed(user)
        data            =   client.get(f'{BASE_URL}returns/', {'status': 'approved'}).json()['results']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['status'], 'approved')
        self.assertEqual(client.get(f'{BASE_URL}returns/', {'status': 'inventado'}).status_code, 400)

    def test_status_transition_flow(self):
        user, store       =   self._setup()
        req             =   self._req(store)
        client          =   _authed(user)
        url             =   f'{BASE_URL}returns/{req.pk}/status/'
        r               =   client.post(url, {'status': 'in_review'}, format = 'json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'in_review')
        r               =   client.post(url, {'status': 'approved'}, format = 'json')
        self.assertEqual(r.json()['status'], 'approved')
        r               =   client.post(url, {'status': 'closed'}, format = 'json')
        self.assertEqual(r.json()['status'], 'closed')
        #closed es terminal.
        self.assertEqual(client.post(url, {'status': 'new'}, format = 'json').status_code, 400)

    def test_invalid_transition_returns_400(self):
        user, store       =   self._setup()
        req             =   self._req(store, status = 'rejected')
        #rejected solo puede ir a closed.
        response        =   _authed(user).post(f'{BASE_URL}returns/{req.pk}/status/', {'status': 'approved'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        #Mismo estado es idempotente (200).
        response        =   _authed(user).post(f'{BASE_URL}returns/{req.pk}/status/', {'status': 'rejected'}, format = 'json')
        self.assertEqual(response.status_code, 200)

    def test_status_invalid_value_returns_400(self):
        user, store       =   self._setup()
        req             =   self._req(store)
        response        =   _authed(user).post(f'{BASE_URL}returns/{req.pk}/status/', {'status': 'hackeado'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_status_idor_other_store_returns_404(self):
        user_a, store_a   =   self._setup()
        user_b, _, store_b   =   _make_owner(username = 'intruso', slug = 'tienda-intrusa')
        req             =   self._req(store_a)
        response        =   _authed(user_b).post(f'{BASE_URL}returns/{req.pk}/status/', {'status': 'approved'}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_status_missing_request_returns_404(self):
        user, _           =   self._setup()
        response        =   _authed(user).post(f'{BASE_URL}returns/99999/status/', {'status': 'approved'}, format = 'json')
        self.assertEqual(response.status_code, 404)
