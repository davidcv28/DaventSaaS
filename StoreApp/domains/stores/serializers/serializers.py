import re
from urllib.parse import parse_qs, quote, urlparse

from django.db import IntegrityError
from rest_framework import serializers

from StoreApp.domains.services.services import (
    DEFAULT_SITE_TEMPLATES,
    effective_site_templates,
    normalize_site_templates,
    site_mode_of,
)
from StoreApp.domains.services.services import (
    validate_site_templates as validate_site_templates_plan,
)
from StoreApp.domains.stores.layout_blocks import clean_layout_config
from StoreApp.domains.stores.models import (
    Store,
    StoreCarouselImage,
    StoreChatbot,
    StoreCustomization,
    StoreGalleryImage,
)
from StoreApp.domains.stores.services import (
    allowed_templates_of,
    plan_benefits_of,
    profile_has_benefit,
    storage_payload,
)
from StoreApp.domains.stores.services.storage import object_url
from StoreApp.domains.stores.site_theme import (
    clean_site_theme,
    filter_site_theme,
    merge_theme,
)

from .config_fields import CustomizationFields, StoresFields
from .mixins import StoreCreateMixin, StoreMixinValidator
from .validators import (
    validate_facebook,
    validate_instagram,
    validate_tiktok,
    validate_whatsapp,
)

"""

Serializers del dominio Stores.

"""
#=========================================
# STORE SERIALIZER (claim / cambio de link)
#=========================================
class StoreSerializer(StoreMixinValidator, StoreCreateMixin, serializers.ModelSerializer):
    id                          =   serializers.ReadOnlyField()
    user                        =   serializers.HiddenField(**StoresFields['user'])
    slug                        =   serializers.CharField(**StoresFields['slug'])
    is_published                =   serializers.BooleanField(**StoresFields['is_published'])
    class Meta:
        model                   =   Store
        fields                  =   ['id', 'user', 'slug', 'is_published']
    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            #El unique de slug/user le gana al pre-check en claims concurrentes.
            raise serializers.ValidationError({'slug': 'Ese link ya está en uso. Elegí otro.'})
#=========================================
# STORE CAROUSEL IMAGE SERIALIZER (banners de la web pública)
#=========================================
class StoreCarouselImageSerializer(serializers.ModelSerializer):
    url                         =   serializers.SerializerMethodField()
    size                        =   serializers.IntegerField(source = 'image_size', read_only = True)
    class Meta:
        model                   =   StoreCarouselImage
        fields                  =   ['id', 'url', 'position', 'size']
    def get_url(self, image):
        return object_url(image.image_key)
#=========================================
# STORE GALLERY IMAGE SERIALIZER (sección Galería de la web pública)
#=========================================
class StoreGalleryImageSerializer(serializers.ModelSerializer):
    url                         =   serializers.SerializerMethodField()
    size                        =   serializers.IntegerField(source = 'image_size', read_only = True)
    class Meta:
        model                   =   StoreGalleryImage
        fields                  =   ['id', 'url', 'position', 'size']
    def get_url(self, image):
        return object_url(image.image_key)
