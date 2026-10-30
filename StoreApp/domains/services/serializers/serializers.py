from django.db.models import Max
from rest_framework import serializers

from StoreApp.domains.services.models import StoreService

from .config_fields import ServiceFields
from .mixins import ServiceMixinValidator

"""

Serializers del dominio Services.
Los serializers de escritura reciben context['store'] desde el viewset
(la tienda del usuario autenticado) para validar pertenencia y
unicidad por tienda.

"""
#=========================================
# SERVICE SERIALIZER (escritura del dueño)
#=========================================
class ServiceSerializer(ServiceMixinValidator, serializers.ModelSerializer):
    name                        =   serializers.CharField(**ServiceFields['name'])
    description                 =   serializers.CharField(**ServiceFields['description'])
    price                       =   serializers.DecimalField(**ServiceFields['price'])
    duration                    =   serializers.CharField(**ServiceFields['duration'])
    icon                        =   serializers.CharField(**ServiceFields['icon'])
    is_active                   =   serializers.BooleanField(**ServiceFields['is_active'])
    class Meta:
        model                   =   StoreService
        fields                  =   ['id', 'name', 'description', 'price', 'duration', 'icon', 'is_active', 'position']
        read_only_fields        =   ['position']
    def create(self, validated_data):
        #Alta al final de la lista: el create del viewset corre bajo el
        #lock de la fila de la tienda, así dos altas concurrentes no
        #pueden pisarse la misma position.
        store                   =   validated_data['store']
        last                    =   store.service_items.aggregate(m = Max('position'))['m']
        validated_data['position']  =   (last or 0) + 1
        return super().create(validated_data)
#=========================================
# SERVICE SERIALIZER LIST (mis servicios, panel del dueño)
#=========================================
class ServiceSerializerList(serializers.ModelSerializer):
    class Meta:
        model                   =   StoreService
        fields                  =   ['id', 'name', 'description', 'price', 'duration', 'icon', 'is_active', 'position', 'created_at']
#=========================================
# SERVICE PUBLIC SERIALIZER (visitante de la página Servicios)
#=========================================
class ServicePublicSerializer(serializers.ModelSerializer):
    """Payload mínimo del servicio en la web pública: nada de flags internos."""
    class Meta:
        model                   =   StoreService
        fields                  =   ['id', 'name', 'description', 'price', 'duration', 'icon']
