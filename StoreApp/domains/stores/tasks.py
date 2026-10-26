from celery import shared_task
"""

Tareas celery del dominio Stores — corren en el worker (`celery` en
docker-compose) disparadas por `celery-beat` (CELERY_BEAT_SCHEDULE en
settings). El mismo envío puede correrlo el cron de Render o a mano con
`manage.py send_whatsapp_digest`.

"""
#=========================================
# DAILY WHATSAPP DIGEST (resumen del día de la tienda, premium)
#=========================================
@shared_task(name = 'stores.send_daily_whatsapp_digest')
def send_daily_whatsapp_digest():
    from StoreApp.domains.stores.services import send_daily_digests
    return send_daily_digests()
