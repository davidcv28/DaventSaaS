from django.utils import timezone
from rest_framework import serializers

from StoreApp.domains.catalog.models import (
    Brand,
    Category,
    Discount,
    Product,
    ProductReview,
    SpecialOfferCampaign,
)
from StoreApp.domains.catalog.services.services import (
    discount_covers,
    discount_price_of,
    manual_offer_of,
    running_discounts_of,
)
from StoreApp.domains.stores.services.storage import object_url

from .config_fields import (
    DiscountFields,
    ProductFields,
    ReviewFields,
    ReviewLimits,
    TaxonomyFields,
)
from .mixins import (
    CategorySchemaMixinValidator,
    DiscountMixinValidator,
    ProductMixinValidator,
    TaxonomyMixinValidator,
)

"""

Serializers del dominio Catalog.
Los serializers de escritura reciben context['store'] desde el viewset
(la tienda del usuario autenticado) para validar pertenencia y
unicidad por tienda.

"""
def _campaign_payload(campaign):
    """Bloque aditivo {slug,name,accent,label_url,...} o None sin campaña."""
    if campaign is None:
        return None
    return {
        'id'            :   campaign.pk,
        'slug'          :   campaign.slug,
        'name'          :   campaign.name,
        'accent'        :   campaign.accent,
        #La etiqueta sale firmada (private=True): la URL pública del bucket
        #puede no estar habilitada — igual que /api/offers/<slug>/label/.
        'label_url'     :   object_url(campaign.label_key, private = True),
        'label_alt'     :   campaign.label_alt,
        'label_width'   :   campaign.label_width,
        'label_height'  :   campaign.label_height,
        #Ventana y estado de la campaña: el panel muestra "no disponible"
        #cuando el descuento está etiquetado pero la campaña no corre.
        'is_running'    :   campaign.is_running(),
        'is_recurring'  :   campaign.is_recurring,
        'starts_at'     :   campaign.window()[0],
        'ends_at'       :   campaign.window()[1],
    }
#=========================================
# CATEGORY SERIALIZER
#=========================================
class CategorySerializer(TaxonomyMixinValidator, CategorySchemaMixinValidator, serializers.ModelSerializer):
    name                        =   serializers.CharField(**TaxonomyFields['name'])
    feature_schema              =   serializers.JSONField(**TaxonomyFields['feature_schema'])
    products_count              =   serializers.IntegerField(read_only = True)
    class Meta:
        model                   =   Category
        fields                  =   ['id', 'name', 'feature_schema', 'position', 'products_count']
#=========================================
# BRAND SERIALIZER
#=========================================
class BrandSerializer(TaxonomyMixinValidator, serializers.ModelSerializer):
    name                        =   serializers.CharField(**TaxonomyFields['name'])
    image                       =   serializers.SerializerMethodField()
    products_count              =   serializers.IntegerField(read_only = True)
    class Meta:
        model                   =   Brand
        fields                  =   ['id', 'name', 'image', 'position', 'products_count']
    def get_image(self, brand):
        return object_url(brand.image_key)
#=========================================
# SPECIAL OFFER CAMPAIGN SERIALIZER (lectura pública + CRUD staff)
#=========================================
class SpecialOfferCampaignSerializer(serializers.ModelSerializer):
    label_url                   =   serializers.SerializerMethodField()
    starts_at                   =   serializers.SerializerMethodField()
    ends_at                     =   serializers.SerializerMethodField()
    is_running                  =   serializers.SerializerMethodField()
    class Meta:
        model                   =   SpecialOfferCampaign
        fields                  =   [
            'id', 'slug', 'name', 'description', 'accent', 'label_url', 'label_alt',
            'label_width', 'label_height', 'month', 'day', 'duration_days',
            'is_recurring', 'is_active', 'position', 'starts_at', 'ends_at', 'is_running',
        ]
        read_only_fields        =   ['label_url', 'label_alt', 'label_width', 'label_height']
    def get_label_url(self, campaign):
        return object_url(campaign.label_key, private = True)
    def get_starts_at(self, campaign):
        #Ventana coherente (vigente o próxima): inicio y fin del mismo tramo.
        return campaign.window()[0]
    def get_ends_at(self, campaign):
        return campaign.window()[1]
    def get_is_running(self, campaign):
        return campaign.is_running()
