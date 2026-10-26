from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from AdminApp.domains.users.models import UserProfile
"""

Web del cliente: Store es la identidad pública del negocio.
El slug lo elige el usuario en su primer ingreso al sistema
(no se autogenera desde el nombre comercial). Del Store cuelgan
el catálogo, la personalización y las estadísticas.

"""
#=========================================
# STORE MODEL
#=========================================
class Store(models.Model):
    user                        =   models.OneToOneField(UserProfile, on_delete = models.CASCADE, related_name = 'store')
    slug                        =   models.SlugField(max_length = 60, unique = True, verbose_name = 'Link público')
    is_published                =   models.BooleanField(default = True, verbose_name = 'Link activo')
    #Moderación staff: una web bloqueada devuelve 404 en todas las rutas
    #públicas sin importar is_published ni la suscripción. El dueño sigue
    #entrando a su panel; la causa queda registrada en blocked_reason.
    is_blocked                  =   models.BooleanField(default = False, verbose_name = 'Web bloqueada por el administrador')
    blocked_reason              =   models.CharField(max_length = 200, blank = True, verbose_name = 'Motivo del bloqueo')
    blocked_at                  =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha del bloqueo')
    storage_used_bytes          =   models.BigIntegerField(default = 0, verbose_name = 'Almacenamiento usado (bytes)')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Tienda'
        verbose_name_plural     =   'Tiendas'
    def __str__(self):
        return self.slug
#=========================================
# STORE CUSTOMIZATION MODEL
#=========================================
def default_site_templates():
    """Web mínima por defecto: portada + catálogo (el viejo site_mode='both')."""
    return ['landing', 'catalog']
