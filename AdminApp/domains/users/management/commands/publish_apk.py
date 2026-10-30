import re
from pathlib import Path

from django.core.management import BaseCommand, CommandError

from StoreApp.domains.stores.services.storage import (
    _bucket,
    _client,
    object_url,
    storage_configured,
)

"""
Publicación de la APK de DAVENT en Cloudflare R2 (distribución web directa).

Sube el binario firmado a dos keys:
  apk/<versionCode>/davent-<versionName>.apk  -> histórico inmutable por versión
  apk/davent-latest.apk                       -> URL estable, la que se publicita
                                               (la página /descargar apunta acá)

Uso:
    venv/Scripts/python.exe manage.py publish_apk --file frontend/apk-dist/davent-1.0-1.apk
    venv/Scripts/python.exe manage.py publish_apk --file app-release.apk \
        --version-name 1.0 --version-code 1

Si no se pasan --version-*, se parsean del nombre de archivo
'davent-<versionName>-<versionCode>.apk' (convención del script de build).

Después de subir hay que actualizar las env del server para que el update
checker vea la versión nueva (GET /api/config/ -> bloque 'app'):
    APP_APK_VERSION_NAME, APP_APK_VERSION_CODE, APP_APK_URL
    (APP_APK_URL = la URL pública de apk/davent-latest.apk)

Requiere las mismas credenciales R2 del storage de imágenes (S3_API,
R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET). El bucket debe exponer
R2_PUBLIC_URL para que el link de descarga sea estable.
"""

_APK_CONTENT_TYPE   =   'application/vnd.android.package-archive'
_LATEST_KEY         =   'apk/davent-latest.apk'
_NAME_RE            =   re.compile(r'davent-(?P<name>.+)-(?P<code>\d+)\.apk$')
# Nombre con el que el navegador guarda el archivo al bajarlo (la URL de la
# key no cambia). 'attachment' además fuerza descarga en vez de abrirlo.
_DOWNLOAD_NAME      =   'attachment; filename="DaventApp.apk"'


class Command(BaseCommand):
    help = 'Sube la APK firmada a R2 (key versionada + davent-latest.apk estable).'

    def add_arguments(self, parser):
        parser.add_argument('--file', required = True, help = 'Ruta local del .apk firmado.')
        parser.add_argument('--version-name', help = 'Ej. 1.0 — si falta se parsea del nombre del archivo.')
        parser.add_argument('--version-code', type = int, help = 'Entero creciente — si falta se parsea del nombre del archivo.')

    def handle(self, *args, **options):
        if not storage_configured():
            raise CommandError('Falta configuración de R2: S3_API, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY y R2_BUCKET.')
        apk         =   Path(options['file'])
        if not apk.is_file() or apk.suffix.lower() != '.apk':
            raise CommandError(f'No existe el APK: {apk}')
        version_name, version_code    =   self._versions(apk, options)
        client      =   _client()
        body        =   apk.read_bytes()
        versioned   =   f'apk/{version_code}/davent-{version_name}.apk'
        #La key versionada es inmutable (una por release); la estable cambia en
        #cada publicación: cache corto para que el update checker y la página de
        #descarga vean la nueva a los pocos minutos.
        client.put_object(
            Bucket              =   _bucket(),
            Key                 =   versioned,
            Body                =   body,
            ContentType         =   _APK_CONTENT_TYPE,
            ContentDisposition  =   _DOWNLOAD_NAME,
            CacheControl        =   'public, max-age=31536000, immutable',
        )
        client.put_object(
            Bucket              =   _bucket(),
            Key                 =   _LATEST_KEY,
            Body                =   body,
            ContentType         =   _APK_CONTENT_TYPE,
            ContentDisposition  =   _DOWNLOAD_NAME,
            CacheControl        =   'public, max-age=300',
        )
        size_mb     =   len(body) / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f'APK {version_name} (code {version_code}, {size_mb:.1f} MB) publicada:'))
        self.stdout.write(f'  {versioned}')
        self.stdout.write(f'  {_LATEST_KEY}')
        self.stdout.write('')
        self.stdout.write(f'URL estable de descarga: {object_url(_LATEST_KEY) or "(configurar R2_PUBLIC_URL)"}')
        self.stdout.write('Actualizá el env del server:')
        self.stdout.write(f'  APP_APK_VERSION_NAME={version_name}')
        self.stdout.write(f'  APP_APK_VERSION_CODE={version_code}')
        self.stdout.write(f'  APP_APK_URL={object_url(_LATEST_KEY) or "<url pública del bucket>/apk/davent-latest.apk"}')

    @staticmethod
    def _versions(apk : Path, options) -> tuple:
        """(--version-name, --version-code) o parseo del nombre del archivo."""
        name        =   options.get('version_name')
        code        =   options.get('version_code')
        match       =   _NAME_RE.search(apk.name)
        if not name:
            if not match:
                raise CommandError('Falta --version-name (el archivo no sigue la convención davent-<name>-<code>.apk).')
            name        =   match.group('name')
        if not code:
            if not match:
                raise CommandError('Falta --version-code (el archivo no sigue la convención davent-<name>-<code>.apk).')
            code        =   int(match.group('code'))
        return name, code
