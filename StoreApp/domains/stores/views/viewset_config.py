from rest_framework.permissions import IsAuthenticated
from StoreApp.domains.stores.models                    import Store
from StoreApp.domains.stores.serializers.serializers   import (
    StoreSerializer,
    StoreSerializerList
)
"""

Configuración de los viewsets del dominio Stores.
El usuario elige su link en el primer ingreso (create) y puede
renombrarlo después (update). Un perfil = una tienda (OneToOne).

"""
#=========================================
# STORE CONFIGS
#=========================================
StoreConfigs = {
    'create': {
        'serializer' :   StoreSerializer,
        'queryset'   :   Store.objects.all(),
        'permissions':   [IsAuthenticated],
        'message'    :   'Tu link público se creó correctamente'
    },
    'update': {
        'serializer' :   StoreSerializer,
        'queryset'   :   lambda view : Store.objects.filter(user__user = view.request.user),
        'permissions':   [IsAuthenticated],
        'message'    :   'Tu link público se actualizó correctamente'
    },
    'get': {
        'serializer'    :   StoreSerializerList,
        'queryset'      :   lambda view : Store.objects.select_related('customization').order_by('-created_at')
                                if view.request.user.is_staff
                                else Store.objects.select_related('customization').filter(user__user = view.request.user).order_by('-created_at'),
        'permissions'   :   [IsAuthenticated],
    },
}
