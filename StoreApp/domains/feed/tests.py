"""
Tests del dominio feed.

Las escrituras de comprador (comentar/likear/votar) van por
FeedWriteThrottle: con AnonRateThrottle el límite quedaba desactivado
para todo request autenticado (Customer JWT setea request.user).
"""
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from StoreApp.domains.feed.views.views import FeedWriteThrottle


class _FakeUser:
    is_authenticated = True
    pk = 42


class FeedWriteThrottleTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_throttle_keys_authenticated_and_anonymous(self):
        factory     =   APIRequestFactory()
        throttle    =   FeedWriteThrottle()
        url         =   '/api/stores/public/tienda/feed/1/like/'
        anon        =   factory.post(url)
        anon.user   =   AnonymousUser()
        authed      =   factory.post(url)
        authed.user =   _FakeUser()
        #Anon keyea por IP; autenticado por pk — ninguno devuelve None.
        self.assertIsNotNone(throttle.get_cache_key(anon, None))
        key         =   throttle.get_cache_key(authed, None)
        self.assertIsNotNone(key)
        self.assertIn('42', key)
