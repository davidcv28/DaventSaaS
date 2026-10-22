"""Config de gunicorn para la API (Docker).

Se puede tunear por env: GUNICORN_WORKERS / GUNICORN_THREADS.
"""
import os

bind         = "0.0.0.0:8000"
# Solo nginx llega a este puerto (red interna de compose); confiar en los
# headers X-Forwarded-* que inyecta.
forwarded_allow_ips = "*"

# I/O-bound (R2, MercadoPago, SMTP): workers gthread = workers * threads de
# concurrencia real sin el costo de workers sync extra.
workers      = int(os.getenv("GUNICORN_WORKERS", "3"))
threads      = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"
worker_tmp_dir = "/dev/shm"

timeout          = 60
graceful_timeout = 30          # drain al hacer `compose up -d` (deploy sin corte)
keepalive        = 5
# Recicla workers periódicamente: acota fugas de memoria/FDs.
max_requests        = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog  = "-"
loglevel  = "info"
