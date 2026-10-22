"""App Celery del proyecto: la usan los workers (contenedor `celery`).

Las tareas se autodescubren como `tasks.py` dentro de cada app instalada.
Broker y resultados: Redis (CELERY_BROKER_URL / CELERY_RESULT_BACKEND en .env).
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')

app = Celery('davent')
app.config_from_object('django.conf:settings', namespace = 'CELERY')
app.autodiscover_tasks()
