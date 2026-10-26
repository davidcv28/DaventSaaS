import json
import logging
import re
from datetime import timedelta
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.cache import patch_cache_control
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
    profile_has_benefit, allowed_templates_of, storage_payload,
    upload_logo, delete_logo, upload_cover, delete_cover,
    upload_carousel_image, delete_carousel_image,
    upload_gallery_image, delete_gallery_image,
    issue_captcha, verify_captcha, send_contact_message, contact_target,
    record_store_visit, visit_stats_of,
)
from .viewset_base   import StoreBaseViewSet
from .viewset_config import StoreConfigs
from DaventProject.throttling import PublicReadThrottle
"""

Viewsets del dominio Stores.

"""
#Campos del diseño reservados a has_design_advanced (Plan premium): en un
#PATCH/PUT de customization se descartan del payload en vez de rechazar la
#request, así el resto del formulario (contenido, logo y tema) se guarda
#igual y los valores ya guardados quedan intactos. Las plantillas se
#validan aparte, por nivel de plan (allowed_templates_of del servicio).
logger                  =   logging.getLogger(__name__)
DESIGN_ADVANCED_FIELDS  =   ('name_font', 'name_font_size', 'accent')
#El mapa de ubicación tiene su propio beneficio (has_location_map: Estándar
#y Premium): se descarta igual que los campos premium, por separado.
LOCATION_FIELDS         =   ('show_location',)
#Las opiniones de producto (valoraciones + comentarios) son premium
#(has_product_comments): sin el flag ambos toggles se descartan del PATCH.
REVIEW_FIELDS           =   ('show_reviews', 'show_comments')
#Ordenamientos admitidos por el catálogo público (whitelist cerrada: el
#param ?sort= jamás llega crudo al order_by). Sin sort válido queda el
#ordering del Meta de Product (name, id). Los precios ordenan/filtran por
#el efectivo (la oferta cuando existe): effective_price se anota en el query.
CATALOG_SORTS           =   {
    'price_asc'     :   ('effective_price', 'name'),
    'price_desc'    :   ('-effective_price', 'name'),
    'recent'        :   ('-created_at', '-id'),
    'name'          :   ('name', 'id'),
}
#Días que un producto se considera "novedad" en el catálogo público
#(filtro ?new=1 y new_count) — espejo de PRODUCT_NEW_DAYS del frontend.
CATALOG_NEW_DAYS        =   7
#Topes defensivos de los filtros avanzados: el ?features= viaja como JSON
#{nombre: [valores]} y nunca se evalúa más allá de estos límites.
CATALOG_FEATURE_GROUPS  =   10
CATALOG_FEATURE_VALUES  =   15
CATALOG_IDS_MAX         =   50
#Topes de las facetas devueltas (un atributo con más valores se recorta a
#los más frecuentes; los atributos con menos uso quedan fuera del panel).
CATALOG_FACET_GROUPS    =   12
CATALOG_FACET_VALUES    =   30
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
    if not value.is_finite() or value < 0:
        return None
    #Sin tope, un bound astronómico (p.ej. '1e999') desborda la columna
    #numeric(12,2) y devuelve un 500 público. Se clampea al máximo del
    #campo: gte deja el resultado vacío y lte lo deja completo — la
    #semántica del filtro se conserva sin romper la query.
    return min(value, Decimal('9999999999.99'))
def _id_list(raw):
    """Ids separados por coma (?category=1,2): los no numéricos se descartan."""
    ids =   set()
    for piece in str(raw or '').split(','):
        piece   =   piece.strip()
        if piece.isdigit():
            ids.add(int(piece))
        if len(ids) >= CATALOG_IDS_MAX:
            break
    return ids
def _flag(raw):
    """Flags booleanos del catálogo (?offer=1 / ?new=1)."""
    return str(raw or '').strip().lower() in ('1', 'true', 'yes', 'on')
def _feature_tokens(value):
    """
    Un valor de característica puede listar varias opciones ("S, M / L"):
    se trocea por los separadores habituales para poder facetarlo.
    """
    return [token.strip() for token in re.split(r'[,;/·]', str(value)) if token.strip()]