class StoreCustomization(models.Model):
    """
    Apariencia y contenido editable de la web pública del cliente.
    Solo se puede editar con el beneficio 'has_customization' del plan
    vigente (premium); el viewset lo fuerza del lado del servidor.
    theme/accent son catálogos cerrados: el frontend los traduce a
    paletas CSS propias (nada de CSS libre del usuario).
    """
    THEME_LIGHT                 =   'light'
    THEME_DARK                  =   'dark'
    THEME_CHOICES               =   [
        (THEME_LIGHT, 'Claro'),
        (THEME_DARK,  'Oscuro'),
    ]
    ACCENT_INDIGO               =   'indigo'
    ACCENT_VIOLET               =   'violet'
    ACCENT_EMERALD              =   'emerald'
    ACCENT_AMBER                =   'amber'
    ACCENT_ROSE                 =   'rose'
    ACCENT_SKY                  =   'sky'
    ACCENT_ORANGE               =   'orange'
    ACCENT_LIME                 =   'lime'
    ACCENT_CHOICES              =   [
        (ACCENT_INDIGO,  'Índigo'),
        (ACCENT_VIOLET,  'Violeta'),
        (ACCENT_EMERALD, 'Esmeralda'),
        (ACCENT_AMBER,   'Ámbar'),
        (ACCENT_ROSE,    'Rosa'),
        (ACCENT_SKY,     'Celeste'),
        (ACCENT_ORANGE,  'Naranja'),
        (ACCENT_LIME,    'Lima'),
    ]
    FONT_INTER                  =   'inter'
    # Catálogo cerrado de Google Fonts (espejo de STORE_FONTS en stores.api.js):
    # el frontend las carga on-demand desde fonts.googleapis.com.
    FONT_CHOICES                =   [
        (FONT_INTER,             'Inter'),
        ('montserrat',           'Montserrat'),
        ('poppins',              'Poppins'),
        ('raleway',              'Raleway'),
        ('nunito',               'Nunito'),
        ('work-sans',            'Work Sans'),
        ('dm-sans',              'DM Sans'),
        ('sora',                 'Sora'),
        ('space-grotesk',        'Space Grotesk'),
        ('comfortaa',            'Comfortaa'),
        ('quicksand',            'Quicksand'),
        ('rubik',                'Rubik'),
        ('oswald',               'Oswald'),
        ('bebas-neue',           'Bebas Neue'),
        ('anton',                'Anton'),
        ('archivo-black',        'Archivo Black'),
        ('righteous',            'Righteous'),
        ('playfair-display',     'Playfair Display'),
        ('merriweather',         'Merriweather'),
        ('lora',                 'Lora'),
        ('fraunces',             'Fraunces'),
        ('cinzel',               'Cinzel'),
        ('pacifico',             'Pacifico'),
        ('dancing-script',       'Dancing Script'),
        ('caveat',               'Caveat'),
        ('lobster',              'Lobster'),
        ('space-mono',           'Space Mono'),
        ('jetbrains-mono',       'JetBrains Mono'),
        ('manrope',              'Manrope'),
        ('archivo',              'Archivo'),
        ('bricolage-grotesque',  'Bricolage Grotesque'),
        ('figtree',              'Figtree'),
    ]
    TEMPLATE_CLASSIC            =   'classic'
    #Diseños de la web pública (catálogo cerrado) por nivel de plan:
    #base para todo plan con has_customization, TEMPLATE_PLUS suman las
    #plantillas de campaña con has_design_plus (Estándar) y
    #TEMPLATE_ADVANCED quedan para has_design_advanced (Premium). El
    #viewset descarta del payload un diseño fuera del nivel del plan y
    #la web fuerza 'classic' si el guardado deja de estar permitido.
    TEMPLATE_BASE               =   ('classic', 'perspective', 'duo', 'bloque', 'riso')
    TEMPLATE_PLUS               =   ('street', 'promo')
    TEMPLATE_ADVANCED           =   ('terminal', 'lookbook', 'shop', 'cobre', 'minimal', 'boutique', 'signature', 'aurora')
    TEMPLATE_CHOICES            =   [
        (TEMPLATE_CLASSIC,   'Clásico'),
        ('perspective',      'Perspectiva'),
        ('duo',              'Dúo'),
        ('bloque',           'Bloque'),
        ('riso',             'Riso'),
        ('promo',            'Publicidad'),
        ('street',           'Urbano'),
        ('terminal',         'Terminal'),
        ('lookbook',         'Lookbook'),
        ('shop',             'Tienda Pro'),
        ('cobre',            'Cobre'),
        ('minimal',          'Minimal'),
        ('boutique',         'Boutique'),
        ('signature',        'Signature'),
        ('aurora',           'Aurora'),
    ]
    NAME_SIZE_MIN               =   20
    NAME_SIZE_MAX               =   64
    NAME_SIZE_DEFAULT           =   32
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'customization')
    display_name                =   models.CharField(max_length = 60, blank = True, verbose_name = 'Nombre visible')
    name_font                   =   models.CharField(max_length = 40, choices = FONT_CHOICES, default = FONT_INTER, verbose_name = 'Fuente del nombre')
    name_font_size              =   models.PositiveSmallIntegerField(default = NAME_SIZE_DEFAULT, validators = [MinValueValidator(NAME_SIZE_MIN), MaxValueValidator(NAME_SIZE_MAX)], verbose_name = 'Tamaño del nombre (px)')
    headline                    =   models.CharField(max_length = 140, blank = True, verbose_name = 'Titular')
    logo_key                    =   models.CharField(max_length = 200, blank = True, verbose_name = 'Logo (key en R2)')
    logo_size                   =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño del logo (bytes)')
    #Imagen de portada (premium, has_design_advanced): fondo del hero de la
    #web pública. Una sola imagen, normalizada a WebP; consume la misma cuota.
    cover_key                   =   models.CharField(max_length = 200, blank = True, verbose_name = 'Portada (key en R2)')
    cover_size                  =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño de la portada (bytes)')
    description                 =   models.TextField(max_length = 800, blank = True, verbose_name = 'Descripción')
    #Sección "Sobre nosotros": la web pública la renderiza solo si show_about
    #está activo y hay algún contenido cargado (texto, misión, especialidades
    #o años). about_title vacío -> título por defecto en el frontend.
    #Se edita desde la sección "Mi empresa" del dashboard.
    about_title                 =   models.CharField(max_length = 80, blank = True, verbose_name = 'Título de la sección Sobre nosotros')
    about_text                  =   models.TextField(max_length = 2000, blank = True, verbose_name = 'Texto de la sección Sobre nosotros')
    about_years                 =   models.PositiveSmallIntegerField(null = True, blank = True, validators = [MinValueValidator(0), MaxValueValidator(150)], verbose_name = 'Años de trayectoria')
    about_mission               =   models.TextField(max_length = 400, blank = True, verbose_name = 'Misión')
    about_specialties           =   models.CharField(max_length = 300, blank = True, verbose_name = 'Especialidades')
    show_about                  =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Sobre nosotros')
    #Formulario de contacto: los mensajes llegan a contact_email o, si está
    #vacío, al email de la cuenta del dueño. show_contact apaga la sección.
    contact_email               =   models.EmailField(blank = True, verbose_name = 'Email de contacto público')
    show_contact                =   models.BooleanField(default = True, verbose_name = 'Mostrar sección de contacto')
    theme                       =   models.CharField(max_length = 10, choices = THEME_CHOICES, default = THEME_LIGHT, verbose_name = 'Tema')
    template                    =   models.CharField(max_length = 12, choices = TEMPLATE_CHOICES, default = TEMPLATE_CLASSIC, verbose_name = 'Diseño de la web')
    accent                      =   models.CharField(max_length = 10, choices = ACCENT_CHOICES, default = ACCENT_INDIGO, verbose_name = 'Color de acento')
    whatsapp                    =   models.CharField(max_length = 20, blank = True, verbose_name = 'WhatsApp')
    instagram                   =   models.CharField(max_length = 40, blank = True, verbose_name = 'Instagram')
    tiktok                      =   models.CharField(max_length = 40, blank = True, verbose_name = 'TikTok')
    facebook                    =   models.CharField(max_length = 60, blank = True, verbose_name = 'Facebook')
    #Default off por privacidad: el mapa expone el domicilio del perfil (que
    #puede ser la casa del dueño) — opt-in consciente desde el dashboard.
    show_location               =   models.BooleanField(default = False, verbose_name = 'Mostrar mapa de ubicación')
    #Sección "Galería": grilla de imágenes propias del negocio. El dueño
    #decide si aparece (además se oculta sola si no hay imágenes cargadas);
    #el cupo lo fija el beneficio 'max_gallery_images' del plan.
    show_gallery                =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Galería')
    #Página "Catálogo": el dueño puede apagarla para usar su web solo como
    #vidriera del negocio. No borra productos ni gestión del panel: la ruta
    #/<slug>/catalogo y el endpoint público devuelven 404 hasta reactivarla.
    show_catalog                =   models.BooleanField(default = True, verbose_name = 'Mostrar página de catálogo')
    #Páginas que componen la web pública del cliente (catálogo cerrado y
    #multi-selección): 'landing' = portada de marketing, 'services' =
    #página de servicios con pedido por WhatsApp, 'catalog' = catálogo de
    #productos. La cantidad máxima la fija el beneficio 'max_site_templates'
    #del plan (básico/estándar = 2, premium/trial = ilimitado) y 'services'
    #además exige el flag 'has_services_site' (estándar en adelante).
    #services.validate_site_templates fuerza ambas reglas en el serializer;
    #las filas viejas se migraron desde site_mode (marketing->['landing'],
    #catalog->['catalog'], both->['landing','catalog']). El serializer
    #mantiene show_catalog sincronizado ('catalog' presente -> True) y
    #expone site_mode derivado para compat con las plantillas del catálogo.
    SITE_TEMPLATES              =   ('landing', 'services', 'catalog')
    site_templates              =   models.JSONField(default = default_site_templates, blank = True, verbose_name = 'Páginas de la web')
    #===== Config de la página "Servicios" (dominio services) =====
    #Bloques del embudo de pedido: los pasos "cómo funciona" (filas
    #{icon,title,text}), los días y franjas que ofrece el formulario,
    #si el pedido pide dirección y las notas de precio/pago. Todo se
    #coordinada por WhatsApp: la web nunca persiste reservas ni pagos.
    SERVICE_STEPS_MAX           =   4
    SERVICE_STEP_TITLE_MAX      =   60
    SERVICE_STEP_TEXT_MAX       =   160
    SERVICE_DAYS_MAX            =   7
    SERVICE_DAY_MAX             =   24
    SERVICE_SLOTS_MAX           =   4
    SERVICE_SLOT_MAX            =   24
    SERVICE_NOTE_MAX            =   160
    service_steps               =   models.JSONField(default = list, blank = True, verbose_name = 'Pasos de cómo funciona')
    service_days                =   models.JSONField(default = list, blank = True, verbose_name = 'Días de atención')
    service_slots               =   models.JSONField(default = list, blank = True, verbose_name = 'Franjas horarias')
    service_ask_address         =   models.BooleanField(default = True, verbose_name = 'Pedir dirección en el pedido')
    service_price_note          =   models.CharField(max_length = SERVICE_NOTE_MAX, blank = True, verbose_name = 'Nota de precios orientativos')
    service_pay_note            =   models.CharField(max_length = SERVICE_NOTE_MAX, blank = True, verbose_name = 'Nota de pago en persona')
    #Franja de etiquetas bajo la portada (destacados): el dueño decide si aparece.
    show_highlights             =   models.BooleanField(default = True, verbose_name = 'Mostrar franja de etiquetas')
    #===== Opiniones de visitantes sobre los productos del catálogo =====
    #Valoraciones: estrellas 1-5 en las tarjetas y la ficha (disponible en
    #todos los planes). Comentarios: texto de la opinión en la ficha —
    #requiere el beneficio 'has_product_comments' (premium); si la tienda
    #baja de plan quedan guardados pero la web los oculta (el serializer
    #público expone show_comments=False sin el flag). Apagados por
    #defecto: el dueño los enciende desde "Mis catálogos".
    show_reviews                =   models.BooleanField(default = False, verbose_name = 'Valoraciones en productos')
    show_comments               =   models.BooleanField(default = False, verbose_name = 'Comentarios en productos (premium)')
    #===== Secciones de marketing de la portada ("Mi empresa") =====
    #Bloques de contenido rico para que la web funcione como landing
    #completa, no solo como vidriera: servicios, cifras, testimonios,
    #preguntas frecuentes, horarios y un cierre con llamado a la acción.
    #Las listas viajan en JSON y el serializer las sanea (cantidad tope,
    #textos recortados, filas incompletas descartadas, iconos de catálogo
    #cerrado). Cada bloque se apaga con su show_* y además se oculta solo
    #en la web cuando quedó vacío — igual que Sobre nosotros/Galería.
    SERVICES_MAX                =   6
    SERVICE_TITLE_MAX           =   60
    SERVICE_TEXT_MAX            =   160
    SERVICE_ICONS               =   frozenset([
        'package', 'truck', 'wrench', 'tag', 'percent', 'gift', 'star', 'zap',
        'shield-check', 'clock', 'map-pin', 'users', 'phone', 'message-circle',
        'store', 'credit-card', 'wallet', 'crown', 'badge-check', 'trending-up',
        'calendar', 'flame', 'megaphone', 'check',
    ])
    STATS_MAX                   =   4
    STAT_VALUE_MAX              =   20
    STAT_LABEL_MAX              =   60
    TESTIMONIALS_MAX            =   6
    TESTIMONIAL_NAME_MAX        =   60
    TESTIMONIAL_DETAIL_MAX      =   80
    TESTIMONIAL_TEXT_MAX        =   300
    FAQS_MAX                    =   8
    FAQ_Q_MAX                   =   140
    FAQ_A_MAX                   =   500
    HOURS_MAX                   =   8
    HOURS_LABEL_MAX             =   60
    HOURS_VALUE_MAX             =   60
    #Cinta de anuncios bajo la portada: filas {icon, text} que corren en
    #marquee (ícono del catálogo SERVICE_ICONS, texto corto).
    ANNOUNCEMENTS_MAX           =   6
    ANNOUNCEMENT_TEXT_MAX       =   60
    #Sección "Video": embed de YouTube/Vimeo solamente. El serializer
    #normaliza el link pegado por el dueño a la URL de embed oficial
    #(youtube-nocookie/player.vimeo) y descarta cualquier otro host.
    VIDEO_URL_MAX               =   300
    VIDEO_TITLE_MAX             =   80
    CATALOG_NOTE_MAX            =   160
    FOOTER_TEXT_MAX             =   160
    #Orden de las secciones de la portada (claves cerradas): el hero va
    #primero y el contacto último siempre; el serializer descarta claves
    #desconocidas y completa las que falten al final en este orden base.
    #La web pública lo aplica como CSS order sobre .sp-page-root (flex).
    SECTION_ORDER               =   ('about', 'services', 'stats', 'gallery', 'testimonials', 'faq', 'video', 'cta')
    services                    =   models.JSONField(default = list, blank = True, verbose_name = 'Qué ofrecemos')
    services_title              =   models.CharField(max_length = 80, blank = True, verbose_name = 'Título de la sección Qué ofrecemos')
    show_services               =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Qué ofrecemos')
    stats                       =   models.JSONField(default = list, blank = True, verbose_name = 'Números del negocio')
    show_stats                  =   models.BooleanField(default = True, verbose_name = 'Mostrar números del negocio')
    testimonials                =   models.JSONField(default = list, blank = True, verbose_name = 'Testimonios')
    testimonials_title          =   models.CharField(max_length = 80, blank = True, verbose_name = 'Título de la sección Testimonios')
    show_testimonials           =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Testimonios')
    faqs                        =   models.JSONField(default = list, blank = True, verbose_name = 'Preguntas frecuentes')
    faqs_title                  =   models.CharField(max_length = 80, blank = True, verbose_name = 'Título de la sección Preguntas frecuentes')
    show_faq                    =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Preguntas frecuentes')
    #Horarios de atención: filas {label: 'Lun a vie', value: '9 a 18 h'},
    #se renderizan dentro de la sección Contáctanos.
    hours                       =   models.JSONField(default = list, blank = True, verbose_name = 'Horarios de atención')
    show_hours                  =   models.BooleanField(default = True, verbose_name = 'Mostrar horarios de atención')
    #Cierre de la portada: banda de llamado a la acción. El botón lleva a
    #WhatsApp si hay número cargado; si no, al formulario o al catálogo.
    cta_title                   =   models.CharField(max_length = 120, blank = True, verbose_name = 'Título del llamado a la acción')
    cta_text                    =   models.CharField(max_length = 280, blank = True, verbose_name = 'Texto del llamado a la acción')
    cta_label                   =   models.CharField(max_length = 40, blank = True, verbose_name = 'Texto del botón')
    show_cta                    =   models.BooleanField(default = True, verbose_name = 'Mostrar llamado a la acción')
    section_order               =   models.JSONField(default = list, blank = True, verbose_name = 'Orden de las secciones de la portada')
    #Cinta de anuncios bajo la portada y sección Video: bloques extra de
    #marketing que el dueño configura desde "Mi empresa".
    announcements               =   models.JSONField(default = list, blank = True, verbose_name = 'Cinta de anuncios')
    show_announcements          =   models.BooleanField(default = True, verbose_name = 'Mostrar cinta de anuncios')
    video_url                   =   models.CharField(max_length = VIDEO_URL_MAX, blank = True, verbose_name = 'Video (URL de embed)')
    video_title                 =   models.CharField(max_length = VIDEO_TITLE_MAX, blank = True, verbose_name = 'Título de la sección Video')
    show_video                  =   models.BooleanField(default = True, verbose_name = 'Mostrar sección Video')
    #Textos sueltos: aviso que encabeza la página del catálogo y una línea
    #extra en el pie de la web pública.
    catalog_note                =   models.CharField(max_length = CATALOG_NOTE_MAX, blank = True, verbose_name = 'Aviso en el catálogo')
    footer_text                 =   models.CharField(max_length = FOOTER_TEXT_MAX, blank = True, verbose_name = 'Texto del pie')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Personalización de tienda'
        verbose_name_plural     =   'Personalizaciones de tiendas'
    def __str__(self):
        return f'customization:{self.store.slug}'
