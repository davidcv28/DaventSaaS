from rest_framework import viewsets, status
from rest_framework.response import Response

"""

Creamos la base de los viewsets que utilizaremos del dominio Payments

"""

#=========================================
# PAYMENT BASE VIEWSET
#=========================================
class PaymentBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    def get_action_key(self):
        if self.action == 'create':
            return 'create'
        if self.action in ('update', 'partial_update', 'approve'):
            return 'update'
        if self.action == 'webhook':
            return 'webhook'
        if self.action in ('checkout', 'sync', 'admin_summary'):
            return self.action
        return 'get'
    def get_serializer_class(self):
        return self.viewset_config[self.get_action_key()]['serializer']
    def get_queryset(self):
        queryset = self.viewset_config[self.get_action_key()]['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        permissions_get = self.viewset_config[self.get_action_key()]['permissions']
        return [permission() for permission in permissions_get]
    #=========================================
    # LIST METHOD (mis pagos / listado admin / rollups)
    #=========================================
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    #=========================================
    # RETRIEVE METHOD
    #=========================================
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    #=========================================
    # CREATE METHOD
    #=========================================
    def create(self, request):
        serializer  =   self.get_serializer(data = request.data, context = {'request': request})
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' : self.viewset_config['create']['message']
            }, status = status.HTTP_201_CREATED
        )
    #=========================================
    # UPDATE METHOD
    #=========================================
    def update(self, request, pk = None):
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance, data = request.data, context = {'request': request}, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' : self.viewset_config['update']['message']
            }
        )
