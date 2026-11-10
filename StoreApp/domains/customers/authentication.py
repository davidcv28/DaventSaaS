"""
Autenticación JWT de compradores (e-commerce DAVENT).

`CustomerJWTAuthentication` lee `Authorization: Bearer <jwt>` y valida el
token emitido por customer-auth (firma SECRET_KEY + exp +
`token_type='customer_access'` + claim `customer_id`). Setea
`request.customer` y devuelve el Customer como `request.user` (el modelo
expone `is_authenticated`/`is_anonymous` para que los permisos DRF lo
traten como usuario autenticado).

Un token DAVENT (auth.User) NO pasa: su `token_type` es 'access' y no
lleva `customer_id` — y viceversa, un `customer_access` no autentica los
endpoints SaaS (JWTAuthentication exige 'access' y busca `user_id`).

`IsCustomer` es el permiso de las vistas autenticadas del dominio.
"""
from datetime import UTC, datetime

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.exceptions import TokenError

from StoreApp.domains.customers.models import Customer
from StoreApp.domains.customers.services.tokens import parse_access_token


def customer_session_valid(customer, token):
    """
    Revocación global post-reset de contraseña: si el token se emitió
    antes de `customer.tokens_valid_after`, la sesión está muerta aunque
    el JWT no haya expirado ni esté en blacklist.
    """
    valid_after  =   customer.tokens_valid_after
    if valid_after is None:
        return True
    iat          =   token.get('iat')
    if iat is None:
        return False
    issued_at    =   datetime.fromtimestamp(int(iat), tz = UTC)
    return issued_at >= valid_after


class CustomerJWTAuthentication(BaseAuthentication):
    """Bearer JWT de comprador → request.customer / request.user."""

    def authenticate_header(self, request):
        #Sin esto DRF degrada los 401 a 403 (no puede emitir
        #WWW-Authenticate). El esquema es Bearer — el access token viaja
        #en el header, no en cookie.
        return 'Bearer'

    def authenticate(self, request):
        header  =   request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        raw     =   header[7:].strip()
        if not raw:
            return None
        try:
            token   =   parse_access_token(raw)
        except TokenError as exc:
            raise AuthenticationFailed('Token de cliente inválido o expirado.') from exc
        customer_id    =   token.get('customer_id')
        if not customer_id:
            raise AuthenticationFailed('Token sin identidad de cliente.')
        customer        =   Customer.objects.filter(pk = customer_id, is_active = True).first()
        if customer is None:
            raise AuthenticationFailed('La cuenta de cliente no existe o está inactiva.')
        if not customer_session_valid(customer, token):
            raise AuthenticationFailed('La sesión fue revocada. Iniciá sesión de nuevo.')
        request.customer    =   customer
        return customer, token


class IsCustomer(BasePermission):
    """Solo cuentas de comprador autenticadas (request.customer)."""
    message = 'Autenticación de cliente requerida.'

    def has_permission(self, request, view):
        return isinstance(getattr(request, 'customer', None), Customer) and request.customer.is_active
