from django.db.models import Count, Q
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
# STORE LIST QUERYSET (joins + prefetch + anotaciones que pide el serializer)
#=========================================
def _store_list_queryset(view):
    #El serializer expande customization, carrusel, galería, dueño+plan y el
    #conteo de imágenes de productos: todo resuelto acá — sin los prefetch/
    #anotación el listado hacía ~10 queries extra por tienda.
    qs  =   (
        Store.objects
        .select_related('customization', 'user__user', 'user__suscription__plan_suscription')
        .prefetch_related('carousel_images', 'gallery_images')
        .annotate(_n_product_images = Count('products', filter = ~Q(products__image_key = '')))
        .order_by('-created_at')
    )
    #El listado staff suma dueño, plan y acceso vigente (panel admin).
    #Con ?mine=1 el staff recibe solo su propia tienda (panel de usuario):
    #sin eso rows[0] sería la web de otro cliente y todo PATCH daría 404.
    if view.request.user.is_staff and view.request.query_params.get('mine') != '1':
        return qs
    return qs.filter(user__user = view.request.user)
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
        'queryset'      :   _store_list_queryset,
        'permissions'   :   [IsAuthenticated],
    },
}
