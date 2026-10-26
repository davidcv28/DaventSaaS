from django.utils import timezone
from rest_framework import serializers
from StoreApp.domains.catalog.models import Category, Brand, Product, Discount
from StoreApp.domains.catalog.services.services import (
    running_discounts_of, discount_covers, discount_price_of,
)
from StoreApp.domains.stores.services.storage import object_url
from .config_fields import TaxonomyFields, ProductFields, DiscountFields
from .mixins        import TaxonomyMixinValidator, CategorySchemaMixinValidator, ProductMixinValidator, DiscountMixinValidator
"""

Serializers del dominio Catalog.
Los serializers de escritura reciben context['store'] desde el viewset
(la tienda del usuario autenticado) para validar pertenencia y
unicidad por tienda.

"""
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
    products_count              =   serializers.IntegerField(read_only = True)
    class Meta:
        model                   =   Brand
        fields                  =   ['id', 'name', 'position', 'products_count']
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
    #binary=True: en multipart llega como string JSON y se parsea solo.
    features                    =   serializers.JSONField(binary = True, **ProductFields['features'])
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'offer_price', 'category', 'brand', 'is_active', 'features']
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
            'brand', 'brand_name', 'is_active', 'features', 'image', 'created_at',
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
        return [discount.name for discount in self._discounts() if discount_covers(discount, product)]
#=========================================
# PRODUCT PUBLIC SERIALIZER (visitante de la web)
#=========================================
class ProductPublicSerializer(serializers.ModelSerializer):
    image                       =   serializers.SerializerMethodField()
    offer_price                 =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'offer_price', 'features', 'image', 'category', 'brand', 'created_at']
    def get_image(self, product):
        return object_url(product.image_key)
    def get_offer_price(self, product):
        #public_catalog anota effective_offer = menor entre la oferta manual
        #y el mejor descuento vigente — toda la web pública muestra el mismo
        #precio efectivo (badge, tachado, orden y filtros).
        return getattr(product, 'effective_offer', product.offer_price)
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
    class Meta:
        model                   =   Discount
        fields                  =   ['id', 'name', 'percent', 'scope', 'category', 'brand', 'products', 'starts_at', 'ends_at', 'is_active']
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
    class Meta:
        model                   =   Discount
        fields                  =   [
            'id', 'name', 'percent', 'scope', 'category', 'category_name', 'brand', 'brand_name',
            'products', 'products_count', 'starts_at', 'ends_at', 'is_active', 'status', 'created_at',
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
        return 'active'
    def get_products_count(self, discount):
        return discount.products.count()
