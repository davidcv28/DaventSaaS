from django.db import models
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
    FONT_SANS                   =   'sans'
    FONT_SERIF                  =   'serif'
    FONT_ROUNDED                =   'rounded'
    FONT_CONDENSED              =   'condensed'
    FONT_CHOICES                =   [
        (FONT_SANS,      'Moderna'),
        (FONT_SERIF,     'Elegante'),
        (FONT_ROUNDED,   'Redondeada'),
        (FONT_CONDENSED, 'Condensada'),
    ]
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'customization')
    display_name                =   models.CharField(max_length = 60, blank = True, verbose_name = 'Nombre visible')
    name_font                   =   models.CharField(max_length = 10, choices = FONT_CHOICES, default = FONT_SANS, verbose_name = 'Fuente del nombre')
    headline                    =   models.CharField(max_length = 140, blank = True, verbose_name = 'Titular')
    logo_key                    =   models.CharField(max_length = 200, blank = True, verbose_name = 'Logo (key en R2)')
    logo_size                   =   models.PositiveIntegerField(default = 0, verbose_name = 'Tamaño del logo (bytes)')
    description                 =   models.TextField(max_length = 800, blank = True, verbose_name = 'Descripción')
    theme                       =   models.CharField(max_length = 10, choices = THEME_CHOICES, default = THEME_LIGHT, verbose_name = 'Tema')
    accent                      =   models.CharField(max_length = 10, choices = ACCENT_CHOICES, default = ACCENT_INDIGO, verbose_name = 'Color de acento')
    whatsapp                    =   models.CharField(max_length = 20, blank = True, verbose_name = 'WhatsApp')
    instagram                   =   models.CharField(max_length = 40, blank = True, verbose_name = 'Instagram')
    tiktok                      =   models.CharField(max_length = 40, blank = True, verbose_name = 'TikTok')
    facebook                    =   models.CharField(max_length = 60, blank = True, verbose_name = 'Facebook')
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
