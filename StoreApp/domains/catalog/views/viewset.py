import csv
import io
from decimal import Decimal

from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from DaventProject.throttling import PublicReadThrottle

from StoreApp.domains.catalog.serializers.serializers import (
    BrandSerializer,
    ProductSerializerList,
)
from StoreApp.domains.catalog.services.price_updates import (
    BULK_FIELDS,
    BULK_MODES,
    BULK_SCOPES,
    ROUNDINGS,
    bulk_update_prices,
    import_prices,
    parse_decimal,
    parse_price_csv,
)
from StoreApp.domains.catalog.services.services import (
    can_add_product,
    catalog_enabled,
    products_limit,
)
from StoreApp.domains.stores.services import (
    delete_brand_image,
    delete_product_image,
    profile_has_benefit,
    remove_background,
    storage_payload,
    upload_brand_image,
    upload_product_image,
    validate_image_file,
)

from .viewset_base import CatalogBaseViewSet
from .viewset_config import (
    BrandConfigs,
    CategoryConfigs,
    DiscountConfigs,
    ProductConfigs,
    ReviewConfigs,
)

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
    # BRAND IMAGE (logo PNG -> WebP con transparencia, multipart)
    #=========================================
    @action(detail = True, methods = ['post', 'delete'], url_path = 'image')
    def image(self, request, pk = None):
        denied  =   self._deny_without_catalog()
        if denied: return denied
        brand   =   self.get_object()
        store   =   brand.store
        if request.method == 'DELETE':
            delete_brand_image(brand)
            message =   'La imagen de la marca se eliminó.'
        else:
            upload  =   request.FILES.get('image')
            if upload is None:
                return Response({'image': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
            try:
                upload_brand_image(brand, upload)
            except ValueError as error:
                return Response({'image': str(error)}, status = status.HTTP_400_BAD_REQUEST)
            message =   'La imagen de la marca se actualizó.'
        return Response(
            {
                'Exito'     :   message,
                'item'      :   BrandSerializer(brand).data,
                'storage'   :   storage_payload(store, store.user),
            },
            status = status.HTTP_200_OK,
        )
    def perform_destroy(self, instance):
        # Libera la imagen (R2 + cuota) antes de borrar la marca.
        if instance.image_key:
            delete_brand_image(instance)
        instance.delete()
#=========================================
# DISCOUNT VIEWSET (descuentos programados de la tienda)
#=========================================
class DiscountViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   DiscountConfigs
    def _deny_without_discounts(self):
        #Sistema de descuentos programados: función premium
        #('has_discounts'). Sin el flag la web ya no los aplica
        #(running_discounts_of sale vacío) y el panel tampoco los gestiona.
        if not profile_has_benefit(self.my_store().user, 'has_discounts'):
            return Response(
                {'detail': 'Los descuentos programados están disponibles con el plan Premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return None
    def list(self, request, *args, **kwargs):
        denied  =   self._deny_without_discounts()
        if denied: return denied
        return super().list(request, *args, **kwargs)
    def create(self, request):
        denied  =   self._deny_without_discounts()
        if denied: return denied
        return self._swap_item(request, super().create(request))
    def update(self, request, pk = None):
        denied  =   self._deny_without_discounts()
        if denied: return denied
        return self._swap_item(request, super().update(request, pk))
    def partial_update(self, request, pk = None):
        return self.update(request, pk)
    def destroy(self, request, pk = None):
        denied  =   self._deny_without_discounts()
        if denied: return denied
        return super().destroy(request, pk)
    def _swap_item(self, request, response):
        """
        Como en ProductViewSet: tras guardar, el `item` de la respuesta se
        re-serializa con DiscountSerializerList para que viaje el estado
        derivado de la ventana (scheduled/active/ended/paused).
        """
        if response.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
            return response
        from StoreApp.domains.catalog.serializers.serializers import (
            DiscountSerializerList,
        )
        discount    =   self.get_queryset().filter(pk = response.data['item']['id']).first()
        if discount is not None:
            response.data['item']   =   DiscountSerializerList(discount).data
        return response
#=========================================
# SPECIAL OFFER CAMPAIGN VIEWSET (calendario de ofertas: lectura pública,
# alta/edición solo staff — las etiquetas son assets del sistema en R2)
#=========================================
class SpecialOfferCampaignViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/offers/          → público: campañas activas ordenadas (con
                                is_running y la ventana del año en curso).
    GET /api/offers/<slug>/label/ → redirige a la etiqueta servida desde R2.
    Escritura                 → IsAdminUser (el calendario es del sistema).
    """
    #Lectura pública: scope 'public_read' (1000/h por IP) como el resto de
    #endpoints públicos — sin esto los GET del calendario descontaban de la
    #cuota 'user' (1000/día) del dueño logueado y, agotada, el dashboard no
    #podía cargar las campañas (avisos "Se acerca…" y opciones del select
    #de vigencia desaparecían con un 429).
    def get_throttles(self):
        if self.request.method in SAFE_METHODS:
            return [PublicReadThrottle()]
        return super().get_throttles()
    lookup_field        =   'slug'
    def get_queryset(self):
        from StoreApp.domains.catalog.models import SpecialOfferCampaign
        if self.request.method in SAFE_METHODS:
            return SpecialOfferCampaign.objects.filter(is_active = True)
        return SpecialOfferCampaign.objects.all()
    def get_serializer_class(self):
        from StoreApp.domains.catalog.serializers.serializers import (
            SpecialOfferCampaignSerializer,
        )
        return SpecialOfferCampaignSerializer
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]
    @action(detail = True, methods = ['get'], url_path = 'label')
    def label(self, request, slug = None):
        from StoreApp.domains.stores.services.storage import object_url
        campaign    =   get_object_or_404(self.get_queryset(), slug = slug)
        #La etiqueta es un asset público del sistema, pero la URL pública del
        #bucket puede no estar habilitada: se redirige a la firmada (7 días).
        url         =   object_url(campaign.label_key, private = True)
        if not url:
            raise Http404
        return HttpResponseRedirect(url)
#=========================================
# REVIEW VIEWSET (moderación del dueño: lista y borra opiniones de su
# tienda; el alta vive en la web pública, nunca en este endpoint)
#=========================================
class ReviewViewSet(CatalogGateMixin, CatalogBaseViewSet):
    viewset_config  =   ReviewConfigs
    http_method_names   =   ['get', 'patch', 'delete', 'head', 'options']
    def _deny_without_reviews(self):
        #Las opiniones son premium ('has_product_comments'): sin el flag
        #tampoco se moderan desde el panel (la web pública ya las cierra).
        if not profile_has_benefit(self.my_store().user, 'has_product_comments'):
            return Response(
                {'detail': 'Las valoraciones y comentarios están disponibles con el plan Premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return None
    def list(self, request, *args, **kwargs):
        denied  =   self._deny_without_reviews()
        if denied: return denied
        return super().list(request, *args, **kwargs)
    def destroy(self, request, pk = None):
        denied  =   self._deny_without_reviews()
        if denied: return denied
        return super().destroy(request, pk)
    def update(self, request, pk = None):
        #La opinión ajena no se edita: PATCH /reviews/<pk>/ queda cerrado
        #— la respuesta del dueño vive en la acción `reply` de abajo.
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
    def partial_update(self, request, pk = None):
        return self.update(request, pk)
    #=========================================
    # REPLY (respuesta pública del dueño a una opinión)
    #=========================================
    @action(detail = True, methods = ['patch'], url_path = 'reply')
    def reply(self, request, pk = None):
        """
        PATCH /api/reviews/<pk>/reply/ {owner_reply} — función exclusiva del
        dueño: la opinión ajena no se edita (solo se borra) y el visitante
        nunca llega a este endpoint (IsAuthenticated + queryset de su
        tienda). Texto vacío = quitar la respuesta de la web.
        """
        denied  =   self._deny_without_reviews()
        if denied: return denied
        from StoreApp.domains.catalog.serializers.serializers import (
            ReviewReplySerializer,
            ReviewSerializerList,
        )
        review      =   self.get_object()
        serializer  =   ReviewReplySerializer(review, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        review.refresh_from_db()
        return Response(
            {
                'Exito' : 'La respuesta se publicó en tu web.' if review.owner_reply else 'La respuesta se quitó de tu web.',
                'item'  : ReviewSerializerList(review).data,
            }
        )
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
    #=========================================
    # BULK PRICES (aumento/baja masiva del dueño)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'bulk-prices')
    def bulk_prices(self, request):
        """
        {mode: percent|delta|set, value, field?: price|offer_price,
         scope?: all|category|brand|products, category?, brand?,
         product_ids?[], rounding?: none|unit|ten|hundred}
        Actualiza el campo elegido en el recorte pedido y devuelve cuántos
        productos cambiaron. Nunca baja de 0 (clamp).
        """
        denied      =   self._deny_without_catalog()
        if denied: return denied
        data        =   request.data or {}
        errors      =   {}
        mode        =   data.get('mode')
        if mode not in BULK_MODES:
            errors['mode']  =   'Elegí cómo actualizar: porcentaje, monto fijo o precio nuevo.'
        field       =   data.get('field') or 'price'
        if field not in BULK_FIELDS:
            errors['field'] =   'Campo inválido.'
        scope       =   data.get('scope') or 'all'
        if scope not in BULK_SCOPES:
            errors['scope'] =   'Alcance inválido.'
        rounding    =   data.get('rounding') or 'none'
        if rounding not in ROUNDINGS:
            errors['rounding']  =   'Redondeo inválido.'
        value       =   parse_decimal(data.get('value'))
        if value is None:
            errors['value'] =   'Ingresá un número válido.'
        elif mode == 'percent' and value <= Decimal(-100):
            errors['value'] =   'La baja no puede ser del 100% o más.'
        elif mode == 'set' and value < 0:
            errors['value'] =   'El precio no puede ser negativo.'
        store       =   self.my_store()
        category_id =   data.get('category')
        brand_id    =   data.get('brand')
        product_ids =   data.get('product_ids') or []
        if scope == 'category' and not store.categories.filter(pk = category_id).exists():
            errors['category']  =   'Elegí una categoría de tu tienda.'
        if scope == 'brand' and not store.brands.filter(pk = brand_id).exists():
            errors['brand'] =   'Elegí una marca de tu tienda.'
        if scope == 'products' and not product_ids:
            errors['product_ids']   =   'Elegí al menos un producto.'
        if errors:
            return Response(errors, status = status.HTTP_400_BAD_REQUEST)
        updated     =   bulk_update_prices(
            store, mode = mode, value = value, field = field, scope = scope,
            category_id = category_id, brand_id = brand_id,
            product_ids = product_ids, rounding = rounding,
        )
        return Response({'Exito': f'Se actualizaron {updated} productos.', 'updated': updated})
    #=========================================
    # IMPORT PRICES (lista del proveedor en CSV)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'import-prices')
    def import_prices_csv(self, request):
        """
        multipart {file, dry_run?}: CSV con columnas id|nombre + precio
        (+ oferta opcional). Devuelve {updated, matched, skipped[],
        preview[]}; dry_run=1 reporta sin guardar.
        """
        denied      =   self._deny_without_catalog()
        if denied: return denied
        upload      =   request.FILES.get('file')
        if upload is None:
            return Response({'file': 'Adjuntá el archivo CSV de la lista de precios.'}, status = status.HTTP_400_BAD_REQUEST)
        if upload.size > 2 * 1024 * 1024:
            return Response({'file': 'El archivo supera los 2 MB.'}, status = status.HTTP_400_BAD_REQUEST)
        rows, fatal =   parse_price_csv(upload)
        if fatal:
            return Response({'file': fatal}, status = status.HTTP_400_BAD_REQUEST)
        dry_run     =   str(request.data.get('dry_run', '')).lower() in ('1', 'true')
        report      =   import_prices(self.my_store(), rows, dry_run = dry_run)
        report['Exito'] =   f'Se actualizaron {report["updated"]} productos.' if not dry_run else 'Vista previa: no se guardó nada todavía.'
        return Response(report)
    #=========================================
    # EXPORT PRICES (plantilla/backup de la lista)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'export-prices')
    def export_prices(self, request):
        """CSV id,nombre,precio,oferta,categoría,marca de la tienda (base del import)."""
        denied      =   self._deny_without_catalog()
        if denied: return denied
        buffer      =   io.StringIO()
        writer      =   csv.writer(buffer)
        writer.writerow(['id', 'nombre', 'precio', 'oferta', 'categoria', 'marca'])
        for p in self.get_queryset():
            writer.writerow([p.id, p.name, p.price, p.offer_price if p.offer_price is not None else '', p.category.name if p.category else '', p.brand.name if p.brand else ''])
        response    =   HttpResponse('\ufeff' + buffer.getvalue(), content_type = 'text/csv; charset=utf-8')
        response['Content-Disposition'] =   'attachment; filename="precios.csv"'
        return response
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
