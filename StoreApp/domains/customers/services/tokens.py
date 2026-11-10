"""
JWT de compradores (e-commerce DAVENT).

Tokens propios firmados con el mismo SECRET_KEY que los de DAVENT pero
con `token_type` propio — un access de comprador JAMÁS autentica contra
los endpoints SaaS (JWTAuthentication de SimpleJWT exige 'access'/'refresh'
y además nuestros claims no existen en los tokens de auth.User) y
viceversa: un token DAVENT no pasa `CustomerJWTAuthentication`.

Desviación documentada del spec (`token_type='customer'`): SimpleJWT
RESERVA el claim `token_type` para discriminar access vs refresh
(`verify_token_type` exige coincidencia exacta con la clase que parsea).
Un solo valor 'customer' para ambos tipos haría que un REFRESH de 30 días
se aceptara como access. Por eso los tipos son 'customer_access' y
'customer_refresh': siguen marcando el token como de comprador y la
dicotomía access/refresh queda intacta.

Claims: `customer_id` (pk de Customer — NO `user_id`, que SimpleJWT usa
para auth.User) + jti/iat/exp estándar.
"""
from datetime import timedelta

from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

#Access 30 min + refresh 30 días — el SPA renueva en silencio (cookie
#httpOnly + single-flight), así que el comprador no re-loguea, pero un
#access filtrado pre-logout solo sobrevive como mucho 30 min (la ventana
#residual del logout era 12 h — security audit run-1).
CUSTOMER_ACCESS_LIFETIME      =   timedelta(minutes = 30)
CUSTOMER_REFRESH_LIFETIME     =   timedelta(days = 30)


class CustomerAccessToken(AccessToken):
    token_type  =   'customer_access'
    lifetime    =   CUSTOMER_ACCESS_LIFETIME


class CustomerRefreshToken(RefreshToken):
    token_type  =   'customer_refresh'
    lifetime    =   CUSTOMER_REFRESH_LIFETIME


def issue_customer_tokens(customer):
    """
    Emite el par (access_str, refresh_token). El access viaja en el body
    (lo guarda el front en memoria); el refresh viaja SOLO en cookie
    httpOnly `customer_refresh` + rotación por blacklist en cada refresh.
    """
    access      =   CustomerAccessToken()
    access['customer_id']   =   customer.pk
    refresh     =   CustomerRefreshToken()
    refresh['customer_id']  =   customer.pk
    return str(access), refresh


def parse_access_token(raw_token):
    """Valida firma+exp+tipo; devuelve el CustomerAccessToken o lanza TokenError."""
    return CustomerAccessToken(raw_token)


def parse_refresh_token(raw_token):
    """
    Valida firma+exp+tipo+blacklist (BlacklistMixin de RefreshToken); el
    OutstandingToken se crea con user=None porque el claim es
    `customer_id`, no `user_id` — la columna user es nullable.
    """
    return CustomerRefreshToken(raw_token)
