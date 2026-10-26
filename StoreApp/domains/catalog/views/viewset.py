from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from StoreApp.domains.catalog.services.services   import catalog_enabled, can_add_product, products_limit
from StoreApp.domains.catalog.serializers.serializers import ProductSerializerList
from StoreApp.domains.stores.services             import upload_product_image, delete_product_image, storage_payload, validate_image_file, remove_background
from .viewset_base   import CatalogBaseViewSet
from .viewset_config import CategoryConfigs, BrandConfigs, ProductConfigs, DiscountConfigs, ReviewConfigs
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
# DISCOUNT VIEWSET (descuentos programados de la tienda)
#=========================================
class DiscountViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   DiscountConfigs
    def _swap_item(self, request, response):
        """
        Como en ProductViewSet: tras guardar, el `item` de la respuesta se
        re-serializa con DiscountSerializerList para que viaje el estado
        derivado de la ventana (scheduled/active/ended/paused).
        """
        if response.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
            return response
        from StoreApp.domains.catalog.serializers.serializers import DiscountSerializerList
        discount    =   self.get_queryset().filter(pk = response.data['item']['id']).first()
        if discount is not None:
            response.data['item']   =   DiscountSerializerList(discount).data
        return response
    def create(self, request):
        return self._swap_item(request, super().create(request))
    def update(self, request, pk = None):
        return self._swap_item(request, super().update(request, pk))
#=========================================
# REVIEW VIEWSET (moderación del dueño: lista y borra opiniones de su
# tienda; el alta vive en la web pública, nunca en este endpoint)
#=========================================
class ReviewViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   ReviewConfigs
    http_method_names   =   ['get', 'delete', 'head', 'options']
#=========================================
# BACKGROUND REMOVAL THROTTLE (inferencia en CPU: acotada por usuario)
#=========================================
class BackgroundRemovalThrottle(UserRateThrottle):
    scope   =   'bg_removal'
#=========================================
# PRODUCT VIEWSET (imagen multipart + cupo max_products)
#=========================================
class ProductViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   ProductConfigs
    @action(detail = False, methods = ['post'], url_path = 'remove-background', throttle_classes = [BackgroundRemovalThrottle])
    def remove_background(self, request):
        """
        Editor de imagen del catálogo: devuelve (sin guardar nada) la foto del
        producto sin fondo, centrada sobre un lienzo blanco, para que el dueño
        la previsualice y la adjunte al guardar el producto.
        """
        denied      =   self._deny_without_catalog()
        if denied: return denied
        upload      =   request.FILES.get('image')
        if upload is None:
            return Response({'image': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            error   =   validate_image_file(upload)
            if error:
                raise ValueError(error)
            body, _, content_type   =   remove_background(upload)
        except ValueError as error:
            return Response({'image': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return HttpResponse(body, content_type = content_type)
    def _normalize_relations(self, request):
        """
        En multipart los selects vacíos llegan como ''/none: se mapean a
        None para que category/brand (allow_null) los acepten y limpien.
        features viaja como string JSON (JSONField binary): el vacío se
        mapea a '{}' para que limpie en vez de romper el parseo.
        """
        data    =   request.data
        if not hasattr(data, 'get'):
            return
        try:
            mutable =   data.copy()
        except Exception:
            return
        changed =   False
        for field in ('category', 'brand', 'offer_price'):
            value   =   mutable.get(field)
            if value in ('', 'null', 'none', 'None'):
                mutable[field]  =   None
                changed         =   True
        if mutable.get('features') in ('', 'null', 'none', 'None'):
            mutable['features'] =   '{}'
            changed             =   True
        if changed:
            request._full_data  =   mutable
    def create(self, request):
        store   =   self.my_store()
        denied  =   self._deny_without_catalog()
        if denied: return denied
        self._normalize_relations(request)
        #El cupo se rechequea bajo lock de la fila de la tienda: dos creates
        #concurrentes ya no pueden pasar ambos el límite max_products.
        with transaction.atomic():
            locked      =   type(store).objects.select_for_update().get(pk = store.pk)
            if not can_add_product(locked):
                limit   =   products_limit(locked.user)
                return Response(
                    {'detail': f'Tu plan admite hasta {limit} productos. Pasate a un plan superior para sumar más.'},
                    status = status.HTTP_403_FORBIDDEN,
                )
            response    =   super().create(request)
        product     =   self._product_from_response(request, response)
        if product is not None:
            #El context trae la tienda: discount_offer/names de los
            #descuentos vigentes viajan también en la respuesta de guardado.
            response.data['item']   =   ProductSerializerList(product, context = self.get_serializer_context()).data
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
            response.data['item']   =   ProductSerializerList(product, context = self.get_serializer_context()).data
            response.data['storage']    =   storage_payload(product.store, store.user)
        return response
    def destroy(self, request, pk = None):
        denied  =   self._deny_without_catalog()
        if denied: return denied
        instance    =   self.get_object()
        store       =   instance.store
        self.perform_destroy(instance)
        # Devuelve la cuota actualizada para que el medidor se refresque sin recargar.
        return Response(
            {'Exito': 'El producto se eliminó.', 'storage': storage_payload(store, store.user)},
            status = status.HTTP_200_OK,
        )
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
