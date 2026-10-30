"""
Tests del guard central de env vars (auditoría 30/10/2026, bloque 2).

Cada regla se prueba en positivo (config sana → sin errores) y negativo
(config peligrosa → id project.E00x).
"""
import os
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from DaventProject.envguard import DANGEROUS_NAMES, collect_errors

BASE = {
    'DEBUG'                 :   False,
    'SECRET_KEY'            :   'k' * 64,
    'ALLOWED_HOSTS'         :   ['davent.com', 'localhost'],
    'CORS_ALLOWED_ORIGINS'  :   ['https://www.davent.com'],
    'CSRF_TRUSTED_ORIGINS'  :   ['https://www.davent.com'],
    'EMAIL_BACKEND'         :   'django.core.mail.backends.smtp.EmailBackend',
    'REDIS_URL'             :   'redis://:pass@redis:6379/1',
    'DATABASE_URL'          :   'sqlite:///db.sqlite3',
    'SECRETS_MASTER_KEYS'   :   'k1:abc',
    'SECRETS_HASH_KEY'      :   'h1:def',
}


def _ids(env = None, **overrides):
    config =   dict(BASE)
    config.update(overrides)
    with override_settings(**config), patch.dict(os.environ, env or {}, clear = True):
        return {item['id'] for item in collect_errors()}


class EnvGuardRuleTests(TestCase):
    def test_clean_production_config_has_no_errors(self):
        self.assertEqual(_ids(), set())

    def test_dangerous_names(self):
        for name in DANGEROUS_NAMES:
            self.assertIn('project.E006', _ids({name: 'x'}), name)

    def test_unsigned_webhooks_flag(self):
        self.assertIn('project.E007', _ids({'MP_WEBHOOK_ALLOW_UNSIGNED': 'True'}))
        self.assertNotIn('project.E007', _ids({'MP_WEBHOOK_ALLOW_UNSIGNED': 'False'}))

    def test_deploy_check_strict(self):
        self.assertIn('project.E008', _ids({'DEPLOY_CHECK_STRICT': '0'}))
        self.assertNotIn('project.E008', _ids({'DEPLOY_CHECK_STRICT': '1'}))

    def test_allowed_hosts_wildcard(self):
        self.assertIn('project.E009', _ids(ALLOWED_HOSTS = ['*']))

    def test_origin_wildcards(self):
        self.assertIn('project.E010', _ids(CORS_ALLOWED_ORIGINS = ['*']))
        self.assertIn('project.E010', _ids(CSRF_TRUSTED_ORIGINS = ['*']))

    def test_secret_key_weak(self):
        self.assertIn('project.E011', _ids(SECRET_KEY = 'change-me'))
        self.assertIn('project.E011', _ids(SECRET_KEY = 'short'))
        self.assertNotIn('project.E011', _ids(SECRET_KEY = 'z' * 60))

    def test_redis_required_in_production(self):
        self.assertIn('project.E012', _ids(REDIS_URL = ''))
        self.assertNotIn('project.E012', _ids(DEBUG = True, REDIS_URL = ''))

    def test_console_email_backend_in_production(self):
        self.assertIn('project.E013', _ids(EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'))
        self.assertNotIn('project.E013', _ids(DEBUG = True, EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'))

    def test_mp_payer_email_in_production(self):
        self.assertIn('project.E014', _ids({'MP_PAYER_EMAIL': 'test_user_1@testuser.com'}))

    def test_hash_key_reusing_master_key(self):
        self.assertIn('project.E015', _ids(SECRETS_MASTER_KEYS = 'k1:abc', SECRETS_HASH_KEY = 'k1:abc'))

    def test_remote_database_without_sslmode(self):
        remote  =   {'ENGINE': 'django.db.backends.postgresql', 'HOST': 'db.example.com', 'NAME': 'davent'}
        self.assertIn('project.E016', _ids(DATABASES = {'default': remote}))
        secured =   dict(remote, OPTIONS = {'sslmode': 'require'})
        self.assertNotIn('project.E016', _ids(DATABASES = {'default': secured}))

    def test_debug_not_boolean(self):
        self.assertIn('project.E017', _ids({'DEBUG': 'maybe'}))

    def test_http_origin_in_production(self):
        self.assertIn('project.E018', _ids(CORS_ALLOWED_ORIGINS = ['http://www.davent.com']))


class EnvGuardCommandTests(TestCase):
    def test_check_env_exits_nonzero_on_errors(self):
        with patch('DaventProject.envguard.collect_errors', return_value = [{
            'id': 'project.E011', 'name': 'SECRET_KEY', 'message': 'm', 'hint': 'h',
        }]):
            with self.assertRaises(SystemExit):
                call_command('check_env')

    def test_env_example_does_not_declare_dangerous_names(self):
        root    =   os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        path    =   os.path.join(root, '.env.example')
        with open(path, encoding = 'utf-8') as handle:
            declared =   {line.split('=', 1)[0].strip() for line in handle if '=' in line and not line.strip().startswith('#')}
        self.assertEqual(declared & DANGEROUS_NAMES, set())