#=========================================
# STORE CHATBOT SERIALIZER (asistente de la web pública)
#=========================================
class StoreChatbotSerializer(serializers.ModelSerializer):
    """
    Config del chatbot (beneficio 'has_chatbot': solo Premium).
    `qa` llega como lista de {'q', 'a'}: se recorta a QA_MAX_ITEMS y
    se descartan pares sin pregunta o sin respuesta.
    """
    class Meta:
        model                   =   StoreChatbot
        fields                  =   ['is_enabled', 'greeting', 'qa']
    def validate_greeting(self, value):
        return (value or '').strip()
    def validate_qa(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Debe ser una lista de preguntas y respuestas.')
        clean                   =   []
        for item in value[:StoreChatbot.QA_MAX_ITEMS]:
            if not isinstance(item, dict):
                continue
            q                   =   str(item.get('q') or '').strip()[:StoreChatbot.QA_MAX_QUESTION]
            a                   =   str(item.get('a') or '').strip()[:StoreChatbot.QA_MAX_ANSWER]
            if q and a:
                clean.append({'q': q, 'a': a})
        return clean
#=========================================
# STORE CUSTOMIZATION SERIALIZER (diseño de la web pública)
#=========================================
class StoreCustomizationSerializer(serializers.ModelSerializer):
    display_name                =   serializers.CharField(**CustomizationFields['display_name'])
    accent_custom               =   serializers.CharField(**CustomizationFields['accent_custom'])
    cover_overlay               =   serializers.IntegerField(**CustomizationFields['cover_overlay'])
    cover_focus_x               =   serializers.IntegerField(**CustomizationFields['cover_focus_x'])
    cover_focus_y               =   serializers.IntegerField(**CustomizationFields['cover_focus_y'])
    headline                    =   serializers.CharField(**CustomizationFields['headline'])
    description                 =   serializers.CharField(**CustomizationFields['description'])
    about_title                 =   serializers.CharField(**CustomizationFields['about_title'])
    about_text                  =   serializers.CharField(**CustomizationFields['about_text'])
    about_years                 =   serializers.IntegerField(**CustomizationFields['about_years'])
    about_mission               =   serializers.CharField(**CustomizationFields['about_mission'])
    about_specialties           =   serializers.CharField(**CustomizationFields['about_specialties'])
    contact_email               =   serializers.EmailField(**CustomizationFields['contact_email'])
    services                    =   serializers.JSONField(**CustomizationFields['services'])
    services_title              =   serializers.CharField(**CustomizationFields['services_title'])
    stats                       =   serializers.JSONField(**CustomizationFields['stats'])
    testimonials                =   serializers.JSONField(**CustomizationFields['testimonials'])
    testimonials_title          =   serializers.CharField(**CustomizationFields['testimonials_title'])
    faqs                        =   serializers.JSONField(**CustomizationFields['faqs'])
    faqs_title                  =   serializers.CharField(**CustomizationFields['faqs_title'])
    hours                       =   serializers.JSONField(**CustomizationFields['hours'])
    cta_title                   =   serializers.CharField(**CustomizationFields['cta_title'])
    cta_text                    =   serializers.CharField(**CustomizationFields['cta_text'])
    cta_label                   =   serializers.CharField(**CustomizationFields['cta_label'])
    section_order               =   serializers.JSONField(**CustomizationFields['section_order'])
    layout_config               =   serializers.JSONField(**CustomizationFields['layout_config'])
    layout_config_draft         =   serializers.JSONField(**CustomizationFields['layout_config_draft'])
    site_theme                  =   serializers.JSONField(**CustomizationFields['site_theme'])
    site_theme_draft            =   serializers.JSONField(**CustomizationFields['site_theme_draft'])
    has_unpublished             =   serializers.SerializerMethodField()
    announcements               =   serializers.JSONField(**CustomizationFields['announcements'])
    video_url                   =   serializers.CharField(**CustomizationFields['video_url'])
    video_title                 =   serializers.CharField(**CustomizationFields['video_title'])
    videos                      =   serializers.JSONField(**CustomizationFields['videos'])
    live_stream_url             =   serializers.CharField(**CustomizationFields['live_stream_url'])
    catalog_note                =   serializers.CharField(**CustomizationFields['catalog_note'])
    footer_text                 =   serializers.CharField(**CustomizationFields['footer_text'])
    site_templates              =   serializers.JSONField(**CustomizationFields['site_templates'])
    benefits                    =   serializers.JSONField(**CustomizationFields['benefits'])
    timeline                    =   serializers.JSONField(**CustomizationFields['timeline'])
    team                        =   serializers.JSONField(**CustomizationFields['team'])
    plans                       =   serializers.JSONField(**CustomizationFields['plans'])
    plans_title                 =   serializers.CharField(**CustomizationFields['plans_title'])
    service_steps               =   serializers.JSONField(**CustomizationFields['service_steps'])
    service_days                =   serializers.JSONField(**CustomizationFields['service_days'])
    service_slots               =   serializers.JSONField(**CustomizationFields['service_slots'])
    service_price_note          =   serializers.CharField(**CustomizationFields['service_price_note'])
    service_pay_note            =   serializers.CharField(**CustomizationFields['service_pay_note'])
    whatsapp                    =   serializers.CharField(**CustomizationFields['whatsapp'])
    instagram                   =   serializers.CharField(**CustomizationFields['instagram'])
    tiktok                      =   serializers.CharField(**CustomizationFields['tiktok'])
    facebook                    =   serializers.CharField(**CustomizationFields['facebook'])
    #El diseño también puede ser el slug de un DesignPattern del catálogo
    #(brigada…): TEMPLATE_CHOICES solo cubre las plantillas Vue, así que el
    #ChoiceField del modelo rechazaba el id y el PATCH lo perdía.
    template                    =   serializers.CharField(max_length = 12)
    template_draft              =   serializers.CharField(max_length = 12, required = False)
    logo                        =   serializers.SerializerMethodField()
    cover                       =   serializers.SerializerMethodField()
    carousel                    =   serializers.SerializerMethodField()
    gallery                     =   serializers.SerializerMethodField()
    decor                       =   serializers.SerializerMethodField()
    class Meta:
        model                   =   StoreCustomization
        fields                  =   [
            'display_name', 'name_font', 'name_font_size', 'headline', 'description', 'theme', 'theme_toggle', 'icon_style', 'accent', 'template', 'template_draft',
            'accent_custom', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay', 'cover_focus_x', 'cover_focus_y',
            'about_title', 'about_text', 'about_years', 'about_mission', 'about_specialties',
            'services', 'services_title', 'show_services', 'stats', 'show_stats',
            'testimonials', 'testimonials_title', 'show_testimonials',
            'faqs', 'faqs_title', 'show_faq', 'hours', 'show_hours',
            'cta_title', 'cta_text', 'cta_label', 'show_cta', 'section_order', 'layout_config',
            'layout_config_draft', 'site_theme', 'site_theme_draft', 'has_unpublished',
            'announcements', 'show_announcements', 'video_url', 'video_title', 'show_video',
            'videos', 'live_stream_url',
            'catalog_note', 'footer_text',
            'benefits', 'show_benefits', 'timeline', 'show_timeline', 'team', 'show_team',
            'plans', 'plans_title', 'show_plans',
            'show_offers', 'show_brands', 'show_countdown',
            'show_about', 'contact_email', 'show_contact',
            'whatsapp', 'instagram', 'tiktok', 'facebook', 'show_location', 'show_gallery', 'show_catalog',
            'ecommerce_enabled',
            'site_templates', 'service_steps', 'service_days', 'service_slots', 'service_ask_address',
            'service_price_note', 'service_pay_note',
            'show_highlights', 'show_reviews', 'show_comments',
            'logo', 'cover', 'logo_size', 'cover_size', 'carousel', 'gallery', 'decor', 'updated_at',
        ]
        read_only_fields        =   ['updated_at', 'logo_size', 'cover_size']
    def validate_icon_style(self, value):
        #Set de iconos del menú: slug del catálogo (vacío = hereda el diseño).
        from StoreApp.domains.design.models import DesignIconStyle
        slug                    =   str(value or '').strip().lower()
        if not slug:
            return ''
        if not DesignIconStyle.objects.filter(slug = slug, is_active = True).exists():
            raise serializers.ValidationError('Ese estilo de iconos no existe.')
        return slug
    @staticmethod
    def _template_id(value):
        #Id de plantilla Vue (TEMPLATE_CHOICES) o slug de un DesignPattern
        #activo del catálogo (la web resuelve ambos por slug).
        slug                    =   str(value or '').strip().lower()
        known                   =   {key for key, _ in StoreCustomization.TEMPLATE_CHOICES}
        if slug in known:
            return slug
        from StoreApp.domains.design.models import DesignPattern
        if DesignPattern.objects.filter(slug = slug, is_active = True).exists():
            return slug
        raise serializers.ValidationError('Ese diseño no existe.')
    def validate_template(self, value):
        return self._template_id(value)
    def validate_template_draft(self, value):
        return self._template_id(value)
    def get_logo(self, customization):
        return object_url(customization.logo_key)
    def get_cover(self, customization):
        return object_url(customization.cover_key)
    def get_carousel(self, customization):
        images                  =   customization.store.carousel_images.all()
        return StoreCarouselImageSerializer(images, many = True).data
    def get_gallery(self, customization):
        #Filtro en Python para reutilizar el prefetch del queryset del listado
        #(.filter() clonaría el queryset y pegaría un query extra por tienda).
        images                  =   [img for img in customization.store.gallery_images.all() if img.kind == StoreGalleryImage.KIND_GALLERY]
        return StoreGalleryImageSerializer(images, many = True).data
    def get_decor(self, customization):
        images                  =   [img for img in customization.store.gallery_images.all() if img.kind == StoreGalleryImage.KIND_DECOR]
        return StoreGalleryImageSerializer(images, many = True).data
    @staticmethod
    def _rows(value, max_items, message):
        #Base común de las listas de marketing: se trunca al tope y se
        #descarta lo que no sea dict (mismo criterio que validate_qa).
        if not isinstance(value, list):
            raise serializers.ValidationError(message)
        return [item for item in value[:max_items] if isinstance(item, dict)]

    def validate_services(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.SERVICES_MAX, 'Debe ser una lista de servicios.'):
            icon                =   str(item.get('icon') or '').strip().lower()
            title               =   str(item.get('title') or '').strip()[:StoreCustomization.SERVICE_TITLE_MAX]
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.SERVICE_TEXT_MAX]
            if title and text:
                clean.append({'icon': icon if icon in StoreCustomization.SERVICE_ICONS else 'package', 'title': title, 'text': text})
        return clean

    def validate_stats(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.STATS_MAX, 'Debe ser una lista de números.'):
            number              =   str(item.get('value') or '').strip()[:StoreCustomization.STAT_VALUE_MAX]
            label               =   str(item.get('label') or '').strip()[:StoreCustomization.STAT_LABEL_MAX]
            if number and label:
                clean.append({'value': number, 'label': label})
        return clean

    def validate_testimonials(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.TESTIMONIALS_MAX, 'Debe ser una lista de testimonios.'):
            name                =   str(item.get('name') or '').strip()[:StoreCustomization.TESTIMONIAL_NAME_MAX]
            detail              =   str(item.get('detail') or '').strip()[:StoreCustomization.TESTIMONIAL_DETAIL_MAX]
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.TESTIMONIAL_TEXT_MAX]
            if name and text:
                clean.append({'name': name, 'detail': detail, 'text': text})
        return clean

    def validate_faqs(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.FAQS_MAX, 'Debe ser una lista de preguntas y respuestas.'):
            q                   =   str(item.get('q') or '').strip()[:StoreCustomization.FAQ_Q_MAX]
            a                   =   str(item.get('a') or '').strip()[:StoreCustomization.FAQ_A_MAX]
            if q and a:
                clean.append({'q': q, 'a': a})
        return clean

    def validate_hours(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.HOURS_MAX, 'Debe ser una lista de horarios.'):
            label               =   str(item.get('label') or '').strip()[:StoreCustomization.HOURS_LABEL_MAX]
            time                =   str(item.get('value') or '').strip()[:StoreCustomization.HOURS_VALUE_MAX]
            if label and time:
                clean.append({'label': label, 'value': time})
        return clean

    def validate_site_templates(self, value):
        #Páginas de la web: el servicio fuerza la whitelist, el cupo
        #max_site_templates y el flag has_services_site del plan vigente.
        store               =   getattr(self.instance, 'store', None) if self.instance is not None else None
        return validate_site_templates_plan(getattr(store, 'user', None), value)

    def validate_service_steps(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.SERVICE_STEPS_MAX, 'Debe ser una lista de pasos.'):
            icon                =   str(item.get('icon') or '').strip().lower()
            title               =   str(item.get('title') or '').strip()[:StoreCustomization.SERVICE_STEP_TITLE_MAX]
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.SERVICE_STEP_TEXT_MAX]
            if title and text:
                clean.append({'icon': icon if icon in StoreCustomization.SERVICE_ICONS else 'check', 'title': title, 'text': text})
        return clean

    @staticmethod
    def _labels(value, max_items, max_len, message):
        #Listas de etiquetas cortas (días/franjas del pedido): se recortan,
        #se descartan vacías y repetidas ignorando mayúsculas.
        if not isinstance(value, list):
            raise serializers.ValidationError(message)
        seen, clean             =   set(), []
        for raw in value:
            text                =   str(raw or '').strip()[:max_len]
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            clean.append(text)
            if len(clean) >= max_items:
                break
        return clean

    def validate_benefits(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.BENEFITS_MAX, 'Debe ser una lista de beneficios.'):
            icon                =   str(item.get('icon') or '').strip().lower()
            title               =   str(item.get('title') or '').strip()[:StoreCustomization.BENEFIT_TITLE_MAX]
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.BENEFIT_TEXT_MAX]
            if title:
                clean.append({'icon': icon if icon in StoreCustomization.SERVICE_ICONS else 'shield-check', 'title': title, 'text': text})
        return clean

    def validate_timeline(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.TIMELINE_MAX, 'Debe ser una lista de hitos.'):
            label               =   str(item.get('label') or '').strip()[:StoreCustomization.TIMELINE_LABEL_MAX]
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.TIMELINE_TEXT_MAX]
            if label and text:
                clean.append({'label': label, 'text': text})
        return clean

    def validate_team(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.TEAM_MAX, 'Debe ser una lista de integrantes.'):
            name                =   str(item.get('name') or '').strip()[:StoreCustomization.TEAM_NAME_MAX]
            role                =   str(item.get('role') or '').strip()[:StoreCustomization.TEAM_ROLE_MAX]
            if name:
                clean.append({'name': name, 'role': role})
        return clean

    def validate_plans(self, value):
        #Planes publicitarios ({name, price, note?, items?[]}): el precio es
        #texto libre (nunca se cobra por la plataforma) y sin precio la fila
        #no informa nada — se descarta igual que en _clean_price_list.
        clean                   =   []
        for item in self._rows(value, StoreCustomization.PLANS_MAX, 'Debe ser una lista de planes.'):
            name                =   str(item.get('name') or '').strip()[:StoreCustomization.PLAN_NAME_MAX]
            price               =   str(item.get('price') or '').strip()[:StoreCustomization.PLAN_PRICE_MAX]
            if not (name and price):
                continue
            plan                =   {'name': name, 'price': price}
            note                =   str(item.get('note') or '').strip()[:StoreCustomization.PLAN_NOTE_MAX]
            if note:
                plan['note']    =   note
            features            =   []
            for feature in (item.get('items') or [])[:StoreCustomization.PLAN_FEATURES_MAX] if isinstance(item.get('items'), list) else []:
                text            =   str(feature or '').strip()[:StoreCustomization.PLAN_FEATURE_MAX]
                if text:
                    features.append(text)
            if features:
                plan['items']   =   features
            clean.append(plan)
        return clean

    def validate_service_days(self, value):
        return self._labels(value, StoreCustomization.SERVICE_DAYS_MAX, StoreCustomization.SERVICE_DAY_MAX, 'Debe ser una lista de días.')

    def validate_service_slots(self, value):
        return self._labels(value, StoreCustomization.SERVICE_SLOTS_MAX, StoreCustomization.SERVICE_SLOT_MAX, 'Debe ser una lista de franjas.')

    def validate_section_order(self, value):
        #Campo legado: el orden de las secciones ya no es editable (la web
        #aplica siempre SECTION_ORDER); se sigue aceptando el payload para
        #no romper clientes viejos. Solo claves del catálogo, sin repetidas;
        #las que no vengan conservan su orden base al final.
        if not isinstance(value, list):
            raise serializers.ValidationError('Debe ser una lista de secciones.')
        seen, order             =   set(), []
        for raw in value:
            key                 =   str(raw or '').strip()
            if key in StoreCustomization.SECTION_ORDER and key not in seen:
                seen.add(key)
                order.append(key)
        return order + [k for k in StoreCustomization.SECTION_ORDER if k not in seen]

    def validate_layout_config(self, value):
        #Editor de bloques (Diseño web → Bloques): el catálogo cerrado
        #TEMPLATE_BLOCKS decide ids/variantes/props admitidos; lo
        #desconocido se descarta y los bloques premium se quitan sin
        #has_design_advanced. Una config vacía/irreconocible queda en {}
        #y la web cae al layout por defecto de la plantilla.
        store                   =   getattr(self.instance, 'store', None) if self.instance is not None else None
        profile                 =   getattr(store, 'user', None)
        has_advanced            =   profile_has_benefit(profile, 'has_design_advanced') if profile is not None else False
        has_ai                  =   profile_has_benefit(profile, 'has_ai_design') if profile is not None else False
        return clean_layout_config(value, has_advanced, has_ai)

    def validate_layout_config_draft(self, value):
        #El borrador del editor de bloques corre la misma whitelist que el
        #publicado: solo cambia la columna destino (la web no lo lee).
        return self.validate_layout_config(value)

    def get_has_unpublished(self, customization):
        #El borrador difiere del publicado = hay cambios del Studio sin publicar.
        return (
            (customization.layout_config_draft or {}) != (customization.layout_config or {})
            or (customization.site_theme_draft or {}) != (customization.site_theme or {})
            or customization.template_draft != customization.template
        )

    def _clean_theme(self, value, field):
        #Tema visual del Studio: clean_site_theme aplica la whitelist del
        #contrato (secciones/claves/enums cerrados, hex, rangos, tamaño y
        #fondos solo con imágenes propias) y descarta en silencio lo que el
        #plan no cubre (como `accent`). El resultado se mergea sobre la
        #columna destino para que los valores premium guardados sobrevivan
        #una baja de plan y los PATCH parciales no pisen secciones ajenas.
        store                   =   getattr(self.instance, 'store', None) if self.instance is not None else None
        profile                 =   getattr(store, 'user', None)
        has_advanced            =   profile_has_benefit(profile, 'has_design_advanced') if profile is not None else False
        has_plus                =   has_advanced or (profile_has_benefit(profile, 'has_design_plus') if profile is not None else False)
        has_style               =   has_plus or (profile_has_benefit(profile, 'has_customization') if profile is not None else False)
        #`_reset: true` = reemplazo total (cambio de diseño): sin merge con
        #lo guardado — las claves/secciones ausentes no sobreviven. El flag
        #no es parte del contrato: se descarta antes de clean_site_theme.
        reset                   =   isinstance(value, dict) and value.get('_reset') is True
        payload                 =   {k: v for k, v in value.items() if k != '_reset'} if reset else value
        cleaned                 =   clean_site_theme(payload, has_plus = has_plus, has_advanced = has_advanced, has_style = has_style, store = store)
        if reset:
            return cleaned
        return merge_theme(getattr(self.instance, field, None), cleaned)

    def validate_site_theme(self, value):
        #Publica de una: además de guardar el publicado, validate() copia el
        #resultado al borrador (salvo que venga site_theme_draft explícito).
        return self._clean_theme(value, 'site_theme')

    def validate_site_theme_draft(self, value):
        return self._clean_theme(value, 'site_theme_draft')

    def validate_announcements(self, value):
        clean                   =   []
        for item in self._rows(value, StoreCustomization.ANNOUNCEMENTS_MAX, 'Debe ser una lista de anuncios.'):
            icon                =   str(item.get('icon') or '').strip().lower()
            text                =   str(item.get('text') or '').strip()[:StoreCustomization.ANNOUNCEMENT_TEXT_MAX]
            if text:
                clean.append({'icon': icon if icon in StoreCustomization.SERVICE_ICONS else 'megaphone', 'text': text})
        return clean

    #Videos de la portada: embeds de YouTube, Vimeo, TikTok, Instagram y
    #Facebook. El link que pega el dueño se normaliza a la URL de embed
    #oficial de cada red — el iframe público jamás apunta a un host ajeno.
    _YT_HOSTS                   =   {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}
    _VIMEO_HOSTS                =   {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}
    _TIKTOK_HOSTS               =   {'tiktok.com', 'www.tiktok.com', 'm.tiktok.com'}
    _IG_HOSTS                   =   {'instagram.com', 'www.instagram.com'}
    _FB_HOSTS                   =   {'facebook.com', 'www.facebook.com', 'm.facebook.com'}
    _TWITCH_HOSTS               =   {'twitch.tv', 'www.twitch.tv', 'm.twitch.tv'}
    _YT_ID                      =   re.compile(r'^[A-Za-z0-9_-]{6,20}$')
    _IG_CODE                    =   re.compile(r'^[A-Za-z0-9_-]{5,30}$')
    _TIKTOK_ID                  =   re.compile(r'^\d{8,25}$')
    _TWITCH_CHAN                =   re.compile(r'^[A-Za-z0-9_]{3,25}$')
    @staticmethod
    def _parsed_video_url(value):
        parsed                  =   urlparse(value if '://' in value else f'https://{value}')
        host                    =   (parsed.hostname or '').lower()
        parts                   =   [p for p in parsed.path.split('/') if p]
        return parsed, host, parts
    def _youtube_embed(self, host, parts, parsed):
        if host == 'youtu.be':
            video_id            =   parts[0] if parts else None
        elif parts and parts[0] in ('embed', 'shorts', 'live') and len(parts) > 1:
            video_id            =   parts[1]
        elif parts and parts[0] == 'watch':
            video_id            =   (parse_qs(parsed.query).get('v') or [None])[0]
        else:
            video_id            =   None
        if not (video_id and self._YT_ID.match(video_id)):
            raise serializers.ValidationError('Pegá el link completo del video de YouTube.')
        return f'https://www.youtube-nocookie.com/embed/{video_id}'
    def _facebook_embed(self, parsed, parts):
        #Post canónico -> embed oficial plugins/video.php?href=…
        canonical                =   None
        if 'watch' in parts:
            vid                   =   (parse_qs(parsed.query).get('v') or [None])[0]
            if vid and vid.isdigit():
                canonical         =   f'https://www.facebook.com/watch/?v={vid}'
        elif parts and parts[0] == 'reel' and len(parts) > 1:
            canonical             =   f'https://www.facebook.com/reel/{parts[1]}'
        elif 'videos' in parts:
            i                     =   parts.index('videos')
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                canonical         =   'https://www.facebook.com/' + '/'.join(parts[:i + 2])
        if not canonical:
            raise serializers.ValidationError('Pegá el link completo del video de Facebook (…/videos/…, /reel/… o /watch/?v=…).')
        return f'https://www.facebook.com/plugins/video.php?href={quote(canonical, safe="")}&show_text=false'
    def _video_embed(self, value):
        """Normaliza un link de video al embed oficial de su red."""
        value                   =   (value or '').strip()
        if not value:
            return ''
        parsed, host, parts     =   self._parsed_video_url(value)
        #URLs ya normalizadas (se reenvían al editar la lista): se aceptan
        #tal cual si apuntan al embed oficial del host permitido.
        if host in ('youtube-nocookie.com', 'www.youtube-nocookie.com') and len(parts) >= 2 and parts[0] == 'embed' and self._YT_ID.match(parts[1]):
            return f'https://www.youtube-nocookie.com/embed/{parts[1]}'
        if host in self._YT_HOSTS:
            return self._youtube_embed(host, parts, parsed)
        if host in self._VIMEO_HOSTS:
            video_id            =   parts[-1] if parts else None
            if video_id and video_id.isdigit():
                return f'https://player.vimeo.com/video/{video_id}'
            raise serializers.ValidationError('Pegá el link completo del video de Vimeo.')
        if host in self._TIKTOK_HOSTS:
            #/@usuario/video/7312345678901234567 -> embed oficial v2
            video_id            =   parts[2] if len(parts) >= 3 and parts[1] == 'video' else None
            if video_id is None and len(parts) >= 3 and parts[0] == 'embed' and parts[1] == 'v2':
                video_id        =   parts[2]
            if video_id and self._TIKTOK_ID.match(video_id):
                return f'https://www.tiktok.com/embed/v2/{video_id}'
            raise serializers.ValidationError('Pegá el link completo del video de TikTok (…/@usuario/video/…).')
        if host in self._IG_HOSTS:
            #/p/, /reel/ o /tv/ + shortcode -> embed oficial
            if len(parts) >= 2 and parts[0] in ('p', 'reel', 'tv') and self._IG_CODE.match(parts[1]):
                return f'https://www.instagram.com/{parts[0]}/{parts[1]}/embed/'
            raise serializers.ValidationError('Pegá el link completo del video de Instagram (…/reel/…, /p/… o /tv/…).')
        if host in self._FB_HOSTS:
            if parts[:2] == ['plugins', 'video.php']:
                #Embed ya normalizado: se conserva solo el href canónico.
                href            =   (parse_qs(parsed.query).get('href') or [None])[0]
                if href:
                    return f'https://www.facebook.com/plugins/video.php?href={quote(href, safe="")}&show_text=false'
            return self._facebook_embed(parsed, parts)
        raise serializers.ValidationError('Solo se admiten videos de YouTube, Vimeo, TikTok, Instagram o Facebook.')
    def validate_video_url(self, value):
        return self._video_embed(value)
    def validate_videos(self, value):
        #Lista de embeds de redes: cada link se normaliza como video_url y
        #el total se recorta al tope max_videos del plan vigente (Básico 3,
        #Estándar 10, Premium 15; sin el beneficio en el plan, el techo
        #duro VIDEOS_MAX). Filas repetidas se descartan.
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Debe ser una lista de links de video.')
        store                   =   getattr(self.instance, 'store', None)
        benefits                =   plan_benefits_of(store.user) if store is not None else {}
        limit                   =   benefits.get('max_videos')
        cap                     =   StoreCustomization.VIDEOS_MAX if limit is None else min(int(limit), StoreCustomization.VIDEOS_MAX)
        clean                   =   []
        for item in value[:cap]:
            raw                 =   item.get('url') if isinstance(item, dict) else item
            embed               =   self._video_embed(raw)
            if embed and embed not in clean:
                clean.append(embed)
        return clean
    def validate_live_stream_url(self, value):
        #Transmisión en vivo (Premium, has_live_stream): YouTube y Facebook
        #reusan el embed de video; Twitch guarda la URL del canal y el
        #front arma player.twitch.tv con ?parent=<host de la tienda>.
        value                   =   (value or '').strip()
        if not value:
            return ''
        parsed, host, parts     =   self._parsed_video_url(value)
        if host == 'player.twitch.tv':
            #URL de player ya normalizada (se reenvía al editar): conservar
            #solo el canal válido.
            channel             =   (parse_qs(parsed.query).get('channel') or [''])[0]
            if channel and self._TWITCH_CHAN.match(channel):
                return f'https://player.twitch.tv/?channel={channel}'
            raise serializers.ValidationError('Pegá el link de tu canal de Twitch (twitch.tv/tu-canal).')
        if host in self._TWITCH_HOSTS:
            channel             =   (parts[0] if parts else '').strip('/')
            if channel and self._TWITCH_CHAN.match(channel):
                return f'https://player.twitch.tv/?channel={channel}'
            raise serializers.ValidationError('Pegá el link de tu canal de Twitch (twitch.tv/tu-canal).')
        if host in self._YT_HOSTS or host in self._FB_HOSTS or host in ('youtube-nocookie.com', 'www.youtube-nocookie.com'):
            return self._video_embed(value)
        raise serializers.ValidationError('Para el vivo admitimos YouTube, Facebook y Twitch.')

    def validate(self, attrs):
        #site_templates manda sobre show_catalog: se derivan siempre
        #juntos (la página catálogo apagada devuelve 404 en la web).
        templates               =   attrs.get('site_templates')
        if templates is not None:
            attrs['show_catalog']   =   'catalog' in templates
        #Guardar un publicado también alinea su borrador (el editor de hoy
        #guarda y deja la web al día en el mismo paso); un *_draft explícito
        #en el payload manda sobre esta copia.
        for name in ('layout_config', 'site_theme', 'template'):
            draft                   =   f'{name}_draft'
            if name in attrs and draft not in attrs:
                attrs[draft]        =   attrs[name]
        return attrs

    def to_representation(self, customization):
        data                    =   super().to_representation(customization)
        #site_templates sale siempre normalizado (una fila vieja o vacía
        #autocorrige la lectura al default) y site_mode se expone derivado
        #solo para compat con las plantillas del catálogo.
        templates               =   normalize_site_templates(customization.site_templates) or list(DEFAULT_SITE_TEMPLATES)
        data['site_templates']  =   templates
        data['site_mode']       =   site_mode_of(templates)
        #Lectura tolerante del diseño: una fila con un id retirado (restaurada
        #de un backup viejo, o anterior a la mig. 0053) se sirve con el diseño
        #nuevo al que la remapea TEMPLATE_RETIRED_MAP — nunca cae al fallback
        #ni rompe el render.
        retired                 =   StoreCustomization.TEMPLATE_RETIRED_MAP
        for field in ('template', 'template_draft'):
            value               =   data.get(field)
            if value in retired:
                data[field]     =   retired[value]
        return data

    def validate_accent_custom(self, value):
        value                   =   (value or '').strip()
        if value and not re.fullmatch(StoreCustomization.HEX_COLOR_RE, value):
            raise serializers.ValidationError('Ingresá un color hexadecimal válido, por ejemplo #1a7f5a.')
        return value.lower()

    def validate_whatsapp(self, value):
        value                   =   value.strip().replace(' ', '').replace('-', '')
        if value and not validate_whatsapp(value):
            raise serializers.ValidationError('Ingresá un número válido: 8 a 15 dígitos, con "+" opcional. Ej. +5493871551234')
        return value
    def validate_instagram(self, value):
        value                   =   value.strip().lstrip('@').lower()
        if value and not validate_instagram(value):
            raise serializers.ValidationError('Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos')
        return value
    def validate_tiktok(self, value):
        value                   =   value.strip().lstrip('@').lower()
        if value and not validate_tiktok(value):
            raise serializers.ValidationError('Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos')
        return value
    def validate_facebook(self, value):
        value                   =   value.strip().strip('/')
        if 'facebook.com/' in value:
            value               =   value.split('facebook.com/', 1)[1].strip('/').split('/')[0]
        if value and not validate_facebook(value):
            raise serializers.ValidationError('Ingresá el nombre de tu página o usuario: letras, números y puntos')
        return value