#=========================================
# PRODUCT SERIALIZER (escritura del dueño)
#=========================================
class ProductSerializer(ProductMixinValidator, serializers.ModelSerializer):
    name                        =   serializers.CharField(**ProductFields['name'])
    description                 =   serializers.CharField(**ProductFields['description'])
    price                       =   serializers.DecimalField(**ProductFields['price'])
    offer_price                 =   serializers.DecimalField(**ProductFields['offer_price'])
    category                    =   serializers.PrimaryKeyRelatedField(queryset = Category.objects.all(), **ProductFields['category'])
    brand                       =   serializers.PrimaryKeyRelatedField(queryset = Brand.objects.all(), **ProductFields['brand'])
    is_active                   =   serializers.BooleanField(**ProductFields['is_active'])
    #Solo visible/comprable para clientes con plan vigente
    #exclusive_access (memberships) — el flag viaja al público solo como
    #"existe para miembros": la vidriera anónima lo excluye siempre.
    is_exclusive                =   serializers.BooleanField(**ProductFields['is_exclusive'])
    #binary=True: en multipart llega como string JSON y se parsea solo.
    features                    =   serializers.JSONField(binary = True, **ProductFields['features'])
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'offer_price', 'category', 'brand', 'is_active', 'is_exclusive', 'features']
#=========================================
# PRODUCT SERIALIZER LIST (mi catálogo, con imagen y nombres)
#=========================================
class ProductSerializerList(serializers.ModelSerializer):
    image                       =   serializers.SerializerMethodField()
    category_name               =   serializers.CharField(source = 'category.name', read_only = True)
    brand_name                  =   serializers.CharField(source = 'brand.name', read_only = True)
    discount_offer              =   serializers.SerializerMethodField()
    discount_names              =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Product
        fields                  =   [
            'id', 'name', 'description', 'price', 'offer_price', 'category', 'category_name',
            'brand', 'brand_name', 'is_active', 'is_exclusive', 'features', 'image', 'created_at',
            'discount_offer', 'discount_names',
        ]
    def get_image(self, product):
        return object_url(product.image_key)
    def _discounts(self):
        #Los descuentos vigentes se resuelven una sola vez por request y se
        #comparten entre todos los ítems del listado (mismo dict de context).
        if '_running_discounts' not in self.context:
            store                           =   self.context.get('store')
            self.context['_running_discounts']  =   running_discounts_of(store) if store else []
        return self.context['_running_discounts']
    def get_discount_offer(self, product):
        #Mejor precio que deja un descuento programado vigente (None si
        #ninguno lo cubre). El precio de lista/offer_price manuales no se tocan.
        return discount_price_of(product, self._discounts())
    def get_discount_names(self, product):
        #Con oferta manual el descuento programado no aplica (se salta):
        #tampoco se anuncian sus nombres en el panel.
        if manual_offer_of(product) is not None:
            return []
        return [discount.name for discount in self._discounts() if discount_covers(discount, product)]
#=========================================
# PRODUCT PUBLIC SERIALIZER (visitante de la web)
#=========================================
class ProductPublicSerializer(serializers.ModelSerializer):
    image                       =   serializers.SerializerMethodField()
    offer_price                 =   serializers.SerializerMethodField()
    discount                    =   serializers.SerializerMethodField()
    rating_avg                  =   serializers.SerializerMethodField()
    rating_count                =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'offer_price', 'features', 'image', 'category', 'brand', 'created_at', 'discount', 'rating_avg', 'rating_count']
    def get_image(self, product):
        return object_url(product.image_key)
    def get_offer_price(self, product):
        #public_catalog anota effective_offer = menor entre la oferta manual
        #y el mejor descuento vigente — toda la web pública muestra el mismo
        #precio efectivo (badge, tachado, orden y filtros).
        return getattr(product, 'effective_offer', product.offer_price)
    def get_discount(self, product):
        #public_catalog anota effective_discount = el descuento que firma la
        #oferta (o None si gana la manual). Se expone nombre, % y vencimiento
        #para que la plantilla muestre la promo ("Black Friday", "termina
        #el 30/11") sin revelar nada interno (scope, estado, ids).
        discount    =   getattr(product, 'effective_discount', None)
        if discount is None:
            return None
        return {
            'name'      :   discount.name,
            'percent'   :   discount.percent,
            'ends_at'   :   discount.ends_at,
            'campaign'  :   _campaign_payload(discount.campaign),
        }
    def get_rating_avg(self, product):
        #public_catalog anota el promedio solo si la tienda habilitó
        #valoraciones (show_reviews): sin anotación viaja None y la web no
        #muestra estrellas. Se redondea a 1 decimal para las medias.
        avg =   getattr(product, 'rating_avg', None)
        return round(avg, 1) if avg is not None else None
    def get_rating_count(self, product):
        return getattr(product, 'rating_count', None)
