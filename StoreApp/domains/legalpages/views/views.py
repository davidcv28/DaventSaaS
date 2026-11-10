import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import ResilientAnonRateThrottle
from StoreApp.domains.legalpages.models import ReturnRequest, StoreLegalPage
from StoreApp.domains.legalpages.serializers import (
    LegalPageWriteSerializer,
    ReturnRequestCreateSerializer,
    ReturnRequestSerializer,
    ReturnRequestStatusSerializer,
)
from StoreApp.domains.legalpages.services import (
    legal_detail_payload,
    legal_page_payload,
    notify_return_request,
    public_store_or_404,
    save_legal_page,
)
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.public_cache import bump_public_store
from StoreApp.domains.stores.services import issue_captcha, verify_captcha

"""
Vistas del dominio legalpages.

Dueño (JWT, IDOR 404 — solo SU tienda):
- GET  /api/store-legal-pages/                  → las 3 páginas (defaults si no existen)
- PUT  /api/store-legal-pages/<kind>/           → guardar página (terms|privacy|returns)
- POST /api/store-legal-pages/<kind>/reset/     → volver al texto base
- GET  /api/store-legal-pages/returns/          → bandeja de solicitudes (?status=)
- PUT  /api/store-legal-pages/returns/          → edita la página legal 'returns'
- POST /api/store-legal-pages/returns/<id>/status/ → gestiona estado de una solicitud

Público (sin auth, throttles + captcha en el POST):
- GET  /api/stores/public/<slug>/legal/                  → índice de páginas publicadas
- GET  /api/stores/public/<slug>/legal/<kind>/           → página con datos fiscales interpolados
- GET  /api/stores/public/<slug>/legal/captcha/          → challenge del formulario
- POST /api/stores/public/<slug>/legal/returns/request/  → solicitud de devolución (201 siempre)
"""
logger  =   logging.getLogger(__name__)
#=========================================
# THROTTLES
#=========================================
class LegalPublicReadThrottle(ResilientAnonRateThrottle):
    #Lecturas públicas: mismo scope holgado que el resto de la web de la
    #tienda (public_read = 1000/hour por IP).
    scope   =   'public_read'

class ReturnRequestThrottle(ResilientAnonRateThrottle):
    #Alta de solicitudes: scope antispam de formularios públicos. Se
    #reutiliza 'store_contact' (10/hour) — DEFAULT_THROTTLE_RATES vive en
    #settings.py (orquestador) y no se toca por track; si se quiere un
    #scope propio ('store_return_request') se agrega ahí.
    scope   =   'store_contact'
#=========================================
# HELPERS
#=========================================
def _own_store(request):
    """La tienda del usuario autenticado; sin tienda o ajena → 404."""
    return get_object_or_404(
        Store.objects.select_related('user__user', 'customization', 'fiscal_profile'),
        user__user = request.user,
    )

def _kind_or_404(kind):
    if kind not in StoreLegalPage.KIND_LABELS:
        raise Http404
    return kind
#=========================================
# VISTAS DEL DUEÑO
#=========================================
class StoreLegalPagesView(APIView):
    """GET /api/store-legal-pages/ — las 3 páginas de SU tienda."""
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   _own_store(request)
        pages   =   StoreLegalPage.get_or_create_defaults(store)
        return Response({'pages': [legal_page_payload(page, store) for page in pages]}, status = status.HTTP_200_OK)

class StoreLegalPageDetailView(APIView):
    """PUT /api/store-legal-pages/<kind>/ — guarda título/cuerpo/publicación."""
    permission_classes    =   [IsAuthenticated]
    def put(self, request, kind):
        _kind_or_404(kind)
        store       =   _own_store(request)
        serializer  =   LegalPageWriteSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        page, _     =   save_legal_page(store, kind, serializer.validated_data)
        bump_public_store(store.pk)
        return Response(legal_page_payload(page, store), status = status.HTTP_200_OK)

class StoreLegalPageResetView(APIView):
    """POST /api/store-legal-pages/<kind>/reset/ — vuelve al texto base."""
    permission_classes    =   [IsAuthenticated]
    def post(self, request, kind):
        _kind_or_404(kind)
        store   =   _own_store(request)
        deleted, _   =   StoreLegalPage.objects.filter(store = store, kind = kind).delete()
        if deleted:
            #La página vuelve a servirse desde el default y queda
            #despublicada hasta que el dueño la publique de nuevo.
            bump_public_store(store.pk)
        return Response({'ok': True, 'kind': kind}, status = status.HTTP_200_OK)

