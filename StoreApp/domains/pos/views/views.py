import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import ResilientAnonRateThrottle
from StoreApp.domains.pos.models import PosDevice
from StoreApp.domains.pos.serializers import PosAppSerializer, PosPairSerializer
from StoreApp.domains.pos.services import (
    catalog_for,
    create_pairing_code,
    device_from_request,
    issue_device_token,
    issue_license,
    redeem_pairing_code,
    rubro_options,
    store_rubro,
)
from StoreApp.domains.stores.models import Store

"""
Vistas del dominio POS (PLAN_POS §2/§4).

Dueño (JWT, IDOR 404 — solo SU tienda):
- POST /api/pos/pair-code/ → {code, expires_at} — código de vinculación
  de 8 chars, expira 10 min, un solo uso. Exige has_pos_app del plan.
- GET  /api/pos/apps/      → catálogo PosApp filtrado por plan + rubro.

Dispositivo (sin sesión DAVENT — el código/token es la única llave):
- POST /api/pos/pair/    → {device_token} — canje del código, rate-limited.
- POST /api/pos/license/ → {license} — licencia JWT EdDSA (la app la
  verifica offline con la clave pública embebida).
"""
logger  =   logging.getLogger(__name__)
#=========================================
# THROTTLES
#=========================================
class PosPairThrottle(ResilientAnonRateThrottle):
    """
    Canje del código de vinculación: bucket por CÓDIGO (5/min — PLAN_POS
    §7, el código tiene 10 min de vida así que el límite por código es
    efectivamente por tienda). Sin código en el body el bucket cae a IP.
    """
    scope   =   'pos_pair'

    def get_cache_key(self, request, view):
        code    =   str((request.data or {}).get('code') or '').strip().upper()
        ident   =   code or self.get_ident(request)
        return  'throttle_%s_%s' % (self.scope, ident)

class PosPairIpThrottle(ResilientAnonRateThrottle):
    """
    Bucket por IP del mismo canje: sin él un atacante que rota el valor
    de `code` abriría un bucket nuevo por intento y el límite por código
    no acotaría la enumeración de códigos ajenos.
    """
    scope   =   'pos_pair'
#=========================================
# HELPERS
#=========================================
def _own_store(request, *, pos_benefit = False):
    """
    La tienda del usuario autenticado; sin tienda → 404 (IDOR). Con
    pos_benefit=True exige además el flag has_pos_app del plan vigente
    → 403 (la tienda ES suya, lo que falta es el beneficio).
    """
    store   =   get_object_or_404(
        Store.objects.select_related('user', 'customization'),
        user__user = request.user,
    )
    if pos_benefit:
        from StoreApp.domains.stores.services import profile_has_benefit
        if not profile_has_benefit(store.user, 'has_pos_app'):
            raise PermissionDenied('Tu plan no incluye la app de mostrador.')
    return store
#=========================================
# VISTAS DEL DUEÑO
#=========================================
class PosPairCodeView(APIView):
    """POST /api/pos/pair-code/ — genera el código de vinculación de SU tienda."""
    permission_classes    =   [IsAuthenticated]
    def post(self, request):
        store   =   _own_store(request, pos_benefit = True)
        row     =   create_pairing_code(store, request.user)
        return Response({'code': row.code, 'expires_at': row.expires_at}, status = status.HTTP_201_CREATED)

class PosAppsView(APIView):
    """
    GET /api/pos/apps/ — catálogo filtrado por plan + rubro de SU tienda.
    ?rubro=<slug> pisa el rubro derivado del diseño (el dueño puede
    explorar apps de otros rubros desde el selector de la card).
    Responde {rubro, rubros, apps}.
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   _own_store(request)
        derived =   store_rubro(store)
        rubro   =   str(request.query_params.get('rubro') or '').strip() or derived
        return Response({
            'rubro'     :   rubro,
            'rubros'    :   rubro_options(),
            'apps'      :   PosAppSerializer(catalog_for(store, rubro = rubro), many = True).data,
        }, status = status.HTTP_200_OK)
#=========================================
# VISTAS DEL DISPOSITIVO (anónimas — el código/token es la credencial)
#=========================================
class PosPairView(APIView):
    """
    POST /api/pos/pair/ — canjea {code, device_name} por un device_token
    (JWT HS256, long-lived, revocable vía PosDevice.revoked_at).
    """
    authentication_classes    =   []
    permission_classes        =   [AllowAny]
    throttle_classes          =   [PosPairThrottle, PosPairIpThrottle]
    def post(self, request):
        serializer  =   PosPairSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        device      =   redeem_pairing_code(
            serializer.validated_data['code'],
            serializer.validated_data['device_name'],
        )
        if device is None:
            #Mensaje genérico: no revela si el código existe, venció o ya
            #se usó (el endpoint es anónimo — nada de oráculo de códigos).
            return Response(
                {'code': ['El código no es válido, venció o ya fue usado.']},
                status = status.HTTP_400_BAD_REQUEST,
            )
        return Response({'device_token': issue_device_token(device)}, status = status.HTTP_201_CREATED)

class PosLicenseView(APIView):
    """
    POST /api/pos/license/ — device_token (Bearer) → licencia JWT EdDSA.
    Dispositivo desvinculado (revoked_at) → 403, no emite licencia.
    """
    authentication_classes    =   []
    permission_classes        =   [AllowAny]
    def post(self, request):
        device  =   device_from_request(request)
        if device is None:
            return Response(
                {'detail': 'Credencial de dispositivo inválida.'},
                status = status.HTTP_401_UNAUTHORIZED,
            )
        if device.revoked_at is not None:
            return Response(
                {'detail': 'Este dispositivo fue desvinculado.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        license_jwt =   issue_license(device)
        PosDevice.objects.filter(pk = device.pk).update(last_seen_at = timezone.now())
        return Response({'license': license_jwt}, status = status.HTTP_200_OK)
