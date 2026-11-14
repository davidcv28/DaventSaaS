import base64
import secrets
from datetime import timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.text import slugify

from StoreApp.domains.pos.models import PosApp, PosDevice, PosPairingCode

"""
Servicios del dominio POS (PLAN_POS).

Dos credenciales distintas, a propósito:
- device_token: JWT HS256 con clave de SERVIDOR (POS_DEVICE_TOKEN_KEY —
  nunca viaja al binario). Identifica al dispositivo y es revocable por
  PosDevice.revoked_at.
- licencia: JWT EdDSA Ed25519 con POS_LICENSE_PRIVATE_KEY_B64. La app
  embebe la CLAVE PÚBLICA y verifica firma+fecha sin internet — por eso
  nunca HS256 acá (el secreto compartido terminaría dentro del binario).
"""

#Alfabeto sin caracteres ambiguos (sin 0/O, 1/I/L): el dueño tipea el
#código a mano en la app de mostrador.
PAIR_CODE_ALPHABET        =   'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
PAIR_CODE_LENGTH          =   8
PAIR_CODE_TTL             =   timedelta(minutes = 10)

DEVICE_TOKEN_TYPE         =   'pos_device'
LICENSE_ISSUER            =   'davent'
LICENSE_TTL               =   timedelta(days = 45)
#Días de aviso entre 'denied' y el bloqueo operativo de la app (§8.1:
#"al menos cinco (5) días de anticipación").
DENIED_GRACE              =   timedelta(days = 5)

#Ranking de tiers del catálogo: PosApp.tier_min <= plan vigente. Las
#claves son slugs de PlanPresentation; un plan desconocido no alcanza
#para ninguna app y un tier_min desconocido oculta la entrada.
TIER_RANK                 =   {
    'basico'    :   0,
    'estandar'  :   1,
    'premium'   :   2,
    'ecommerce' :   3,
}
GENERAL_RUBRO             =   'general'

#=========================================
# PLAN DEL DUEÑO (slug + estado del beneficio POS)
#=========================================
def plan_slug_of(profile):
    """
    Slug del plan vigente del perfil (PlanPresentation.slug; si la fila
    de presentación no existe se deriva del name — 'Plan ecommerce' →
    'ecommerce'). None si no hay suscripción cargada.
    """
    suscription =   getattr(profile, 'suscription', None)
    if suscription is None:
        return None
    plan        =   suscription.plan_suscription
    try:
        return plan.presentation.slug
    except Exception:
        return slugify(plan.name).removeprefix('plan-') or slugify(plan.name)

def license_state(profile):
    """
    (status, denied_reason, plan_slug) para el claim de la licencia.

    'active' solo con suscripción vigente (grants_access: status + fecha
    + gracia de débito) Y flag has_pos_app del plan. Suscripción vencida
    o ausente → 'plan_expired'; vigente pero sin el flag (downgrade) →
    'plan_changed'.
    """
    from StoreApp.domains.stores.services import profile_has_benefit
    suscription =   getattr(profile, 'suscription', None)
    plan_slug   =   plan_slug_of(profile)
    if suscription is None or not suscription.grants_access():
        return 'denied', 'plan_expired', plan_slug
    if not profile_has_benefit(profile, 'has_pos_app'):
        return 'denied', 'plan_changed', plan_slug
    return 'active', None, plan_slug
#=========================================
# RUBRO DE LA TIENDA (diseño elegido → DesignCategory)
#=========================================
def store_rubro(store):
    """
    Rubro de la tienda como slug de DesignCategory: primero el patrón
    activo (customization.template = slug de DesignPattern), después el
    estilo elegido (site_theme.style.id = slug de DesignStyle). Sin
    diseño elegido cae a 'general'.
    """
    customization   =   getattr(store, 'customization', None)
    if customization is None:
        return GENERAL_RUBRO
    from StoreApp.domains.design.models import DesignPattern, DesignStyle
    template    =   (customization.template or '').strip()
    if template:
        categoria   =   DesignPattern.objects.filter(slug = template).values_list('categoria__slug', flat = True).first()
        if categoria:
            return categoria
    site_theme  =   customization.site_theme if isinstance(customization.site_theme, dict) else {}
    style_id    =   (site_theme.get('style') or {}).get('id') or ''
    if isinstance(style_id, str) and style_id.strip():
        categoria   =   DesignStyle.objects.filter(slug = style_id.strip()).values_list('categoria__slug', flat = True).first()
        if categoria:
            return categoria
    return GENERAL_RUBRO
#=========================================
# CATÁLOGO VISIBLE (plan + rubro)
#=========================================
def catalog_for(store):
    """
    Apps activas visibles para la tienda: tier_min <= plan vigente del
    dueño Y (rubro de la tienda ∈ rubros, o la app trae 'general'). Una
    tienda sin diseño elegido (rubro 'general') ve todo el catálogo que
    su plan alcanza — la indecisión no la penaliza (PLAN_POS §1).
    """
    plan_rank   =   TIER_RANK.get(plan_slug_of(store.user) or '', -1)
    rubro       =   store_rubro(store)
    apps        =   []
    for app in PosApp.objects.filter(is_active = True).order_by('position', 'id'):
        if TIER_RANK.get(app.tier_min, 99) > plan_rank:
            continue
        rubros  =   set(app.rubros or [])
        if rubro != GENERAL_RUBRO and rubro not in rubros and GENERAL_RUBRO not in rubros:
            continue
        apps.append(app)
    return apps
