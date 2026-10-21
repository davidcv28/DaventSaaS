from rest_framework import serializers
from StoreApp.domains.stores.models import Store, StoreCustomization
from .config_fields import StoresFields, CustomizationFields
from .mixins        import StoreMixinValidator, StoreCreateMixin
from .validators    import validate_whatsapp, validate_instagram
"""

Serializers del dominio Stores.

"""
#=========================================
# STORE SERIALIZER (claim / cambio de link)
#=========================================
class StoreSerializer(StoreMixinValidator, StoreCreateMixin, serializers.ModelSerializer):
    id                          =   serializers.ReadOnlyField()
    user                        =   serializers.HiddenField(**StoresFields['user'])
    slug                        =   serializers.CharField(**StoresFields['slug'])
    is_published                =   serializers.BooleanField(**StoresFields['is_published'])
    class Meta:
        model                   =   Store
        fields                  =   ['id', 'user', 'slug', 'is_published']
#=========================================
# STORE CUSTOMIZATION SERIALIZER (diseño de la web pública)
#=========================================
class StoreCustomizationSerializer(serializers.ModelSerializer):
    headline                    =   serializers.CharField(**CustomizationFields['headline'])
    description                 =   serializers.CharField(**CustomizationFields['description'])
    whatsapp                    =   serializers.CharField(**CustomizationFields['whatsapp'])
    instagram                   =   serializers.CharField(**CustomizationFields['instagram'])
    class Meta:
        model                   =   StoreCustomization
        fields                  =   ['headline', 'description', 'theme', 'accent', 'whatsapp', 'instagram', 'updated_at']
        read_only_fields        =   ['updated_at']
    def validate_whatsapp(self, value):
        value                   =   value.strip().replace(' ', '').replace('-', '')
        if value and not validate_whatsapp(value):
            raise serializers.ValidationError('Ingresá un número válido: 8 a 15 dígitos, con "+" opcional. Ej. +5493871551234')
        return value
    def validate_instagram(self, value):
        value                   =   value.strip().lstrip('@').lower()
        if value and not validate_instagram(value):
            raise serializers.ValidationError('Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos')
        return value
#=========================================
# STORE SERIALIZER LIST
#=========================================
class StoreSerializerList(serializers.ModelSerializer):
    public_path                 =   serializers.SerializerMethodField()
    customization               =   StoreCustomizationSerializer(read_only = True)
    class Meta:
        model                   =   Store
        fields                  =   ['id', 'slug', 'is_published', 'created_at', 'public_path', 'customization']
    def get_public_path(self, store):
        return f'/tienda/{store.slug}'
#=========================================
# STORE PUBLIC SERIALIZER (datos que ve cualquier visitante)
#=========================================
class StorePublicSerializer(serializers.ModelSerializer):
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    city_name                   =   serializers.CharField(source = 'user.city.name_city', read_only = True)
    province_name               =   serializers.CharField(source = 'user.province.name_province', read_only = True)
    customization               =   StoreCustomizationSerializer(read_only = True)
    class Meta:
        model                   =   Store
        fields                  =   ['slug', 'business_name', 'city_name', 'province_name', 'customization']
