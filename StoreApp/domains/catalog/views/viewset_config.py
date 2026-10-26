from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from StoreApp.domains.catalog.models                    import Category, Brand, Product, Discount
from StoreApp.domains.catalog.serializers.serializers   import (
    CategorySerializer, BrandSerializer, ProductSerializer, ProductSerializerList,
    DiscountSerializer, DiscountSerializerList,
)
"""

Configuración de los viewsets del dominio Catalog.
Los queryset siempre recortan a la tienda del usuario autenticado
(view.my_store()); nunca se exponen objetos de otra tienda.

"""
def _own_categories(view):
    return Category.objects.filter(store = view.my_store()).annotate(products_count = Count('products'))
def _own_brands(view):
    return Brand.objects.filter(store = view.my_store()).annotate(products_count = Count('products'))
def _own_products(view):
    return Product.objects.filter(store = view.my_store()).select_related('category', 'brand')
def _own_discounts(view):
    return Discount.objects.filter(store = view.my_store()).select_related('category', 'brand').prefetch_related('products')
#=========================================
# CATEGORY CONFIGS
#=========================================
CategoryConfigs = {
    'create': {
        'serializer' :   CategorySerializer,
        'queryset'   :   _own_categories,
        'permissions':   [IsAuthenticated],
        'message'    :   'La categoría se creó correctamente',
    },
    'update': {
        'serializer' :   CategorySerializer,
        'queryset'   :   _own_categories,
        'permissions':   [IsAuthenticated],
        'message'    :   'La categoría se actualizó correctamente',
    },
    'get': {
        'serializer'    :   CategorySerializer,
        'queryset'      :   _own_categories,
        'permissions'   :   [IsAuthenticated],
        'delete_message':   'La categoría se eliminó correctamente',
    },
}
#=========================================
# BRAND CONFIGS
#=========================================
BrandConfigs = {
    'create': {
        'serializer' :   BrandSerializer,
        'queryset'   :   _own_brands,
        'permissions':   [IsAuthenticated],
        'message'    :   'La marca se creó correctamente',
    },
    'update': {
        'serializer' :   BrandSerializer,
        'queryset'   :   _own_brands,
        'permissions':   [IsAuthenticated],
        'message'    :   'La marca se actualizó correctamente',
    },
    'get': {
        'serializer'    :   BrandSerializer,
        'queryset'      :   _own_brands,
        'permissions'   :   [IsAuthenticated],
        'delete_message':   'La marca se eliminó correctamente',
    },
}
#=========================================
# PRODUCT CONFIGS
#=========================================
ProductConfigs = {
    'create': {
        'serializer' :   ProductSerializer,
        'queryset'   :   _own_products,
        'permissions':   [IsAuthenticated],
        'message'    :   'El producto se creó correctamente',
    },
    'update': {
        'serializer' :   ProductSerializer,
        'queryset'   :   _own_products,
        'permissions':   [IsAuthenticated],
        'message'    :   'El producto se actualizó correctamente',
    },
    'get': {
        'serializer'    :   ProductSerializerList,
        'queryset'      :   _own_products,
        'permissions'   :   [IsAuthenticated],
        'delete_message':   'El producto se eliminó correctamente',
    },
}
#=========================================
# DISCOUNT CONFIGS
#=========================================
DiscountConfigs = {
    'create': {
        'serializer' :   DiscountSerializer,
        'queryset'   :   _own_discounts,
        'permissions':   [IsAuthenticated],
        'message'    :   'El descuento se creó correctamente',
    },
    'update': {
        'serializer' :   DiscountSerializer,
        'queryset'   :   _own_discounts,
        'permissions':   [IsAuthenticated],
        'message'    :   'El descuento se actualizó correctamente',
    },
    'get': {
        'serializer'    :   DiscountSerializerList,
        'queryset'      :   _own_discounts,
        'permissions'   :   [IsAuthenticated],
        'delete_message':   'El descuento se eliminó correctamente',
    },
}
