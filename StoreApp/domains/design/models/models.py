import re

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
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
TIER_CHOICES = [
    ('base', 'Base'),
    ('plus', 'Plus'),
    ('advanced', 'Advanced'),
]

#=========================================
# CONTRATO DE EFECTOS DEL ESTILO
#=========================================
#DesignStyle solo puede tocar bordes, colores y detalles basicos. Todo lo
#demas (estructura, layout, HTML, orden de secciones) se recorta: un estilo
#nunca puede romper la composicion del diseno.
STYLE_EFFECT_COLORS = (
    'accent', 'primary', 'secondary', 'bg', 'surface', 'text', 'muted',
    'border', 'success', 'danger',
)
STYLE_EFFECT_RADIUS      =   {'none', 'sm', 'md', 'lg', 'xl', 'pill'}
STYLE_EFFECT_SHADOW      =   {'none', 'soft', 'medium', 'strong'}
STYLE_EFFECT_BORDER      =   {'none', 'solid', 'dashed'}
STYLE_EFFECT_SPACE       =   {'compact', 'normal', 'spacious'}
STYLE_EFFECT_BUTTON      =   {'square', 'rounded', 'pill'}
STYLE_EFFECT_DIVIDER     =   {'none', 'line', 'dots'}
STYLE_EFFECT_KEYS        =   frozenset({
    *STYLE_EFFECT_COLORS,
    'radius', 'border_width', 'border_style', 'shadow', 'space',
    'button_shape', 'divider',
})
_HEX_RE                  =   re.compile(r'^#[0-9a-fA-F]{3,8}$')
_NUM_RE                  =   re.compile(r'^\d{1,2}$')


def clean_style_effects(raw):
    """
    Normaliza el bloque `effects` de DesignStyle.
    Devuelve solo las claves del contrato con valores validos. Una clave
    desconocida o estructural (layout, template, html...) se descarta en
    silencio: el estilo no puede alterar la composicion.
    """
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, value in raw.items():
        if key not in STYLE_EFFECT_KEYS:
            continue
        if key in STYLE_EFFECT_COLORS:
            if isinstance(value, str) and _HEX_RE.match(value.strip()):
                clean[key] = value.strip().lower()
            continue
        if key == 'border_width':
            if isinstance(value, bool):
                continue
            if isinstance(value, int) and 0 <= value <= 4:
                clean[key] = value
            continue
        text = str(value or '').strip().lower()
        allowed = {
            'radius': STYLE_EFFECT_RADIUS,
            'shadow': STYLE_EFFECT_SHADOW,
            'border_style': STYLE_EFFECT_BORDER,
            'space': STYLE_EFFECT_SPACE,
            'button_shape': STYLE_EFFECT_BUTTON,
            'divider': STYLE_EFFECT_DIVIDER,
        }.get(key)
        if allowed and text in allowed:
            clean[key] = text
    return clean

#=========================================
# VARIABLES DE PATRON (HTML/CSS/JS)
#=========================================
#Cada patron declara las variables que su markup puede recibir. El render
#reemplaza {{nombre}} por el dato de la tienda; una variable no declarada
#nunca se interpola (fail-closed contra inyeccion).
PATTERN_VAR_TYPES = ('text', 'html_text', 'color', 'number', 'image', 'list')
#Nombres reservados del contrato: una variable nunca puede pisar la
#estructura del diseno.
PATTERN_VAR_RESERVED = frozenset({'layout', 'layout_config', 'html', 'css', 'js', 'template', 'blocks', 'style'})
_VAR_NAME_RE      = re.compile(r'^[a-z][a-z0-9_]{0,39}$')
_PATTERN_VAR_RE   = re.compile(r'\{\{\s*([a-z][a-z0-9_]{0,39})\s*\}\}')


