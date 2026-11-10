import logging
from datetime import timedelta

from django.utils import timezone

from StoreApp.domains.customers.models import StoreMembership
from StoreApp.domains.memberships.models import StoreSubscription

"""

Beneficios de membresía de tienda — CONTRATO PÚBLICO consumido por
cart/orders (track B) en checkout y por el enforcement del catálogo.

Regla de vigencia (evaluada AL LEER, sin cron destructivo): una
suscripción otorga beneficios solo si `status='active'` Y
`vigente_hasta > now`. Por eso:

- Al vencer `vigente_hasta` el cliente pierde TODO automáticamente en
  la próxima lectura — no hace falta una tarea que "apague" nada (el
  flag `expire_check()` solo ordena el status para los listados del
  dueño; correrlo es opcional).
- `cancelled` pierde beneficios AL INSTANTE (los helpers exigen
  'active'): decisión documentada — cancelar = cortar ya, no "hasta el
  fin del período pago". Si se quisiera lo segundo, el helper aceptaría
  también status='cancelled' con vigente_hasta>now.
- `pending`, `past_due`, `expired`, `cancelled` → sin beneficios.
- `customer=None` / `store=None` / sin membresía → vacío/0/False (nunca
  excepción): el checkout de un visitante sin cuenta pasa por acá.

`member_benefits` devuelve el set de códigos {'digital_card',
'free_shipping', 'exclusive_discounts', 'exclusive_access'} — un subset
de MEMBER_BENEFITS derivado de los bools del StorePlan vigente.
Si hay más de una suscripción vigente a la vez (dato anómalo), los
beneficios se UNIFICAN y el descuento toma el mayor porcentaje.

Pendiente documentado: cobro automático de la suscripción por MP del
vendedor (auto-billing/renovación). El MVP es manual como los pedidos:
la suscripción nace 'pending', el dueño acredita y hace POST
.../activate/ — la infra de webhooks MP de storepayments lo reutilizará.
"""
logger   =   logging.getLogger(__name__)
#=========================================
# CATÁLOGO DE BENEFICIOS (códigos estables del contrato)
#=========================================
BENEFIT_DIGITAL_CARD         =   'digital_card'
BENEFIT_FREE_SHIPPING        =   'free_shipping'
BENEFIT_EXCLUSIVE_DISCOUNTS  =   'exclusive_discounts'
BENEFIT_EXCLUSIVE_ACCESS     =   'exclusive_access'
MEMBER_BENEFITS              =   frozenset({
    BENEFIT_DIGITAL_CARD,
    BENEFIT_FREE_SHIPPING,
    BENEFIT_EXCLUSIVE_DISCOUNTS,
    BENEFIT_EXCLUSIVE_ACCESS,
})
#(flag del StorePlan → código de beneficio del contrato)
_PLAN_FLAG_TO_BENEFIT        =   (
    ('has_digital_card',        BENEFIT_DIGITAL_CARD),
    ('has_free_shipping',       BENEFIT_FREE_SHIPPING),
    ('has_exclusive_discounts', BENEFIT_EXCLUSIVE_DISCOUNTS),
    ('has_exclusive_access',    BENEFIT_EXCLUSIVE_ACCESS),
)
#=========================================
# HELPERS INTERNOS
#=========================================
def _persisted(instance):
    #Solo una instancia con pk permite el lookup por FK — None, strings
    #de slug, dicts o instancias sin guardar devuelven queryset vacío.
    return instance is not None and getattr(instance, 'pk', None) is not None

def _vigente_subscriptions(customer, store, now = None):
    """
    QuerySet de las suscripciones que OTORGAN beneficios ahora mismo:
    status='active', vigente_hasta>now, membresía NO suspendida y del
    customer en ESA tienda. Tolerante a customer/store None o sin pk
    (devuelve queryset vacío).
    """
    if customer is None or store is None:
        return StoreSubscription.objects.none()
    if not (_persisted(customer) and _persisted(store)):
        return StoreSubscription.objects.none()
    now     =   now or timezone.now()
    return (
        StoreSubscription.objects
        .filter(
            membership__customer = customer,
            membership__store    = store,
            #Una membresía suspendida por el dueño corta los beneficios
            #aunque la suscripción siga 'active' — es la forma de castigo
            #del comercio sobre su cliente.
            membership__status   = StoreMembership.STATUS_ACTIVE,
            status               = StoreSubscription.STATUS_ACTIVE,
            vigente_hasta__gt    = now,
        )
        .select_related('plan')
    )
