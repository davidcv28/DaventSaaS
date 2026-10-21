from rest_framework import status
from rest_framework.response import Response
from StoreApp.domains.catalog.services.services   import catalog_enabled, can_add_product, products_limit
from StoreApp.domains.catalog.serializers.serializers import ProductSerializerList
from StoreApp.domains.stores.services             import upload_product_image, delete_product_image, storage_payload
from .viewset_base   import CatalogBaseViewSet
from .viewset_config import CategoryConfigs, BrandConfigs, ProductConfigs
"""

Viewsets del dominio Catalog.

"""
#=========================================
# CATALOG GATE MIXIN (catálogo = suscripción activa)
#=========================================
class CatalogGateMixin:
    def _deny_without_catalog(self):
        if not catalog_enabled(self.my_store().user):
            return Response(
                {'detail': 'El catálogo se habilita con una suscripción activa. Elegí tu plan.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return None
    def create(self, request, *args, **kwargs):
        denied  =   self._deny_without_catalog()
        if denied: return denied
        return super().create(request)
    def update(self, request, pk = None):
        denied  =   self._deny_without_catalog()
        if denied: return denied
        return super().update(request, pk)
    def destroy(self, request, pk = None):
        denied  =   self._deny_without_catalog()
        if denied: return denied
        return super().destroy(request, pk)
#=========================================
# CATEGORY VIEWSET
#=========================================
class CategoryViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   CategoryConfigs
#=========================================
# BRAND VIEWSET
#=========================================
class BrandViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   BrandConfigs
#=========================================
# PRODUCT VIEWSET (imagen multipart + cupo max_products)
#=========================================
class ProductViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   ProductConfigs
    def _normalize_relations(self, request):
        """
        En multipart los selects vacíos llegan como ''/none: se mapean a
        None para que category/brand (allow_null) los acepten y limpien.
        """
        data    =   request.data
        if not hasattr(data, 'get'):
            return
        try:
            mutable =   data.copy()
        except Exception:
            return
        changed =   False
        for field in ('category', 'brand'):
            value   =   mutable.get(field)
            if value in ('', 'null', 'none', 'None'):
                mutable[field]  =   None
                changed         =   True
        if changed:
            request._full_data  =   mutable
    def create(self, request):
        store   =   self.my_store()
        denied  =   self._deny_without_catalog()
        if denied: return denied
        self._normalize_relations(request)
        if not can_add_product(store):
            limit   =   products_limit(store.user)
            return Response(
                {'detail': f'Tu plan admite hasta {limit} productos. Pasate a un plan superior para sumar más.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        response    =   super().create(request)
        product     =   self._product_from_response(request, response)
        if product is not None:
            response.data['item']   =   ProductSerializerList(product).data
            response.data['storage']    =   storage_payload(product.store, store.user)
        return response
    def update(self, request, pk = None):
        store   =   self.my_store()
        denied  =   self._deny_without_catalog()
        if denied: return denied
        self._normalize_relations(request)
        response    =   super().update(request, pk)
        product     =   self._product_from_response(request, response)
        if product is not None:
            response.data['item']   =   ProductSerializerList(product).data
            response.data['storage']    =   storage_payload(product.store, store.user)
        return response
    def perform_destroy(self, instance):
        # Libera la imagen (R2 + cuota) antes de borrar el registro.
        if instance.image_key:
            delete_product_image(instance)
        instance.delete()
    def _product_from_response(self, request, response):
        """
        Sube/quita la imagen multipart tras guardar el producto y devuelve
        la instancia refrescada (None si la respuesta no fue de éxito).
        """
        if response.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
            return None
        product     =   self.get_queryset().filter(pk = response.data['item']['id']).first()
        if product is None:
            return None
        upload      =   request.FILES.get('image')
        try:
            if upload is not None:
                upload_product_image(product, upload)
            elif str(request.data.get('image_clear', '')).lower() in ('1', 'true'):
                delete_product_image(product)
        except ValueError as error:
            response.data['image_error']    =   str(error)
        return product
