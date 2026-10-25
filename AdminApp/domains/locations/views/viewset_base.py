from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from DaventProject.throttling import PublicReadThrottle


#================================
# LOCATION BASE VIEWSET (solo lectura pública para selects)
#================================
class LocationBaseViewSet(viewsets.GenericViewSet):
    view_config = {}
    #Los selects del registro consultan provincias/ciudades/CP por cada
    #visitante anónimo: scope 'public_read' (no el anon global de 100/día).
    throttle_classes = [PublicReadThrottle]

    def get_action_view(self):
        config = self.view_config.get(self.action)
        if not config:
            #drf_spectacular introspecciona con actions sintéticas al generar
            #el schema durante check --deploy; el fallback evita que rompa.
            config = next(iter(self.view_config.values()), None)
        if not config:
            raise ValueError(f'No hay configuración disponible para la acción solicitada: {self.action}')
        return config

    def get_serializer_class(self):
        return self.get_action_view()['serializer']

    def get_queryset(self):
        queryset = self.get_action_view()['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset

    def get_permissions(self):
        #Sin 'permissions' en la config se cae a IsAuthenticated (fail-closed).
        permissions = self.get_action_view().get('permissions', [IsAuthenticated])
        return [permission() for permission in permissions]

    #///LIST METHOD///
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #///RETRIEVE METHOD///
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

