from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from StoreApp.domains.stores.models                  import Store, StoreCustomization, StoreCarouselImage, StoreGalleryImage, StoreChatbot
from StoreApp.domains.stores.serializers.serializers import (
    StoreSerializerList, StorePublicSerializer, StoreCustomizationSerializer,
    StoreCarouselImageSerializer, StoreGalleryImageSerializer, StoreContactSerializer,
    StoreChatbotSerializer,
)
from StoreApp.domains.stores.serializers.validators  import (
    RESERVED_SLUGS,
    validate_slug_format,
    validate_slug_available,
)
from StoreApp.domains.stores.services                import (
    profile_has_benefit, storage_payload, upload_logo, delete_logo, upload_cover, delete_cover,
    upload_carousel_image, delete_carousel_image,
    upload_gallery_image, delete_gallery_image,
    issue_captcha, verify_captcha, send_contact_message, contact_target,
    record_store_visit, visit_stats_of,
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
DESIGN_ADVANCED_FIELDS  =   ('name_font', 'name_font_size', 'accent', 'template')
#El mapa de ubicación tiene su propio beneficio (has_location_map: Estándar
#y Premium): se descarta igual que los campos premium, por separado.
LOCATION_FIELDS         =   ('show_location',)
#Ordenamientos admitidos por el catálogo público (whitelist cerrada: el
#param ?sort= jamás llega crudo al order_by). Sin sort válido queda el
#ordering del Meta de Product (name, id).
CATALOG_SORTS           =   {
    'price_asc'     :   ('price', 'name'),
    'price_desc'    :   ('-price', 'name'),
    'recent'        :   ('-created_at', '-id'),
    'name'          :   ('name', 'id'),
}
#=========================================
# HELPERS
#=========================================
def _price_bound(raw):
    #Parseo defensivo de ?min_price=/max_price= del catálogo público: un
    #valor inválido o negativo se ignora (no filtra), como hacen los ids
    #no numéricos de category/brand.
    from decimal import Decimal, InvalidOperation
    try:
        value   =   Decimal(str(raw).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value.is_finite() and value >= 0 else None
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
    # CREATE OVERRIDE (claim del link: exige correo verificado — anti-abuso trial)
    #=========================================
    def create(self, request):
        #Sin email verificado cualquiera podría farmear tiendas con el plan de
        #prueba. Solo el claim se bloquea: panel y cuenta siguen funcionando.
        profile     =   getattr(request.user, 'profile', None)
        if profile is not None and not profile.email_verified and not request.user.is_staff:
            return Response(
                {'detail': 'Antes de crear tu web pública tenés que verificar tu correo electrónico. Revisá tu casilla o pedí el reenvío desde tu panel.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return super().create(request)
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
        record_store_visit(store, request)
        serializer  =   StorePublicSerializer(store)
        return Response(serializer.data, status = status.HTTP_200_OK)
    #=========================================
    # STATS (visitas de la web del dueño, beneficio has_stats: Estándar+)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'stats')
    def stats(self, request):
        profile     =   getattr(request.user, 'profile', None)
        store       =   getattr(profile, 'store', None)
        if store is None:
            return Response({'detail': 'Todavía no tenés una web creada.'}, status = status.HTTP_404_NOT_FOUND)
        if not profile_has_benefit(profile, 'has_stats'):
            return Response({'detail': 'Las estadísticas de visitas están disponibles desde el plan Estándar.'}, status = status.HTTP_403_FORBIDDEN)
        return Response(visit_stats_of(store), status = status.HTTP_200_OK)
    #=========================================
    # CHATBOT (asistente de la web pública, beneficio has_chatbot: solo Premium)
    #=========================================
    @action(detail = False, methods = ['get', 'patch'], url_path = 'chatbot')
    def chatbot(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if request.method != 'GET' and not profile_has_benefit(store.user, 'has_chatbot'):
            return Response(
                {'detail': 'El chatbot de tu web está disponible con el plan Premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        cfg, _          =   StoreChatbot.objects.get_or_create(store = store)
        if request.method == 'GET':
            return Response(StoreChatbotSerializer(cfg).data, status = status.HTTP_200_OK)
        serializer      =   StoreChatbotSerializer(cfg, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito'     : 'El chatbot se actualizó correctamente',
                'chatbot'   : serializer.data,
            },
            status = status.HTTP_200_OK,
        )
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
            Store.objects.select_related('user', 'customization'),
            slug = slug, is_published = True, is_blocked = False,
        )
        #La web pública se apaga sin suscripción vigente (baja o vencimiento sin renovar)
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        #El dueño puede apagar el catálogo y usar su web solo como vidriera:
        #mismo criterio que show_contact en el formulario (404, no vacío).
        customization     =   getattr(store, 'customization', None)
        if customization is not None and customization.show_catalog is False:
            raise Http404
        products        =   Product.objects.filter(store = store, is_active = True).select_related('category', 'brand')
        category_id     =   request.query_params.get('category')
        brand_id        =   request.query_params.get('brand')
        search          =   (request.query_params.get('q') or '').strip()
        min_price       =   _price_bound(request.query_params.get('min_price'))
        max_price       =   _price_bound(request.query_params.get('max_price'))
        sort            =   (request.query_params.get('sort') or '').strip()
        if category_id and category_id.isdigit():
            products    =   products.filter(category_id = int(category_id))
        if brand_id and brand_id.isdigit():
            products    =   products.filter(brand_id = int(brand_id))
        if search:
            from django.db.models import Q
            products    =   products.filter(Q(name__icontains = search) | Q(description__icontains = search))
        if min_price is not None:
            products    =   products.filter(price__gte = min_price)
        if max_price is not None:
            products    =   products.filter(price__lte = max_price)
        ordering        =   CATALOG_SORTS.get(sort)
        if ordering:
            products    =   products.order_by(*ordering)
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
        if not send_contact_message(store, name = data['name'], email = data['email'], message = data['message']):
            return Response(
                {'detail': 'No pudimos enviar tu mensaje en este momento. Probá de nuevo más tarde.'},
                status = status.HTTP_503_SERVICE_UNAVAILABLE,
            )
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
    # COVER (imagen de portada de la web, premium, multipart)
    #=========================================
    @action(detail = False, methods = ['post', 'delete'], url_path = 'customization/cover')
    def customization_cover(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_design_advanced'):
            return Response(
                {'detail': 'La imagen de portada está disponible en el Plan premium.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        if request.method == 'DELETE':
            delete_cover(customization)
            message     =   'La imagen de portada se eliminó correctamente'
        else:
            upload      =   request.FILES.get('cover')
            if upload is None:
                return Response({'cover': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
            try:
                upload_cover(customization, upload)
            except ValueError as error:
                return Response({'cover': str(error)}, status = status.HTTP_400_BAD_REQUEST)
            message     =   'La imagen de portada se actualizó correctamente'
        return Response(
            {
                'Exito'         : message,
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
    #=========================================
    # GALLERY (sección Galería de la web, tope max_gallery_images por plan)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'customization/gallery')
    def gallery_add(self, request):
        #El cupo por plan (Básico 0 / Estándar 5 / Premium 15) lo fuerza el
        #servicio con ValueError -> 400; acá solo se exige suscripción activa.
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La galería de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        upload          =   request.FILES.get('image')
        if upload is None:
            return Response({'image': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            image       =   upload_gallery_image(store, upload, request.data.get('kind') or 'gallery')
        except ValueError as error:
            return Response({'image': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'Exito' : 'La imagen se agregó a la galería' if image.kind == 'gallery' else 'La imagen decorativa se agregó a tu portada',
                'image' : StoreGalleryImageSerializer(image).data,
                'storage'   : storage_payload(image.store, store.user),
            },
            status = status.HTTP_201_CREATED,
        )

    @action(detail = False, methods = ['delete'], url_path = r'customization/gallery/(?P<image_id>\d+)')
    def gallery_remove(self, request, image_id = None):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La galería de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        image           =   get_object_or_404(StoreGalleryImage, pk = image_id, store = store)
        delete_gallery_image(image)
        return Response(
            {
                'Exito' : 'La imagen se eliminó de la galería',
                'storage'   : storage_payload(image.store, store.user),
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['patch'], url_path = 'customization/gallery/order')
    def gallery_order(self, request):
        store           =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La galería de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        order           =   request.data.get('order')
        if not isinstance(order, list):
            return Response({'order': 'Enviá la lista de ids en el nuevo orden.'}, status = status.HTTP_400_BAD_REQUEST)
        images          =   {image.id: image for image in store.gallery_images.all()}
        position        =   0
        for image_id in order:
            image       =   images.get(image_id)
            if image is None:
                continue
            if image.position != position:
                image.position  =   position
                image.save(update_fields = ['position'])
            position    +=  1
        return Response({'Exito': 'El orden de la galería se actualizó'}, status = status.HTTP_200_OK)
