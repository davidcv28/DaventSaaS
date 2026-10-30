from django.core.management import BaseCommand

from DaventProject.envguard import collect_errors, mask

"""

Tabla nombre→OK/ERROR de las variables de entorno auditadas, con valores
enmascarados. Exit != 0 si hay errores: es el gate del CI y del runbook de
deploy (mismas reglas que `check --deploy` → project.E006…E018).

"""

#Nombres auditados (los que aparecen en la tabla aunque estén sanos).
AUDITED = (
    'DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS',
    'CSRF_TRUSTED_ORIGINS', 'REDIS_URL', 'DATABASE_URL', 'EMAIL_BACKEND',
    'MP_PAYER_EMAIL', 'MP_WEBHOOK_ALLOW_UNSIGNED', 'SECRETS_HASH_KEY',
    'SECRETS_MASTER_KEYS', 'DEPLOY_CHECK_STRICT',
    'PYTHONPATH', 'PYTHONSTARTUP', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
    'DJANGO_SETTINGS_MODULE', 'AUTO_SEED', 'DJANGO_SUPERUSER_PASSWORD',
)


class Command(BaseCommand):
    help = 'Audita las variables de entorno críticas/peligrosas (tabla enmascarada, exit 1 si hay errores).'

    def handle(self, *args, **options):
        from django.conf import settings
        errors      =   collect_errors()
        by_name     =   {}
        for item in errors:
            by_name.setdefault(item['name'], []).append(item)
        self.stdout.write(f"{'VARIABLE':<28} {'VALOR':<24} ESTADO")
        for name in AUDITED:
            value   =   getattr(settings, name, None)
            if value is None:
                import os
                value   =   os.environ.get(name, '')
            state   =   'ERROR' if name in by_name else 'OK'
            self.stdout.write(f'{name:<28} {mask(value):<24} {state}')
        for item in errors:
            self.stdout.write(self.style.ERROR(f"  [{item['id']}] {item['name']}: {item['message']} -> {item['hint']}"))
        if errors:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('check_env: entorno sano'))
