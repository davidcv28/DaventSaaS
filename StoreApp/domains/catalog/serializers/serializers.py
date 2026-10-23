from rest_framework import serializers
from StoreApp.domains.catalog.models import Category, Brand, Product
from StoreApp.domains.stores.services.storage import object_url
from .config_fields import TaxonomyFields, ProductFields
from .mixins        import TaxonomyMixinValidator, CategorySchemaMixinValidator, ProductMixinValidator
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
    category                    =   serializers.PrimaryKeyRelatedField(queryset = Category.objects.all(), **ProductFields['category'])
    brand                       =   serializers.PrimaryKeyRelatedField(queryset = Brand.objects.all(), **ProductFields['brand'])
    is_active                   =   serializers.BooleanField(**ProductFields['is_active'])
    #binary=True: en multipart llega como string JSON y se parsea solo.
    features                    =   serializers.JSONField(binary = True, **ProductFields['features'])
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'category', 'brand', 'is_active', 'features']
#=========================================
# PRODUCT SERIALIZER LIST (mi catálogo, con imagen y nombres)
#=========================================
class ProductSerializerList(serializers.ModelSerializer):
    image                       =   serializers.SerializerMethodField()
    category_name               =   serializers.CharField(source = 'category.name', read_only = True)
    brand_name                  =   serializers.CharField(source = 'brand.name', read_only = True)
    class Meta:
        model                   =   Product
        fields                  =   [
            'id', 'name', 'description', 'price', 'category', 'category_name',
            'brand', 'brand_name', 'is_active', 'features', 'image', 'created_at',
        ]
    def get_image(self, product):
        return object_url(product.image_key)
#=========================================
# PRODUCT PUBLIC SERIALIZER (visitante de la web)
#=========================================
class ProductPublicSerializer(serializers.ModelSerializer):
    image                       =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Product
        fields                  =   ['id', 'name', 'description', 'price', 'features', 'image', 'category', 'brand']
    def get_image(self, product):
        return object_url(product.image_key)
