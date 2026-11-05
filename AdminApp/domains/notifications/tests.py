"""
Tests del dominio notifications: avisos del sistema del panel (opiniones,
mensajes del staff, suscripción y changelog) — deduplicados por
(user, kind, dedupe_key), scoped al dueño y separados del chat.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.chat.models import ChatThread
from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.notifications.models import ChangelogEntry, Notification
from AdminApp.domains.notifications.services import (
    mark_reviews_seen,
    notify_product_review,
    notify_staff_message,
    unread_reviews_count,
)
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product, ProductReview
from StoreApp.domains.stores.models import Store
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

NOTIFICATIONS_URL    =   '/api/notifications/'
READ_URL             =   '/api/notifications/read/'
REVIEWS_SEEN_URL     =   '/api/notifications/reviews-seen/'
CHANGELOG_URL        =   '/api/changelog/'


def _client(user):
    client      =   APIClient()
    #Re-fetch por request: force_authenticate con la MISMA instancia de
    #User arrastraría caches de relaciones reversas (profile.suscription
    #cachea DoesNotExist) entre "requests" — en prod cada request trae
    #instancias frescas.
    client.force_authenticate(user = User.objects.get(pk = user.pk))
    return client


def _make_user(username):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'7{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(username = username, email = f'{username}@gmail.com', password = 'Xq7#mP2vL9bT')
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'27{abs(hash(username + username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
        email_verified  =   True,
    )
    return user, profile


def _grant(profile, **benefits):
    """Plan + suscripción vigente de 30 días (bool = flag, int|None = limit)."""
    plan        =   SuscriptionPlan.objects.create(name = f'Plan {profile.user.username}')
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


class NotificationServiceTests(TestCase):
    """Dedup y triggers de los servicios del dominio."""

    def setUp(self):
        #El throttle notifications comparte la cache entre tests.
        cache.clear()
        self.user, self.profile =   _make_user('duenio')
        self.store              =   Store.objects.create(user = self.profile, slug = 'mi-tienda')

    def test_review_notification_is_single_and_updates(self):
        product     =   Product.objects.create(store = self.store, name = 'Calza', price = 10)
        notify_product_review(self.store, product_name = 'Calza')
        notify_product_review(self.store, product_name = 'Remera')
        qs          =   self.user.notifications.filter(kind = Notification.KIND_REVIEW)
        self.assertEqual(qs.count(), 1)
        notif       =   qs.get()
        self.assertEqual(notif.title, 'Un producto acaba de recibir una opinión')
        self.assertEqual(notif.body, 'Sobre Remera.')
        self.assertEqual(notif.target, 'reviews')
        self.assertIsNone(notif.read_at)
        #Marcar leído y que llegue otra opinión: el MISMO aviso vuelve a
        #no-leído (sigue siendo uno solo, no se acumulan).
        notif.read_at   =   timezone.now()
        notif.save(update_fields = ['read_at'])
        notify_product_review(self.store, product_name = 'Buzo')
        notif.refresh_from_db()
        self.assertIsNone(notif.read_at)
        self.assertEqual(self.user.notifications.count(), 1)

    def test_staff_message_notification_targets_support_not_chat(self):
        thread  =   ChatThread.objects.create(customer = self.user)
        notify_staff_message(thread)
        notif   =   self.user.notifications.get()
        self.assertEqual(notif.kind, Notification.KIND_ADMIN_MESSAGE)
        self.assertEqual(notif.target, 'support')

    def test_changelog_publish_fanout_once(self):
        other, _   =   _make_user('otro')
        entry       =   ChangelogEntry.objects.create(title = 'Borrador', body = 'x', is_published = False)
        self.assertEqual(self.user.notifications.count(), 0)
        entry.is_published  =   True
        entry.save()
        for u in (self.user, other):
            notif   =   u.notifications.get(kind = Notification.KIND_CHANGELOG)
            self.assertEqual(notif.target, 'changelog')
            self.assertEqual(notif.title, 'Se agregaron nuevas funcionalidades')
        #Re-publicar no re-notifica (published_at ya estaba fijado).
        entry.is_published  =   False
        entry.save()
        entry.is_published  =   True
        entry.save()
        self.assertEqual(self.user.notifications.filter(kind = Notification.KIND_CHANGELOG).count(), 1)


class NotificationApiTests(TestCase):
    """Endpoints del panel: scoping, leído y badge de opiniones."""

    def setUp(self):
        cache.clear()
        self.user, self.profile =   _make_user('duenio')
        self.store              =   Store.objects.create(user = self.profile, slug = 'mi-tienda')
        self.other, other_p     =   _make_user('intruso')
        Store.objects.create(user = other_p, slug = 'otra-tienda')

    def test_list_is_scoped_to_owner(self):
        Notification.objects.create(user = self.user, kind = 'system', title = 'Mío', dedupe_key = 'a')
        Notification.objects.create(user = self.other, kind = 'system', title = 'Ajeno', dedupe_key = 'b')
        data        =   _client(self.user).get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread'], 1)
        self.assertEqual([n['title'] for n in data['notifications']], ['Mío'])
        #El intruso tampoco ve las de este usuario.
        data2       =   _client(self.other).get(NOTIFICATIONS_URL).data
        self.assertEqual([n['title'] for n in data2['notifications']], ['Ajeno'])

    def test_read_single_and_all(self):
        n1  =   Notification.objects.create(user = self.user, kind = 'system', title = 'Uno', dedupe_key = 'a')
        n2  =   Notification.objects.create(user = self.user, kind = 'system', title = 'Dos', dedupe_key = 'b')
        client  =   _client(self.user)
        client.post(READ_URL, {'id': n1.id}, format = 'json')
        data    =   client.get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread'], 1)
        client.post(READ_URL, {'all': True}, format = 'json')
        data    =   client.get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread'], 0)
        #El id ajeno no se puede marcar (404 silencioso del filtro).
        client.post(READ_URL, {'id': n2.id + 999}, format = 'json')

    def test_unread_reviews_badge_and_seen(self):
        product     =   Product.objects.create(store = self.store, name = 'P', price = 1)
        ProductReview.objects.create(
            store = self.store, product = product,
            is_positive = True, name = 'A', surname = 'B', email = 'a@x.com',
        )
        #Sin plan no hay beneficio: el badge es 0 aunque haya reviews.
        data    =   _client(self.user).get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread_reviews'], 0)
        #Con has_product_comments: la review cuenta como sin leer.
        _grant(self.profile, has_product_comments = True)
        #plan_benefits_of cachea ~10s entre requests: se limpia para simular
        #el vencimiento del TTL (en prod el badge tarda eso en refrescar).
        cache.clear()
        data    =   _client(self.user).get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread_reviews'], 1)
        self.assertIsNone(data['reviews_seen_at'])
        res     =   _client(self.user).post(REVIEWS_SEEN_URL).data
        self.assertEqual(res['unread_reviews'], 0)
        self.store.refresh_from_db()  #el POST guardó sobre otra instancia
        self.assertIsNotNone(self.store.reviews_seen_at)
        #Una review nueva vuelve a contar.
        ProductReview.objects.create(
            store = self.store, product = product,
            is_positive = False, name = 'C', surname = 'D', email = 'c@x.com',
        )
        data    =   _client(self.user).get(NOTIFICATIONS_URL).data
        self.assertEqual(data['unread_reviews'], 1)

    def test_reviews_seen_does_not_touch_other_store(self):
        _grant(self.profile, has_product_comments = True)
        ProductReview.objects.create(
            store = self.store, product = Product.objects.create(store = self.store, name = 'P', price = 1),
            is_positive = True, name = 'A', surname = 'B', email = 'a@x.com',
        )
        mark_reviews_seen(self.user)
        self.assertEqual(unread_reviews_count(self.user), 0)
        #La otra tienda nunca fue "vista" por su dueño.
        other_store    =   Store.objects.get(user__user = self.other)
        self.assertIsNone(other_store.reviews_seen_at)

    def test_changelog_api_auth_and_publish_filter(self):
        #Anónimo: 401.
        self.assertEqual(APIClient().get(CHANGELOG_URL).status_code, 401)
        ChangelogEntry.objects.create(title = 'Borrador', body = 'x', is_published = False)
        ChangelogEntry.objects.create(title = 'Publicada', body = 'y', is_published = True)
        titles  =   [c['title'] for c in _client(self.user).get(CHANGELOG_URL).data]
        self.assertEqual(titles, ['Publicada'])
        #Staff ve todo (incluye borradores).
        staff, staff_p   =   _make_user('staff')
        staff.is_staff   =   True
        staff.save()
        titles  =   [c['title'] for c in _client(staff).get(CHANGELOG_URL).data]
        self.assertEqual(sorted(titles), ['Borrador', 'Publicada'])
        #El fan-out llega a usuarios activos creados hasta ese momento.
        self.assertFalse(staff.notifications.filter(kind = Notification.KIND_CHANGELOG).exists())
        ChangelogEntry.objects.create(title = 'Tercera', body = 'z', is_published = True)
        self.assertTrue(staff.notifications.filter(kind = Notification.KIND_CHANGELOG).exists())

    def test_subscription_warning_sync(self):
        _grant(self.profile)
        suscription   =   self.profile.suscription
        suscription.end_date    =   timezone.now() + timedelta(days = 2)
        suscription.save(update_fields = ['end_date'])
        data    =   _client(self.user).get(NOTIFICATIONS_URL).data
        notif   =   self.user.notifications.get(kind = Notification.KIND_SUBSCRIPTION)
        self.assertEqual(notif.target, 'plans')
        self.assertIn('por vencer', notif.title)
        #Renovación automática viva: no hay aviso que mostrar.
        suscription.auto_renew      =   True
        suscription.cancelled_at    =   None
        suscription.save(update_fields = ['auto_renew', 'cancelled_at'])
        _client(self.user).get(NOTIFICATIONS_URL)
        self.assertFalse(self.user.notifications.filter(kind = Notification.KIND_SUBSCRIPTION, read_at__isnull = True).exists())