#=========================================
# STORE CAROUSEL IMAGE MODEL
#=========================================
class StoreCarouselImage(models.Model):
    """
    Imagen del carrusel de portada de la web pública (máx.
    services.CAROUSEL_MAX_IMAGES por tienda). Consume la misma cuota
    max_storage_mb que el logo y las imágenes de productos.
    """
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'carousel_images', db_index = False)
    image_key                   =   models.CharField(max_length = 200, verbose_name = 'Imagen (key en R2)')
    image_size                  =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño (bytes)')
    position                    =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Imagen de carrusel'
        verbose_name_plural     =   'Imágenes de carrusel'
        ordering                =   ['position', 'id']
        indexes                 =   [
            models.Index(fields = ['store'], name = 'idx_carousel_store'),
        ]
    def __str__(self):
        return f'carousel:{self.store.slug}#{self.position}'
#=========================================
# STORE GALLERY IMAGE MODEL
#=========================================
class StoreGalleryImage(models.Model):
    """
    Imagen de la sección Galería de la web pública. El tope lo fija el
    beneficio 'max_gallery_images' del plan vigente (Básico 0, Estándar 5,
    Premium 15); además consume la misma cuota max_storage_mb/max_images
    que el logo, el carrusel y los productos. `kind='decor'`: hasta 3 imágenes
    ilustrativas de la portada (premium) que gastan cupo de la galería.
    """
    KIND_GALLERY                =   'gallery'
    KIND_DECOR                  =   'decor'
    KINDS                       =   (KIND_GALLERY, KIND_DECOR)
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'gallery_images', db_index = False)
    kind                        =   models.CharField(max_length = 10, choices = [(KIND_GALLERY, 'Galería'), (KIND_DECOR, 'Decoración de portada')], default = KIND_GALLERY, verbose_name = 'Tipo')
    image_key                   =   models.CharField(max_length = 200, verbose_name = 'Imagen (key en R2)')
    image_size                  =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño (bytes)')
    position                    =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at                  =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Imagen de galería'
        verbose_name_plural     =   'Imágenes de galería'
        ordering                =   ['position', 'id']
        indexes                 =   [
            models.Index(fields = ['store'], name = 'idx_gallery_store'),
        ]
    def __str__(self):
        return f'gallery:{self.store.slug}#{self.position}'
