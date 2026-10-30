from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from StoreApp.domains.stores.models import Store

"""

Base de los viewsets del dominio Catalog.
Todo objeto vive dentro de la tienda del usuario autenticado:
_my_store() la resuelve una vez por request y queda en context['store']
para que los serializers validen pertenencia y unicidad por tienda.

"""
#=========================================
# CATALOG BASE VIEWSET
#=========================================
class CatalogBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    _store          =   None
    def my_store(self):
        """Tienda del usuario autenticado (404 si aún no hizo el onboarding)."""
        if self._store is None:
            self._store =   get_object_or_404(Store, user__user = self.request.user)
        return self._store
    def get_serializer_context(self):
        context             =   super().get_serializer_context()
        context['store']    =   self.my_store()
        return context
    def _action_key(self):
        return 'update' if self.action in ('update', 'partial_update') else self.action
    def get_serializer_class(self):
        key = self._action_key()
        if key == 'create':
            return self.viewset_config['create']['serializer']
        if key == 'update':
            return self.viewset_config['update']['serializer']
        return self.viewset_config['get']['serializer']
    def get_queryset(self):
        key = self._action_key()
        config          =   self.viewset_config.get(key) or self.viewset_config['get']
        queryset        =   config['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        key = self._action_key()
        config          =   self.viewset_config.get(key) or self.viewset_config['get']
        return [permission() for permission in config['permissions']]
    #=========================================
    # LIST METHOD
    #=========================================
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    #=========================================
    # CREATE METHOD
    #=========================================
    def create(self, request):
        serializer  =   self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save(store = self.my_store())
        return Response(
            {
                'Exito' : self.viewset_config['create']['message'],
                'item'  : serializer.data,
            }, status = status.HTTP_201_CREATED
        )
    #=========================================
    # UPDATE / PARTIAL UPDATE METHODS
    #=========================================
    def update(self, request, pk = None):
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance, data = request.data, partial = (request.method == 'PATCH'))
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' : self.viewset_config['update']['message'],
                'item'  : serializer.data,
            }
        )
    def partial_update(self, request, pk = None):
        return self.update(request, pk)
    #=========================================
    # DESTROY METHOD
    #=========================================
    def destroy(self, request, pk = None):
        instance    =   self.get_object()
        self.perform_destroy(instance)
        return Response({'Exito': self.viewset_config['get'].get('delete_message', 'Se eliminó correctamente')})
    def perform_destroy(self, instance):
        instance.delete()
