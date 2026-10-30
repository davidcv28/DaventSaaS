from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

"""

Creamos la base de los viewsets que utilizaremos del dominio Legal

"""

#=========================================
# CONTENT REPORT THROTTLE (denuncia pública -> email a legal: antispam)
#=========================================
class ContentReportRateThrottle(AnonRateThrottle):
    #Cada create válido dispara un correo a LEGAL_REPORTS_EMAIL: sin scope
    #propio quedaba limitado solo por el anon genérico (100/día) — vector
    #de email-bombing al buzón legal. Scope 'content_report' en settings.
    scope   =   'content_report'

#=========================================
# CONTENT REPORT BASE VIEWSET
#=========================================
class ContentReportBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    throttle_classes =  [ContentReportRateThrottle]
    def get_action_key(self):
        if self.action == 'create':
            return 'create'
        if self.action in ('update', 'partial_update'):
            return 'update'
        return 'get'
    def get_serializer_class(self):
        return self.viewset_config[self.get_action_key()]['serializer']
    def get_queryset(self):
        queryset    =   self.viewset_config[self.get_action_key()]['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        permissions     =   self.viewset_config[self.get_action_key()]['permissions']
        return [permission() for permission in permissions]
    #=========================================
    # LIST METHOD (listado de denuncias - solo admin)
    #=========================================
    def list(self, request, *args, **kwargs):
        queryset    =   self.filter_queryset(self.get_queryset())
        page        =   self.paginate_queryset(queryset)
        if page is not None:
            serializer  =   self.get_serializer(page, many = True)
            return self.get_paginated_response(serializer.data)
        serializer      =   self.get_serializer(queryset, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # RETRIEVE METHOD (detalle de denuncia - solo admin)
    #=========================================
    def retrieve(self, request, *args, **kwargs):
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # CREATE METHOD (denuncia pública - AllowAny)
    #=========================================
    def create(self, request):
        serializer  =   self.get_serializer(data = request.data, context = {'request': request})
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' :   self.viewset_config['create']['message']
            }, status = status.HTTP_201_CREATED
        )
    #=========================================
    # UPDATE METHOD (estado y notas internas - solo admin)
    #=========================================
    def update(self, request, pk = None):
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance, data = request.data, context = {'request': request}, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' :   self.viewset_config['update']['message']
            }, status = status.HTTP_200_OK
        )
    def partial_update(self, request, pk = None):
        #Sin este método el PATCH del panel admin devolvía 405: la gestión
        #de denuncias solo respondía a PUT.
        return self.update(request, pk)