#=========================================
# STORE CUSTOMIZATION PUBLIC SERIALIZER (web pública: oculta el email de
# contacto — el formulario existe justamente para no exponerlo a scrapers)
#=========================================
class StoreCustomizationPublicSerializer(StoreCustomizationSerializer):
    #La web pública ve solo lo PUBLICADO: los borradores del Studio y su
    #estado de sincronía quedan para el dueño (Studio/panel).
    #Los canales directos tampoco viajan en claro (número de WhatsApp y
    #usuarios de redes): el visitante ve flags has_* y los enlaces salen
    #por el redirect /api/stores/public/<slug>/r/<kind>/ — un scraper del
    #payload o del DOM no cosecha datos de contacto.
    has_whatsapp            =   serializers.SerializerMethodField()
    has_instagram           =   serializers.SerializerMethodField()
    has_tiktok              =   serializers.SerializerMethodField()
    has_facebook            =   serializers.SerializerMethodField()
    class Meta(StoreCustomizationSerializer.Meta):
        fields              =   [f for f in StoreCustomizationSerializer.Meta.fields
                                 if f not in ('contact_email', 'layout_config_draft', 'site_theme_draft', 'template_draft', 'has_unpublished',
                                              'whatsapp', 'instagram', 'tiktok', 'facebook')]
        fields             +=   ['has_whatsapp', 'has_instagram', 'has_tiktok', 'has_facebook']
    def get_has_whatsapp(self, customization):
        return bool((customization.whatsapp or '').strip())
    def get_has_instagram(self, customization):
        return bool((customization.instagram or '').strip())
    def get_has_tiktok(self, customization):
        return bool((customization.tiktok or '').strip())
    def get_has_facebook(self, customization):
        return bool((customization.facebook or '').strip())
    def to_representation(self, customization):
        data                =   super().to_representation(customization)
        #Las opiniones (valoraciones y comentarios) son premium
        #(has_product_comments): si la tienda bajó de plan la web pública
        #no las muestra aunque los toggles quedaron en True (al volver a
        #premium reaparecen solos).
        if not profile_has_benefit(customization.store.user, 'has_product_comments'):
            data['show_reviews']    =   False
            data['show_comments']   =   False
        #La identidad visual Premium nueva no se muestra si el plan bajó
        #(los valores quedan guardados y reaparecen al volver a Premium).
        if not profile_has_benefit(customization.store.user, 'has_design_advanced'):
            data.update(accent_custom = '', logo_scale = 'm', logo_mode = 'logo_name', mono_style = 'accent',
                        cover_overlay = 0, cover_focus_x = 50, cover_focus_y = 50)
        #Los videos se sirven hasta el tope del plan vigente (una baja de
        #plan muestra solo los primeros N, como el resto de los límites) y
        #el stream en vivo es Premium (has_live_stream): sin el flag la URL
        #no viaja — el valor queda guardado para cuando vuelva el plan.
        if 'videos' in data:
            limit               =   plan_benefits_of(customization.store.user).get('max_videos')
            cap                 =   StoreCustomization.VIDEOS_MAX if limit is None else min(int(limit), StoreCustomization.VIDEOS_MAX)
            data['videos']      =   (data.get('videos') or [])[:cap]
        if not profile_has_benefit(customization.store.user, 'has_live_stream'):
            data['live_stream_url'] =   ''
        #El tema del Studio viaja EFECTIVO según el plan: con has_design_plus
        #el subconjunto básico (radius/density) + el estilo; el plan Básico
        #solo el estilo y su juego de colores; sin beneficios, {} — una
        #tienda sin site_theme se ve idéntica a hoy.
        data['site_theme']      =   filter_site_theme(
            customization.site_theme,
            has_plus        =   profile_has_benefit(customization.store.user, 'has_design_plus'),
            has_advanced    =   profile_has_benefit(customization.store.user, 'has_design_advanced'),
            has_style       =   profile_has_benefit(customization.store.user, 'has_customization'),
        )
        #site_templates viaja EFECTIVO al público: lo guardado intersectado
        #con el plan vigente y recortado al cupo (la página Servicios sale
        #sola al bajar de Estándar; al subir reaparece con sus ítems).
        effective                   =   effective_site_templates(customization.store)
        data['site_templates']      =   effective
        data['site_mode']           =   site_mode_of(effective)
        data['show_catalog']        =   'catalog' in effective
        return data