#=========================================
# STORE CHATBOT MODEL
#=========================================
class StoreChatbot(models.Model):
    """
    Chatbot de la web pública del cliente (beneficio 'has_chatbot':
    solo Premium). No es IA: responde a las visitas con los
    pares pregunta/respuesta que el dueño carga desde su panel.
    `qa` es una lista JSON de {'q': pregunta, 'a': respuesta}
    (el serializer limita cantidad y longitudes).
    """
    QA_MAX_ITEMS                =   12
    QA_MAX_QUESTION             =   120
    QA_MAX_ANSWER               =   500
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'chatbot')
    is_enabled                  =   models.BooleanField(default = False, verbose_name = 'Chatbot activo')
    greeting                    =   models.CharField(max_length = 200, blank = True, verbose_name = 'Mensaje de bienvenida')
    qa                          =   models.JSONField(default = list, blank = True, verbose_name = 'Preguntas y respuestas')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Chatbot de tienda'
        verbose_name_plural     =   'Chatbots de tiendas'
    def __str__(self):
        return f'chatbot:{self.store.slug}'
#=========================================
# STORE DAILY VISIT MODEL
#=========================================
class StoreDailyVisit(models.Model):
    """
    Contador diario de visitas a la web pública (sección Estadísticas,
    beneficio 'has_stats'). Una fila por tienda y día: el incremento se
    hace con F() para no perder hits concurrentes. No guarda IPs ni
    ningún dato del visitante.
    """
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'daily_visits')
    date                        =   models.DateField(verbose_name = 'Día')
    count                       =   models.PositiveIntegerField(default = 0, verbose_name = 'Visitas')
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Visita diaria'
        verbose_name_plural     =   'Visitas diarias'
        ordering                =   ['-date']
        constraints             =   [
            models.UniqueConstraint(fields = ['store', 'date'], name = 'uniq_visit_store_date'),
        ]
        indexes                 =   [
            models.Index(fields = ['store', 'date'], name = 'idx_visit_store_date'),
        ]
    def __str__(self):
        return f'{self.store.slug}@{self.date}:{self.count}'
