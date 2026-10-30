from rest_framework import status, viewsets
from rest_framework.response import Response

"""

Base de los viewsets del dominio Stores.

"""
#=========================================
# STORE BASE VIEWSET
#=========================================
class StoreBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    def _action_key(self):
        """PUT y PATCH comparten la config 'update'."""
        return 'update' if self.action in ('update', 'partial_update') else self.action
    def get_serializer_class(self):
        if self.action == 'create':
            return self.viewset_config['create']['serializer']
        if self._action_key() == 'update' and 'update' in self.viewset_config:
            return self.viewset_config['update']['serializer']
        return self.viewset_config['get']['serializer']
    def get_queryset(self):
        key = self._action_key()
        if self.action == 'create':
            queryset = self.viewset_config['create']['queryset']
        elif key == 'update' and 'update' in self.viewset_config:
            queryset = self.viewset_config['update']['queryset']
        else:
            queryset = self.viewset_config['get']['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        key = self._action_key()
        if self.action == 'create':
            permissions_get = self.viewset_config['create']['permissions']
        elif key == 'update' and 'update' in self.viewset_config:
            permissions_get = self.viewset_config['update']['permissions']
        else:
            permissions_get = self.viewset_config['get']['permissions']
        return [permission() for permission in permissions_get]
    def paginate_queryset(self, queryset):
        #El cliente lista solo su propia tienda (≤1 fila): el COUNT de la
        #paginación es costo puro. El staff sí pagina el listado completo.
        if not self.request.user.is_staff:
            return None
        return super().paginate_queryset(queryset)
    #=========================================
    # LIST METHOD (mi tienda / listado admin)
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
    #=========================================
    # PARTIAL UPDATE METHOD (PATCH)
    #=========================================
    def partial_update(self, request, pk = None):
        return self.update(request, pk)