#=========================================
# STORE SERIALIZER LIST
#=========================================
class StoreSerializerList(serializers.ModelSerializer):
    public_path                 =   serializers.SerializerMethodField()
    customization               =   StoreCustomizationSerializer(read_only = True)
    storage                     =   serializers.SerializerMethodField()
    #Datos del dueño: alimentan la sección "Webs" del panel admin
    #(para el dueño repiten su propia info, no suman exposición).
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    owner_id                    =   serializers.IntegerField(source = 'user.user_id', read_only = True)
    owner_name                  =   serializers.CharField(source = 'user.user.username', read_only = True)
    owner_email                 =   serializers.CharField(source = 'user.user.email', read_only = True)
    plan_name                   =   serializers.SerializerMethodField()
    has_access                  =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Store
        fields                  =   ['id', 'slug', 'is_published', 'is_blocked', 'blocked_reason', 'blocked_at', 'created_at',
                                     'public_path', 'customization', 'storage',
                                     'business_name', 'owner_id', 'owner_name', 'owner_email', 'plan_name', 'has_access']
    def get_public_path(self, store):
        return f'/{store.slug}'
    def get_storage(self, store):
        # Cuota de imágenes del plan vigente ({used_bytes, max_mb, images, max_images}).
        return storage_payload(store, store.user)
    def get_plan_name(self, store):
        suscription             =   getattr(store.user, 'suscription', None)
        return suscription.plan_suscription.name if suscription else None
    def get_has_access(self, store):
        suscription             =   getattr(store.user, 'suscription', None)
        return bool(suscription and suscription.grants_access())
