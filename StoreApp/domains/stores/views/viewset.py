import copy
import hashlib
import json
import logging
import re
from datetime import timedelta

from django.core.signing import BadSignature, TimestampSigner
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.cache import patch_cache_control
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from DaventProject.cache_utils import cache_get, cache_set
from DaventProject.throttling import PublicReadThrottle
from StoreApp.domains.stores.models import (
    Store,
    StoreCarouselImage,
    StoreChatbot,
    StoreCustomization,
    StoreGalleryImage,
    StudioVersion,
)
from StoreApp.domains.stores.public_cache import public_cache_stamp
from StoreApp.domains.stores.serializers.serializers import (
    StoreCarouselImageSerializer,
    StoreChatbotSerializer,
    StoreContactSerializer,
    StoreCustomizationSerializer,
    StoreGalleryImageSerializer,
    StorePublicSerializer,
    StoreSerializerList,
)
from StoreApp.domains.stores.serializers.validators import (
    RESERVED_SLUGS,
    validate_slug_available,
    validate_slug_format,
)
from StoreApp.domains.stores.services import (
    allowed_templates_of,
    contact_target,
    delete_carousel_image,
    delete_cover,
    delete_gallery_image,
    delete_logo,
    issue_captcha,
    profile_has_benefit,
    record_store_visit,
    send_contact_message,
    storage_payload,
    upload_carousel_image,
    upload_cover,
    upload_gallery_image,
    upload_logo,
    verify_captcha,
    visit_stats_of,
)
from StoreApp.domains.stores.services.ai_design import (
    AiDesignError,
    design_image_url,
    upload_design_image,
)
from StoreApp.domains.stores.services.ai_design import (
    apply as apply_ai_design,
)
from StoreApp.domains.stores.services.ai_design import (
    generate as generate_ai_design,
)
from StoreApp.domains.stores.services.ai_design import (
    prefill as prefill_ai_design,
)
from StoreApp.domains.stores.services.ai_design import (
    refine as refine_ai_design,
)
from StoreApp.domains.stores.services.ai_design_telemetry import (
    record_event as record_ai_design_event,
)

from .viewset_base import StoreBaseViewSet
from .viewset_config import StoreConfigs

