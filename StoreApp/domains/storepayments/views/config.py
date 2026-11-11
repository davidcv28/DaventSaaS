"""
Config de cobros del dueño (StorePaymentConfig — métodos manuales).

GET devuelve la config de SU tienda (si nunca se guardó, los defaults
del modelo sin persistir — la lectura no escribe). PATCH actualiza con
validación estricta en el serializer (WhatsApp solo dígitos, deadline
1-720h, coherencia de métodos).

El resto del panel "Cobros" vive en views/integrations.py: fiscal
(StoreFiscalProfile), login social (StoreOAuthConfig) y storage R2
propio (StoreStorageConfig).
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.serializers import (
    StorePaymentConfigSerializer,
    StoreShippingConfigSerializer,
)
from StoreApp.domains.stores.models import StorePaymentConfig, StoreShippingConfig

from .mp import owner_store, require_benefit


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
        require_benefit(store, 'has_ecommerce')
        cfg     =   self._config(store)
        return Response(StorePaymentConfigSerializer(cfg).data, status = status.HTTP_200_OK)
    def patch(self, request):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        cfg     =   self._config(store, create = True)
        serializer  =   StorePaymentConfigSerializer(cfg, data = request.data, partial = True, context = {'store': store})
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_200_OK)


class StoreShippingConfigView(APIView):
    """
    Envío a domicilio del checkout (StoreShippingConfig — una fila por
    tienda). GET devuelve la config de SU tienda (sin fila = defaults
    sin persistir: home_price NULL = "a coordinar"). PATCH merge:
    home_price ausente conserva, null/0+ lo fija (0 = envío gratis).
    """
    permission_classes    =   [IsAuthenticated]
    def _config(self, store, create = False):
        if create:
            return StoreShippingConfig.objects.get_or_create(store = store)[0]
        cfg =   StoreShippingConfig.objects.filter(store = store).first()
        #Sin fila todavía: instancia no persistida con los defaults del
        #modelo — el GET informa sin escribir.
        return cfg if cfg is not None else StoreShippingConfig(store = store)
    def get(self, request):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        cfg     =   self._config(store)
        return Response(StoreShippingConfigSerializer(cfg).data, status = status.HTTP_200_OK)
    def patch(self, request):
        store   =   owner_store(request)
        require_benefit(store, 'has_ecommerce')
        cfg     =   self._config(store, create = True)
        serializer  =   StoreShippingConfigSerializer(cfg, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_200_OK)
