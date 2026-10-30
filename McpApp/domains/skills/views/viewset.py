import json

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from McpApp.domains.skills.models import DesignModelMcp
from McpApp.domains.skills.serializers import (
    DesignStyleListSerializer,
    DesignStyleSerializer,
)
from McpApp.domains.skills.services import (
    SERVER_NAME,
    SERVER_VERSION,
    call_tool,
    catalog_summary,
    list_categories,
    search_design_styles,
    tools_list,
)

"""
Views del dominio skills + endpoint MCP (JSON-RPC sobre HTTP).

- Lectura del catálogo: cualquier usuario autenticado.
- Alta/edición/baja: solo staff.
- /api/mcp/: el mismo contrato que el servidor stdio, para agentes
  remotos autenticados (staff).
"""

#=========================================
# DESIGN STYLE VIEWSET
#=========================================
class DesignStyleViewSet(viewsets.ModelViewSet):
    queryset            =   DesignModelMcp.objects.all()
    serializer_class    =   DesignStyleSerializer
    permission_classes  =   [IsAuthenticated]
    lookup_field        =   'slug'
    lookup_value_regex  =   '[^/]+'

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return DesignStyleListSerializer
        return DesignStyleSerializer

    def get_queryset(self):
        qs      =   super().get_queryset()
        query   =   self.request.query_params.get('q', '').strip()
        if query and self.action == 'list':
            return qs.filter(
                Q(slug__icontains = query)
                | Q(nombre__icontains = query)
                | Q(tags__icontains = query)
            )
        return qs

    @action(detail = False, methods = ['get'], url_path = 'search')
    def search(self, request):
        rows    =   search_design_styles(
            query       =   request.query_params.get('q', ''),
            categoria   =   request.query_params.get('categoria', ''),
            tags        =   [t for t in request.query_params.get('tags', '').split(',') if t],
            limit       =   request.query_params.get('limit', 10),
        )
        return Response({'styles': DesignStyleListSerializer(rows, many = True).data})

    @action(detail = False, methods = ['get'], url_path = 'categories')
    def categories(self, request):
        return Response({'categories': list_categories()})

    @action(detail = False, methods = ['get'], url_path = 'catalog')
    def catalog(self, request):
        return Response({'catalog': catalog_summary(limit = request.query_params.get('limit', 50))})


#=========================================
# MCP ENDPOINT — POST /api/mcp/
#=========================================
class McpEndpointView(APIView):
    permission_classes  =   [IsAuthenticated]

    def post(self, request):
        payload =   request.data if isinstance(request.data, dict) else {}
        method  =   payload.get('method', '')
        msg_id  =   payload.get('id')
        params  =   payload.get('params') or {}

        if method == 'initialize':
            result  =   {
                'protocolVersion'   :   '2024-11-05',
                'capabilities'      :   {'tools': {}},
                'serverInfo'        :   {'name': SERVER_NAME, 'version': SERVER_VERSION},
            }
        elif method == 'tools/list':
            result  =   {'tools': tools_list()}
        elif method == 'tools/call':
            try:
                result  =   call_tool(params.get('name', ''), params.get('arguments') or {})
            except ValueError as exc:
                return Response({
                    'jsonrpc': '2.0', 'id': msg_id,
                    'error': {'code': -32602, 'message': str(exc)},
                }, status = status.HTTP_400_BAD_REQUEST)
            result  =   {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii = False)}]}
        elif method == 'ping':
            result  =   {}
        else:
            return Response({
                'jsonrpc': '2.0', 'id': msg_id,
                'error': {'code': -32601, 'message': f'Método no soportado: {method}'},
            }, status = status.HTTP_400_BAD_REQUEST)

        return Response({'jsonrpc': '2.0', 'id': msg_id, 'result': result})