#=========================================
# REVIEW SERIALIZER (lectura del dueño: moderación desde el panel)
#=========================================
class ReviewSerializerList(serializers.ModelSerializer):
    product_name                =   serializers.CharField(source = 'product.name', read_only = True)
    class Meta:
        model                   =   ProductReview
        fields                  =   ['id', 'product', 'product_name', 'is_positive', 'text', 'name', 'surname', 'email', 'owner_reply', 'replied_at', 'created_at']
#=========================================
# REVIEW REPLY SERIALIZER (respuesta del dueño: el único campo editable
# de una opinión — el visitante nunca la toca y el dueño no edita la
# opinión ajena, solo puede borrarla)
#=========================================
class ReviewReplySerializer(serializers.ModelSerializer):
    owner_reply                 =   serializers.CharField(
        max_length    =   ReviewLimits['text_max'],
        allow_blank   =   True,
        trim_whitespace = True,
        required      =   False,
    )
    class Meta:
        model                   =   ProductReview
        fields                  =   ['owner_reply']
    def update(self, instance, validated_data):
        reply                   =   (validated_data.get('owner_reply') or '').strip()
        instance.owner_reply    =   reply
        #La fecha marca cuándo respondió el comercio; vaciar la respuesta
        #la quita de la web pública y limpia el sello.
        instance.replied_at     =   timezone.now() if reply else None
        instance.save(update_fields = ['owner_reply', 'replied_at'])
        return instance
#=========================================
# REVIEW PUBLIC SERIALIZER (ficha pública: jamás expone el email y el
# apellido viaja reducido a su inicial — "María P.")
#=========================================
class ReviewPublicSerializer(serializers.ModelSerializer):
    surname_initial             =   serializers.SerializerMethodField()
    class Meta:
        model                   =   ProductReview
        fields                  =   ['is_positive', 'text', 'name', 'surname_initial', 'owner_reply', 'replied_at', 'created_at']
    def get_surname_initial(self, review):
        surname =   (review.surname or '').strip()
        return f'{surname[0]}.' if surname else ''
#=========================================
# REVIEW CREATE SERIALIZER (escritura pública: rating según show_reviews,
# texto según show_comments — el viewset pasa ambos flags en context)
#=========================================
class ReviewCreateSerializer(serializers.ModelSerializer):
    is_positive                 =   serializers.BooleanField(**ReviewFields['is_positive'])
    text                        =   serializers.CharField(**ReviewFields['text'])
    name                        =   serializers.CharField(**ReviewFields['name'])
    surname                     =   serializers.CharField(**ReviewFields['surname'])
    email                       =   serializers.EmailField(**ReviewFields['email'])
    #Honeypot + captcha firmado (mismo challenge del formulario de contacto).
    website                     =   serializers.CharField(required = False, allow_blank = True, write_only = True)
    challenge_id                =   serializers.CharField(write_only = True)
    captcha_answer              =   serializers.CharField(max_length = 8, write_only = True)
    class Meta:
        model                   =   ProductReview
        fields                  =   ['is_positive', 'text', 'name', 'surname', 'email', 'website', 'challenge_id', 'captcha_answer']
    def validate(self, attrs):
        can_rate                =   self.context.get('can_rate', False)
        can_comment             =   self.context.get('can_comment', False)
        vote                    =   attrs.get('is_positive')
        text                    =   (attrs.get('text') or '').strip()
        attrs['text']           =   text
        if not can_rate and vote is not None:
            raise serializers.ValidationError({'is_positive': 'Esta tienda no tiene valoraciones habilitadas.'})
        if not can_comment and text:
            raise serializers.ValidationError({'text': 'Esta tienda no tiene comentarios habilitados.'})
        if can_rate and not can_comment and vote is None:
            raise serializers.ValidationError({'is_positive': 'Indicá si te gustó o no.'})
        if can_comment and not can_rate and not text:
            raise serializers.ValidationError({'text': 'Escribí tu comentario.'})
        if vote is None and not text:
            raise serializers.ValidationError({'is_positive': 'Dejá una valoración o un comentario.'})
        return attrs
