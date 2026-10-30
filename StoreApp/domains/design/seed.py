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
DEFAULT_PATTERN     =   'raiz'
DEFAULT_STYLE       =   BASE_STYLE['slug']

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
