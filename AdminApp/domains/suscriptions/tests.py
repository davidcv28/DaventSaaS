"""
Tests de seguridad del dominio suscriptions.

La suscripción nace IMPAGA (el acceso lo otorga el cobro, nunca el alta),
el plan de prueba no es elegible ni reactivable, y el cambio de plan de
una suscripción vigente queda pendiente hasta acreditar el pago.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile

SUSCRIPTIONS_URL  =   '/api/suscriptions/'
PLANS_URL         =   '/api/suscription-plans/'
ASSIGN_URL        =   '/api/suscriptions/assign/'


def _make_user(username, staff = False):
    province    =   Province.objects.create(name_province = f'Prov {username}')
    zipcode     =   ZipCode.objects.create(zipcode = f'7{abs(hash(username)) % 1000:03d}')
    city        =   City.objects.create(name_city = f'Ciudad {username}', province = province, zipcode = zipcode)
    user        =   User.objects.create_user(
        username = username, email = f'{username}@gmail.com',
        password = 'Xq7#mP2vL9bT', is_staff = staff,
    )
    profile     =   UserProfile.objects.create(
        user            =   user,
        first_name      =   'Ana',
        last_name       =   'Perez',
        document        =   f'25{abs(hash(username + username)) % 10**6:06d}',
        province        =   province,
        city            =   city,
    )
    return user, profile


def _plan(name = 'Plan pago', price = 1000, **kwargs):
    return SuscriptionPlan.objects.create(name = name, price = price, **kwargs)


class SuscriptionCreateTests(TestCase):
    """El alta crea una suscripción PENDIENTE DE PAGO: no otorga acceso."""

    def _client(self):
        user, profile   =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, profile

    def test_create_is_pending_not_active(self):
        #Anti-regresión: antes el default del modelo daba 30 días gratis.
        client, _       =   self._client()
        plan            =   _plan()
        response        =   client.post(SUSCRIPTIONS_URL, {'plan_suscription': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 201)
        suscription     =   Suscription.objects.get()
        self.assertFalse(suscription.grants_access())

    def test_trial_plan_not_selectable(self):
        #El plan de prueba se otorga en el registro, no por POST: el
        #queryset del campo lo excluye (idempotente con el anti multi-cuenta).
        client, _       =   self._client()
        trial           =   _plan(name = 'Trial', price = 0, is_trial = True)
        response        =   client.post(SUSCRIPTIONS_URL, {'plan_suscription': trial.pk}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_second_suscription_rejected(self):
        client, profile =   self._client()
        Suscription.objects.create(user = profile, plan_suscription = _plan())
        response        =   client.post(SUSCRIPTIONS_URL, {'plan_suscription': _plan(name = 'Otro').pk}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_anonymous_create_rejected(self):
        response        =   APIClient().post(SUSCRIPTIONS_URL, {'plan_suscription': _plan().pk}, format = 'json')
        self.assertEqual(response.status_code, 401)


class SuscriptionUpdateTests(TestCase):
    """El cambio de plan es 'pendiente de pago', nunca un upgrade gratis."""

    def test_update_sets_pending_plan_not_current(self):
        user, profile   =   _make_user('cliente')
        suscription     =   Suscription.objects.create(
            user = profile, plan_suscription = _plan(name = 'Actual'),
            end_date = timezone.now() + timedelta(days = 20),
            status = Suscription.STATUS_ACTIVE,
        )
        new_plan        =   _plan(name = 'Nuevo')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(
            f'{SUSCRIPTIONS_URL}{suscription.pk}/', {'plan_suscription': new_plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        suscription.refresh_from_db()
        self.assertEqual(suscription.plan_suscription.name, 'Actual')
        self.assertEqual(suscription.pending_plan_suscription, new_plan)

    def test_update_foreign_suscription_404(self):
        _, profile      =   _make_user('cliente')
        _, other        =   _make_user('otro')
        suscription     =   Suscription.objects.create(user = other, plan_suscription = _plan())
        user, _         =   _make_user('tercero')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.put(
            f'{SUSCRIPTIONS_URL}{suscription.pk}/', {'plan_suscription': _plan(name = 'X').pk}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_list_scoped_to_owner(self):
        _, profile      =   _make_user('cliente')
        _, other        =   _make_user('otro')
        Suscription.objects.create(user = profile, plan_suscription = _plan(name = 'Mío'))
        Suscription.objects.create(user = other, plan_suscription = _plan(name = 'Ajeno'))
        user, _         =   _make_user('tercero')
        client          =   APIClient()
        client.force_authenticate(user = User.objects.get(username = 'cliente'))
        response        =   client.get(SUSCRIPTIONS_URL)
        names           =   [row['plan_name'] for row in (response.data['results'] if isinstance(response.data, dict) else response.data)]
        self.assertEqual(names, ['Mío'])


class AssignPlanTests(TestCase):
    """Asignación manual de planes: solo staff, ids numéricos, sin trial."""

    def _staff(self):
        admin, _        =   _make_user('admin', staff = True)
        client          =   APIClient()
        client.force_authenticate(user = admin)
        return client

    def test_assign_forbidden_for_non_staff(self):
        user, _         =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(ASSIGN_URL, {'user_id': 1, 'plan_id': 1}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_assign_grants_30_days(self):
        client          =   self._staff()
        _, profile      =   _make_user('cliente')
        plan            =   _plan()
        response        =   client.post(ASSIGN_URL, {'user_id': profile.user_id, 'plan_id': plan.pk}, format = 'json')
        self.assertEqual(response.status_code, 200)
        suscription     =   Suscription.objects.get(user = profile)
        self.assertTrue(suscription.grants_access())

    def test_assign_rejects_trial_plan(self):
        client          =   self._staff()
        _, profile      =   _make_user('cliente')
        trial           =   _plan(name = 'Trial', price = 0, is_trial = True)
        response        =   client.post(ASSIGN_URL, {'user_id': profile.user_id, 'plan_id': trial.pk}, format = 'json')
        self.assertEqual(response.status_code, 404)

    def test_assign_rejects_non_numeric_ids(self):
        #Regresión: ids no numéricos llegaban al ORM y tiraban 500.
        client          =   self._staff()
        response        =   client.post(ASSIGN_URL, {'user_id': 'abc', 'plan_id': 'xyz'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_assign_unknown_user(self):
        client          =   self._staff()
        response        =   client.post(ASSIGN_URL, {'user_id': 999999, 'plan_id': _plan().pk}, format = 'json')
        self.assertEqual(response.status_code, 400)


class PlanEndpointTests(TestCase):
    """El catálogo público de planes excluye el de prueba."""

    def test_plan_catalog_excludes_trial(self):
        _plan(name = 'Básico', price = 100)
        _plan(name = 'Trial', price = 0, is_trial = True)
        response        =   APIClient().get(PLANS_URL)
        self.assertEqual(response.status_code, 200)
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual([row['name'] for row in rows], ['Básico'])

    def test_plan_write_requires_staff(self):
        user, _         =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(PLANS_URL, {'name': 'Nuevo', 'price': '10'}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_plan_name_letters_accepted(self):
        #Regresión: el ^ invertido rechazaba todo nombre que empezara con letra.
        admin, _        =   _make_user('admin', staff = True)
        client          =   APIClient()
        client.force_authenticate(user = admin)
        response        =   client.post(PLANS_URL, {'name': 'Premium', 'price': '10'}, format = 'json')
        self.assertEqual(response.status_code, 201)

    def test_plan_name_with_digits_rejected(self):
        admin, _        =   _make_user('admin', staff = True)
        client          =   APIClient()
        client.force_authenticate(user = admin)
        response        =   client.post(PLANS_URL, {'name': 'Plan 3000', 'price': '10'}, format = 'json')
        self.assertEqual(response.status_code, 400)


class GrantsAccessTests(TestCase):
    """grants_access(): activa + vigente; gracia de 5 días solo con débito."""

    def _suscription(self, **kwargs):
        _, profile      =   _make_user('cliente')
        defaults        =   {
            'user'              :   profile,
            'plan_suscription'  :   _plan(),
            'status'            :   Suscription.STATUS_ACTIVE,
            'start_date'        :   timezone.now() - timedelta(days = 10),
            'end_date'          :   timezone.now() + timedelta(days = 20),
        }
        defaults.update(kwargs)
        return Suscription.objects.create(**defaults)

    def test_pending_payment_grants_nothing(self):
        suscription     =   self._suscription(status = Suscription.STATUS_PENDING_PAYMENT)
        self.assertFalse(suscription.grants_access())

    def test_expired_without_renewal_grants_nothing(self):
        suscription     =   self._suscription(
            end_date = timezone.now() - timedelta(days = 1), auto_renew = False)
        self.assertFalse(suscription.grants_access())

    def test_grace_period_only_with_auto_renew(self):
        suscription     =   self._suscription(
            end_date = timezone.now() - timedelta(days = 3), auto_renew = True)
        self.assertTrue(suscription.grants_access())

    def test_grace_expired_grants_nothing(self):
        suscription     =   self._suscription(
            end_date = timezone.now() - timedelta(days = 6), auto_renew = True)
        self.assertFalse(suscription.grants_access())
