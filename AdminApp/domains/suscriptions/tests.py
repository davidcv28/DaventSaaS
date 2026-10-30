"""
Tests de seguridad del dominio suscriptions.

La suscripción nace IMPAGA (el acceso lo otorga el cobro, nunca el alta),
el plan de prueba no es elegible ni reactivable, y el cambio de plan de
una suscripción vigente queda pendiente hasta acreditar el pago.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import (
    Coupon,
    CouponRedemption,
    Suscription,
    SuscriptionPlan,
)
from AdminApp.domains.users.models import UserProfile

SUSCRIPTIONS_URL  =   '/api/suscriptions/'
PLANS_URL         =   '/api/suscription-plans/'
ASSIGN_URL        =   '/api/suscriptions/assign/'
REDEEM_URL        =   '/api/suscriptions/redeem-coupon/'


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


class CouponRedeemTests(TestCase):
    """Canje de cupones: un canje por usuario, sin pisar un plan pago vigente."""

    def setUp(self):
        # Los contadores del throttle viven en el cache compartido del proceso.
        # SQLite reutiliza PKs tras el rollback de cada test, así que la clave
        # del throttle (scope + user.pk) se repite entre tests y los 10/h de
        # `coupon_redeem` se agotan a mitad de la clase -> 429 en vez del
        # status esperado. Limpiar el cache aísla cada test.
        cache.clear()

    def _client(self):
        user, profile   =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, profile

    def _coupon(self, plan_name = 'Premium', **kwargs):
        defaults        =   {'code': 'FLYER7', 'plan': _plan(name = plan_name), 'days': 7}
        defaults.update(kwargs)
        return Coupon.objects.create(**defaults)

    def test_redeem_grants_coupon_plan_days(self):
        client, profile =   self._client()
        coupon          =   self._coupon()
        response        =   client.post(REDEEM_URL, {'code': 'flyer7'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        suscription     =   Suscription.objects.get(user = profile)
        self.assertEqual(suscription.plan_suscription, coupon.plan)
        self.assertTrue(suscription.grants_access())
        self.assertAlmostEqual(
            (suscription.end_date - timezone.now()).days, 7, delta = 1)
        self.assertTrue(
            CouponRedemption.objects.filter(coupon = coupon, user = profile).exists())

    def test_redeem_replaces_active_trial(self):
        #La trial del registro sí se pisa: el cupón es un upgrade del período gratis.
        client, profile =   self._client()
        trial           =   _plan(name = 'Trial', price = 0, is_trial = True)
        Suscription.objects.create(
            user = profile, plan_suscription = trial, status = Suscription.STATUS_ACTIVE,
            end_date = timezone.now() + timedelta(days = 1))
        coupon          =   self._coupon()
        response        =   client.post(REDEEM_URL, {'code': coupon.code}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Suscription.objects.get(user = profile).plan_suscription, coupon.plan)

    def test_redeem_rejected_with_active_paid_plan(self):
        #Un plan pago vigente nunca se pisa con una promo.
        client, profile =   self._client()
        Suscription.objects.create(
            user = profile, plan_suscription = _plan(name = 'Pago'), status = Suscription.STATUS_ACTIVE,
            end_date = timezone.now() + timedelta(days = 20))
        self._coupon()
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_redeem_rejected_with_active_debit(self):
        #Un preapproval sin baja confirmada puede cobrar en vuelo tras el
        #canje: hay que darlo de baja antes de canjear el cupón.
        client, profile =   self._client()
        Suscription.objects.create(
            user = profile, plan_suscription = _plan(name = 'Pago'),
            status = Suscription.STATUS_PENDING_PAYMENT,
            end_date = timezone.now(),
            auto_renew = True, preapproval_id = 'pre-9')
        self._coupon()
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CouponRedemption.objects.exists())
        #La suscripción quedó intacta: ni el plan ni el débito se tocaron.
        suscription     =   Suscription.objects.get(user = profile)
        self.assertEqual(suscription.plan_suscription.name, 'Pago')
        self.assertEqual(suscription.preapproval_id, 'pre-9')

    def test_redeem_allowed_after_debit_cancelled(self):
        #cancelled_at certifica la baja en MP: el canje solo limpia los restos
        #locales sin volver a llamar a la API de Mercado Pago.
        client, profile =   self._client()
        Suscription.objects.create(
            user = profile, plan_suscription = _plan(name = 'Pago'),
            status = Suscription.STATUS_PENDING_PAYMENT,
            end_date = timezone.now(),
            preapproval_id = 'pre-9', cancelled_at = timezone.now())
        coupon          =   self._coupon()
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        suscription     =   Suscription.objects.get(user = profile)
        self.assertEqual(suscription.plan_suscription, coupon.plan)
        self.assertIsNone(suscription.preapproval_id)

    def test_redeem_unknown_code(self):
        client, _       =   self._client()
        response        =   client.post(REDEEM_URL, {'code': 'NOEXISTE'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_redeem_inactive_coupon(self):
        client, _       =   self._client()
        self._coupon(is_active = False)
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_redeem_expired_coupon(self):
        client, _       =   self._client()
        self._coupon(expires_at = timezone.now() - timedelta(days = 1))
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_redeem_exhausted_max_uses(self):
        client, _       =   self._client()
        _, other        =   _make_user('otro')
        coupon          =   self._coupon(max_uses = 1)
        CouponRedemption.objects.create(coupon = coupon, user = other)
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_redeem_same_coupon_twice_rejected(self):
        client, profile =   self._client()
        coupon          =   self._coupon()
        client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        #Vencemos la promo a mano: el segundo canje del MISMO cupón se rechaza.
        Suscription.objects.filter(user = profile).update(
            end_date = timezone.now() - timedelta(days = 1))
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            CouponRedemption.objects.filter(coupon = coupon, user = profile).count(), 1)

    def test_redeem_allowed_after_promo_expires(self):
        client, profile =   self._client()
        self._coupon()
        client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        Suscription.objects.filter(user = profile).update(
            end_date = timezone.now() - timedelta(days = 1))
        self._coupon(code = 'OTRA8', plan_name = 'Otro Premium')
        response        =   client.post(REDEEM_URL, {'code': 'OTRA8'}, format = 'json')
        self.assertEqual(response.status_code, 200)

    def test_redeem_anonymous_rejected(self):
        self._coupon()
        response        =   APIClient().post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 401)


class CouponBillingIsolationTests(TestCase):
    """El canje promocional NO es un cobro: no genera Payment (historial de
    pagos) ni Invoice (factura). La actividad queda en CouponRedemption y
    se expone al cliente por /api/suscriptions/my-redemptions/."""

    PAYMENTS_URL    =   '/api/payments/'
    REDEMPTIONS_URL =   '/api/suscriptions/my-redemptions/'

    def _client(self):
        user, profile   =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        return client, profile

    def _coupon(self, **kwargs):
        defaults        =   {'code': 'FLYER7', 'plan': _plan(name = 'Premium'), 'days': 7}
        defaults.update(kwargs)
        return Coupon.objects.create(**defaults)

    def test_redeem_creates_no_payment_no_invoice(self):
        from AdminApp.domains.invoices.models import Invoice
        from AdminApp.domains.payments.models import Payment
        client, profile =   self._client()
        self._coupon()
        response        =   client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(
            CouponRedemption.objects.filter(user = profile).count(), 1)

    def test_payment_history_stays_empty_after_redeem(self):
        client, _       =   self._client()
        self._coupon()
        client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        response        =   client.get(self.PAYMENTS_URL)
        self.assertEqual(response.status_code, 200)
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(rows, [])

    def test_my_redemptions_lists_redeemed_coupon(self):
        client, _       =   self._client()
        coupon          =   self._coupon()
        client.post(REDEEM_URL, {'code': 'FLYER7'}, format = 'json')
        response        =   client.get(self.REDEMPTIONS_URL)
        self.assertEqual(response.status_code, 200)
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['code'], coupon.code)
        self.assertEqual(rows[0]['plan_name'], coupon.plan.name)
        self.assertEqual(rows[0]['days'], coupon.days)

    def test_my_redemptions_scoped_to_owner(self):
        #El canje de otro usuario nunca se filtra al historial propio.
        client, _       =   self._client()
        _, other        =   _make_user('otro')
        coupon          =   self._coupon()
        CouponRedemption.objects.create(coupon = coupon, user = other)
        response        =   client.get(self.REDEMPTIONS_URL)
        self.assertEqual(response.status_code, 200)
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(rows, [])

    def test_my_redemptions_anonymous_rejected(self):
        self.assertEqual(
            APIClient().get(self.REDEMPTIONS_URL).status_code, 401)


class CouponAdminTests(TestCase):
    """Gestión de cupones desde el panel admin: solo staff."""

    COUPONS_URL     =   '/api/coupons/'

    def _staff(self):
        admin, _        =   _make_user('admin', staff = True)
        client          =   APIClient()
        client.force_authenticate(user = admin)
        return client

    def test_list_forbidden_for_non_staff(self):
        user, _         =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        self.assertEqual(client.get(self.COUPONS_URL).status_code, 403)

    def test_create_forbidden_for_non_staff(self):
        user, _         =   _make_user('cliente')
        client          =   APIClient()
        client.force_authenticate(user = user)
        response        =   client.post(
            self.COUPONS_URL, {'code': 'X1A', 'plan': _plan().pk, 'days': 7}, format = 'json')
        self.assertEqual(response.status_code, 403)

    def test_create_normalizes_code_uppercase(self):
        client          =   self._staff()
        response        =   client.post(
            self.COUPONS_URL, {'code': '  flyer7  ', 'plan': _plan().pk, 'days': 7}, format = 'json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Coupon.objects.get().code, 'FLYER7')

    def test_create_rejects_duplicate_code_case_insensitive(self):
        client          =   self._staff()
        plan            =   _plan()
        Coupon.objects.create(code = 'FLYER7', plan = plan, days = 7)
        response        =   client.post(
            self.COUPONS_URL, {'code': 'flyer7', 'plan': plan.pk, 'days': 7}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_create_rejects_trial_plan(self):
        client          =   self._staff()
        trial           =   _plan(name = 'Trial', price = 0, is_trial = True)
        response        =   client.post(
            self.COUPONS_URL, {'code': 'X1A', 'plan': trial.pk, 'days': 7}, format = 'json')
        self.assertEqual(response.status_code, 400)

    def test_update_deactivates_coupon(self):
        client          =   self._staff()
        coupon          =   Coupon.objects.create(code = 'FLYER7', plan = _plan(), days = 7)
        response        =   client.put(
            f'{self.COUPONS_URL}{coupon.pk}/', {'is_active': False}, format = 'json')
        self.assertEqual(response.status_code, 200)
        coupon.refresh_from_db()
        self.assertFalse(coupon.is_active)

    def test_list_includes_redemptions(self):
        client          =   self._staff()
        _, profile      =   _make_user('cliente')
        coupon          =   Coupon.objects.create(code = 'FLYER7', plan = _plan(), days = 7)
        CouponRedemption.objects.create(coupon = coupon, user = profile)
        response        =   client.get(self.COUPONS_URL)
        self.assertEqual(response.status_code, 200)
        rows            =   response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(rows[0]['uses'], 1)
        self.assertEqual(rows[0]['redemptions'][0]['user_name'], 'cliente')