#=========================================
# STORE PUBLIC SERIALIZER (datos que ve cualquier visitante)
#=========================================
class StorePublicSerializer(serializers.ModelSerializer):
    business_name               =   serializers.CharField(source = 'user.business_name', read_only = True)
    city_name                   =   serializers.CharField(source = 'user.city.name_city', read_only = True)
    province_name               =   serializers.CharField(source = 'user.province.name_province', read_only = True)
    customization               =   StoreCustomizationPublicSerializer(read_only = True)
    has_design_advanced         =   serializers.SerializerMethodField()
    allowed_templates           =   serializers.SerializerMethodField()
    location_address            =   serializers.SerializerMethodField()
    chatbot                     =   serializers.SerializerMethodField()
    service_items               =   serializers.SerializerMethodField()
    orders_enabled              =   serializers.SerializerMethodField()
    shipping                    =   serializers.SerializerMethodField()
    payments                    =   serializers.SerializerMethodField()
    class Meta:
        model                   =   Store
        fields                  =   ['slug', 'business_name', 'city_name', 'province_name', 'customization', 'has_design_advanced', 'allowed_templates', 'location_address', 'chatbot', 'service_items', 'orders_enabled', 'shipping', 'payments']
    def get_has_design_advanced(self, store):
        #Solo premium: define si la web muestra portada (carrusel) o el
        #botón de modo claro/oscuro para el visitante en el nav.
        return profile_has_benefit(store.user, 'has_design_advanced')
    def get_allowed_templates(self, store):
        #Whitelist de plantillas según el nivel del plan: la web fuerza
        #'classic' si el diseño guardado deja de estar permitido (baja de
        #plan o plantilla retirada del catálogo).
        return list(allowed_templates_of(store.user))
    def get_location_address(self, store):
        #Dirección lista para geocodificar (mapa embebido, has_location_map):
        #None si el dueño la apagó en Diseño web o no tiene domicilio cargado.
        customization         =   getattr(store, 'customization', None)
        if not customization or not customization.show_location:
            return None
        if not profile_has_benefit(store.user, 'has_location_map'):
            return None
        user                  =   store.user
        if not user.address:
            return None
        parts                 =   [user.address]
        if user.city:
            parts.append(user.city.name_city)
        if user.province:
            parts.append(user.province.name_province)
        parts.append('Argentina')
        return ', '.join(parts)
    def get_orders_enabled(self, store):
        #Gate efectivo de venta online (ecommerce_enabled + perfil fiscal
        #completo) — la web pública lo usa para mostrar/ocultar el CTA de
        #compra. Mismo predicado que los endpoints de pedido (gate único).
        from StoreApp.domains.stores.services.commerce import orders_enabled
        return orders_enabled(store)
    def get_shipping(self, store):
        #Tarifa de envío a domicilio para el checkout: home_price NULL =
        #"a coordinar" (sin precio online — el pedido lo pacta por
        #WhatsApp). El retiro en el local siempre es sin cargo.
        cfg     =   getattr(store, 'shipping_config', None)
        price   =   cfg.home_price if cfg is not None else None
        return {'home_price': str(price) if price is not None else None}
    def get_payments(self, store):
        #Medios de cobro habilitados del checkout (mismo subconjunto público
        #que /membership-plans/): la ficha de producto los muestra sin otro
        #request. La plata va al vendedor — DAVENT nunca la toca.
        cfg         =   getattr(store, 'payment_config', None)
        mp_on       =   bool(cfg.mp_enabled) if cfg else True
        account     =   getattr(store, 'mp_account', None)
        return {
            'accept_transfer'   :   cfg.accept_transfer if cfg else True,
            'accept_whatsapp'   :   cfg.accept_whatsapp if cfg else True,
            'accept_cash'       :   cfg.accept_cash if cfg else False,
            'mp_enabled'        :   mp_on,
            'mp_connected'      :   mp_on and bool(account and account.is_connected),
        }
    def get_chatbot(self, store):
        #{'greeting', 'qa'} solo si el plan tiene 'has_chatbot' y el
        #dueño lo activó; el widget público no se renderiza con None.
        if not profile_has_benefit(store.user, 'has_chatbot'):
            return None
        cfg                     =   getattr(store, 'chatbot', None)
        if not cfg or not cfg.is_enabled:
            return None
        return {'greeting': cfg.greeting, 'qa': cfg.qa or []}
    def get_service_items(self, store):
        #Servicios activos de la página "Servicios": los carga la action
        #public() solo cuando la página está habilitada en los
        #site_templates efectivos — sin el flag el viaje no se hace y el
        #payload sale vacío. Nunca se persisten pedidos: la selección del
        #visitante se coordina por WhatsApp.
        items                   =   getattr(store, '_service_items', None)
        if not items:
            return []
        from StoreApp.domains.services.serializers.serializers import (
            ServicePublicSerializer,
        )
        return ServicePublicSerializer(items, many = True).data
#=========================================
# STORE CONTACT SERIALIZER (formulario público "Contáctanos")
#=========================================
class StoreContactSerializer(serializers.Serializer):
    #El honeypot `website` queda oculto para humanos: los bots lo completan
    #y el viewset les devuelve éxito falso sin enviar nada.
    name                        =   serializers.CharField(min_length = 2, max_length = 80, trim_whitespace = True)
    email                       =   serializers.EmailField()
    message                     =   serializers.CharField(min_length = 10, max_length = 2000)
    website                     =   serializers.CharField(required = False, allow_blank = True, write_only = True)
    challenge_id                =   serializers.CharField(write_only = True)
    captcha_answer              =   serializers.CharField(max_length = 8, write_only = True)
