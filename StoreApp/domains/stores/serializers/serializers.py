from rest_framework import serializers
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreCarouselImage
from StoreApp.domains.stores.services.storage import object_url
from StoreApp.domains.stores.services        import profile_has_benefit
from .config_fields import StoresFields, CustomizationFields
from .mixins        import StoreMixinValidator, StoreCreateMixin
from .validators    import validate_whatsapp, validate_instagram, validate_tiktok, validate_facebook
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
# STORE CAROUSEL IMAGE SERIALIZER (banners de la web pública)
#=========================================
class StoreCarouselImageSerializer(serializers.ModelSerializer):
    url                         =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreCarouselImage
        fields                  =   ['id', 'url', 'position']
    def get_url(self, image):
        return object_url(image.image_key)
#=========================================
# STORE CUSTOMIZATION SERIALIZER (diseño de la web pública)
#=========================================
class StoreCustomizationSerializer(serializers.ModelSerializer):
    display_name                =   serializers.CharField(**CustomizationFields['display_name'])
    headline                    =   serializers.CharField(**CustomizationFields['headline'])
    description                 =   serializers.CharField(**CustomizationFields['description'])
    whatsapp                    =   serializers.CharField(**CustomizationFields['whatsapp'])
    instagram                   =   serializers.CharField(**CustomizationFields['instagram'])
    tiktok                      =   serializers.CharField(**CustomizationFields['tiktok'])
    facebook                    =   serializers.CharField(**CustomizationFields['facebook'])
    logo                        =   serializers.SerializerMethodField()
    carousel                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreCustomization
        fields                  =   [
            'display_name', 'name_font', 'name_font_size', 'headline', 'description', 'theme', 'accent',
            'whatsapp', 'instagram', 'tiktok', 'facebook', 'show_location', 'logo', 'carousel', 'updated_at',
        ]
        read_only_fields        =   ['updated_at']
    def get_logo(self, customization):
        return object_url(customization.logo_key)
    def get_carousel(self, customization):
        images                  =   customization.store.carousel_images.all()
        return StoreCarouselImageSerializer(images, many = True).data
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
    def validate_tiktok(self, value):
        value                   =   value.strip().lstrip('@').lower()
        if value and not validate_tiktok(value):
            raise serializers.ValidationError('Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos')
        return value
    def validate_facebook(self, value):
        value                   =   value.strip().strip('/')
        if 'facebook.com/' in value:
            value               =   value.split('facebook.com/', 1)[1].strip('/').split('/')[0]
        if value and not validate_facebook(value):
            raise serializers.ValidationError('Ingresá el nombre de tu página o usuario: letras, números y puntos')
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
        return f'/{store.slug}'
#=========================================
# STORE PUBLIC SERIALIZER (datos que ve cualquier visitante)
#=========================================
class StorePublicSerializer(serializers.ModelSerializer):
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    city_name                   =   serializers.CharField(source = 'user.city.name_city', read_only = True)
    province_name               =   serializers.CharField(source = 'user.province.name_province', read_only = True)
    customization               =   StoreCustomizationSerializer(read_only = True)
    has_design_advanced         =   serializers.SerializerMethodField()
    location_address            =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Store
        fields                  =   ['slug', 'business_name', 'city_name', 'province_name', 'customization', 'has_design_advanced', 'location_address']
    def get_has_design_advanced(self, store):
        #Solo premium: define si la web muestra portada (carrusel) o el
        #botón de modo claro/oscuro para el visitante en el nav.
        return profile_has_benefit(store.user, 'has_design_advanced')
    def get_location_address(self, store):
        #Dirección lista para geocodificar (mapa embebido, has_location_map):
        #None si el dueño la apagó en Diseño web o no tiene domicilio cargado.
        customization         =   getattr(store, 'customization', None)
        if not customization or not customization.show_location:
            return None
        if not profile_has_benefit(store.user, 'has_location_map'):
            return None
        user                  =   store.user
        if not user.address:
            return None
        parts                 =   [user.address]
        if user.city:
            parts.append(user.city.name_city)
        if user.province:
            parts.append(user.province.name_province)
        parts.append('Argentina')
        return ', '.join(parts)
