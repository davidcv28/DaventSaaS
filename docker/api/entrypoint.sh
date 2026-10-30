#!/bin/sh
set -e

# En compose el job `migrate` hace collectstatic+migrate UNA sola vez por
# deploy (api/celery arrancan con RUN_MIGRATIONS/RUN_COLLECTSTATIC=0): repetirlo
# en cada restart costaba ~4-6s de arranque y hacía que dos réplicas migraran
# en paralelo. En plataformas sin job previo (Render free) quedan en "1".
if [ "$1" = "gunicorn" ]; then
    # Fail-closed: en producción (DEBUG=False) la config se valida ANTES de
    # servir tráfico. Render construye directo del Dockerfile —no pasa por el
    # job `test` de CI ni por el preflight del VPS— así que sin esto un env
    # incompleto (ADMIN_URL default, keyring de PII ausente, HSTS apagado)
    # arrancaba igual. Si falla, el deploy queda en rojo y Render sigue
    # sirviendo la versión anterior.
    if [ "$DEBUG" != "True" ]; then
        python manage.py check --deploy --fail-level ERROR
    fi
    if [ "$RUN_COLLECTSTATIC" != "0" ]; then
        python manage.py collectstatic --noinput
    fi
    if [ "$RUN_MIGRATIONS" != "0" ]; then
        python manage.py migrate --noinput
    fi
    # Seeds idempotentes: solo cuando AUTO_SEED=1 (deploys sin shell, ej. Render free).
    if [ "$AUTO_SEED" = "1" ]; then
        python manage.py seed_locations
        python manage.py suscriptions
        python manage.py seed_benefits
    fi
    # Superuser inicial en plataformas sin shell: se setea por env y falla
    # silencioso si el usuario ya existe (restarts del servicio).
    if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        python manage.py createsuperuser --noinput || true
    fi
fi

exec "$@"
