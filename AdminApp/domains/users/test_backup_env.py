"""
Tests de higiene de secretos (auditoría 30/10/2026, bloque 1).

`backup_db` pasa a pg_dump un env MÍNIMO: el hijo no puede heredar
SECRET_KEY, la keyring de PII ni los tokens de MercadoPago.
"""
import os
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings

BACKUP = 'AdminApp.domains.users.management.commands.backup_db'


class BackupEnvTests(TestCase):
    def test_pg_dump_child_env_has_no_secrets(self):
        database    =   {
            'ENGINE'    :   'django.db.backends.postgresql',
            'NAME'      :   'davent',
            'USER'      :   'davent',
            'PASSWORD'  :   'db-pass',
            'HOST'      :   'db',
            'PORT'      :   '5432',
        }
        proc        =   MagicMock(returncode = 0, stdout = b'')
        client      =   MagicMock()
        client.get_paginator.return_value.paginate.return_value = []
        leaked      =   {
            'SECRET_KEY'            :   'secret',
            'MP_WEBHOOK_SECRET'     :   'mp',
            'SECRET_MP_KEY'         :   'mp-key',
            'SECRETS_MASTER_KEYS'   :   'k1:abc',
            'EMAIL_HOST_PASSWORD'   :   'smtp',
            'R2_SECRET_ACCESS_KEY'  :   'r2',
        }
        with override_settings(DATABASES = {'default': database}), \
             patch.dict(os.environ, leaked), \
             patch(f'{BACKUP}.storage_configured', return_value = True), \
             patch(f'{BACKUP}._client', return_value = client), \
             patch(f'{BACKUP}._bucket', return_value = 'bucket'), \
             patch(f'{BACKUP}.subprocess.run', return_value = proc) as run:
            call_command('backup_db')

        env =   run.call_args.kwargs['env']
        for name in leaked:
            self.assertNotIn(name, env)
        self.assertEqual(env['PGPASSWORD'], 'db-pass')
        self.assertEqual(env['PGDATABASE'], 'davent')
        self.assertIn('PATH', env)
