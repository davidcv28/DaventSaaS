from rest_framework import viewsets, status
from rest_framework.response import Response
"""

Base de los viewsets del dominio Benefits (solo lectura: list/retrieve).

"""
#=========================================
# BENEFIT BASE VIEWSET
#=========================================
class BenefitBaseViewSet(viewsets.GenericViewSet):
    viewset_config  =   {}
    def get_serializer_class(self):
        return self.viewset_config['get']['serializer']
    def get_queryset(self):
        queryset    =   self.viewset_config['get']['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        return [permission() for permission in self.viewset_config['get']['permissions']]
    #=========================================
    # LIST METHOD
    #=========================================
    def list(self, request, *args, **kwargs):
        queryset    =   self.filter_queryset(self.get_queryset())
        page        =   self.paginate_queryset(queryset)
        if page is not None:
            serializer  =   self.get_serializer(page, many = True)
            return self.get_paginated_response(serializer.data)
        serializer  =   self.get_serializer(queryset, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # RETRIEVE METHOD
    #=========================================
    def retrieve(self, request, *args, **kwargs):
        instance    =   self.get_object()
        serializer  =   self.get_serializer(instance)
        return Response(serializer.data, status = status.HTTP_200_OK)
