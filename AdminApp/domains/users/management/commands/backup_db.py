import gzip
import os
import subprocess
from datetime import timedelta

from decouple import config
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from StoreApp.domains.stores.services.storage import (
    _bucket,
    _client,
    storage_configured,
)

"""
Backup de la base Postgres hacia Cloudflare R2.

Flujo: pg_dump (plain) -> gzip -> put_object bajo 'backups/davent-YYYYMMDD-HHMM.sql.gz',
y después poda los dumps más viejos que BACKUP_RETENTION_DAYS (default 14).

Pensado para correr como cron del host sobre el contenedor api:
    docker compose exec -T api python manage.py backup_db

Requiere pg_dump en la imagen (postgresql-client en docker/api/Dockerfile) y
las mismas credenciales R2 del storage de imágenes (S3_API, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET). Falla ruidoso (exit != 0) si falta config.

Restore manual:
    aws s3 cp s3://<bucket>/backups/davent-XXXX.sql.gz - | gunzip | \
        docker compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB
"""


class Command(BaseCommand):
    help = 'Vuelca Postgres (pg_dump), lo comprime y lo sube a R2 con retención configurable.'

    def handle(self, *args, **options):
        db          =   settings.DATABASES['default']
        if 'postgres' not in db.get('ENGINE', ''):
            raise CommandError('backup_db solo soporta PostgreSQL (la DATABASE_URL actual no es Postgres).')
        if not storage_configured():
            raise CommandError('Falta configuración de R2: S3_API, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY y R2_BUCKET.')
        retention   =   config('BACKUP_RETENTION_DAYS', default = 14, cast = int)
        key         =   f"backups/davent-{timezone.now().strftime('%Y%m%d-%H%M')}.sql.gz"
        #pg_dump lee credenciales del entorno (PGPASSWORD), nunca de argv/logs.
        #Env MÍNIMO: heredar os.environ.copy() le pasaba al hijo SECRET_KEY,
        #SECRETS_MASTER_KEYS, tokens de MP, SMTP y R2 — cualquier volcado del
        #proceso los exponía. Solo viajan las variables que pg_dump necesita.
        env         =   {
            'PATH'          :   os.environ.get('PATH', ''),
            'HOME'          :   os.environ.get('HOME') or os.environ.get('USERPROFILE', ''),
            'PGHOST'        :   str(db.get('HOST') or 'localhost'),
            'PGPORT'        :   str(db.get('PORT') or '5432'),
            'PGUSER'        :   str(db.get('USER') or 'postgres'),
            'PGDATABASE'    :   db['NAME'],
            'PGSSLMODE'     :   os.environ.get('PGSSLMODE', 'prefer'),
        }
        if db.get('PASSWORD'):
            env['PGPASSWORD']   =   db['PASSWORD']
        cmd         =   [
            'pg_dump', '--format=plain', '--no-owner', '--no-privileges',
            '--host', str(db.get('HOST') or 'localhost'),
            '--port', str(db.get('PORT') or '5432'),
            '--username', str(db.get('USER') or 'postgres'),
            db['NAME'],
        ]
        self.stdout.write(f"Volcando {db['NAME']} con pg_dump…")
        proc        =   subprocess.run(cmd, capture_output = True, env = env, check = False)
        if proc.returncode != 0:
            detail      =   proc.stderr.decode(errors = 'replace')[:500]
            raise CommandError(f'pg_dump falló (exit {proc.returncode}): {detail}')
        payload     =   gzip.compress(proc.stdout, compresslevel = 9)
        client      =   _client()
        client.put_object(
            Bucket          =   _bucket(),
            Key             =   key,
            Body            =   payload,
            ContentType     =   'application/gzip',
        )
        self.stdout.write(self.style.SUCCESS(f'Backup subido a R2: {key} ({len(payload) // 1024} KB)'))
        self._prune(client, retention)

    def _prune(self, client, retention_days : int) -> None:
        """Borra los dumps 'backups/*' más viejos que la ventana de retención."""
        cutoff      =   timezone.now() - timedelta(days = retention_days)
        stale       =   []
        paginator   =   client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket = _bucket(), Prefix = 'backups/'):
            for obj in page.get('Contents', []):
                if obj['LastModified'] < cutoff:
                    stale.append({'Key': obj['Key']})
        for i in range(0, len(stale), 1000):
            client.delete_objects(Bucket = _bucket(), Delete = {'Objects': stale[i:i + 1000]})
        if stale:
            self.stdout.write(f'Retención {retention_days}d: {len(stale)} backup(s) viejo(s) eliminados.')
