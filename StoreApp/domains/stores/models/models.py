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
    ACCENT_CHOICES              =   [
        (ACCENT_INDIGO,  'Índigo'),
        (ACCENT_VIOLET,  'Violeta'),
        (ACCENT_EMERALD, 'Esmeralda'),
        (ACCENT_AMBER,   'Ámbar'),
        (ACCENT_ROSE,    'Rosa'),
        (ACCENT_SKY,     'Celeste'),
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
    ]
    TEMPLATE_CLASSIC            =   'classic'
    #Diseños de la web pública (catálogo cerrado): clásico es el diseño base
    #y los dos restantes se habilitan con has_design_advanced (Plan premium).
    #El viewset descarta el campo del payload sin ese beneficio y el frontend
    #además lo fuerza a 'classic' si la tienda pierde el plan premium.
    TEMPLATE_CHOICES            =   [
        (TEMPLATE_CLASSIC,   'Clásico'),
        ('perspective',      'Perspectiva'),
        ('promo',            'Publicidad'),
        ('atelier',          'Atelier'),
        ('street',           'Urbano'),
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
