# syntax=docker/dockerfile:1
# Imagen de la API DRF (gunicorn) — también la usa el worker Celery y el job migrate.

# ---------- Stage 1: compila wheels de requirements.txt ----------
FROM python:3.11-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# gcc/libpq por si alguna dependencia no trae wheel para py3.11.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- Stage 2: runtime mínimo, sin toolchain ----------
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
# pg_dump para `manage.py backup_db` (cron del host -> compose exec api).
# La imagen base solo ofrece el cliente 15 y el server de compose es 16:
# se instala postgresql-client-16 desde el repo oficial PGDG.
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget gnupg ca-certificates \
    && echo "deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*
# Usuario no-root: un RCE dentro del contenedor no es root.
RUN groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app
WORKDIR /app
COPY requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
COPY . .
COPY docker/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app
USER app
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "docker/api/gunicorn.conf.py", "DaventProject.wsgi:application"]
