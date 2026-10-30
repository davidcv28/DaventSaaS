from django.contrib.postgres.fields import ArrayField
from django.db import models

"""

Catálogo de diseño de la plataforma.

DesignStyle es el tema (tokens: paleta, tipografías, radios) y
DesignPattern es el patrón completo (HTML + CSS + JS) que se aplica a la
web del cliente. Ambos viven en la base: el front no guarda presets, solo
pide el catálogo y aplica lo que devuelve la API.

La plantilla del usuario, los catálogos y los servicios no se cargan
aquí: nacen vacíos. Solo esta tabla se puebla con patrones y estilos.

"""
#=========================================
# DESIGN STYLE MODEL (tema: tokens de diseño)
#=========================================
class DesignStyle(models.Model):
    slug                =   models.SlugField(max_length = 120, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    categoria           =   models.CharField(max_length = 60, db_index = True, verbose_name = 'Categoría')
    #Paleta, fuentes, radios y sombras: se mergea sobre el tema neutro
    tokens              =   models.JSONField(default = dict, blank = True, verbose_name = 'Tokens de diseño')
    tags                =   ArrayField(
        models.CharField(max_length = 50),
        default = list,
        blank = True,
        verbose_name = 'Tags',
    )
    is_active           =   models.BooleanField(default = True, db_index = True, verbose_name = 'Activo')
    position            =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'design'
        verbose_name        =   'Estilo de diseño'
        verbose_name_plural =   'Estilos de diseño'
        ordering            =   ['position', 'nombre', 'id']
        indexes             =   [
            models.Index(fields = ['categoria', 'position'], name = 'idx_design_style_cat'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.slug})'
#=========================================
# DESIGN PATTERN MODEL (patrón completo: HTML + CSS + JS)
#=========================================
class DesignPattern(models.Model):
    slug                =   models.SlugField(max_length = 120, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    categoria           =   models.CharField(max_length = 60, db_index = True, verbose_name = 'Categoría')
    descripcion         =   models.TextField(blank = True, verbose_name = 'Descripción')
    #Markup del patrón (secciones/bloques que arma la web del cliente)
    html                =   models.TextField(blank = True, verbose_name = 'HTML')
    css                 =   models.TextField(blank = True, verbose_name = 'CSS')
    js                  =   models.TextField(blank = True, verbose_name = 'JS')
    #Tokens propios del patrón (se aplican junto con el HTML)
    tokens              =   models.JSONField(default = dict, blank = True, verbose_name = 'Tokens de diseño')
    tags                =   ArrayField(
        models.CharField(max_length = 50),
        default = list,
        blank = True,
        verbose_name = 'Tags',
    )
    #Clave/URL de la miniatura que muestra el catálogo
    preview             =   models.CharField(max_length = 255, blank = True, verbose_name = 'Miniatura')
    style               =   models.ForeignKey(
        DesignStyle,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'patterns',
        verbose_name = 'Estilo',
    )
    is_active           =   models.BooleanField(default = True, db_index = True, verbose_name = 'Activo')
    position            =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'design'
        verbose_name        =   'Patrón de diseño'
        verbose_name_plural =   'Patrones de diseño'
        ordering            =   ['position', 'nombre', 'id']
        indexes             =   [
            models.Index(fields = ['categoria', 'position'], name = 'idx_design_pattern_cat'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.slug})'
