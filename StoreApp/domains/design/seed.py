"""

Datos base del catálogo de diseño.

`seed_data.json` es la foto exportada del catálogo actual del front
(`frontend/scripts/export-design-catalog.mjs`): los 22 estilos del Studio
y los 8 patrones de plantilla. El comando `seed_design_catalog` los
inserta/actualiza por slug — los datos viven en la base, no en el front.

BASE_STYLE es el estilo predeterminado de la plataforma: una paleta
neutra que cualquier tienda puede aplicar sin elegir nada.

"""
#=========================================
# BASE STYLE (estilo predeterminado)
#=========================================
BASE_STYLE = {
    'slug'          :   'base',
    'nombre'        :   'Base',
    'categoria'     :   'general',
    'descripcion'   :   'Estilo neutro de la plataforma: claro, legible y sin adornos.',
    'tier'          :   'base',
    'template'      :   'raiz',
    'page_theme'    :   'light',
    'tokens'        :   {
        'palette'       :   {
            'primary'       :   '#0f766e',
            'secondary'     :   '#134e4a',
            'accent'        :   '#0f766e',
            'bg'            :   '#ffffff',
            'surface'       :   '#f8fafc',
            'text'          :   '#0f172a',
            'muted'         :   '#64748b',
            'border'        :   '#e2e8f0',
            'success'       :   '#059669',
            'danger'        :   '#dc2626',
        },
        'containers'    :   {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography'    :   {'heading': 'inter', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 700, 'letterSpacing': '-0.01em'},
        'buttons'       :   {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background'    :   {'type': 'solid', 'value': None, 'overlay': 'none'},
        'motion'        :   {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'mobile'        :   {'cardStyle': 'standard', 'heroHeight': 'standard'},
        'preview'       :   '/design-previews/styles/base.png',
    },
    'layout'        :   {},
    'layout_spec'   :   {},
    'tags'          :   ['general', 'base', 'neutro'],
    'preview'       :   '/design-previews/styles/base.png',
    'concept'       :   'Base neutra: teal institucional, Inter y contenedores suaves.',
    'anim'          :   {'hero': 'fade-rise', 'reveal': 'fade', 'hover': 'lift', 'button': 'soft-press'},
    'easing'        :   'cubic-bezier(.4,0,.2,1)',
    'duration'      :   '480ms',
    'icons'         :   {'style': 'line', 'stroke': '1.5', 'size': '24', 'corners': 'rounded'},
}
DEFAULT_PATTERN     =   'esencial'
DEFAULT_STYLE       =   BASE_STYLE['slug']

#=========================================
# CATEGORÍAS (rubros compartidos patrón/estilo)
#=========================================
#La taxonomía es una sola: los patrones ya venían con rubro y los estilos
#traían descriptores ("Tienda de moda nocturna") que STYLE_RUBRO pliega al
#rubro que les corresponde.
CATEGORIES          =   [
    {'slug': 'general',        'nombre': 'General'},
    {'slug': 'indumentaria',   'nombre': 'Indumentaria'},
    {'slug': 'calzado',        'nombre': 'Calzado'},
    {'slug': 'deporte',        'nombre': 'Deporte'},
    {'slug': 'gastronomia',    'nombre': 'Gastronomía'},
    {'slug': 'hogar',          'nombre': 'Hogar'},
    {'slug': 'turismo',        'nombre': 'Turismo'},
    {'slug': 'viajes',         'nombre': 'Viajes'},
    {'slug': 'tecnologia',     'nombre': 'Tecnología'},
    {'slug': 'computacion',    'nombre': 'Computación'},
    {'slug': 'retail',         'nombre': 'Retail'},
    {'slug': 'servicios',      'nombre': 'Servicios'},
    {'slug': 'seguridad',      'nombre': 'Seguridad'},
    {'slug': 'premium',        'nombre': 'Premium'},
]

#Descriptor histórico de `categoria` en estilos -> slug de rubro.
#El seed viejo guardaba texto libre; esta tabla lo normaliza una sola vez.
STYLE_RUBRO         =   {
    'Boutique chic':                        'indumentaria',
    'Calzado y deportes':                   'calzado',
    'Componentes de PC':                    'tecnologia',
    'Deporte claro':                        'deporte',
    'Deporte oscuro':                       'deporte',
    'Hogar y objetos':                      'hogar',
    'Lookbook editorial':                   'indumentaria',
    'Marketplace':                          'retail',
    'Marketplace de ofertas':               'retail',
    'Marketplace nocturno':                 'retail',
    'Premium':                              'premium',
    'Retail de indumentaria':               'indumentaria',
    'Revista de moda':                      'indumentaria',
    'Runway nocturno':                      'indumentaria',
    'Sastrería corporativa':                'indumentaria',
    'Sastrería editorial':                  'indumentaria',
    'Sastrería industrial':                 'indumentaria',
    'Sastrería nocturna':                   'indumentaria',
    'Seguridad contra incendios':           'seguridad',
    'Seguridad y protección':               'seguridad',
    'Servicios profesionales':              'servicios',
    'Servicios profesionales archivo':      'servicios',
    'Servicios profesionales nocturnos':    'servicios',
    'Streetwear':                           'indumentaria',
    'Tecnologia oscura':                     'tecnologia',
    'Tienda de indumentaria':               'indumentaria',
    'Tienda de indumentaria nocturna':      'indumentaria',
    'Tienda de moda':                       'indumentaria',
    'Tienda de moda de autor':              'indumentaria',
    'Tienda de moda de autor nocturna':     'indumentaria',
    'Tienda de moda nocturna':              'indumentaria',
    'Tienda de modista':                    'indumentaria',
    'Tienda de modista nocturna':           'indumentaria',
    'Turismo':                              'turismo',
    'Turismo nocturno':                     'turismo',
    'Viajes y experiencias':                'viajes',
    'Viajes y experiencias nocturnas':      'viajes',
    'Workwear':                             'indumentaria',
    'gastronomia':                          'gastronomia',
    'gastronomia nocturna':                 'gastronomia',
    'general':                              'general',
}
DEFAULT_RUBRO       =   'general'


def style_rubro(categoria):
    """Descriptor de categoría del seed -> slug de rubro (fallback general)."""
    return STYLE_RUBRO.get(str(categoria or '').strip(), DEFAULT_RUBRO)

#=========================================
# MARKUP DEL PATRÓN (HTML/CSS/JS de arranque)
#=========================================
def build_markup(pattern):
    """Esqueleto estático del patrón: una sección por bloque de la landing."""
    slug        =   pattern['slug']
    accent      =   (pattern.get('tokens') or {}).get('accent') or '#0f766e'
    blocks      =   [
        b for b in (pattern.get('layout') or {}).get('landing') or []
        if b.get('enabled', True)
    ]
    sections    =   '\n'.join(
        f'  <section class="dp-block" data-block="{b["id"]}"></section>' for b in blocks
    )
    html        =   f'<div class="dp dp-{slug}" data-pattern="{slug}">\n{sections}\n</div>'
    css         =   (
        f'.dp-{slug} {{\n'
        f'  --dp-accent: {accent};\n'
        f'  display: flex;\n'
        f'  flex-direction: column;\n'
        f'}}\n'
        f'.dp-{slug} .dp-block {{ width: 100%; }}'
    )
    return html, css, ''