def _feature_filters(raw):
    """
    Parseo defensivo de ?features={"Talle":["M","L"]}: un JSON inválido o
    con otra forma no filtra nada (mismo criterio que los ids inválidos).
    """
    try:
        data    =   json.loads(str(raw or ''))
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned =   {}
    for name, values in data.items():
        if len(cleaned) >= CATALOG_FEATURE_GROUPS:
            break
        name    =   str(name).strip()
        if not name:
            continue
        if not isinstance(values, list):
            values  =   [values]
        values  =   [str(v).strip() for v in values if str(v).strip()][:CATALOG_FEATURE_VALUES]
        if values:
            cleaned[name]   =   values
    return cleaned
def _features_match(features, filters):
    """
    True si el producto cumple todos los grupos pedidos: dentro de un
    atributo los valores suman (OR), entre atributos se exigen (AND).
    """
    if not isinstance(features, dict):
        return False
    lowered =   {str(k).strip().casefold(): v for k, v in features.items()}
    for name, values in filters.items():
        raw =   lowered.get(name.casefold())
        if raw is None:
            return False
        tokens  =   {t.casefold() for t in _feature_tokens(raw)}
        if not any(v.casefold() in tokens for v in values):
            return False
    return True
def _product_haystack(product):
    """
    Texto buscable del producto (búsqueda ?q=): nombre, descripción,
    categoría, marca y características — como el buscador de la plantilla.
    """
    parts   =   [product.name or '', product.description or '']
    parts.append(product.category.name if product.category_id else '')
    parts.append(product.brand.name if product.brand_id else '')
    if isinstance(product.features, dict):
        parts += [str(k) for k in product.features.keys()]
        parts += [str(v) for v in product.features.values()]
    return ' '.join(parts).casefold()
def _natural_key(text):
    """Orden "humano" de los valores de una faceta: 2 < 10, S < XL."""
    return [int(piece) if piece.isdigit() else piece.casefold() for piece in re.split(r'(\d+)', str(text))]

def _apply_order(queryset, order):
    """
    Reasigna `position` según la lista de ids recibida. Las imágenes que
    el payload no menciona conservan su orden relativo y van al final —
    sin esto quedaban pisando posiciones ya asignadas (orden duplicado
    en el carrusel/galería pública). Los ids repetidos del payload se
    ignoran (moverlos dos veces también dejaba el orden inconsistente).
    """
    images      =   {image.id: image for image in queryset}
    seen        =   set()
    position    =   0
    for image_id in order:
        image   =   images.get(image_id)
        if image is None or image.id in seen:
            continue
        seen.add(image.id)
        if image.position != position:
            image.position  =   position
            image.save(update_fields = ['position'])
        position    +=  1
    for image in sorted((i for i in images.values() if i.id not in seen), key = lambda i: (i.position, i.id)):
        if image.position != position:
            image.position  =   position
            image.save(update_fields = ['position'])
        position    +=  1
#=========================================
# VISIT THROTTLE (anti-inflación del contador de visitas, rate en settings)
#=========================================
class StoreVisitThrottle(AnonRateThrottle):
    #El GET público de la tienda suma +1 visita/día por visitante: scope
    #dedicado más acotado que public_read para frenar el inflate de stats.
    scope   =   'store_visit'
#=========================================
# CONTACT THROTTLE (antispam del formulario público, rate en settings)
#=========================================
class StoreContactThrottle(AnonRateThrottle):
    scope   =   'store_contact'
#=========================================
# REVIEW THROTTLE (alta de opiniones públicas, antispam por IP)
#=========================================
class StoreReviewThrottle(AnonRateThrottle):
    scope   =   'store_review'
