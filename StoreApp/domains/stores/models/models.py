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
    que el logo, el carrusel y los productos.
    """
    store                       =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'gallery_images', db_index = False)
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