def clean_pattern_variables(raw):
    """
    Normaliza la declaracion `variables` de DesignPattern:
    {nombre: {label, type, default}}.
    """
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for name, spec in raw.items():
        key = str(name or '').strip().lower()
        if not _VAR_NAME_RE.match(key) or key in PATTERN_VAR_RESERVED:
            continue
        if not isinstance(spec, dict):
            spec = {'default': spec}
        var_type = str(spec.get('type') or 'text').strip().lower()
        if var_type not in PATTERN_VAR_TYPES:
            var_type = 'text'
        item = {'type': var_type}
        label = str(spec.get('label') or '').strip()[:60]
        if label:
            item['label'] = label
        default = spec.get('default')
        if isinstance(default, (str, int, float)) and not isinstance(default, bool):
            item['default'] = str(default)[:500]
        clean[key] = item
    return clean


class DesignStyle(models.Model):
    slug                =   models.SlugField(max_length = 120, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 120, verbose_name = 'Nombre')
    categoria           =   models.CharField(max_length = 60, db_index = True, verbose_name = 'Categoría')
    descripcion         =   models.TextField(blank = True, verbose_name = 'Descripción')
    tier                =   models.CharField(max_length = 10, choices = TIER_CHOICES, default = 'base', verbose_name = 'Nivel de plan')
    #Plantilla y layout que aplica el estilo (vacío = solo tema)
    template            =   models.CharField(max_length = 20, blank = True, verbose_name = 'Plantilla')
    layout              =   models.JSONField(default = dict, blank = True, verbose_name = 'Layout por superficie')
    layout_spec         =   models.JSONField(default = dict, blank = True, verbose_name = 'Layout compacto (spec)')
    page_theme          =   models.CharField(max_length = 10, default = 'light', verbose_name = 'Modo claro/oscuro')
    #Paleta, fuentes, radios y sombras: se mergea sobre el tema neutro
    tokens              =   models.JSONField(default = dict, blank = True, verbose_name = 'Tokens de diseño')
    #Solo bordes, colores y detalles basicos (ver clean_style_effects).
    #Nunca estructura ni composicion.
    effects             =   models.JSONField(default = dict, blank = True, verbose_name = 'Efectos permitidos')
    tags                =   ArrayField(
        models.CharField(max_length = 50),
        default = list,
        blank = True,
        verbose_name = 'Tags',
    )
    is_default          =   models.BooleanField(default = False, db_index = True, verbose_name = 'Predeterminado')
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
        constraints         =   [
            models.UniqueConstraint(
                fields = ['is_default'],
                condition = models.Q(is_default = True),
                name = 'uq_design_style_default',
            ),
        ]

    def save(self, *args, **kwargs):
        self.effects = clean_style_effects(self.effects)
        super().save(*args, **kwargs)

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
    tier                =   models.CharField(max_length = 10, choices = TIER_CHOICES, default = 'base', verbose_name = 'Nivel de plan')
    #Plantilla del front que monta el patrón y layout por superficie
    template            =   models.CharField(max_length = 20, blank = True, verbose_name = 'Plantilla')
    layout              =   models.JSONField(default = dict, blank = True, verbose_name = 'Layout por superficie')
    #Markup del patrón (secciones/bloques que arma la web del cliente)
    html                =   models.TextField(blank = True, verbose_name = 'HTML')
    css                 =   models.TextField(blank = True, verbose_name = 'CSS')
    js                  =   models.TextField(blank = True, verbose_name = 'JS')
    #Variables que acepta el markup ({{nombre}}): {nombre: {type, label, default}}
    variables           =   models.JSONField(default = dict, blank = True, verbose_name = 'Variables del patrón')
    #Modo noche propio del patron (el visitante siempre puede alternarlo)
    supports_dark_mode  =   models.BooleanField(default = True, verbose_name = 'Admite modo noche')
    #Set de iconos de los controles de menu que trae el diseno
    icon_style          =   models.ForeignKey(
        'DesignIconStyle',
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'patterns',
        verbose_name = 'Estilo de iconos',
    )
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
    is_default          =   models.BooleanField(default = False, db_index = True, verbose_name = 'Predeterminado')
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
        constraints         =   [
            models.UniqueConstraint(
                fields = ['is_default'],
                condition = models.Q(is_default = True),
                name = 'uq_design_pattern_default',
            ),
        ]

    def save(self, *args, **kwargs):
        self.variables = clean_pattern_variables(self.variables)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} ({self.slug})'

    def render(self, context = None):
        """
        Interpola `{{variable}}` en el HTML usando solo las variables
        declaradas. Una variable no declarada se reemplaza por vacio: el
        markup nunca ejecuta datos arbitrarios de la tienda.
        """
        from django.utils.html import escape
        declared = self.variables or {}
        def _replace(match):
            name = match.group(1)
            spec = declared.get(name)
            if not spec:
                return ''
            value = (context or {}).get(name, spec.get('default', ''))
            return escape(str(value))
        return _PATTERN_VAR_RE.sub(_replace, self.html or '')

