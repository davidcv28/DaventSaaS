from SuscriptionApp.domains.benefits.models import Benefit
"""

Servicios del dominio Stores.

Los beneficios del plan vigente (SuscriptionApp/benefits) son la fuente
de verdad para forzar del lado del servidor qué puede editar cada
cliente en su web pública.

"""
SUSCRIPTION_STATUS_ACTIVE   =   'Suscripción activa'
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
    if suscription is None or suscription.status != SUSCRIPTION_STATUS_ACTIVE:
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