"""

Viewsets del dominio Stores.

"""
#Campos del diseño reservados a has_design_advanced (Plan premium): en un
#PATCH/PUT de customization se descartan del payload en vez de rechazar la
#request, así el resto del formulario (contenido, logo y tema) se guarda
#igual y los valores ya guardados quedan intactos. Las plantillas se
#validan aparte, por nivel de plan (allowed_templates_of del servicio).
logger                  =   logging.getLogger(__name__)
DESIGN_ADVANCED_FIELDS  =   ('name_font', 'name_font_size', 'accent', 'accent_custom', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay', 'cover_focus_x', 'cover_focus_y')
#El mapa de ubicación tiene su propio beneficio (has_location_map: Estándar
#y Premium): se descarta igual que los campos premium, por separado.
LOCATION_FIELDS         =   ('show_location',)
#Las opiniones de producto (valoraciones + comentarios) son premium
#(has_product_comments): sin el flag ambos toggles se descartan del PATCH.
REVIEW_FIELDS           =   ('show_reviews', 'show_comments')
#El tema del Studio exige algún beneficio de diseño (has_design_plus da el
#subconjunto básico radius/density; has_design_advanced, el tema completo).
#El plan Básico (has_customization) conserva el campo pero solo persiste el
#estilo elegido + su juego de colores de fuentes/contenedores. Sin ningún
#beneficio el campo entero se descarta del PATCH como los campos premium y
#lo guardado queda intacto; el filtro fino por sección corre en el
#serializer vía site_theme.clean_site_theme.
SITE_THEME_FIELDS       =   ('site_theme', 'site_theme_draft')
#Link temporal "compartir vista previa": token firmado (TimestampSigner,
#salt propio) que habilita la vista del borrador en la web pública sin
#auth. Vence solo (PREVIEW_SHARE_TTL) — no hay modelo ni revocación:
#se regenera desde customization/share/. El objeto firmado lleva el pk
#de la tienda: un token no sirve para previsualizar otra web.
PREVIEW_SHARE_TTL       =   3 * 24 * 3600   #3 días
PREVIEW_SIGNER_SALT     =   'davent.stores.preview'
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
#TTL del cache server-side de los payloads públicos (web de cliente): solo
#barre entradas huérfanas — la frescura la garantiza el versionado (epoch,
#ver) que bustea al instante en cada save/delete de lo que compone el
#payload (ver public_cache.py). Una tienda viral cuesta ~1 fetch a cache
#por pageview en vez de ~8 queries a la DB.
PUBLIC_CACHE_TTL        =   120
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

#Solo estos params cambian el payload del catálogo público. Cualquier otro
#(?x=<aleatorio>) se ignora en la huella: sin la whitelist cada query string
#arbitraria creaba una entrada nueva del payload completo (cache flooding).
CATALOG_FINGERPRINT_PARAMS = ('category', 'brand', 'q', 'features', 'offer', 'new', 'min_price', 'max_price', 'sort')

def _params_fingerprint(request):
    #Huella estable de la querystring para el cache del catálogo público:
    #se canonizan SOLO los filtros soportados, con el mismo parseo que usa
    #_public_catalog_data (orden de parámetros y de valores no cambia la
    #respuesta; un ?q= enorme se recorta a 80 chars).
    params  =   request.query_params
    def _canon(name):
        raw =   params.get(name)
        if raw is None:
            return ''
        if name in ('category', 'brand'):
            return tuple(sorted(_id_list(raw)))
        if name == 'q':
            return raw.strip().casefold()[:80]
        if name == 'features':
            parsed  =   _feature_filters(raw)
            return tuple(sorted((key.casefold(), tuple(sorted(values))) for key, values in parsed.items()))
        if name in ('offer', 'new'):
            return _flag(raw)
        if name in ('min_price', 'max_price'):
            bound   =   _price_bound(raw)
            return str(bound) if bound is not None else ''
        return raw.strip()
    canonical =   tuple((name, _canon(name)) for name in CATALOG_FINGERPRINT_PARAMS)
    return hashlib.md5(repr(canonical).encode(), usedforsecurity=False).hexdigest()

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
# AI DESIGN THROTTLE (motor de diseño, rate en settings)
#=========================================
class AiDesignThrottle(UserRateThrottle):
    #Por usuario: generar es barato (motor local) pero armar 3 propuestas
    #recorre catálogo y galería — el scope acota el abuso sin molestar al
    #dueño que prueba variantes.
    scope   =   'ai_design'
#=========================================
# AI DESIGN IMAGE THROTTLE (fotos del pedido de imágenes, rate en settings)
#=========================================
class AiDesignImageThrottle(UserRateThrottle):
    #Cada foto se recodifica con Pillow y consume cuota del plan: 60/h deja
    #subir las 2-3 fotos de cada propuesta sin abrir la puerta al storage.
    scope   =   'ai_design_image'
#=========================================
# STORE VIEWSET
#=========================================
class StoreViewSet(StoreBaseViewSet):
    viewset_config  =   StoreConfigs
    #Acciones que atienden visitantes anónimos (web pública, contacto, reseñas).
    PUBLIC_ACTIONS  =   ('public', 'public_catalog', 'contact_captcha', 'contact', 'review_captcha', 'product_reviews')

    def initialize_request(self, request, *args, **kwargs):
        #get_authenticators() corre dentro de super().initialize_request(),
        #antes de que ViewSetMixin resuelva self.action: lo dejamos listo acá
        #para poder desactivar la autenticación en las acciones públicas.
        self.action =   self.action_map.get(request.method.lower())
        return super().initialize_request(request, *args, **kwargs)

    def get_authenticators(self):
        #DRF autentica ANTES de evaluar permisos: con un Bearer vencido (access
        #zombie tras expirar la sesión) el 401 se disparaba igual en endpoints
        #AllowAny y la consola se llenaba de errores en la web pública. Las
        #acciones públicas no necesitan identidad: cero autenticadores.
        if self.action in self.PUBLIC_ACTIONS:
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.action in self.PUBLIC_ACTIONS:
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
        try:
            return super().create(request)
        except IntegrityError:
            #Carrera de dos claims del mismo slug (doble click / 2 pestañas):
            #el pre-check pasó en ambos, la constraint única corta acá. Antes
            #salía un 500; ahora el mismo 400 que el pre-check.
            return Response(
                {'slug': ['Ese link ya está en uso.']},
                status = status.HTTP_400_BAD_REQUEST,
            )
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
        #Modo vista previa (?preview=<token firmado>): la web muestra el
        #BORRADOR del Studio (layout/tema/plantilla) — el swap se hace en
        #la instancia antes de serializar, así filter_site_theme aplica el
        #mismo gating de plan. Va por fuera del cache compartido (el
        #payload difiere del público y es tráfico de una sola persona),
        #no suma visita a las estadísticas y viaja no-store.
        if self._preview_ok(request, store):
            customization       =   getattr(store, 'customization', None)
            if customization is not None:
                customization.layout_config   =   customization.layout_config_draft
                customization.site_theme        =   customization.site_theme_draft
                customization.template          =   customization.template_draft
            data                =   dict(StorePublicSerializer(store).data)
            data['preview']     =   True
            response            =   Response(data, status = status.HTTP_200_OK)
            patch_cache_control(response, private = True, no_store = True)
            return response
        #Cache server-side del payload (PUBLIC_CACHE_TTL): es idéntico para
        #todos los visitantes — una tienda con tráfico viral deja de pegarle
        #a la DB por pageview. Quedan vivos el fetch del store (1 query:
        #unpublish/block cortan al instante) y el conteo de visitas, que va
        #por fuera del cache y siempre corre. La versión (epoch,ver) bustea
        #al instante ante cualquier save/delete de lo que compone el payload.
        epoch, ver  =   public_cache_stamp(store.pk)
        cache_key   =   f'store:public:v1:{store.pk}:{epoch}:{ver}'
        data        =   cache_get(cache_key)
        if data is None:
            #La página "Servicios" viaja en el mismo payload cuando está
            #habilitada en los site_templates efectivos: una sola query extra
            #y solo en ese caso (service_items sale [] en el resto).
            from StoreApp.domains.services.services import effective_site_templates
            if 'services' in effective_site_templates(store):
                from StoreApp.domains.services.models import StoreService
                store._service_items    =   list(StoreService.objects.filter(store = store, is_active = True))
            data    =   dict(StorePublicSerializer(store).data)
            cache_set(cache_key, data, PUBLIC_CACHE_TTL)
        record_store_visit(store, request)
        response    =   Response(data, status = status.HTTP_200_OK)
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
        #Cache server-side idem public(): la key lleva (epoch, versión de la
        #tienda, huella de la query) — cada filtro/búsqueda genera un payload
        #distinto y los kill-switches de arriba quedan vivos en cada request.
        epoch, ver  =   public_cache_stamp(store.pk)
        cache_key   =   f'store:catalog:v1:{store.pk}:{epoch}:{ver}:{_params_fingerprint(request)}'
        data        =   cache_get(cache_key)
        if data is None:
            data    =   self._public_catalog_data(request, store, customization)
            cache_set(cache_key, data, PUBLIC_CACHE_TTL)
        response    =   Response(data, status = status.HTTP_200_OK)
        #Idem /public/<slug>/: el visitante que pasa de la portada al catálogo
        #o a una ficha no vuelve a pegarle a la API por el mismo listado.
        patch_cache_control(response, public = True, max_age = 30)
        return response
    #=========================================
    # PUBLIC CATALOG payload (todo el cómputo pesado; la action lo cachea)
    #=========================================
    def _public_catalog_data(self, request, store, customization):
        from StoreApp.domains.catalog.models import Product
        from StoreApp.domains.catalog.serializers.serializers import (
            BrandSerializer,
            CategorySerializer,
            DiscountPublicSerializer,
            ProductPublicSerializer,
        )
        from StoreApp.domains.catalog.services.services import (
            effective_pricing_of,
            running_discounts_of,
        )
        products        =   Product.objects.filter(store = store, is_active = True).select_related('category', 'brand')
        #La valoración solo se anota si el dueño habilitó opiniones y el
        #plan las incluye (has_product_comments, premium): score 0-5 =
        #5 × likes/votos (is_positive binario — el promedio sale del ratio
        #de likes); sin el flag viaja rating_avg/count en None.
        if customization is not None and customization.show_reviews and profile_has_benefit(store.user, 'has_product_comments'):
            from django.db.models import (
                Avg,
                Case,
                Count,
                ExpressionWrapper,
                FloatField,
                Q,
                Value,
                When,
            )
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
        return {
            'categories'    :   CategorySerializer(categories, many = True).data,
            'brands'        :   BrandSerializer(brands, many = True).data,
            'promotions'    :   DiscountPublicSerializer(promotions, many = True).data,
            'products'      :   ProductPublicSerializer(items, many = True).data,
            'facets'        :   facet_list,
            'offer_count'   :   offer_count,
            'new_count'     :   new_count,
            'price_max'     :   price_max,
        }
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
        from StoreApp.domains.catalog.serializers.config_fields import ReviewLimits
        from StoreApp.domains.catalog.serializers.serializers import (
            ReviewCreateSerializer,
            ReviewPublicSerializer,
        )
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
        if not profile_has_benefit(store.user, 'has_design_plus') and not profile_has_benefit(store.user, 'has_design_advanced') and not profile_has_benefit(store.user, 'has_customization'):
            discard.extend(SITE_THEME_FIELDS)
        if discard:
            data        =   request.data.copy()
            for field in discard:
                data.pop(field, None)
        #Plantilla según el nivel del plan (Básico: Clásico/Perspectiva;
        #Estándar suma Urbano/Publicidad; Premium, todo): un diseño fuera
        #del nivel se descarta del payload como los campos premium. El
        #borrador corre la misma whitelist (template_draft).
        allowed_templates       =   allowed_templates_of(store.user)
        for name in ('template', 'template_draft'):
            if name in data and data.get(name) not in allowed_templates:
                if data is request.data:
                    data        =   request.data.copy()
                data.pop(name)
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
    # AI DESIGN: PROPUESTAS / APLICAR AL BORRADOR (motor propio, sin IA paga)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'ai-design', throttle_classes = [AiDesignThrottle])
    def ai_design(self, request):
        #Entrevista corta + datos reales -> 2-3 propuestas de web completa.
        #Mismos gates que el editor: sin personalización no hay diseño que
        #aplicar, y el motor es un beneficio de plan aparte.
        store       =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        if not profile_has_benefit(store.user, 'has_ai_design'):
            return Response(
                {'detail': 'El diseño automático está disponible en tu plan actual.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return Response(generate_ai_design(store, request.data), status = status.HTTP_200_OK)

    @action(detail = False, methods = ['get'], url_path = 'ai-design/prefill', throttle_classes = [AiDesignThrottle])
    def ai_design_prefill(self, request):
        #Lo que la IA ya sabe del negocio (nombre, ciudad, rubro, conteos):
        #la entrevista arranca con eso a la vista en vez de preguntarlo.
        store       =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        if not profile_has_benefit(store.user, 'has_ai_design'):
            return Response(
                {'detail': 'El diseño automático está disponible en tu plan actual.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        return Response(prefill_ai_design(store), status = status.HTTP_200_OK)

    @action(detail = False, methods = ['post'], url_path = 'ai-design/refine', throttle_classes = [AiDesignThrottle])
    def ai_design_refine(self, request):
        #Ajuste de la propuesta elegida (tipografía/aire/color/portada) sin
        #rehacer la tanda: recibe semilla + id + constraints, devuelve la
        #misma propuesta recalculada. El ajuste queda en la caché de la
        #tanda, así que `apply` publica exactamente lo que se vio.
        store       =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        if not profile_has_benefit(store.user, 'has_ai_design'):
            return Response(
                {'detail': 'El diseño automático está disponible en tu plan actual.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        try:
            data    =   refine_ai_design(store, request.data)
        except AiDesignError as error:
            return Response({'detail': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response(data, status = status.HTTP_200_OK)

    @action(detail = False, methods = ['post'], url_path = 'ai-design/apply', throttle_classes = [AiDesignThrottle])
    def ai_design_apply(self, request):
        #El cliente manda semilla + id: el backend RECALCULA la propuesta con
        #el mismo motor (nunca aplica un layout enviado por el navegador).
        store       =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        if not profile_has_benefit(store.user, 'has_ai_design'):
            return Response(
                {'detail': 'El diseño automático está disponible en tu plan actual.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        def _flag(value):
            return value if isinstance(value, bool) else str(value or '').strip().lower() in ('1', 'true', 'yes', 'on')
        try:
            apply_ai_design(
                store,
                request.data.get('seed'),
                request.data.get('proposal_id'),
                autofill        =   _flag(request.data.get('autofill')),
                #Extras: la elección del dueño (ids aceptados) o, sin lista,
                #los que ya viajan en la propuesta. `skip_extras` rechaza
                #todos y los deja apagados en el borrador.
                extras          =   request.data.get('extras'),
                skip_extras     =   _flag(request.data.get('skip_extras')),
            )
        except AiDesignError as error:
            return Response({'detail': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        customization   =   StoreCustomization.objects.get_or_create(store = store)[0]
        return Response(
            {
                'Exito'         : 'Tu web ya está publicada',
                'published'     : True,
                'customization' :   StoreCustomizationSerializer(customization).data,
                'storage'       :   storage_payload(store, store.user),
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['post'], url_path = 'ai-design/event', throttle_classes = [AiDesignThrottle])
    def ai_design_event(self, request):
        #Telemetría del funnel (5.1): sin gate de plan a propósito — si el
        #dueño perdió el beneficio igual queremos saber dónde abandonó.
        store       =   get_object_or_404(Store, user__user = request.user)
        try:
            record_ai_design_event(store, request.data)
        except ValueError as error:
            return Response({'detail': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True}, status = status.HTTP_200_OK)

    @action(detail = False, methods = ['post'], url_path = 'ai-design/image', throttle_classes = [AiDesignImageThrottle])
    def ai_design_image(self, request):
        #Foto del pedido de imágenes de la propuesta: se guarda como imagen
        #de galería (WebP liviano, sin recorte) y consume la cuota del plan.
        #El `request_id` es informativo para la UI (qué pedido resolvió).
        store       =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        if not profile_has_benefit(store.user, 'has_ai_design'):
            return Response(
                {'detail': 'El diseño automático está disponible en tu plan actual.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        upload      =   request.FILES.get('image')
        if upload is None:
            return Response({'image': 'Tenés que adjuntar una imagen.'}, status = status.HTTP_400_BAD_REQUEST)
        try:
            image   =   upload_design_image(store, upload)
        except ValueError as error:
            return Response({'image': str(error)}, status = status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'Exito'     : 'La foto se sumó a tu galería',
                'image'     : {'id': image.pk, 'url': design_image_url(image)},
                'storage'   : storage_payload(store, store.user),
                'gallery'   : {'count': store.gallery_images.count()},
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # STUDIO: PUBLISH / DISCARD / VERSIONS / RESTORE (borrador vs publicado)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'customization/publish')
    def customization_publish(self, request):
        #El borrador pasa a ser lo publicado y queda el snapshot en el
        #historial (últimas StudioVersion.MAX_PER_STORE por tienda).
        store               =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        note                =   str(request.data.get('note') or '').strip()[:140]
        customization.layout_config =   copy.deepcopy(customization.layout_config_draft) or {}
        customization.site_theme    =   copy.deepcopy(customization.site_theme_draft) or {}
        #La plantilla del borrador publica solo si sigue en la whitelist
        #del plan (una baja de plan no la re-habilita); si no aplica, el
        #borrador queda resuelto al publicado — has_unpublished limpio.
        if customization.template_draft in allowed_templates_of(store.user):
            customization.template    =   customization.template_draft
        customization.template_draft    =   customization.template
        customization.save(update_fields = ['layout_config', 'site_theme', 'template', 'template_draft', 'updated_at'])
        StudioVersion.objects.create(
            store       =   store,
            snapshot    =   {
                'template'      :   customization.template,
                'layout_config' :   customization.layout_config,
                'site_theme'    :   customization.site_theme,
            },
            note        =   note,
        )
        stale               =   list(StudioVersion.objects.filter(store = store).values_list('pk', flat = True)[StudioVersion.MAX_PER_STORE:])
        if stale:
            StudioVersion.objects.filter(pk__in = stale).delete()
        return Response(
            {
                'Exito'         : 'Publicaste los cambios de tu web',
                'customization' :   StoreCustomizationSerializer(customization).data,
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['post'], url_path = 'customization/discard')
    def customization_discard(self, request):
        #Vuelve el borrador a lo publicado: lo descartado no llega a la web
        #ni queda en el draft del Studio.
        store               =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        customization.layout_config_draft   =   copy.deepcopy(customization.layout_config) or {}
        customization.site_theme_draft      =   copy.deepcopy(customization.site_theme) or {}
        customization.template_draft        =   customization.template
        customization.save(update_fields = ['layout_config_draft', 'site_theme_draft', 'template_draft', 'updated_at'])
        return Response(
            {
                'Exito'         : 'Descartaste los cambios sin publicar',
                'customization' :   StoreCustomizationSerializer(customization).data,
            },
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['get'], url_path = 'customization/versions')
    def customization_versions(self, request):
        #Historial del Studio: últimas MAX_PER_STORE publicaciones (read —
        #mismo scope que GET customization, solo la tienda del dueño).
        store               =   get_object_or_404(Store, user__user = request.user)
        versions            =   StudioVersion.objects.filter(store = store)[:StudioVersion.MAX_PER_STORE]
        return Response(
            [
                {'id': version.pk, 'note': version.note, 'created_at': version.created_at, 'snapshot': version.snapshot}
                for version in versions
            ],
            status = status.HTTP_200_OK,
        )

    @action(detail = False, methods = ['post'], url_path = r'customization/restore/(?P<version_id>\d+)')
    def customization_restore(self, request, version_id = None):
        #Restaura un snapshot: pasa a ser lo publicado y el borrador (la
        #versión ya era una publicación; lo que no trae el snapshot queda).
        store               =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        customization, _    =   StoreCustomization.objects.get_or_create(store = store)
        #El scope por tienda aísla el historial: una versión ajena da 404.
        version             =   get_object_or_404(StudioVersion, pk = version_id, store = store)
        snapshot            =   version.snapshot if isinstance(version.snapshot, dict) else {}
        fields              =   []
        layout              =   snapshot.get('layout_config')
        if isinstance(layout, dict):
            customization.layout_config         =   copy.deepcopy(layout)
            customization.layout_config_draft   =   copy.deepcopy(layout)
            fields                             +=   ['layout_config', 'layout_config_draft']
        theme               =   snapshot.get('site_theme')
        if isinstance(theme, dict):
            customization.site_theme            =   copy.deepcopy(theme)
            customization.site_theme_draft      =   copy.deepcopy(theme)
            fields                             +=   ['site_theme', 'site_theme_draft']
        template            =   snapshot.get('template')
        #La plantilla se restaura solo si sigue en la whitelist del plan
        #(una baja de plan no re-habilita una plantilla premium). El
        #borrador siempre queda alineado al publicado final.
        if template in allowed_templates_of(store.user):
            customization.template              =   template
            fields.append('template')
        customization.template_draft            =   customization.template
        fields.append('template_draft')
        if fields:
            customization.save(update_fields = fields + ['updated_at'])
        return Response(
            {
                'Exito'         : 'Restauraste esa versión de tu web',
                'customization' :   StoreCustomizationSerializer(customization).data,
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # SHARE PREVIEW (link temporal al borrador del Studio, sin auth)
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'customization/share')
    def customization_share(self, request):
        #Emite el token firmado para /<slug>?preview=<token>: la web
        #pública muestra el borrador del Studio (layout/tema/plantilla)
        #a quien tenga el link — pensado para mostrar el diseño a un
        #cliente antes de publicarlo. Vence en PREVIEW_SHARE_TTL.
        store               =   get_object_or_404(Store, user__user = request.user)
        if not profile_has_benefit(store.user, 'has_customization'):
            return Response(
                {'detail': 'La personalización de tu web requiere una suscripción activa.'},
                status = status.HTTP_403_FORBIDDEN,
            )
        token               =   TimestampSigner(salt = PREVIEW_SIGNER_SALT).sign_object({'s': store.pk})
        return Response(
            {
                'token'         :   token,
                'path'          :   f'/{store.slug}?preview={token}',
                'expires_at'    :   (timezone.now() + timedelta(seconds = PREVIEW_SHARE_TTL)).isoformat(),
                'ttl'           :   PREVIEW_SHARE_TTL,
            },
            status = status.HTTP_200_OK,
        )

    def _preview_ok(self, request, store):
        #?preview=<token> válido solo si la firma es íntegra, no venció y
        #apunta a ESTA tienda. Token inválido/ajeno = visitante normal
        #(ve lo publicado — el link malo no rompe la web ni filtra nada).
        token               =   request.query_params.get('preview')
        if not token:
            return False
        try:
            data            =   TimestampSigner(salt = PREVIEW_SIGNER_SALT).unsign_object(token, max_age = PREVIEW_SHARE_TTL)
        except (BadSignature, ValueError):
            return False
        return isinstance(data, dict) and data.get('s') == store.pk
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
