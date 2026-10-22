#!/bin/sh
set -e

# Solo el proceso web recolecta estaticos (migrate/celery no lo necesitan).
if [ "$1" = "gunicorn" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
