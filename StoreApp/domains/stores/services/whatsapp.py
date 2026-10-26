import logging
import re
import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from decouple import config
from django.db.models import Sum
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.stores.models import StoreDailyVisit
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.services.services import profile_has_benefit
"""

Resumen diario de la tienda por WhatsApp (beneficio 'has_whatsapp_digest',
solo Premium y prueba).

El envío usa la Meta WhatsApp Business Cloud API: los mensajes iniciados
por el negocio exigen un TEMPLATE pre-aprobado — no hay API gratuita de
WhatsApp y los gateways no oficiales violan los ToS (banean el número).

Setup (una vez, en Meta for Developers / WhatsApp):
  - WABA + número remitente registrado -> WHATSAPP_PHONE_ID
  - Token permanente de un usuario de sistema -> WHATSAPP_TOKEN (secreto)
  - Template 'resumen_diario_tienda' (utility, es_AR) con 6 variables body:
      📊 Resumen de tu tienda — {{1}}
      {{2}} recibió {{3}} visitas hoy y {{4}} en los últimos 7 días.
      Productos activos: {{5}}.
      Tu web: {{6}}

El job corre una vez por día (celery beat / cron de Render / manage.py
send_whatsapp_digest — los tres llaman a send_daily_digests).

"""
#=========================================
# CONFIG
#=========================================
GRAPH_API_URL   =   'https://graph.facebook.com/v22.0'
FRONTEND_URL    =   config('FRONTEND_URL', default = '') or 'http://localhost:5173'
logger          =   logging.getLogger(__name__)
#=========================================
# E164 (Meta exige dígitos sin '+': 54911...)
#=========================================
def _e164(phone):
    return re.sub(r'\D', '', phone or '')
#=========================================
# SEND WHATSAPP TEMPLATE (Cloud API -> bool)
#=========================================
def send_whatsapp_template(to, params):
    """
    POST /{PHONE_ID}/messages con un template body de N variables.
    False si falta config, el número es inválido o Meta responde !=2xx —
    el caller decide si reintentar (no marca sent_at -> reintenta mañana).
    """
    token       =   getattr(settings, 'WHATSAPP_TOKEN', '')
    phone_id    =   getattr(settings, 'WHATSAPP_PHONE_ID', '')
    to          =   _e164(to)
    if not token or not phone_id:
        logger.warning('whatsapp digest: WHATSAPP_TOKEN/WHATSAPP_PHONE_ID sin configurar — feature apagada')
        return False
    if len(to) < 10:
        logger.warning('whatsapp digest: número inválido %r', to)
        return False
    payload     =   {
        'messaging_product' :   'whatsapp',
        'to'                :   to,
        'type'              :   'template',
        'template'          :   {
            'name'          :   getattr(settings, 'WHATSAPP_TEMPLATE', 'resumen_diario_tienda'),
            'language'      :   {'code': 'es_AR'},
            'components'    :   [{
                'type'          :   'body',
                'parameters'    :   [{'type': 'text', 'text': str(p)} for p in params],
            }],
        },
    }
    try:
        resp        =   requests.post(
                            f'{GRAPH_API_URL}/{phone_id}/messages',
                            headers = {'Authorization': f'Bearer {token}'},
                            json    = payload,
                            timeout = 10,
                        )
    except requests.RequestException as exc:
        logger.error('whatsapp digest: error de red enviando a %s: %s', to, exc)
        return False
    if not resp.ok:
        logger.error('whatsapp digest: Meta %s -> %s %s', to, resp.status_code, resp.text[:300])
        return False
    return True
#=========================================
# DIGEST PARAMS (variables del template para una tienda)
#=========================================
def digest_params(profile, today):
    """
    [fecha, nombre, visitas_hoy, visitas_7d, productos_activos, link]
    None si el perfil no tiene tienda (aún no hizo el onboarding).
    """
    store       =   getattr(profile, 'store', None)
    if store is None:
        return None
    name        =   (getattr(getattr(store, 'customization', None), 'display_name', '') or '').strip() or store.slug
    visits      =   StoreDailyVisit.objects.filter(store = store, date__gte = today - timedelta(days = 6)).aggregate(t = Sum('count'))['t'] or 0
    today_count =   StoreDailyVisit.objects.filter(store = store, date = today).aggregate(t = Sum('count'))['t'] or 0
    products    =   Product.objects.filter(store = store, is_active = True).count()
    link        =   f'{FRONTEND_URL}/{store.slug}'
    return [today.strftime('%d/%m/%Y'), name, today_count, visits, products, link]
#=========================================
# SEND DAILY DIGESTS (job diario — idempotente por sent_at)
#=========================================
def send_daily_digests(now = None):
    """
    Recorre los perfiles con opt-in y manda el resumen. Solo si el plan
    vigente da el beneficio (el flag guardado queda para cuando suba de
    plan). sent_at <20h = ya enviado (absorbe reintentos del scheduler).
    Devuelve {'sent','skipped','failed'} para logs del job.
    """
    now         =   now or timezone.now()
    today       =   timezone.localdate()
    stats       =   {'sent': 0, 'skipped': 0, 'failed': 0}
    profiles    =   (
                    UserProfile.objects
                        .filter(whatsapp_digest = True)
                        .exclude(phone__isnull = True)
                        .exclude(phone = '')
                        .select_related('store__customization', 'suscription__plan_suscription')
                    )
    for profile in profiles:
        if profile.whatsapp_digest_sent_at and now - profile.whatsapp_digest_sent_at < timedelta(hours = 20):
            stats['skipped'] += 1
            continue
        if not profile_has_benefit(profile, 'has_whatsapp_digest'):
            stats['skipped'] += 1
            continue
        params      =   digest_params(profile, today)
        if params is None:
            stats['skipped'] += 1
            continue
        if send_whatsapp_template(profile.phone, params):
            profile.whatsapp_digest_sent_at     =   now
            profile.save(update_fields = ['whatsapp_digest_sent_at'])
            stats['sent'] += 1
        else:
            stats['failed'] += 1
    logger.info('whatsapp digest diario: %s', stats)
    return stats
