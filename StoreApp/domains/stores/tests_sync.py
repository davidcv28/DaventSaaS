"""
Tests de la sección "Sincronización" del dashboard del dueño:
GET /api/stores/sync/ y POST /api/stores/sync/run/.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreSyncEvent
from StoreApp.domains.stores.services import record_sync_event, run_sync, sync_state
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

SYNC_URL      =   '/api/stores/sync/'
SYNC_RUN_URL  =   '/api/stores/sync/run/'


def _owner_with_store(username = 'duenio-sync'):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = '5501')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'30{abs(hash(username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   True,
        phone           =   f'1133{abs(hash(username)) % 10**8:08d}',
    )
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {username}')
    benefit     =   Benefit.objects.get_or_create(code = 'has_customization', defaults = {'label': 'Personalización', 'kind': Benefit.FLAG})[0]
    PlanBenefit.objects.create(plan = plan, benefit = benefit, enabled = True)
    Suscription.objects.create(
        user                =   profile,
        plan_suscription    =   plan,
        end_date            =   timezone.now() + timedelta(days = 30),
        status              =   Suscription.STATUS_ACTIVE,
    )
    store       =   Store.objects.create(user = profile, slug = f'slug-{username}', is_published = True)
    return user, store


class SyncStateTests(TestCase):

    def setUp(self):
        self.user, self.store   =   _owner_with_store()
        self.client             =   APIClient()
        self.client.force_authenticate(user = self.user)

    def test_sync_vacio(self):
        #Sin eventos ni borrador: pending 0, operations vacío, sin last_sync.
        response    =   self.client.get(SYNC_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pending_count'], 0)
        self.assertEqual(response.data['operations'], [])
        self.assertIsNone(response.data['last_sync_at'])

    def test_evento_registrado_aparece(self):
        #record_sync_event deja la fila visible en operations del estado.
        record_sync_event(self.store, 'update-producto', 'Actualización de producto')
        response    =   self.client.get(SYNC_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pending_count'], 0)
        self.assertEqual(len(response.data['operations']), 1)
        operation   =   response.data['operations'][0]
        self.assertEqual(operation['op'], 'update-producto')
        self.assertEqual(operation['status'], 'done')
        self.assertIsNotNone(response.data['last_sync_at'])

    def test_sync_sin_tienda_404(self):
        user, _     =   User.objects.create_user(username = 'sin-tienda', email = 's@gmail.com', password = 'x'), None
        client      =   APIClient()
        client.force_authenticate(user = user)
        self.assertEqual(client.get(SYNC_URL).status_code, 404)

    def test_draft_pendiente_y_run_publica(self):
        #Borrador distinto al publicado → pending_count 1 y pseudo-op al
        #tope; run_sync publica (reusa publish_design_draft) y limpia.
        customization               =   StoreCustomization.objects.create(store = self.store)
        customization.template_draft        =   customization.template
        customization.layout_config_draft   =   {'hero': {'headline': 'Nuevo'}}
        customization.save()
        state       =   sync_state(self.store)
        self.assertEqual(state['pending_count'], 1)
        self.assertEqual(state['operations'][0]['op'], 'publish-diseno')
        self.assertEqual(state['operations'][0]['status'], 'pending')
        response    =   self.client.post(SYNC_RUN_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pending_count'], 0)
        customization.refresh_from_db()
        self.assertEqual(customization.layout_config, {'hero': {'headline': 'Nuevo'}})
        #El run deja el evento 'publish-design' en la bitácora.
        self.assertTrue(
            StoreSyncEvent.objects.filter(store = self.store, op = 'publish-design', status = 'done').exists()
        )

    def test_run_cierra_eventos_pending(self):
        record_sync_event(self.store, 'update-diseno', 'Cambios de diseño sin publicar', status = 'pending')
        state       =   sync_state(self.store)
        self.assertEqual(state['pending_count'], 1)
        run_sync(self.store)
        self.assertEqual(sync_state(self.store)['pending_count'], 0)
        event       =   StoreSyncEvent.objects.get(store = self.store, op = 'update-diseno')
        self.assertEqual(event.status, 'done')
        self.assertIsNotNone(event.processed_at)