#=========================================
# CÓDIGO DE VINCULACIÓN (un solo uso, 10 min)
#=========================================
def create_pairing_code(store, user):
    """
    Nuevo código para la tienda. Los códigos previos sin usar quedan
    anulados (used_at = ahora — así nunca hay dos códigos vivos y la
    fila queda como auditoría del reemplazo).
    """
    now     =   timezone.now()
    store.pos_pairing_codes.filter(used_at__isnull = True).update(used_at = now)
    code    =   ''.join(secrets.choice(PAIR_CODE_ALPHABET) for _ in range(PAIR_CODE_LENGTH))
    return PosPairingCode.objects.create(
        store       =   store,
        code        =   code,
        expires_at  =   now + PAIR_CODE_TTL,
        created_by  =   user,
    )

def redeem_pairing_code(code, device_name):
    """
    Canjea el código: vigente + sin usar → PosDevice nuevo y el código
    quemado atómicamente (el update condicionado evita el doble canje en
    requests concurrentes). None si el código no existe, venció o ya se
    usó — mismo resultado para no filtrar cuál falló.
    """
    normalized  =   str(code or '').strip().upper()
    if not normalized:
        return None
    now         =   timezone.now()
    row         =   PosPairingCode.objects.select_related('store').filter(
        code            =   normalized,
        used_at__isnull =   True,
        expires_at__gt  =   now,
    ).first()
    if row is None:
        return None
    claimed =   PosPairingCode.objects.filter(pk = row.pk, used_at__isnull = True).update(used_at = now)
    if not claimed:
        return None
    return PosDevice.objects.create(store = row.store, name = str(device_name or '').strip()[:120])
#=========================================
# DEVICE TOKEN (JWT HS256, clave de servidor)
#=========================================
def issue_device_token(device):
    """JWT {typ, store_id, device_id, iat} firmado con la clave dedicada."""
    now     =   timezone.now()
    payload =   {
        'typ'       :   DEVICE_TOKEN_TYPE,
        'store_id'  :   device.store_id,
        'device_id' :   str(device.device_id),
        'iat'       :   int(now.timestamp()),
    }
    return jwt.encode(payload, settings.POS_DEVICE_TOKEN_KEY, algorithm = 'HS256')

def decode_device_token(token):
    """Payload del device_token o None (firma inválida, expirado, mal typ)."""
    try:
        payload =   jwt.decode(str(token or ''), settings.POS_DEVICE_TOKEN_KEY, algorithms = ['HS256'])
    except jwt.PyJWTError:
        return None
    if payload.get('typ') != DEVICE_TOKEN_TYPE:
        return None
    return payload

def device_from_request(request):
    """
    PosDevice del header 'Authorization: Bearer <device_token>' o None.
    Valida firma + que el par (store_id, device_id) exista.
    """
    header  =   (request.META.get('HTTP_AUTHORIZATION') or '').strip()
    if not header.startswith('Bearer '):
        return None
    payload =   decode_device_token(header[7:].strip())
    if payload is None:
        return None
    return PosDevice.objects.select_related('store__user').filter(
        device_id   =   payload.get('device_id'),
        store_id    =   payload.get('store_id'),
    ).first()
#=========================================
# LICENCIA (JWT EdDSA Ed25519 — la app la verifica offline)
#=========================================
_license_keys   =   {}

def _license_private_key():
    """
    Ed25519PrivateKey desde POS_LICENSE_PRIVATE_KEY_B64 (base64 del seed
    crudo de 32 bytes). Cacheada por valor: un override_settings en tests
    o una rotación de clave reconstruye la entrada sin estado viejo.
    """
    raw_b64 =   str(getattr(settings, 'POS_LICENSE_PRIVATE_KEY_B64', '') or '').strip()
    key     =   _license_keys.get(raw_b64)
    if key is not None:
        return key
    try:
        raw     =   base64.b64decode(raw_b64, validate = True)
    except Exception:
        raw     =   b''
    if len(raw) != 32:
        raise ImproperlyConfigured(
            'POS_LICENSE_PRIVATE_KEY_B64 debe ser base64 de la clave Ed25519 (32 bytes crudos).'
        )
    key =   Ed25519PrivateKey.from_private_bytes(raw)
    _license_keys[raw_b64]  =   key
    return key

def issue_license(device):
    """
    Licencia firmada del dispositivo. Claims per PLAN_POS §2: status
    'active' solo con plan vigente + has_pos_app; 'denied' declara el
    motivo y grace_until (+5d de aviso). La integridad viaja EN el JWT —
    la app solo respeta el modo degradado si el token firmado lo declara.
    """
    now                 =   timezone.now()
    iat                 =   int(now.timestamp())
    status_, reason, plan_slug  =   license_state(device.store.user)
    claims              =   {
        'iss'           :   LICENSE_ISSUER,
        'store_id'      :   device.store_id,
        'device_id'     :   str(device.device_id),
        'plan'          :   plan_slug,
        'status'        :   status_,
        'denied_reason' :   reason,
        'iat'           :   iat,
        'exp'           :   iat + int(LICENSE_TTL.total_seconds()),
        'grace_until'   :   (now + DENIED_GRACE).isoformat() if status_ == 'denied' else None,
    }
    return jwt.encode(claims, _license_private_key(), algorithm = 'EdDSA')
