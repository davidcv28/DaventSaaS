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
    # El check corre SIEMPRE (queda en el log qué falta), pero solo corta el
    # arranque con DEPLOY_CHECK_STRICT=1. En Render no hay shell: un deploy en
    # rojo por una var que únicamente se carga desde el dashboard (MP_WEBHOOK_SECRET,
    # SECRETS_MASTER_KEYS, ADMIN_URL) deja el servicio sin forma de volver a
    # verde sin editar el dashboard. En el VPS/CI queda estricto.
    if [ "$DEBUG" != "True" ]; then
        if ! python manage.py check --deploy --fail-level ERROR; then
            if [ "$DEPLOY_CHECK_STRICT" = "1" ]; then
                echo "deploy check: configuracion de produccion incompleta (DEPLOY_CHECK_STRICT=1) -> abortando arranque"
                exit 1
            fi
            echo "deploy check: configuracion de produccion incompleta -> arranca igual (DEPLOY_CHECK_STRICT=0)"
        fi
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