class ReturnRequestsView(APIView):
    """
    GET  /api/store-legal-pages/returns/ → bandeja de SU tienda (?status=).
    PUT  /api/store-legal-pages/returns/ → edita la página legal 'returns'
    ('returns' es kind de página y bandeja a la vez: mismo path del
    contrato, se despacha por método).
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store           =   _own_store(request)
        queryset        =   store.return_requests.all()
        status_filter   =   (request.query_params.get('status') or '').strip()
        if status_filter:
            if status_filter not in dict(ReturnRequest.STATUS_CHOICES):
                return Response({'status': ['Estado inválido.']}, status = status.HTTP_400_BAD_REQUEST)
            queryset    =   queryset.filter(status = status_filter)
        data            =   ReturnRequestSerializer(queryset[:500], many = True).data
        return Response({'results': data}, status = status.HTTP_200_OK)
    def put(self, request):
        store       =   _own_store(request)
        serializer  =   LegalPageWriteSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        page, _     =   save_legal_page(store, StoreLegalPage.KIND_RETURNS, serializer.validated_data)
        bump_public_store(store.pk)
        return Response(legal_page_payload(page, store), status = status.HTTP_200_OK)

class ReturnRequestStatusView(APIView):
    """POST /api/store-legal-pages/returns/<id>/status/ — gestiona el estado."""
    permission_classes    =   [IsAuthenticated]
    def post(self, request, pk):
        store       =   _own_store(request)
        req         =   get_object_or_404(store.return_requests, pk = pk)
        serializer  =   ReturnRequestStatusSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        target      =   serializer.validated_data['status']
        if target == req.status:
            return Response(ReturnRequestSerializer(req).data, status = status.HTTP_200_OK)
        if not ReturnRequest.can_transition(req.status, target):
            return Response(
                {'status': [f'No se puede pasar de "{req.get_status_display()}" a "{dict(ReturnRequest.STATUS_CHOICES).get(target, target)}".']},
                status = status.HTTP_400_BAD_REQUEST,
            )
        req.status  =   target
        req.save(update_fields = ['status', 'updated_at'])
        return Response(ReturnRequestSerializer(req).data, status = status.HTTP_200_OK)
#=========================================
# VISTAS PÚBLICAS (visitante anónimo de la web de la tienda)
#=========================================
class PublicLegalIndexView(APIView):
    """GET /api/stores/public/<slug>/legal/ — índice de páginas publicadas."""
    authentication_classes =   []
    permission_classes      =   [AllowAny]
    throttle_classes        =   [LegalPublicReadThrottle]
    def get(self, request, slug):
        store   =   public_store_or_404(slug)
        pages   =   {page.kind: page for page in StoreLegalPage.objects.filter(store = store, is_published = True)}
        index   =   []
        for kind, _label in StoreLegalPage.KIND_CHOICES:
            page    =   pages.get(kind)
            if page is None:
                continue
            title   =   legal_page_payload(page, store, public = True)['title']
            index.append({
                'kind'          :   kind,
                'kind_label'    :   StoreLegalPage.KIND_LABELS[kind],
                'title'         :   title,
                'updated_at'    :   page.updated_at.isoformat() if page.updated_at else None,
                'version'       :   page.version or 1,
            })
        return Response({'pages': index}, status = status.HTTP_200_OK)

class PublicLegalPageView(APIView):
    """GET /api/stores/public/<slug>/legal/<kind>/ — página con fiscales."""
    authentication_classes =   []
    permission_classes      =   [AllowAny]
    throttle_classes        =   [LegalPublicReadThrottle]
    def get(self, request, slug, kind):
        store   =   public_store_or_404(slug)
        page    =   get_object_or_404(StoreLegalPage, store = store, kind = kind, is_published = True)
        return Response(legal_detail_payload(page, store), status = status.HTTP_200_OK)

class PublicLegalCaptchaView(APIView):
    """GET /api/stores/public/<slug>/legal/captcha/ — challenge antispam."""
    authentication_classes =   []
    permission_classes      =   [AllowAny]
    throttle_classes        =   [LegalPublicReadThrottle]
    def get(self, request, slug):
        #Solo tiendas públicas válidas pueden pedir challenge (404 si no).
        public_store_or_404(slug)
        return Response(issue_captcha(slug), status = status.HTTP_200_OK)

class PublicReturnRequestView(APIView):
    """
    POST /api/stores/public/<slug>/legal/returns/request/ — solicitud de
    devolución del comprador. Respuesta SIEMPRE genérica (201 {"ok": true})
    para no revelar si el order_ref existe o la tienda vende.
    """
    authentication_classes =   []
    permission_classes      =   [AllowAny]
    throttle_classes        =   [ReturnRequestThrottle]
    def post(self, request, slug):
        store       =   public_store_or_404(slug)
        serializer  =   ReturnRequestCreateSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        #Honeypot: éxito falso sin persistir nada (mismo criterio que
        #contacto y opiniones).
        if data.get('website'):
            return Response({'ok': True}, status = status.HTTP_201_CREATED)
        if not verify_captcha(slug, data['challenge_id'], data['captcha_answer']):
            return Response(
                {'captcha_answer': 'El captcha venció o la respuesta no es correcta. Probá de nuevo.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        req         =   ReturnRequest.objects.create(
            store           =   store,
            order_ref       =   data.get('order_ref') or '',
            customer_email  =   data['email'],
            name            =   data['name'],
            document        =   data['document'],
            phone           =   data['phone'],
            address         =   data['address'],
            reason          =   data['reason'],
            details         =   data.get('details') or '',
        )
        notify_return_request(store, req)
        return Response({'ok': True}, status = status.HTTP_201_CREATED)