#=========================================
# DESIGN ICON STYLE MODEL (iconos de controles)
#=========================================
#Catalogo de sets de iconos de los controles del menu de la web del
#usuario (barra superior, barra movil, botones). El diseno trae uno por
#defecto; el usuario puede cambiarlo sin tocar el diseno.
ICON_CONTROLS = (
    'home', 'catalog', 'services', 'contact', 'about', 'gallery',
    'search', 'cart', 'menu', 'close', 'theme', 'whatsapp', 'phone',
    'instagram', 'facebook', 'tiktok', 'mail', 'location', 'share',
    'chevron_left', 'chevron_right', 'arrow_right', 'plus', 'minus',
)
ICON_VIEW_BOX_RE    =   re.compile(r'^0 0 \d{1,3} \d{1,3}$')
ICON_PATH_RE        =   re.compile(r'^[MmZzLlHhVvCcSsQqTtAa0-9eE.,\s+\-]{1,2000}$')


def clean_icon_set(raw):
    """
    Normaliza `icons`: {control: {path, view_box?, fill?, stroke?}}.
    Solo controles conocidos y path data SVG (nada de HTML).
    """
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for control, spec in raw.items():
        key = str(control or '').strip().lower()
        if key not in ICON_CONTROLS or not isinstance(spec, dict):
            continue
        path = str(spec.get('path') or '').strip()
        if not path or not ICON_PATH_RE.match(path):
            continue
        item = {'path': path}
        view_box = str(spec.get('view_box') or '0 0 24 24').strip()
        item['view_box'] = view_box if ICON_VIEW_BOX_RE.match(view_box) else '0 0 24 24'
        if spec.get('fill') is True:
            item['fill'] = True
        if isinstance(spec.get('stroke'), (int, float)) and not isinstance(spec.get('stroke'), bool):
            width = float(spec['stroke'])
            if 0 <= width <= 4:
                item['stroke'] = round(width, 2)
        clean[key] = item
    return clean


class DesignIconStyle(models.Model):
    slug                =   models.SlugField(max_length = 80, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 80, verbose_name = 'Nombre')
    descripcion         =   models.TextField(blank = True, verbose_name = 'Descripción')
    categoria           =   models.CharField(max_length = 40, default = 'menu', verbose_name = 'Categoría')
    icons               =   models.JSONField(default = dict, blank = True, verbose_name = 'Iconos')
    stroke_width        =   models.FloatField(default = 1.6, verbose_name = 'Grosor de trazo')
    preview             =   models.CharField(max_length = 255, blank = True, verbose_name = 'Miniatura')
    is_default          =   models.BooleanField(default = False, db_index = True, verbose_name = 'Predeterminado')
    is_active           =   models.BooleanField(default = True, db_index = True, verbose_name = 'Activo')
    position            =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at          =   models.DateTimeField(auto_now_add = True)
    updated_at          =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'design'
        verbose_name        =   'Estilo de iconos'
        verbose_name_plural =   'Estilos de iconos'
        ordering            =   ['position', 'nombre', 'id']
        constraints         =   [
            models.UniqueConstraint(
                fields = ['is_default'],
                condition = models.Q(is_default = True),
                name = 'uq_design_icon_style_default',
            ),
        ]

    def save(self, *args, **kwargs):
        self.icons = clean_icon_set(self.icons)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} ({self.slug})'
