# Stress test — tráfico público anónimo (solo GET) contra producción.
#
#   Headless (busca el punto de quiebre subiendo la carga):
#     venv/Scripts/python.exe -m locust -f locustfile.py --headless \
#         -u 500 -r 25 -t 5m --host https://davent.com --csv report
#
#   UI web:
#     venv/Scripts/python.exe -m locust -f locustfile.py
#     → http://localhost:8089
#
#   Tiendas reales a golpear (separadas por coma):
#     set DAVENT_SLUGS=tienda-1,tienda-2
#
import os
import random

from locust import HttpUser, between, task

SLUGS = [s.strip() for s in os.environ.get('DAVENT_SLUGS', '').split(',') if s.strip()]


class PublicVisitor(HttpUser):
    """Visitante anónimo que navega la landing y tiendas públicas."""

    wait_time = between(1, 4)

    @task(5)
    def landing(self):
        self.client.get('/', name='/')

    @task(4)
    def plans(self):
        self.client.get('/api/plans/', name='/api/plans/')

    @task(2)
    def design_catalog(self):
        self.client.get('/api/design/catalog/', name='/api/design/catalog/')

    @task(1)
    def offers(self):
        self.client.get('/api/offers/', name='/api/offers/')

    @task(5)
    def store_public(self):
        if not SLUGS:
            return
        slug = random.choice(SLUGS)
        self.client.get(f'/api/stores/public/{slug}/', name='/api/stores/public/<slug>/')

    @task(4)
    def store_catalog(self):
        if not SLUGS:
            return
        slug = random.choice(SLUGS)
        self.client.get(
            f'/api/stores/public/{slug}/catalog/',
            name='/api/stores/public/<slug>/catalog/',
        )