#=========================================
# STORE VIEWSET
#=========================================
class StoreViewSet(StoreBaseViewSet):
    viewset_config  =   StoreConfigs

    def get_permissions(self):
        if self.action in ('public', 'public_catalog', 'contact_captcha', 'contact', 'review_captcha', 'product_reviews'):
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
        if profile is not None and not request.user.is_staff:
            if not profile.email_verified:
                return Response(
                    {'detail': 'Antes de crear tu web pública tenés que verificar tu correo electrónico. Revisá tu casilla o pedí el reenvío desde tu panel.'},
                    status = status.HTTP_403_FORBIDDEN,
                )
            #El celular es el ancla anti-abuso (único por cuenta): el alta
            #social entra sin él y el frontend lo pide aparte — el claim lo
            #exige igual para que ningún usuario sin ancla farmee tiendas.
            if not profile.phone:
                return Response(
                    {'detail': 'Antes de crear tu web pública cargá tu número de celular en tu perfil.'},
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
        logger.warning('Web bloqueada: slug=%s admin=%s reason=%s', store.slug, request.user.pk, reason or '-')
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
        logger.info('Web desbloqueada: slug=%s admin=%s', store.slug, request.user.pk)
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
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)', throttle_classes = [PublicReadThrottle, StoreVisitThrottle])
    def public(self, request, slug = None):
        store       =   get_object_or_404(
            Store.objects.select_related('user__city', 'user__province', 'customization'),
            slug = slug, is_published = True, is_blocked = False,
        )
        #La web pública se apaga sin suscripción vigente (baja o vencimiento sin renovar)
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        #La página "Servicios" viaja en el mismo payload cuando está
        #habilitada en los site_templates efectivos: una sola query extra
        #y solo en ese caso (service_items sale [] en el resto).
        from StoreApp.domains.services.services import effective_site_templates
        if 'services' in effective_site_templates(store):
            from StoreApp.domains.services.models import StoreService
            store._service_items    =   list(StoreService.objects.filter(store = store, is_active = True))
        record_store_visit(store, request)
        serializer  =   StorePublicSerializer(store)
        response    =   Response(serializer.data, status = status.HTTP_200_OK)
        #Cache corta: la misma visita no repide la ficha al navegar entre
        #Inicio/Catálogo/Producto ni al volver atrás. El conteo de visitas no
        #se ve afectado (la dedup por visitante/día ya corre en cache.add).
        patch_cache_control(response, public = True, max_age = 30)
        return response
    #=========================================
    # STATS (visitas de la web del dueño, beneficio has_stats: Estándar+)
    #=========================================
    @action(detail = False, methods = ['get'], url_path = 'stats')
    def stats(self, request):
        #Perfil + tienda + cadena de suscripción en una sola query: el gating
        #de beneficios los reutiliza en memoria (o el cache cross-request).
        from AdminApp.domains.users.models import UserProfile
        profile     =   UserProfile.objects.select_related('store', 'suscription__plan_suscription').filter(user = request.user).first()
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
    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)/catalog', throttle_classes = [PublicReadThrottle])
    def public_catalog(self, request, slug = None):
        from StoreApp.domains.catalog.models import Product
        from StoreApp.domains.catalog.serializers.serializers import (
            CategorySerializer, BrandSerializer, ProductPublicSerializer, DiscountPublicSerializer,
        )
        from StoreApp.domains.catalog.services.services import running_discounts_of, effective_pricing_of
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
        #La página también cae si 'catalog' quedó fuera de los
        #site_templates efectivos (p.ej. bajó a un plan con menos páginas
        #y el catálogo no entró en el cupo).
        from StoreApp.domains.services.services import effective_site_templates
        if 'catalog' not in effective_site_templates(store):
            raise Http404
        products        =   Product.objects.filter(store = store, is_active = True).select_related('category', 'brand')
        #La valoración solo se anota si el dueño habilitó opiniones y el
        #plan las incluye (has_product_comments, premium): score 0-5 =
        #5 × likes/votos (is_positive binario — el promedio sale del ratio
        #de likes); sin el flag viaja rating_avg/count en None.
        if customization is not None and customization.show_reviews and profile_has_benefit(store.user, 'has_product_comments'):
            from django.db.models import Avg, Count, Q, Case, When, Value, FloatField, ExpressionWrapper
            products    =   products.annotate(
                rating_avg      =   ExpressionWrapper(
                    Value(5.0) * Avg(
                        Case(When(reviews__is_positive = True, then = Value(1.0)), default = Value(0.0), output_field = FloatField()),
                        filter = Q(reviews__is_positive__isnull = False),
                    ),
                    output_field = FloatField(),
                ),
                rating_count    =   Count('reviews__is_positive', filter = Q(reviews__is_positive__isnull = False)),
            )
        #Filtros avanzados del catálogo público:
        #  ?category=1,2 / ?brand=3,4   taxonomías multi-selección (OR entre ids)
        #  ?q=texto                     nombre + descripción + categoría + marca + características
        #  ?features={"Talle":["M"]}    atributos dinámicos (OR dentro, AND entre grupos)
        #  ?offer=1 / ?new=1            solo ofertas efectivas / solo novedades (7 días)
        #  ?min_price / ?max_price      rango sobre el precio efectivo
        #  ?sort=name|recent|price_asc|price_desc
        category_ids    =   _id_list(request.query_params.get('category'))
        brand_ids       =   _id_list(request.query_params.get('brand'))
        search          =   (request.query_params.get('q') or '').strip().casefold()
        min_price       =   _price_bound(request.query_params.get('min_price'))
        max_price       =   _price_bound(request.query_params.get('max_price'))
        feature_filters =   _feature_filters(request.query_params.get('features'))
        only_offer      =   _flag(request.query_params.get('offer'))
        only_new        =   _flag(request.query_params.get('new'))
        sort            =   (request.query_params.get('sort') or '').strip()
        ordering        =   CATALOG_SORTS.get(sort)
        if ordering and sort not in ('price_asc', 'price_desc'):
            products    =   products.order_by(*ordering)
        #El precio efectivo es la menor entre la oferta manual y el mejor
        #descuento vigente (programado por el dueño): filtros de precio y el
        #orden por precio se resuelven sobre ese valor ya calculado — el
        #catálogo queda acotado por max_products del plan, así que evaluar
        #en memoria no escala mal y evita materializar nada en la base.
        #El mismo barrido arma las facetas y los conteos globales (ofertas,
        #novedades, techo de precio) sobre TODOS los productos activos. Las
        #facetas, en cambio, solo viajan con ?category= activa — se
        #recolectan los atributos de los productos de esas categorías (si
        #son varias, se combinan): sin selección el panel no mezcla los
        #atributos de todo el catálogo (chocolates + celulares + pantalones
        #sería un mundo de filtros ajenos entre sí), y no se achican al
        #tocar valores — el panel queda estable mientras se filtra.
        discounts       =   running_discounts_of(store)
        new_cutoff      =   timezone.now() - timedelta(days = CATALOG_NEW_DAYS)
        facets          =   {}
        items           =   []
        offer_count     =   0
        new_count       =   0
        price_max       =   None
        for product in products:
            #El descuento solo firma la oferta cuando realmente gana — si la
            #oferta manual queda más baja, no se le cuelga su nombre/fecha.
            product.effective_offer, product.effective_discount =   effective_pricing_of(product, discounts)
            product.effective_price       =   product.effective_offer if product.effective_offer is not None else product.price
            if product.effective_offer is not None:
                offer_count +=  1
            if product.created_at >= new_cutoff:
                new_count   +=  1
            if price_max is None or product.effective_price > price_max:
                price_max   =   product.effective_price
            if isinstance(product.features, dict) and category_ids and product.category_id in category_ids:
                for fname, fvalue in product.features.items():
                    name    =   str(fname).strip()
                    if not name:
                        continue
                    #El mismo atributo puede viajar con casing distinto entre
                    #productos de categorías distintas ("Color"/"color") y lo
                    #mismo pasa con los valores ("verde"/"Verde"): el match de
                    #?features= ignora mayúsculas (_features_match), así que
                    #las facetas se agrupan con la misma regla — un solo grupo
                    #y un solo valor por clave, con sus conteos sumados.
                    entry   =   facets.setdefault(name.casefold(), {'name': name, 'values': {}})
                    for token in _feature_tokens(fvalue):
                        bucket  =   entry['values'].setdefault(token.casefold(), {'value': token, 'count': 0})
                        bucket['count'] +=  1
            if category_ids and product.category_id not in category_ids:
                continue
            if brand_ids and product.brand_id not in brand_ids:
                continue
            if search and search not in _product_haystack(product):
                continue
            if only_new and product.created_at < new_cutoff:
                continue
            if only_offer and product.effective_offer is None:
                continue
            if min_price is not None and product.effective_price < min_price:
                continue
            if max_price is not None and product.effective_price > max_price:
                continue
            if feature_filters and not _features_match(product.features, feature_filters):
                continue
            items.append(product)
        if sort in ('price_asc', 'price_desc'):
            #Orden estable: el nombre queda de desempate ascendente en ambos
            #sentidos (un reverse sobre la tupla invertiría también el nombre).
            items.sort(key = lambda p: p.name)
            items.sort(key = lambda p: p.effective_price, reverse = (sort == 'price_desc'))
        #Los conteos de cada taxonomía viajan en products_count (solo
        #productos activos, como la lista que se filtra).
        from django.db.models import Count, Q
        categories      =   store.categories.annotate(products_count = Count('products', filter = Q(products__is_active = True)))
        brands          =   store.brands.annotate(products_count = Count('products', filter = Q(products__is_active = True)))
        #Orden de los grupos de facetas: con categoría elegida, los atributos
        #que esa categoría declara en su feature_schema van primero y en ese
        #mismo orden (la plantilla del dueño manda); el resto por frecuencia.
        schema_index    =   {}
        if category_ids:
            for cat in categories:
                if cat.id in category_ids:
                    for raw in (cat.feature_schema or []):
                        schema_index.setdefault(str(raw).strip().casefold(), len(schema_index))
        #El casing que se muestra prefiere el que el dueño declaró en el
        #feature_schema de sus categorías ("Color" y no "color"); cuando
        #ninguna lo declara queda el primero visto en los productos.
        schema_names    =   {}
        for cat in categories:
            for raw in (cat.feature_schema or []):
                declared    =   str(raw).strip()
                if declared:
                    schema_names.setdefault(declared.casefold(), declared)
        #Facetas ordenadas: los atributos más usados primero y dentro de cada
        #uno los valores más frecuentes (desempate "natural": 2 < 10).
        facet_list      =   [
            {
                'name'      :   schema_names.get(key, entry['name']),
                'values'    :   [
                    {'value': bucket['value'], 'count': bucket['count']}
                    for bucket in sorted(entry['values'].values(), key = lambda b: (-b['count'], _natural_key(b['value'])))[:CATALOG_FACET_VALUES]
                ],
            }
            for key, entry in facets.items()
        ]
        facet_list.sort(key = lambda f: (schema_index.get(f['name'].casefold(), len(schema_index)), -sum(v['count'] for v in f['values']), f['name'].casefold()))
        facet_list      =   facet_list[:CATALOG_FACET_GROUPS]
        #Las promos vigentes viajan a nivel catálogo (nombre, %, alcance y
        #vencimiento) para que las plantillas armen su propio banner —
        #ordenadas de mayor a menor descuento.
        promotions      =   sorted(discounts, key = lambda d: d.percent, reverse = True)
        response        =   Response(
            {
                'categories'    :   CategorySerializer(categories, many = True).data,
                'brands'        :   BrandSerializer(brands, many = True).data,
                'promotions'    :   DiscountPublicSerializer(promotions, many = True).data,
                'products'      :   ProductPublicSerializer(items, many = True).data,
                'facets'        :   facet_list,
                'offer_count'   :   offer_count,
                'new_count'     :   new_count,
                'price_max'     :   price_max,
            },
            status = status.HTTP_200_OK,
        )
        #Idem /public/<slug>/: el visitante que pasa de la portada al catálogo
        #o a una ficha no vuelve a pegarle a la API por el mismo listado.
        patch_cache_control(response, public = True, max_age = 30)
        return response
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

    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)/contact/captcha', throttle_classes = [PublicReadThrottle])
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
    # PRODUCT REVIEWS (valoraciones y comentarios de visitantes)
    #=========================================
    def _review_store(self, slug):
        """
        Mismas condiciones que la web pública + al menos una de las dos
        opiniones habilitadas por el dueño. Devuelve (store, product) —
        las reseñas son siempre de un producto concreto del catálogo.
        """
        store       =   get_object_or_404(
            Store.objects.select_related('user__user', 'customization'),
            slug = slug, is_published = True, is_blocked = False,
        )
        if not profile_has_benefit(store.user, 'has_public_link'):
            raise Http404
        customization   =   getattr(store, 'customization', None)
        #Las opiniones (valoraciones y comentarios) son premium: sin el
        #flag la tienda no las recibe aunque los toggles quedaran en True.
        has_reviews     =   profile_has_benefit(store.user, 'has_product_comments')
        can_rate        =   bool(customization and customization.show_reviews and has_reviews)
        can_comment     =   bool(customization and customization.show_comments and has_reviews)
        if not (can_rate or can_comment):
            raise Http404
        return store, can_rate, can_comment

    def _review_product(self, store, product_id):
        from StoreApp.domains.catalog.models import Product
        return get_object_or_404(Product, pk = product_id, store = store, is_active = True)

    @action(detail = False, methods = ['get'], url_path = r'public/(?P<slug>[a-z0-9-]+)/reviews/captcha', throttle_classes = [PublicReadThrottle])
    def review_captcha(self, request, slug = None):
        self._review_store(slug)
        return Response(issue_captcha(slug), status = status.HTTP_200_OK)

    @action(detail = False, methods = ['get', 'post'], url_path = r'public/(?P<slug>[a-z0-9-]+)/products/(?P<product_id>[0-9]+)/reviews', throttle_classes = [StoreReviewThrottle])
    def product_reviews(self, request, slug = None, product_id = None):
        from StoreApp.domains.catalog.models import ProductReview
        from StoreApp.domains.catalog.serializers.serializers import (
            ReviewPublicSerializer, ReviewCreateSerializer,
        )
        from StoreApp.domains.catalog.serializers.config_fields import ReviewLimits
        store, can_rate, can_comment    =   self._review_store(slug)
        product                         =   self._review_product(store, product_id)
        if request.method == 'GET':
            reviews     =   product.reviews.all()[:ReviewLimits['list_max']]
            return Response(ReviewPublicSerializer(reviews, many = True).data, status = status.HTTP_200_OK)
        serializer  =   ReviewCreateSerializer(
            data        =   request.data,
            context     =   {'can_rate': can_rate, 'can_comment': can_comment},
        )
        serializer.is_valid(raise_exception = True)
        data        =   serializer.validated_data
        #Honeypot como en contact: éxito falso sin guardar nada.
        if data.get('website'):
            return Response({'Exito': 'Tu opinión fue publicada.'}, status = status.HTTP_200_OK)
        if not verify_captcha(slug, data['challenge_id'], data['captcha_answer']):
            return Response(
                {'captcha_answer': 'El captcha venció o la respuesta no es correcta. Probá de nuevo.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        ProductReview.objects.create(
            store       =   store,
            product     =   product,
            is_positive =   data.get('is_positive') if can_rate else None,
            text        =   data.get('text') or '',
            name        =   data['name'],
            surname     =   data['surname'],
            email       =   data['email'],
        )
        return Response({'Exito': 'Tu opinión fue publicada. ¡Gracias!'}, status = status.HTTP_201_CREATED)
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
        if not profile_has_benefit(store.user, 'has_product_comments'):
            discard.extend(REVIEW_FIELDS)
        if discard:
            data        =   request.data.copy()
            for field in discard:
                data.pop(field, None)
        #Plantilla según el nivel del plan (Básico: Clásico/Perspectiva;
        #Estándar suma Urbano/Publicidad; Premium, todo): un diseño fuera
        #del nivel se descarta del payload como los campos premium.
        if 'template' in data and data.get('template') not in allowed_templates_of(store.user):
            if data is request.data:
                data        =   request.data.copy()
            data.pop('template')
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
        _apply_order(store.carousel_images.all(), order)
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
        _apply_order(store.gallery_images.all(), order)
        return Response({'Exito': 'El orden de la galería se actualizó'}, status = status.HTTP_200_OK)