def is_vigente(subscription, now = None):
    """
    True si ESA suscripción está otorgando beneficios en `now`:
    status='active' + vigente_hasta>now + membresía NO suspendida
    (misma regla que _vigente_subscriptions, sobre una instancia).
    """
    if subscription is None:
        return False
    until   =   subscription.vigente_hasta
    membership   =   getattr(subscription, 'membership', None)
    return (
        subscription.status == StoreSubscription.STATUS_ACTIVE
        and until is not None
        and until > (now or timezone.now())
        and getattr(membership, 'status', None) == StoreMembership.STATUS_ACTIVE
    )
def plan_benefit_codes(plan):
    """Set de códigos de beneficio que habilita el plan (sin suscripción)."""
    if plan is None:
        return set()
    return {code for flag, code in _PLAN_FLAG_TO_BENEFIT if getattr(plan, flag, False)}
def store_display_name(store):
    """
    Nombre público de la tienda para tarjetas/payloads de members:
    display_name de la customización → business_name del perfil → slug.
    """
    customization    =   getattr(store, 'customization', None)
    display          =   getattr(customization, 'display_name', '') or ''
    if display.strip():
        return display.strip()
    profile          =   getattr(store, 'user', None)
    business         =   getattr(profile, 'business_name', '') or ''
    return business.strip() or store.slug
#=========================================
# CONTRATO — lectura de beneficios vigentes
#=========================================
def active_subscription_of(customer, store):
    """
    StoreSubscription vigente (status='active' y vigente_hasta>now) del
    customer en ESA tienda, o None. Si hubiera más de una (anomalía),
    gana la de mayor vigente_hasta.
    """
    return (
        _vigente_subscriptions(customer, store)
        .order_by('-vigente_hasta', '-id')
        .first()
    )
def member_benefits(customer, store):
    """
    Set de códigos de beneficio vigentes del customer en la tienda:
    subset de {'digital_card','free_shipping','exclusive_discounts',
    'exclusive_access'} — vacío sin plan vigente.
    """
    benefits    =   set()
    for subscription in _vigente_subscriptions(customer, store):
        benefits    |=   plan_benefit_codes(subscription.plan)
    return benefits
def member_discount_percent(customer, store):
    """
    % de descuento de miembro vigente (Decimal, 0-100). Si hay varios
    planes vigentes con exclusive_discounts gana el mayor; sin ninguno
    devuelve Decimal('0').
    """
    best    =   None
    for subscription in _vigente_subscriptions(customer, store):
        plan    =   subscription.plan
        if not plan.has_exclusive_discounts:
            continue
        percent =   plan.discount_percent or 0
        if best is None or percent > best:
            best    =   percent
    return best if best is not None else 0
def free_shipping_for(customer, store):
    """True si el plan vigente incluye envío gratis."""
    return BENEFIT_FREE_SHIPPING in member_benefits(customer, store)
def has_exclusive_access(customer, store):
    """True si el plan vigente incluye acceso a productos exclusivos."""
    return BENEFIT_EXCLUSIVE_ACCESS in member_benefits(customer, store)
#=========================================
# ESCRITURA — activación/renovación y baja de vigencia
#=========================================
def grant_period(subscription, actor = None, now = None):
    """
    Activa la suscripción y le otorga el período completo de su plan:
    started_at (si aún no tenía) y vigente_hasta = now + duration_days
    del plan. Devuelve la instancia guardada. La llama el endpoint
    owner .../activate/ (y cualquier futuro webhook de cobro) dentro de
    transaction.atomic + select_for_update — acá NO se bloquea: el lock
    es responsabilidad del caller.
    """
    now         =   now or timezone.now()
    plan        =   subscription.plan
    if plan is None:
        raise ValueError('La suscripción no tiene plan.')
    subscription.started_at      =   subscription.started_at or now
    subscription.vigente_hasta   =   now + timedelta(days = plan.duration_days())
    subscription.status          =   StoreSubscription.STATUS_ACTIVE
    subscription.save(update_fields = ['started_at', 'vigente_hasta', 'status', 'updated_at'])
    logger.info(
        'Suscripción de tienda activada: sub=%s plan=%s hasta=%s actor=%s',
        subscription.pk, plan.pk, subscription.vigente_hasta, actor,
    )
    return subscription
def expire_check(now = None, batch = 500):
    """
    Marca 'expired' las suscripciones 'active' ya vencidas — Cosmético
    para los listados del dueño (un 'active' con vigente_hasta pasado ya
    no da beneficios al leer). Devuelve cuántas actualizó. Opcional:
    los helpers no la necesitan; un cron diario puede llamarla.
    """
    now     =   now or timezone.now()
    stale   =   (
        StoreSubscription.objects
        .filter(status = StoreSubscription.STATUS_ACTIVE, vigente_hasta__lte = now)
        .values_list('pk', flat = True)[:batch]
    )
    return StoreSubscription.objects.filter(pk__in = stale).update(
        status = StoreSubscription.STATUS_EXPIRED, updated_at = now,
    )
