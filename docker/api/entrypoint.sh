#!/bin/sh
set -e

# Solo el proceso web recolecta estaticos y migra (celery no lo necesita).
if [ "$1" = "gunicorn" ]; then
    python manage.py collectstatic --noinput
    python manage.py migrate --noinput
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
