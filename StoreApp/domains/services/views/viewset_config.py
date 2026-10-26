from rest_framework.permissions import IsAuthenticated
from StoreApp.domains.services.models                    import StoreService
from StoreApp.domains.services.serializers.serializers   import ServiceSerializer, ServiceSerializerList
"""

Configuración de los viewsets del dominio Services.
El queryset siempre recorta a la tienda del usuario autenticado
(view.my_store()); nunca se exponen servicios de otra tienda.

"""
def _own_services(view):
    return StoreService.objects.filter(store = view.my_store())
#=========================================
# SERVICE CONFIGS
#=========================================
ServiceConfigs = {
    'create': {
        'serializer' :   ServiceSerializer,
        'queryset'   :   _own_services,
        'permissions':   [IsAuthenticated],
        'message'    :   'El servicio se creó correctamente',
    },
    'update': {
        'serializer' :   ServiceSerializer,
        'queryset'   :   _own_services,
        'permissions':   [IsAuthenticated],
        'message'    :   'El servicio se actualizó correctamente',
    },
    'get': {
        'serializer'    :   ServiceSerializerList,
        'queryset'      :   _own_services,
        'permissions'   :   [IsAuthenticated],
        'delete_message':   'El servicio se eliminó correctamente',
    },
}
