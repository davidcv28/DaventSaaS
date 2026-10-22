from rest_framework import viewsets, status
from rest_framework.response import Response


"""

Creamos la base de los viewsets que utilizaremos del dominio Suscriptions

"""

#=========================================
# SUSCRIPTION BASE VIEWSET
#=========================================
class SuscriptionBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    def get_serializer_class(self):
        if self.action == 'create':
            return self.viewset_config['create']['serializer']
        if self.action == 'update':
            return self.viewset_config['update']['serializer']
        return self.viewset_config['get']['serializer']
    def get_queryset(self):
        if self.action == 'create':
            queryset = self.viewset_config['create']['queryset']
        elif self.action == 'update':
            queryset = self.viewset_config['update']['queryset']
        else:
            queryset = self.viewset_config['get']['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        if self.action == 'create':
            permissions_get = self.viewset_config['create']['permissions']
        elif self.action == 'update':
            permissions_get = self.viewset_config['update']['permissions']
        else:
            permissions_get = self.viewset_config['get']['permissions']
        return [permission() for permission in permissions_get]
    #=========================================
    # LIST METHOD (mi suscripción / listado admin)
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
   
    