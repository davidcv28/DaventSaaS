from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from StoreApp.domains.services.services.services import (
    SERVICES_MAX,
    apply_service_order,
    can_add_service,
    services_enabled,
)

from .viewset_base import ServicesBaseViewSet
from .viewset_config import ServiceConfigs

"""

Viewsets del dominio Services.
Los servicios del cliente se gestionan solo con el flag
'has_services_site' del plan vigente (Estándar en adelante): sin el
beneficio todo el endpoint responde 403 y la página pública queda
apagada aunque haya ítems guardados.

"""
#=========================================
# SERVICE VIEWSET (servicios del dueño, gated por el plan)
#=========================================
class ServiceViewSet(ServicesBaseViewSet):
    viewset_config  =   ServiceConfigs
    def _deny_without_services(self):
        if not services_enabled(self.my_store().user):
            return Response(
                {'detail': 'La página de servicios está disponible desde el plan Estándar.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return None
    def list(self, request, *args, **kwargs):
        denied  =   self._deny_without_services()
        if denied: return denied
        return super().list(request, *args, **kwargs)
    def create(self, request):
        denied  =   self._deny_without_services()
        if denied: return denied
        store   =   self.my_store()
        #El cupo se rechequea bajo lock de la fila de la tienda: dos
        #creates concurrentes no pueden pasar ambos el tope (mismo
        #patrón que max_products del catálogo).
        with transaction.atomic():
            locked  =   type(store).objects.select_for_update().get(pk = store.pk)
            if not can_add_service(locked):
                return Response(
                    {'detail': f'Tu página admite hasta {SERVICES_MAX} servicios.'},
                    status = status.HTTP_403_FORBIDDEN,
                )
            return super().create(request)
    def update(self, request, pk = None):
        denied  =   self._deny_without_services()
        if denied: return denied
        return super().update(request, pk)
    def partial_update(self, request, pk = None):
        return self.update(request, pk)
    def destroy(self, request, pk = None):
        denied  =   self._deny_without_services()
        if denied: return denied
        return super().destroy(request, pk)
    #=========================================
    # ORDER (reordenar la lista de servicios, PATCH {order: [ids]})
    #=========================================
    @action(detail = False, methods = ['patch'], url_path = 'order')
    def order(self, request):
        denied  =   self._deny_without_services()
        if denied: return denied
        order   =   request.data.get('order')
        if not isinstance(order, list):
            return Response({'order': 'Enviá la lista de ids en el nuevo orden.'}, status = status.HTTP_400_BAD_REQUEST)
        #La reasignación de positions es multi-fila: corre atómica para
        #que un corte a la mitad nunca deje el orden inconsistente.
        with transaction.atomic():
            apply_service_order(self.get_queryset(), order)
        return Response({'Exito': 'El orden de tus servicios se actualizó'}, status = status.HTTP_200_OK)
