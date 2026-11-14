#!/bin/sh
# Wrapper del entrypoint de nginx-unprivileged: deriva ADMIN_PATH desde
# ADMIN_URL (el path ofuscado del admin de Django, p.ej. 'gestion-xxx/')
# para que envsubst pueda incrustarlo en el `location` del vhost. Una sola
# fuente de verdad: si ADMIN_URL cambia, el proxy lo sigue solo.
# ADMIN_URL sin setear -> 'admin' (mismo comportamiento del vhost previo).
ADMIN_PATH="$(printf '%s' "${ADMIN_URL:-admin/}" | sed 's|^/*||; s|/*$||')"
export ADMIN_PATH
exec /docker-entrypoint.sh "$@"
