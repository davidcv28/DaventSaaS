"""
Tests del captcha antispam (auditoría 30/10/2026, bloque 4).

La suma de dos dígitos (17 valores) era sorteable: ahora la operación tiene
mucha más entropía, el challenge es de un solo uso y admite 5 intentos.
"""
import secrets
import time

from django.core import signing
from django.core.cache import cache
from django.test import TestCase

from StoreApp.domains.stores.services.contact import (
    CAPTCHA_MAX_AGE,
    CAPTCHA_MAX_ATTEMPTS,
    CAPTCHA_MIN_SECONDS,
    CAPTCHA_SALT,
    _answer_hash,
    issue_captcha,
    verify_captcha,
)


def _challenge(slug : str, answer : int) -> str:
    payload =   {'s': slug, 'h': _answer_hash(slug, answer), 't': time.time() - CAPTCHA_MIN_SECONDS - 1, 'n': secrets.token_urlsafe(16)}
    return signing.dumps(payload, salt = CAPTCHA_SALT)


class CaptchaTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_answer_space_is_wide(self):
        answers =   set()
        for _ in range(120):
            question    =   issue_captcha('tienda')['question']
            answers.add(question)
        #Más de 17 operaciones distintas (el techo del captcha viejo).
        self.assertGreater(len(answers), 17)

    def test_challenge_is_single_use(self):
        challenge   =   _challenge('tienda', 42)
        self.assertTrue(verify_captcha('tienda', challenge, '42'))
        self.assertFalse(verify_captcha('tienda', challenge, '42'))

    def test_attempts_are_limited(self):
        challenge   =   _challenge('tienda', 42)
        for _ in range(CAPTCHA_MAX_ATTEMPTS):
            self.assertFalse(verify_captcha('tienda', challenge, '0'))
        self.assertFalse(verify_captcha('tienda', challenge, '42'))

    def test_ttl_is_short(self):
        self.assertLessEqual(CAPTCHA_MAX_AGE, 300)

    def test_challenge_without_nonce_is_rejected(self):
        payload     =   {'s': 'tienda', 'h': _answer_hash('tienda', 42), 't': time.time() - 30}
        challenge   =   signing.dumps(payload, salt = CAPTCHA_SALT)
        self.assertFalse(verify_captcha('tienda', challenge, '42'))
