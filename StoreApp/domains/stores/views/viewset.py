from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from StoreApp.domains.stores.models                  import Store, StoreCustomization, StoreCarouselImage
from StoreApp.domains.stores.serializers.serializers import (
    StorePublicSerializer, StoreCustomizationSerializer, StoreCarouselImageSerializer,
)
from StoreApp.domains.stores.serializers.validators  import (
    RESERVED_SLUGS,
    validate_slug_format,
    validate_slug_available,
)
from StoreApp.domains.stores.services                import (
    profile_has_benefit, storage_payload, upload_logo, delete_logo,
    upload_carousel_image, delete_carousel_image,
)
from .viewset_base   import StoreBaseViewSet
from .viewset_config import StoreConfigs
"""

Viewsets del dominio Stores.

"""
#=========================================
# STORE VIEWSET
#=========================================
class StoreViewSet(StoreBaseViewSet):
    viewset_config  =   StoreConfigs

    def get_permissions(self):
        if self.action in ('public', 'public_catalog'):
            return [AllowAny()]
        return super().get_permissions()
    #=========================================
    # SLUG AVAILABLE (check de disponibilidad para el onboarding)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'slug-available')
    def slug_available(self, request):
        slug        =   (request.query_params.get('slug') or '').strip().lower()
        if not validate_slug_format(slug):
            return Response({'slug': slug, 'available': False, 'reason': 'invalid'}, status = status.HTTP_200_OK)
        if slug in RESERVED_SLUGS:
            return Response({'slug': slug, 'available': False, 'reason': 'reserved'}, status = status.HTTP_200_OK)
        available   =   validate_slug_available(slug)
        return Response({'slug': slug, 'available': available, 'reason': None if available else 'taken'}, status = status.HTTP_200_OK)
    #=========================================
    # PUBLIC (resolución pública del link, sin auth)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)')
    def public(self, request, slug = None):
        store       =   get_object_or_404(
            Store.objects.select_related('user__city', 'user__province', 'customization'),
            slug = slug, is_published = True,
        )
        #La web pública se apaga sin suscripción vigente (baja o vencimiento sin renovar)
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        serializer  =   StorePublicSerializer(store)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # PUBLIC CATALOG (productos/categorías/marcas visibles, con buscador)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)/catalog')
    def public_catalog(self, request, slug = None):
        from StoreApp.domains.catalog.models import Product
        from StoreApp.domains.catalog.serializers.serializers import (
            CategorySerializer, BrandSerializer, ProductPublicSerializer,
        )
        store           =   get_object_or_404(
            Store.objects.select_related('user'),
            slug = slug, is_published = True,
        )
        #La web pública se apaga sin suscripción vigente (baja o vencimiento sin renovar)
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        products        =   Product.objects.filter(store = store, is_active = True).select_related('category', 'brand')
        category_id     =   request.query_params.get('category')
        brand_id        =   request.query_params.get('brand')
        search          =   (request.query_params.get('q') or '').strip()
        if category_id and category_id.isdigit():
            products    =   products.filter(category_id = int(category_id))
        if brand_id and brand_id.isdigit():
            products    =   products.filter(brand_id = int(brand_id))
        if search:
            from django.db.models import Q
            products    =   products.filter(Q(name__icontains = search) | Q(description__icontains = search))
        categories      =   store.categories.all()
        brands          =   store.brands.all()
        return Response(
            {
                'categories'    :   CategorySerializer(categories, many = True).data,
                'brands'        :   BrandSerializer(brands, many = True).data,
                'products'      :   ProductPublicSerializer(products, many = True).data,
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # CUSTOMIZATION (diseño de la web pública, gated por el plan)
    #=========================================
    @action(detail = False, methods = ['get', 'put', 'patch'], url_path = 'customization')
    def customization(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if request.method != 'GET' and not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        if request.method == 'GET':
            return Response(StoreCustomizationSerializer(customization).data, status = status.HTTP_200_OK)
        serializer        =   StoreCustomizationSerializer(customization, data = request.data, partial = (request.method == 'PATCH'))
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito'         : 'El diseño de tu web se actualizó correctamente',
                'customization' : serializer.data,
                'storage'       : storage_payload(store, store.user),
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # LOGO (subir/quitar el logo de la web, premium, multipart)
    #=========================================
    @action(detail = False, methods = ['post', 'delete'], url_path = 'customization/logo')
    def customization_logo(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'El logo de tu web está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        if request.method == 'DELETE':
            delete_logo(customization)
            return Response(
                {
                    'Exito'         : 'El logo se eliminó correctamente',
                    'customization' : StoreCustomizationSerializer(customization).data,
                    'storage'       : storage_payload(customization.store, store.user),
                },
                status = status.HTTP_200_OK,
            )
        upload          =   request.FILES.get('logo')
        if upload is None:
            return Response({'logo': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            upload_logo(customization, upload)
        except ValueError as error:
            return Response({'logo': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'Exito'         : 'El logo se actualizó correctamente',
                'customization' : StoreCustomizationSerializer(customization).data,
                'storage'       : storage_payload(customization.store, store.user),
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # CAROUSEL (banners de la web, premium, multipart)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'customization/carousel')
    def carousel_add(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'El carrusel de imágenes está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        upload          =   request.FILES.get('image')
        if upload is None:
            return Response({'image': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            image       =   upload_carousel_image(store, upload)
        except ValueError as error:
            return Response({'image': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'Exito' : 'La imagen se agregó al carrusel',
                'image' : StoreCarouselImageSerializer(image).data,
                'storage'   : storage_payload(image.store, store.user),
            },
            status = status.HTTP_201_CREATED,
        )

    @action(detail = False, methods = ['delete'], url_path = r'customization/carousel/(?P<image_id>\d+)')
    def carousel_remove(self, request, image_id = None):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'El carrusel de imágenes está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        image           =   get_object_or_404(StoreCarouselImage, pk = image_id, store = store)
        delete_carousel_image(image)
        return Response(
            {
                'Exito' : 'La imagen se eliminó del carrusel',
                'storage'   : storage_payload(image.store, store.user),
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['patch'], url_path = 'customization/carousel/order')
    def carousel_order(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'El carrusel de imágenes está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        order           =   request.data.get('order')
        if not isinstance(order, list):
            return Response({'order': 'Enviá la lista de ids en el nuevo orden.'}, status = status.HTTP_400_BAD_REQUEST)
        images          =   {image.id: image for image in store.carousel_images.all()}
        position        =   0
        for image_id in order:
            image       =   images.get(image_id)
            if image is None:
                continue
            if image.position != position:
                image.position  =   position
                image.save(update_fields = ['position'])
            position    +=  1
        return Response({'Exito': 'El orden del carrusel se actualizó'}, status = status.HTTP_200_OK)
