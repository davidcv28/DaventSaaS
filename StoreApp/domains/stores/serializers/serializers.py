from rest_framework import serializers
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreCarouselImage, StoreGalleryImage, StoreChatbot
from StoreApp.domains.stores.services.storage import object_url
from StoreApp.domains.stores.services        import profile_has_benefit, storage_payload
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
# STORE GALLERY IMAGE SERIALIZER (sección Galería de la web pública)
#=========================================
class StoreGalleryImageSerializer(serializers.ModelSerializer):
    url                         =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreGalleryImage
        fields                  =   ['id', 'url', 'position']
    def get_url(self, image):
        return object_url(image.image_key)
#=========================================
# STORE CHATBOT SERIALIZER (asistente de la web pública)
#=========================================
class StoreChatbotSerializer(serializers.ModelSerializer):
    """
    Config del chatbot (beneficio 'has_chatbot': Estándar y Premium).
    `qa` llega como lista de {'q', 'a'}: se recorta a QA_MAX_ITEMS y
    se descartan pares sin pregunta o sin respuesta.
    """
    class Meta:
        model                   =   StoreChatbot
        fields                  =   ['is_enabled', 'greeting', 'qa']
    def validate_greeting(self, value):
        return (value or '').strip()
    def validate_qa(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Debe ser una lista de preguntas y respuestas.')
        clean                   =   []
        for item in value[:StoreChatbot.QA_MAX_ITEMS]:
            if not isinstance(item, dict):
                continue
            q                   =   str(item.get('q') or '').strip()[:StoreChatbot.QA_MAX_QUESTION]
            a                   =   str(item.get('a') or '').strip()[:StoreChatbot.QA_MAX_ANSWER]
            if q and a:
                clean.append({'q': q, 'a': a})
        return clean
#=========================================
# STORE CUSTOMIZATION SERIALIZER (diseño de la web pública)
#=========================================
class StoreCustomizationSerializer(serializers.ModelSerializer):
    display_name                =   serializers.CharField(**CustomizationFields['display_name'])
    headline                    =   serializers.CharField(**CustomizationFields['headline'])
    description                 =   serializers.CharField(**CustomizationFields['description'])
    about_title                 =   serializers.CharField(**CustomizationFields['about_title'])
    about_text                  =   serializers.CharField(**CustomizationFields['about_text'])
    about_years                 =   serializers.IntegerField(**CustomizationFields['about_years'])
    about_mission               =   serializers.CharField(**CustomizationFields['about_mission'])
    about_specialties           =   serializers.CharField(**CustomizationFields['about_specialties'])
    contact_email               =   serializers.EmailField(**CustomizationFields['contact_email'])
    whatsapp                    =   serializers.CharField(**CustomizationFields['whatsapp'])
    instagram                   =   serializers.CharField(**CustomizationFields['instagram'])
    tiktok                      =   serializers.CharField(**CustomizationFields['tiktok'])
    facebook                    =   serializers.CharField(**CustomizationFields['facebook'])
    logo                        =   serializers.SerializerMethodField()
    carousel                    =   serializers.SerializerMethodField()
    gallery                     =   serializers.SerializerMethodField()
    decor                       =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreCustomization
        fields                  =   [
            'display_name', 'name_font', 'name_font_size', 'headline', 'description', 'theme', 'accent', 'template',
            'about_title', 'about_text', 'about_years', 'about_mission', 'about_specialties',
            'show_about', 'contact_email', 'show_contact',
            'whatsapp', 'instagram', 'tiktok', 'facebook', 'show_location', 'show_gallery', 'show_catalog',
            'logo', 'carousel', 'gallery', 'decor', 'updated_at',
        ]
        read_only_fields        =   ['updated_at']
    def get_logo(self, customization):
        return object_url(customization.logo_key)
    def get_carousel(self, customization):
        images                  =   customization.store.carousel_images.all()
        return StoreCarouselImageSerializer(images, many = True).data
    def get_gallery(self, customization):
        images                  =   customization.store.gallery_images.filter(kind = StoreGalleryImage.KIND_GALLERY)
        return StoreGalleryImageSerializer(images, many = True).data
    def get_decor(self, customization):
        images                  =   customization.store.gallery_images.filter(kind = StoreGalleryImage.KIND_DECOR)
        return StoreGalleryImageSerializer(images, many = True).data
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
# STORE CUSTOMIZATION PUBLIC SERIALIZER (web pública: oculta el email de
# contacto — el formulario existe justamente para no exponerlo a scrapers)
#=========================================
class StoreCustomizationPublicSerializer(StoreCustomizationSerializer):
    class Meta(StoreCustomizationSerializer.Meta):
        fields              =   [f for f in StoreCustomizationSerializer.Meta.fields if f != 'contact_email']
#=========================================
# STORE SERIALIZER LIST
#=========================================
class StoreSerializerList(serializers.ModelSerializer):
    public_path                 =   serializers.SerializerMethodField()
    customization               =   StoreCustomizationSerializer(read_only = True)
    storage                     =   serializers.SerializerMethodField()
    #Datos del dueño: alimentan la sección "Webs" del panel admin
    #(para el dueño repiten su propia info, no suman exposición).
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    owner_id                    =   serializers.IntegerField(source = 'user.user_id', read_only = True)
    owner_name                  =   serializers.CharField(source = 'user.user.username', read_only = True)
    owner_email                 =   serializers.CharField(source = 'user.user.email', read_only = True)
    plan_name                   =   serializers.SerializerMethodField()
    has_access                  =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Store
        fields                  =   ['id', 'slug', 'is_published', 'is_blocked', 'blocked_reason', 'blocked_at', 'created_at',
                                     'public_path', 'customization', 'storage',
                                     'business_name', 'owner_id', 'owner_name', 'owner_email', 'plan_name', 'has_access']
    def get_public_path(self, store):
        return f'/{store.slug}'
    def get_storage(self, store):
        # Cuota de imágenes del plan vigente ({used_bytes, max_mb, images, max_images}).
        return storage_payload(store, store.user)
    def get_plan_name(self, store):
        suscription             =   getattr(store.user, 'suscription', None)
        return suscription.plan_suscription.name if suscription else None
    def get_has_access(self, store):
        suscription             =   getattr(store.user, 'suscription', None)
        return bool(suscription and suscription.grants_access())
#=========================================
# STORE PUBLIC SERIALIZER (datos que ve cualquier visitante)
#=========================================
class StorePublicSerializer(serializers.ModelSerializer):
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    city_name                   =   serializers.CharField(source = 'user.city.name_city', read_only = True)
    province_name               =   serializers.CharField(source = 'user.province.name_province', read_only = True)
    customization               =   StoreCustomizationPublicSerializer(read_only = True)
    has_design_advanced         =   serializers.SerializerMethodField()
    location_address            =   serializers.SerializerMethodField()
    chatbot                     =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Store
        fields                  =   ['slug', 'business_name', 'city_name', 'province_name', 'customization', 'has_design_advanced', 'location_address', 'chatbot']
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
    def get_chatbot(self, store):
        #{'greeting', 'qa'} solo si el plan tiene 'has_chatbot' y el
        #dueño lo activó; el widget público no se renderiza con None.
        if not profile_has_benefit(store.user, 'has_chatbot'):
            return None
        cfg                     =   getattr(store, 'chatbot', None)
        if not cfg or not cfg.is_enabled:
            return None
        return {'greeting': cfg.greeting, 'qa': cfg.qa or []}
#=========================================
# STORE CONTACT SERIALIZER (formulario público "Contáctanos")
#=========================================
class StoreContactSerializer(serializers.Serializer):
    #El honeypot `website` queda oculto para humanos: los bots lo completan
    #y el viewset les devuelve éxito falso sin enviar nada.
    name                        =   serializers.CharField(min_length = 2, max_length = 80, trim_whitespace = True)
    email                       =   serializers.EmailField()
    message                     =   serializers.CharField(min_length = 10, max_length = 2000)
    website                     =   serializers.CharField(required = False, allow_blank = True, write_only = True)
    challenge_id                =   serializers.CharField(write_only = True)
    captcha_answer              =   serializers.CharField(max_length = 8, write_only = True)
