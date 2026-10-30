import hashlib
from datetime import timedelta
from django.core.cache import cache
from django.db.models import F, Sum
from django.utils import timezone
from SuscriptionApp.domains.benefits.models import Benefit
from StoreApp.domains.stores.models import StoreCustomization, StoreDailyVisit
"""

Servicios del dominio Stores.

Los beneficios del plan vigente (SuscriptionApp/benefits) son la fuente
de verdad para forzar del lado del servidor qué puede editar cada
cliente en su web pública.

"""
#=========================================
# PLAN BENEFITS OF (dict {code: valor} del plan vigente)
#=========================================
#TTL del cache cruzado entre requests: el panel dispara ~10 endpoints en
#ráfaga y cada uno pagaba perfil->suscripción->plan->beneficios (~4 queries).
#La key se invalida en Suscription.save(); el TTL acota los escritos que
#bypassean save() (QuerySet.update, cambios directos en DB).
PLAN_BENEFITS_TTL   =   10

def _benefits_cache_key(profile):
    return 'planben:%s' % profile.pk

def plan_benefits_of(profile):
    """
    Beneficios del plan de la suscripción activa del perfil.
    Devuelve {} si no hay suscripción o está pendiente de pago:
    'limit' -> int (None = ilimitado) | 'flag' -> bool.

    Tres niveles de reuso: memo en la instancia (el serializer público lo
    llama ~5 veces por request), cache cross-request de ~10s (la ráfaga
    del dashboard comparte un solo cálculo) y prefetch si el queryset
    del viewset lo pidió.
    """
    cached  =   getattr(profile, '_plan_benefits_cache', None)
    if cached is not None:
        return cached
    try:
        benefits    =   cache.get(_benefits_cache_key(profile))
    except Exception:
        benefits    =   None
    if benefits is None:
        suscription     =   getattr(profile, 'suscription', None)
        #grants_access() fuerza status + vigencia (end_date + gracia si hay débito automático)
        benefits        =   {}
        if suscription is not None and suscription.grants_access():
            plan        =   suscription.plan_suscription
            prefetched  =   getattr(plan, '_prefetched_objects_cache', {})
            rows        =   prefetched['benefits'] if 'benefits' in prefetched else plan.benefits.select_related('benefit')
            for plan_benefit in rows:
                code                =   plan_benefit.benefit.code
                benefits[code]      =   plan_benefit.value if plan_benefit.benefit.kind == Benefit.LIMIT else plan_benefit.enabled
        try:
            cache.set(_benefits_cache_key(profile), benefits, PLAN_BENEFITS_TTL)
        except Exception:
            pass
    profile._plan_benefits_cache        =   benefits
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
# ALLOWED TEMPLATES OF (diseños de portada según el plan vigente)
#=========================================
def allowed_templates_of(profile):
    """
    Diseños de la web disponibles según el plan (catálogo de 8):
    TEMPLATE_BASE ('raiz','alimentos') va con cualquier has_customization,
    has_design_plus suma TEMPLATE_PLUS
    ('trama','indumentaria','boutique','clasico') y has_design_advanced
    suma TEMPLATE_ADVANCED ('circuito','seguridad'). Sin acceso solo
    'raiz' — la web pública lo usa como whitelist para forzar el fallback
    si el dueño baja de plan. El motor de IA no suma patrones propios:
    sigue proponiendo solo los 6 de PUBLIC_TEMPLATES (ai_design_recipes),
    es decir los 8 del selector menos 'indumentaria' y 'clasico'.
    """
    benefits        =   plan_benefits_of(profile)
    if not benefits.get('has_customization'):
        return (StoreCustomization.TEMPLATE_RAIZ,)
    allowed         =   list(StoreCustomization.TEMPLATE_BASE)
    if benefits.get('has_design_plus'):
        allowed         +=  StoreCustomization.TEMPLATE_PLUS
    if benefits.get('has_design_advanced'):
        allowed         +=  StoreCustomization.TEMPLATE_ADVANCED
    return tuple(allowed)
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
    #Último segmento de X-Forwarded-For: el proxy confiable (Render/CF)
    #appendea la IP real del cliente al final — el primero es spoofeable
    #por el propio visitante e inflaría el dedupe en su favor.
    ip              =   (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[-1].strip() or request.META.get('REMOTE_ADDR') or ''
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
