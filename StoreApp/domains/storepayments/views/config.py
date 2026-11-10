"""
Config de cobros del dueño (StorePaymentConfig — métodos manuales).

GET devuelve la config de SU tienda (si nunca se guardó, los defaults
del modelo sin persistir — la lectura no escribe). PATCH actualiza con
validación estricta en el serializer (WhatsApp solo dígitos, deadline
1-720h, coherencia de métodos).

Hueco documentado (otros tracks de la ola ecommerce): el CRUD completo
de "Cobros" del panel (fiscal StoreFiscalProfile, OAuth social
StoreOAuthConfig, storage R2 StoreStorageConfig) NO vive acá — esos
modelos ya existen en stores.store_ops y sus endpoints los registra el
track que corresponda.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.serializers import StorePaymentConfigSerializer
from StoreApp.domains.stores.models import StorePaymentConfig

from .mp import owner_store


class StorePaymentConfigView(APIView):
    permission_classes    =   [IsAuthenticated]
    def _config(self, store, create = False):
        if create:
            return StorePaymentConfig.objects.get_or_create(store = store)[0]
        cfg =   StorePaymentConfig.objects.filter(store = store).first()
        #Sin fila todavía: instancia no persistida con los defaults del
        #modelo — el GET informa sin escribir.
        return cfg if cfg is not None else StorePaymentConfig(store = store)
    def get(self, request):
        store   =   owner_store(request)
        cfg     =   self._config(store)
        return Response(StorePaymentConfigSerializer(cfg).data, status = status.HTTP_200_OK)
    def patch(self, request):
        store   =   owner_store(request)
        cfg     =   self._config(store, create = True)
        serializer  =   StorePaymentConfigSerializer(cfg, data = request.data, partial = True, context = {'store': store})
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_200_OK)
