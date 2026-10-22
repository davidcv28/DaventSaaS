"""
Tests de seguridad del dominio stores.

El claim del slug exige correo verificado (anti-abuso del plan de prueba).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.users.models import UserProfile

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
