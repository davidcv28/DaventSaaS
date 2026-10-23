import hashlib
from datetime import timedelta
from django.core.cache import cache
from django.db.models import F, Sum
from django.utils import timezone
from SuscriptionApp.domains.benefits.models import Benefit
from StoreApp.domains.stores.models import StoreDailyVisit
"""

Servicios del dominio Stores.

Los beneficios del plan vigente (SuscriptionApp/benefits) son la fuente
de verdad para forzar del lado del servidor qué puede editar cada
cliente en su web pública.

"""
#=========================================
# PLAN BENEFITS OF (dict {code: valor} del plan vigente)
#=========================================
def plan_benefits_of(profile):
    """
    Beneficios del plan de la suscripción activa del perfil.
    Devuelve {} si no hay suscripción o está pendiente de pago:
    'limit' -> int (None = ilimitado) | 'flag' -> bool.
    """
    suscription     =   getattr(profile, 'suscription', None)
    #grants_access() fuerza status + vigencia (end_date + gracia si hay débito automático)
    if suscription is None or not suscription.grants_access():
        return {}
    benefits        =   {}
    for plan_benefit in suscription.plan_suscription.benefits.select_related('benefit'):
        code                =   plan_benefit.benefit.code
        benefits[code]      =   plan_benefit.value if plan_benefit.benefit.kind == Benefit.LIMIT else plan_benefit.enabled
    return benefits
#=========================================
# PROFILE HAS BENEFIT (flag o límite habilitado)
#=========================================
def profile_has_benefit(profile, code):
    """
    True si el plan vigente habilita el beneficio.
    'flag' -> enabled | 'limit' -> None (ilimitado) o entero > 0.
    """
    value           =   plan_benefits_of(profile).get(code, False)
    return True if value is None else bool(value)
#=========================================
# RECORD STORE VISIT (+1 por visitante/día, sin guardar IPs)
#=========================================
def record_store_visit(store, request):
    """
    +1 al contador del día de la tienda. Dedupe best-effort con cache por
    hash(IP+UA+fecha): un mismo visitante cuenta una sola vez por día sin
    guardar su IP. El update con F() no pierde hits concurrentes.
    """
    today           =   timezone.localdate()
    ip              =   (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip() or request.META.get('REMOTE_ADDR') or ''
    ua              =   request.META.get('HTTP_USER_AGENT', '')[:200]
    key             =   'visit:%s:%s' % (store.pk, hashlib.sha256(f'{ip}|{ua}|{today}'.encode()).hexdigest()[:32])
    if not cache.add(key, 1, 86400):
        return
    StoreDailyVisit.objects.get_or_create(store = store, date = today, defaults = {'count': 0})
    StoreDailyVisit.objects.filter(store = store, date = today).update(count = F('count') + 1)
#=========================================
# VISIT STATS OF (serie de N días + total, para el panel del dueño)
#=========================================
def visit_stats_of(store, days = 30):
    today       =   timezone.localdate()
    since       =   today - timedelta(days = days - 1)
    by_date     =   {
        row.date: row.count
        for row in StoreDailyVisit.objects.filter(store = store, date__gte = since)
    }
    series      =   [
        {'date': (since + timedelta(days = i)).isoformat(), 'count': by_date.get(since + timedelta(days = i), 0)}
        for i in range(days)
    ]
    total       =   StoreDailyVisit.objects.filter(store = store).aggregate(t = Sum('count'))['t'] or 0
    return {'total': total, 'today': by_date.get(today, 0), 'days': series}