#=========================================
# DISCOUNT PUBLIC SERIALIZER (promos vigentes del catálogo público)
#=========================================
class DiscountPublicSerializer(serializers.ModelSerializer):
    category_name               =   serializers.CharField(source = 'category.name', read_only = True)
    brand_name                  =   serializers.CharField(source = 'brand.name', read_only = True)
    campaign                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Discount
        fields                  =   ['name', 'percent', 'scope', 'category', 'category_name', 'brand', 'brand_name', 'ends_at', 'campaign']
    def get_campaign(self, discount):
        return _campaign_payload(discount.campaign)
#=========================================
# DISCOUNT SERIALIZER (escritura del dueño)
#=========================================
class DiscountSerializer(DiscountMixinValidator, serializers.ModelSerializer):
    name                        =   serializers.CharField(**DiscountFields['name'])
    percent                     =   serializers.IntegerField(**DiscountFields['percent'])
    category                    =   serializers.PrimaryKeyRelatedField(queryset = Category.objects.all(), **DiscountFields['category'])
    brand                       =   serializers.PrimaryKeyRelatedField(queryset = Brand.objects.all(), **DiscountFields['brand'])
    products                    =   serializers.PrimaryKeyRelatedField(queryset = Product.objects.all(), many = True, required = False)
    starts_at                   =   serializers.DateTimeField(**DiscountFields['starts_at'])
    ends_at                     =   serializers.DateTimeField(**DiscountFields['ends_at'])
    is_active                   =   serializers.BooleanField(**DiscountFields['is_active'])
    campaign                    =   serializers.PrimaryKeyRelatedField(
        queryset    =   SpecialOfferCampaign.objects.filter(is_active = True),
        **DiscountFields['campaign'],
    )
    class Meta:
        model                   =   Discount
        fields                  =   ['id', 'name', 'percent', 'scope', 'category', 'brand', 'products', 'campaign', 'starts_at', 'ends_at', 'is_active']
    def _clean_scope(self, validated, instance = None):
        """Los campos fuera del alcance elegido se limpian (nunca quedan restos)."""
        scope           =   validated.get('scope', getattr(instance, 'scope', Discount.Scope.ALL))
        if scope != Discount.Scope.CATEGORY:
            validated['category']   =   None
        if scope != Discount.Scope.BRAND:
            validated['brand']  =   None
        return scope
    def create(self, validated_data):
        products        =   validated_data.pop('products', [])
        scope           =   self._clean_scope(validated_data)
        discount        =   Discount.objects.create(**validated_data)
        if scope == Discount.Scope.PRODUCTS:
            discount.products.set(products)
        return discount
    def update(self, instance, validated_data):
        products        =   validated_data.pop('products', None)
        scope           =   self._clean_scope(validated_data, instance)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if scope != Discount.Scope.PRODUCTS:
            instance.products.clear()
        elif products is not None:
            instance.products.set(products)
        return instance
#=========================================
# DISCOUNT SERIALIZER LIST (mis descuentos, con estado derivado de la ventana)
#=========================================
class DiscountSerializerList(serializers.ModelSerializer):
    category_name               =   serializers.CharField(source = 'category.name', read_only = True)
    brand_name                  =   serializers.CharField(source = 'brand.name', read_only = True)
    products                    =   serializers.PrimaryKeyRelatedField(many = True, read_only = True)
    status                      =   serializers.SerializerMethodField()
    products_count              =   serializers.SerializerMethodField()
    campaign                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Discount
        fields                  =   [
            'id', 'name', 'percent', 'scope', 'category', 'category_name', 'brand', 'brand_name',
            'products', 'products_count', 'campaign', 'starts_at', 'ends_at', 'is_active', 'status', 'created_at',
        ]
    def get_status(self, discount):
        #Estado vigente derivado de la ventana (la automatización vive acá:
        #scheduled -> active -> ended se resuelve solo al leer).
        now     =   timezone.now()
        if not discount.is_active:
            return 'paused'
        if discount.ends_at is not None and discount.ends_at <= now:
            return 'ended'
        if discount.starts_at > now:
            return 'scheduled'
        #Dentro de la ventana propia pero la campaña no corre: la oferta
        #especial no está disponible aunque el descuento esté "encendido".
        if discount.campaign_id is not None and not discount.campaign.is_running(now):
            return 'unavailable'
        return 'active'
    def get_campaign(self, discount):
        return _campaign_payload(discount.campaign)
    def get_products_count(self, discount):
        #Anotado en el queryset (Count('products')); el fallback cubre el
        #detalle/creación, donde no hace falta la anotación.
        annotated =   getattr(discount, 'products_count', None)
        return annotated if annotated is not None else discount.products.count()
