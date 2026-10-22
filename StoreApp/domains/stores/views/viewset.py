from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from StoreApp.domains.stores.models                  import Store, StoreCustomization, StoreCarouselImage
from StoreApp.domains.stores.serializers.serializers import (
    StoreSerializerList, StorePublicSerializer, StoreCustomizationSerializer,
    StoreCarouselImageSerializer, StoreContactSerializer,
)
from StoreApp.domains.stores.serializers.validators  import (
    RESERVED_SLUGS,
    validate_slug_format,
    validate_slug_available,
)
from StoreApp.domains.stores.services                import (
    profile_has_benefit, storage_payload, upload_logo, delete_logo,
    upload_carousel_image, delete_carousel_image,
    issue_captcha, verify_captcha, send_contact_message, contact_target,
)
from .viewset_base   import StoreBaseViewSet
from .viewset_config import StoreConfigs
"""

Viewsets del dominio Stores.

"""
#Campos del diseño reservados a has_design_advanced (Plan premium): en un
#PATCH/PUT de customization se descartan del payload en vez de rechazar la
#request, así el resto del formulario (contenido, logo y tema) se guarda
#igual y los valores ya guardados quedan intactos.
DESIGN_ADVANCED_FIELDS  =   ('name_font', 'name_font_size', 'accent')
#El mapa de ubicación tiene su propio beneficio (has_location_map: Estándar
#y Premium): se descarta igual que los campos premium, por separado.
LOCATION_FIELDS         =   ('show_location',)
#=========================================
# CONTACT THROTTLE (antispam del formulario público, rate en settings)
#=========================================
class StoreContactThrottle(AnonRateThrottle):
    scope   =   'store_contact'
#=========================================
# STORE VIEWSET
#=========================================
class StoreViewSet(StoreBaseViewSet):
    viewset_config  =   StoreConfigs

    def get_permissions(self):
        if self.action in ('public', 'public_catalog', 'contact_captcha', 'contact'):
            return [AllowAny()]
        if self.action in ('block', 'unblock'):
            return [IsAdminUser()]
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
    # BLOCK / UNBLOCK (moderación staff: la web pública pasa a 404)
    #=========================================
    @action(detail = True, methods = ['post'])
    def block(self, request, pk = None):
        store                   =   self.get_object()
        reason                  =   (request.data.get('reason') or '').strip()[:200]
        store.is_blocked        =   True
        store.blocked_reason    =   reason
        store.blocked_at        =   timezone.now()
        store.save(update_fields = ['is_blocked', 'blocked_reason', 'blocked_at'])
        return Response(
            {
                'Exito' : 'La web se bloqueó correctamente',
                'store' : StoreSerializerList(store).data,
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = True, methods = ['post'])
    def unblock(self, request, pk = None):
        store                   =   self.get_object()
        store.is_blocked        =   False
        store.blocked_reason    =   ''
        store.blocked_at        =   None
        store.save(update_fields = ['is_blocked', 'blocked_reason', 'blocked_at'])
        return Response(
            {
                'Exito' : 'La web se desbloqueó correctamente',
                'store' : StoreSerializerList(store).data,
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # PUBLIC (resolución pública del link, sin auth)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)')
    def public(self, request, slug = None):
        store       =   get_object_or_404(
            Store.objects.select_related('user__city', 'user__province', 'customization'),
            slug = slug, is_published = True, is_blocked = False,
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
            slug = slug, is_published = True, is_blocked = False,
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
    # CONTACT (formulario "Contáctanos" de la web pública, antispam)
    #=========================================
    def _contact_store(self, slug):
        #Mismas condiciones que la web pública + sección habilitada por el dueño.
        store       =   get_object_or_404(
            Store.objects.select_related('user__user', 'customization'),
            slug = slug, is_published = True, is_blocked = False,
        )
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        if getattr(store.customization, 'show_contact', True) is False:
            raise Http404
        return store

    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)/contact/captcha')
    def contact_captcha(self, request, slug = None):
        self._contact_store(slug)
        return Response(issue_captcha(slug), status = status.HTTP_200_OK)

    @action(detail = False, methods = ['post'], url_path = r'public/(?P<slug>[a-z0-9-]+)/contact', throttle_classes = [StoreContactThrottle])
    def contact(self, request, slug = None):
        store       =   self._contact_store(slug)
        serializer  =   StoreContactSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        #Honeypot: si el campo oculto viene completo es un bot — éxito falso.
        if data.get('website'):
            return Response({'Exito': 'Tu mensaje fue enviado.'}, status = status.HTTP_200_OK)
        if not contact_target(store):
            return Response(
                {'detail': 'Esta tienda no puede recibir mensajes por ahora.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        if not verify_captcha(slug, data['challenge_id'], data['captcha_answer']):
            return Response(
                {'captcha_answer': 'El captcha venció o la respuesta no es correcta. Probá de nuevo.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        send_contact_message(store, name = data['name'], email = data['email'], message = data['message'])
        return Response({'Exito': 'Tu mensaje fue enviado. El comercio te va a responder a la brevedad.'}, status = status.HTTP_200_OK)
    #=========================================
    # CUSTOMIZATION (diseño de la web pública, gated por el plan)
    #=========================================
    @action(detail = False, methods = ['get', 'put', 'patch'], url_path = 'customization')
    def customization(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if request.method != 'GET' and not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        if request.method == 'GET':
            return Response(StoreCustomizationSerializer(customization).data, status = status.HTTP_200_OK)
        data            =   request.data
        discard         =   []
        if not profile_has_benefit(store.user, 'has_design_advanced'):
            discard.extend(DESIGN_ADVANCED_FIELDS)
        if not profile_has_benefit(store.user, 'has_location_map'):
            discard.extend(LOCATION_FIELDS)
        if discard:
            data        =   request.data.copy()
            for field in discard:
                data.pop(field, None)
        serializer        =   StoreCustomizationSerializer(customization, data = data, partial = (request.method == 'PATCH'))
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
    # LOGO (subir/quitar el logo de la web, multipart)
    #=========================================
    @action(detail = False, methods = ['post', 'delete'], url_path = 'customization/logo')
    def customization_logo(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'El logo de tu web requiere una suscripción activa.'},
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
        if not profile_has_benefit(store.user, 'has_design_advanced'):
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
        if not profile_has_benefit(store.user, 'has_design_advanced'):
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
        if not profile_has_benefit(store.user, 'has_design_advanced'):
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
