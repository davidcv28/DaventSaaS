#=========================================
# SKINS — catálogo cerrado de 26 familias composibles (motor v5)
#=========================================
#Datos puros (sin Django). Una piel NO es una plantilla: es un presupuesto
#visual que el motor compone con el rubro y el tono. Cada familia declara
#paleta, contenedores, botones, fondo, movimiento, preset tipográfico y
#layout (mismas claves/enums que site_theme v2), y cada familia tiene dos
#variantes concretas (claro/oscuro o dos intensidades).
#
#El id que viaja en la propuesta es "<family>-<variant>" (editorial-ink,
#glass-noir): SIEMPRE derivado de este catálogo, nunca inventado por el
#motor. site_theme valida `skin.id` contra SKIN_IDS y descarta lo que no
#esté acá.
#
#Rubros/tonos afines: el puntaje del motor los usa como afinidad (no como
#bonus ciego); los enums de layout son los del contrato:
#  density  compact|comfortable|spacious
#  grid     12|asym|split|bento|editorial
#  hero     centered|split|cinema|logo|editorial
#  gutter   sm|md|lg
#  measure  narrow|normal|wide
#  radiusScale none|sm|md|lg|xl
#
#ESTILO (v5): además de rubro y tono, cada familia declara `style` — la
#familia de estilos del entrenamiento de diseño (STYLE_FAMILIES). Es lo que
#ordena la selección: la semilla rota DENTRO del estilo afín (minimal con
#minimal) en vez de caer en cualquier piel del catálogo, y así dos
#propuestas del mismo estilo no salen con el mismo look.

SKIN_FAMILIES   =   (
    'glass', 'editorial', 'brutal', 'soft', 'tech', 'warm', 'luxury',
    'kinetic', 'paper', 'neon', 'minimal', 'organic', 'retro', 'corporate',
    'playful', 'mono', 'gradient', 'cinematic',
    #v5: familias que cubren los estilos de diseño (ver STYLE_FAMILIES).
    'swiss', 'magazine', 'pop', 'aurora', 'craft', 'nostalgia', 'prestige', 'showcase',
    #Exclusivas de "Diseñar con IA": identidades de diseños retirados del
    #selector manual (ver AI_ONLY_FAMILIES).
    'atelier', 'terminal', 'riso', 'vitrina', 'cobre', 'lumen',
)

SKIN_FAMILY_SET =   frozenset(SKIN_FAMILIES)

#=========================================
# ESTILOS DE DISEÑO (entrenamiento de "Diseñar con IA")
#=========================================
#8 familias con sus estilos. Un estilo NO es una piel: es el criterio con el
#que el motor agrupa y ordena pieles (y en el que rota la semilla). Todas
#las pieles del catálogo — viejas y nuevas — declaran el suyo, así ningún
#estilo queda sin presupuesto visual y `catalog` cruza a todas las pieles
#que resuelven bien una vitrina.
STYLE_FAMILIES  =   (
    'minimal', 'editorial', 'bold', 'tech', 'craft', 'retro', 'luxury', 'catalog',
)

STYLE_LABELS    =   {
    'minimal':      'Minimalistas y limpios',
    'editorial':    'Editoriales y de revista',
    'bold':         'Atrevidos y expresivos',
    'tech':         'Modernos y tecnológicos',
    'craft':        'Cálidos y artesanales',
    'retro':        'Retro y nostálgicos',
    'luxury':       'Lujo y premium',
    'catalog':      'Ideales para catálogos',
}


def _p(primary, secondary, accent, bg, surface, text, muted, border):
    return {
        'primary': primary, 'secondary': secondary, 'accent': accent,
        'bg': bg, 'surface': surface, 'text': text, 'muted': muted,
        'border': border, 'success': '#15803d', 'danger': '#b91c1c',
    }


def _dark(p):
    """Variante oscura de una paleta: fondo/superficie tintados por el
    primary y texto claro. Conserva acento y semánticos."""
    return {
        'primary': p['primary'], 'secondary': p['secondary'], 'accent': p['accent'],
        'bg': '#0b0d12', 'surface': '#151922', 'text': '#f4f6fa',
        'muted': '#a8b0c0', 'border': '#2a3140',
        'success': '#22c55e', 'danger': '#f87171',
    }


#=========================================
# FAMILIAS
#=========================================
#'variants' declara las dos variantes concretas con su label y (opcional)
#paleta propia; 'dark' = derivar la paleta oscura de la clara.
_FAMILIES   =   {
    'glass': {
        'label': 'Vidrio',
        'variants': (
            {'name': 'frost', 'label': 'Vidrio escarcha'},
            {'name': 'noir', 'label': 'Vidrio nocturno', 'palette': _dark(_p('#334155', '#1e293b', '#6366f1', '', '', '', '', ''))},
        ),
        'palette': _p('#334155', '#1e293b', '#6366f1', '#f4f7fc', '#ffffff', '#0f172a', '#56617a', '#dbe3f0'),
        'containers': {'radius': 'lg', 'shadow': 'deep', 'border': 'thin', 'density': 'comfortable', 'surface': 'glass'},
        'buttons': {'shape': 'rounded', 'style': 'gradient', 'size': 'md'},
        'background': {'type': 'mesh', 'overlay': 'soft'},
        'motion': {'reveal': 'fade', 'hover': 'glow', 'intensity': 'subtle'},
        'typography': {'pair': 'grotesk-clean', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'asym', 'hero': 'split', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'lg'},
        'rubros': ('tecnologia', 'servicios_profesionales', 'turismo', 'otro'),
        'tones': ('moderno', 'serio'),
        'accents': ('#6366f1', '#0ea5e9', '#8b5cf6'),
    },
    'editorial': {
        'label': 'Editorial',
        'variants': (
            {'name': 'ink', 'label': 'Editorial tinta'},
            {'name': 'paper', 'label': 'Editorial papel', 'palette': _p('#1f2937', '#374151', '#b45309', '#f7f4ec', '#fffdf7', '#141414', '#5f5b52', '#e2dccd')},
        ),
        'palette': _p('#111827', '#374151', '#b45309', '#faf8f3', '#ffffff', '#111111', '#5f5b52', '#e3ded2'),
        'containers': {'radius': 'sm', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-editorial', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'editorial', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
        'rubros': ('arte', 'indumentaria', 'gastronomia', 'otro', 'comercio'),
        'tones': ('serio', 'calido'),
        'style': 'editorial',
        'accents': ('#b45309', '#7c3aed', '#1f2937'),
    },
    'brutal': {
        'label': 'Brutal',
        'variants': (
            {'name': 'concrete', 'label': 'Brutal hormigón'},
            {'name': 'acid', 'label': 'Brutal ácido', 'palette': _p('#111111', '#000000', '#d9f99d', '#0a0a0a', '#141414', '#fafafa', '#b4b4b4', '#333333')},
        ),
        'palette': _p('#111111', '#000000', '#facc15', '#ffffff', '#f5f5f5', '#0a0a0a', '#4d4d4d', '#111111'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'bold', 'density': 'compact', 'surface': 'outlined'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'lg'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'bold'},
        'typography': {'pair': 'brutal', 'scale': 'editorial'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'cinema', 'gutter': 'sm', 'measure': 'wide', 'radiusScale': 'none'},
        'rubros': ('construccion', 'arte', 'indumentaria', 'tecnologia'),
        'tones': ('audaz',),
        'accents': ('#facc15', '#ff4d00', '#111111'),
    },
    'soft': {
        'label': 'Suave',
        'variants': (
            {'name': 'blush', 'label': 'Suave rosado'},
            {'name': 'dusk', 'label': 'Suave ocaso', 'palette': _dark(_p('#9d174d', '#831843', '#f472b6', '', '', '', '', ''))},
        ),
        'palette': _p('#9d174d', '#be185d', '#f472b6', '#fdf4f7', '#ffffff', '#3b1524', '#7a5566', '#f3dbe4'),
        'containers': {'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'spacious', 'surface': 'elevated'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'gradient', 'overlay': 'none'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'soft-round', 'scale': 'balanced'},
        'layout': {'density': 'spacious', 'grid': 'split', 'hero': 'centered', 'gutter': 'lg', 'measure': 'normal', 'radiusScale': 'xl'},
        'rubros': ('salud', 'belleza', 'mascotas', 'educacion'),
        'tones': ('calido', 'moderno'),
        'style': 'minimal',
        'accents': ('#f472b6', '#fb7185', '#a78bfa'),
    },
    'tech': {
        'label': 'Técnica',
        'variants': (
            {'name': 'neon', 'label': 'Técnica neón'},
            {'name': 'void', 'label': 'Técnica vacío'},
        ),
        'palette': _p('#0e7490', '#155e75', '#22d3ee', '#f2f9fc', '#ffffff', '#0b1220', '#556170', '#d3e6ee'),
        'containers': {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'compact', 'surface': 'outlined'},
        'buttons': {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background': {'type': 'pattern', 'overlay': 'soft'},
        'motion': {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'medium'},
        'typography': {'pair': 'technical', 'scale': 'balanced'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'split', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'sm'},
        'rubros': ('tecnologia', 'construccion', 'servicios_profesionales'),
        'tones': ('moderno', 'audaz'),
        'accents': ('#22d3ee', '#6366f1', '#10b981'),
    },
    'warm': {
        'label': 'Cálida',
        'variants': (
            {'name': 'clay', 'label': 'Cálida arcilla'},
            {'name': 'ember', 'label': 'Cálida brasa', 'palette': _dark(_p('#9a3412', '#7c2d12', '#f97316', '', '', '', '', ''))},
        ),
        'palette': _p('#9a3412', '#7c2d12', '#f97316', '#fdf6ee', '#fffdf8', '#241a12', '#7a6a58', '#e9dccb'),
        'containers': {'radius': 'lg', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'warm-serif', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'asym', 'hero': 'editorial', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'lg'},
        'rubros': ('gastronomia', 'mascotas', 'belleza', 'comercio'),
        'tones': ('calido',),
        'accents': ('#f97316', '#b45309', '#c2410c'),
    },
    'luxury': {
        'label': 'Lujo',
        'variants': (
            {'name': 'noir', 'label': 'Lujo negro', 'palette': _p('#c8a24a', '#a8842f', '#e5c477', '#0c0b09', '#15130f', '#f7f2e6', '#b3a98f', '#332e24')},
            {'name': 'gilt', 'label': 'Lujo dorado'},
        ),
        'palette': _p('#8a6d1f', '#6d5415', '#b8912f', '#fbf8f0', '#ffffff', '#1a1710', '#6f6550', '#e6ddc8'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-luxe', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'cinema', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
        'rubros': ('belleza', 'indumentaria', 'gastronomia', 'arte'),
        'tones': ('serio', 'calido'),
        'style': 'luxury',
        'accents': ('#b8912f', '#c8a24a', '#7c2d12'),
    },
    'kinetic': {
        'label': 'Cinética',
        'variants': (
            {'name': 'flash', 'label': 'Cinética flash'},
            {'name': 'dusk', 'label': 'Cinética ocaso', 'palette': _dark(_p('#4338ca', '#3730a3', '#818cf8', '', '', '', '', ''))},
        ),
        'palette': _p('#1d4ed8', '#1e40af', '#2563eb', '#f5f7ff', '#ffffff', '#0b1020', '#556070', '#dbe2f5'),
        'containers': {'radius': 'sm', 'shadow': 'medium', 'border': 'bold', 'density': 'compact', 'surface': 'elevated'},
        'buttons': {'shape': 'rounded', 'style': 'gradient', 'size': 'lg'},
        'background': {'type': 'gradient', 'overlay': 'soft'},
        'motion': {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'bold'},
        'typography': {'pair': 'display-heavy', 'scale': 'editorial'},
        'layout': {'density': 'compact', 'grid': 'bento', 'hero': 'cinema', 'gutter': 'sm', 'measure': 'wide', 'radiusScale': 'sm'},
        'rubros': ('tecnologia', 'comercio', 'turismo', 'educacion'),
        'tones': ('audaz', 'moderno'),
        'style': 'tech',
        'accents': ('#2563eb', '#e11d48', '#7c3aed'),
    },
    'paper': {
        'label': 'Papel',
        'variants': (
            {'name': 'kraft', 'label': 'Papel kraft'},
            {'name': 'ink', 'label': 'Papel tinta', 'palette': _p('#292524', '#44403c', '#a16207', '#f2ede3', '#fbf8f1', '#1c1917', '#5c564e', '#ddd4c4')},
        ),
        'palette': _p('#44403c', '#292524', '#a16207', '#f6f2e8', '#fffdf8', '#1c1917', '#615a51', '#e0d8c8'),
        'containers': {'radius': 'sm', 'shadow': 'none', 'border': 'thin', 'density': 'comfortable', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'pattern', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-book', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'editorial', 'hero': 'editorial', 'gutter': 'md', 'measure': 'narrow', 'radiusScale': 'sm'},
        'rubros': ('educacion', 'gastronomia', 'arte', 'otro'),
        'tones': ('calido', 'serio'),
        'style': 'craft',
        'accents': ('#a16207', '#0f766e', '#7c2d12'),
    },
    'neon': {
        'label': 'Neón',
        'variants': (
            {'name': 'pulse', 'label': 'Neón pulso'},
            {'name': 'night', 'label': 'Neón noche', 'palette': _p('#f0abfc', '#e879f9', '#a3e635', '#08080c', '#12121a', '#f7f7fb', '#a5a5b4', '#26263a')},
        ),
        'palette': _p('#7e22ce', '#6b21a8', '#c026d3', '#0d0716', '#1a0f26', '#f9f5ff', '#b8a6c9', '#2f1b42'),
        'containers': {'radius': 'lg', 'shadow': 'deep', 'border': 'thin', 'density': 'compact', 'surface': 'glass'},
        'buttons': {'shape': 'pill', 'style': 'gradient', 'size': 'lg'},
        'background': {'type': 'mesh', 'overlay': 'strong'},
        'motion': {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'bold'},
        'typography': {'pair': 'display-condensed', 'scale': 'editorial'},
        'layout': {'density': 'compact', 'grid': 'bento', 'hero': 'cinema', 'gutter': 'sm', 'measure': 'normal', 'radiusScale': 'lg'},
        'rubros': ('comercio', 'tecnologia', 'arte', 'indumentaria'),
        'tones': ('audaz', 'moderno'),
        'style': 'retro',
        'accents': ('#c026d3', '#a3e635', '#22d3ee'),
    },
    'minimal': {
        'label': 'Minimal',
        'variants': (
            {'name': 'chalk', 'label': 'Minimal tiza'},
            {'name': 'slate', 'label': 'Minimal pizarra', 'palette': _dark(_p('#334155', '#1e293b', '#64748b', '', '', '', '', ''))},
        ),
        'palette': _p('#1f2937', '#374151', '#4b5563', '#fbfbfb', '#ffffff', '#111827', '#5b6470', '#e4e6ea'),
        'containers': {'radius': 'sm', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'ghost', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'modern-sans', 'scale': 'balanced'},
        'layout': {'density': 'spacious', 'grid': '12', 'hero': 'centered', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'sm'},
        'rubros': ('servicios_profesionales', 'tecnologia', 'arte', 'salud'),
        'tones': ('serio', 'moderno'),
        'style': 'minimal',
        'accents': ('#4b5563', '#111827', '#0f766e'),
    },
    'organic': {
        'label': 'Orgánica',
        'variants': (
            {'name': 'sage', 'label': 'Orgánica salvia'},
            {'name': 'moss', 'label': 'Orgánica musgo', 'palette': _dark(_p('#3f6212', '#365314', '#a3b18a', '', '', '', '', ''))},
        ),
        'palette': _p('#3f6212', '#365314', '#84cc16', '#f7faf1', '#ffffff', '#1b2410', '#5f6b4e', '#dfe6d1'),
        'containers': {'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'humanist', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'split', 'hero': 'split', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'xl'},
        'rubros': ('salud', 'gastronomia', 'mascotas', 'turismo'),
        'tones': ('calido', 'serio'),
        'style': 'craft',
        'accents': ('#84cc16', '#0d9488', '#a16207'),
    },
    'retro': {
        'label': 'Retro',
        'variants': (
            {'name': 'sun', 'label': 'Retro sol'},
            {'name': 'teal', 'label': 'Retro verde agua', 'palette': _p('#0f766e', '#115e59', '#f59e0b', '#faf6ec', '#fffdf6', '#1c1a14', '#5f5a4b', '#e4dcc7')},
        ),
        'palette': _p('#c2410c', '#9a3412', '#f59e0b', '#fdf5e8', '#fffdf6', '#241a10', '#6f6250', '#e9dcc4'),
        'containers': {'radius': 'md', 'shadow': 'medium', 'border': 'bold', 'density': 'comfortable', 'surface': 'flat'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'pattern', 'overlay': 'soft'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'medium'},
        'typography': {'pair': 'retro-display', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'bento', 'hero': 'centered', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'md'},
        'rubros': ('gastronomia', 'comercio', 'arte', 'mascotas'),
        'tones': ('calido', 'audaz'),
        'style': 'retro',
        'accents': ('#f59e0b', '#c2410c', '#0f766e'),
    },
    'corporate': {
        'label': 'Corporativa',
        'variants': (
            {'name': 'blue', 'label': 'Corporativa azul'},
            {'name': 'steel', 'label': 'Corporativa acero', 'palette': _p('#1e3a8a', '#1e40af', '#3b82f6', '#f4f7fc', '#ffffff', '#0f172a', '#556070', '#d8e0ee')},
        ),
        'palette': _p('#1e40af', '#1d4ed8', '#3b82f6', '#f6f8fc', '#ffffff', '#0f172a', '#556070', '#dbe2ee'),
        'containers': {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'classic-serif', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': '12', 'hero': 'split', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'md'},
        'rubros': ('servicios_profesionales', 'tecnologia', 'educacion', 'salud'),
        'tones': ('serio', 'moderno'),
        'style': 'catalog',
        'accents': ('#3b82f6', '#1e40af', '#0f766e'),
    },
    'playful': {
        'label': 'Lúdica',
        'variants': (
            {'name': 'candy', 'label': 'Lúdica caramelo'},
            {'name': 'pop', 'label': 'Lúdica pop', 'palette': _p('#db2777', '#be185d', '#facc15', '#fff8f0', '#ffffff', '#2a1620', '#6f5a64', '#f2dbe4')},
        ),
        'palette': _p('#2563eb', '#1d4ed8', '#f59e0b', '#fffdf5', '#ffffff', '#1a1a2e', '#5f5a70', '#e8e2d2'),
        'containers': {'radius': 'xl', 'shadow': 'medium', 'border': 'bold', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'lg'},
        'background': {'type': 'gradient', 'overlay': 'none'},
        'motion': {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'medium'},
        'typography': {'pair': 'friendly', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'bento', 'hero': 'centered', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'xl'},
        'rubros': ('mascotas', 'educacion', 'comercio', 'gastronomia'),
        'tones': ('calido', 'audaz'),
        'style': 'bold',
        'accents': ('#f59e0b', '#db2777', '#22c55e'),
    },
    'mono': {
        'label': 'Monocroma',
        'variants': (
            {'name': 'grey', 'label': 'Monocroma gris'},
            {'name': 'black', 'label': 'Monocroma negra', 'palette': _p('#d4d4d4', '#a3a3a3', '#e5e5e5', '#0a0a0a', '#141414', '#fafafa', '#b0b0b0', '#2e2e2e')},
        ),
        'palette': _p('#171717', '#404040', '#525252', '#fafafa', '#ffffff', '#0a0a0a', '#565656', '#e0e0e0'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'compact', 'surface': 'outlined'},
        'buttons': {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'none', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'display-mono', 'scale': 'balanced'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'split', 'gutter': 'sm', 'measure': 'normal', 'radiusScale': 'none'},
        'rubros': ('tecnologia', 'arte', 'servicios_profesionales', 'indumentaria'),
        'tones': ('serio', 'audaz'),
        'style': 'minimal',
        'accents': ('#525252', '#0a0a0a', '#404040'),
    },
    'gradient': {
        'label': 'Degradada',
        'variants': (
            {'name': 'aurora', 'label': 'Degradada aurora'},
            {'name': 'plum', 'label': 'Degradada ciruela', 'palette': _p('#7c3aed', '#6d28d9', '#f472b6', '#0d0718', '#1a1028', '#f9f5ff', '#b3a4c6', '#2e1f45')},
        ),
        'palette': _p('#6d28d9', '#5b21b6', '#ec4899', '#f8f5ff', '#ffffff', '#170f26', '#5e5273', '#e4dcf3'),
        'containers': {'radius': 'xl', 'shadow': 'deep', 'border': 'none', 'density': 'comfortable', 'surface': 'glass'},
        'buttons': {'shape': 'pill', 'style': 'gradient', 'size': 'lg'},
        'background': {'type': 'mesh', 'overlay': 'soft'},
        'motion': {'reveal': 'rise', 'hover': 'glow', 'intensity': 'medium'},
        'typography': {'pair': 'editorial-display', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'asym', 'hero': 'cinema', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'xl'},
        'rubros': ('belleza', 'tecnologia', 'indumentaria', 'turismo'),
        'tones': ('moderno', 'audaz'),
        'style': 'tech',
        'accents': ('#ec4899', '#8b5cf6', '#22d3ee'),
    },
    'cinematic': {
        'label': 'Cinemática',
        'variants': (
            {'name': 'amber', 'label': 'Cinemática ámbar'},
            {'name': 'noir', 'label': 'Cinemática negra', 'palette': _p('#f59e0b', '#b45309', '#fbbf24', '#08090b', '#121418', '#f5f3ef', '#a8a49c', '#2a2c31')},
        ),
        'palette': _p('#b45309', '#92400e', '#f59e0b', '#12100c', '#1c1913', '#f7f3ea', '#b8ad9b', '#332e26'),
        'containers': {'radius': 'sm', 'shadow': 'deep', 'border': 'none', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'lg'},
        'background': {'type': 'mesh', 'value': 'radial-gradient(70% 60% at 78% 8%, #1b2436 0%, #0a0d12 62%), radial-gradient(50% 45% at 12% 92%, #2a2114 0%, #0a0d12 58%)', 'overlay': 'strong'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'medium'},
        'typography': {'pair': 'display-serif', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'cinema', 'gutter': 'lg', 'measure': 'wide', 'radiusScale': 'sm'},
        'rubros': ('turismo', 'gastronomia', 'arte', 'belleza'),
        'tones': ('serio', 'calido'),
        'style': 'luxury',
        'accents': ('#f59e0b', '#e11d48', '#0ea5e9'),
    },
    #=====================================
    # v5 — ESTILOS DEL ENTRENAMIENTO
    #=====================================
    #Minimalismo suizo (International Style) + Swiss Grid: grilla estricta,
    #sans geométrica, negro sobre blanco y un acento funcional.
    'swiss': {
        'label': 'Suizo',
        'style': 'minimal',
        'variants': (
            {'name': 'grid', 'label': 'Suizo grilla'},
            {'name': 'ink', 'label': 'Suizo negro', 'palette': _p('#ffffff', '#e5e7eb', '#f5f5f5', '#0a0a0a', '#141414', '#fafafa', '#b4b4b4', '#2e2e2e')},
        ),
        'palette': _p('#111111', '#3f3f46', '#dc2626', '#ffffff', '#ffffff', '#0a0a0a', '#565660', '#e4e4e7'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'compact', 'surface': 'outlined'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'geometric', 'scale': 'balanced'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'split', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
        'rubros': ('servicios_profesionales', 'tecnologia', 'construccion', 'educacion'),
        'tones': ('serio', 'moderno'),
        'accents': ('#dc2626', '#111111', '#1d4ed8'),
    },
    #Magazine Layout + Tipografía protagonista (Type-Driven): la tapa del
    #negocio, titular XL y datos en bloques.
    'magazine': {
        'label': 'Revista',
        'style': 'editorial',
        'variants': (
            {'name': 'cover', 'label': 'Revista tapa'},
            {'name': 'type', 'label': 'Revista tipográfica', 'palette': _p('#111111', '#2b2b2b', '#c2410c', '#ffffff', '#ffffff', '#0a0a0a', '#57534e', '#e7e5e4')},
        ),
        'palette': _p('#1c1917', '#44403c', '#b45309', '#fbf9f6', '#ffffff', '#141414', '#5c5a55', '#e5e0d8'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'comfortable', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'display-heavy', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'editorial', 'hero': 'editorial', 'gutter': 'lg', 'measure': 'wide', 'radiusScale': 'none'},
        'rubros': ('arte', 'indumentaria', 'gastronomia', 'comercio'),
        'tones': ('audaz', 'moderno'),
        'accents': ('#b45309', '#111111', '#7c3aed'),
    },
    #Neobrutalismo + Bold Pop + Cartel: bloques planos, borde grueso y un
    #acento que no se puede ignorar.
    'pop': {
        'label': 'Pop',
        'style': 'bold',
        'variants': (
            {'name': 'candy', 'label': 'Pop caramelo'},
            {'name': 'poster', 'label': 'Pop afiche', 'palette': _p('#111111', '#000000', '#fb7185', '#fff7ed', '#ffffff', '#111111', '#4b5563', '#111111')},
        ),
        'palette': _p('#111111', '#000000', '#facc15', '#fef9c3', '#ffffff', '#111111', '#525252', '#111111'),
        'containers': {'radius': 'none', 'shadow': 'deep', 'border': 'bold', 'density': 'compact', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'lg'},
        'background': {'type': 'pattern', 'overlay': 'none'},
        'motion': {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'bold'},
        'typography': {'pair': 'display-heavy', 'scale': 'editorial'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'cinema', 'gutter': 'md', 'measure': 'wide', 'radiusScale': 'none'},
        'rubros': ('comercio', 'indumentaria', 'gastronomia', 'educacion'),
        'tones': ('audaz',),
        'accents': ('#facc15', '#fb7185', '#3b82f6'),
    },
    #Futurismo SaaS + Dark Mode Tech + Gradientes Aurora: limpio, oscuro y
    #técnico, con vidrio y luz en vez de ruido.
    'aurora': {
        'label': 'Aurora',
        'style': 'tech',
        'variants': (
            {'name': 'dawn', 'label': 'Aurora amanecer'},
            {'name': 'night', 'label': 'Aurora nocturna', 'palette': _p('#22d3ee', '#38bdf8', '#a78bfa', '#070b16', '#101828', '#f2f7ff', '#a3b1c9', '#1f2a3f')},
        ),
        'palette': _p('#4f46e5', '#4338ca', '#6366f1', '#f5f6ff', '#ffffff', '#0b1020', '#59637a', '#dfe3f5'),
        'containers': {'radius': 'xl', 'shadow': 'deep', 'border': 'thin', 'density': 'comfortable', 'surface': 'glass'},
        'buttons': {'shape': 'pill', 'style': 'gradient', 'size': 'md'},
        'background': {'type': 'mesh', 'overlay': 'soft'},
        'motion': {'reveal': 'rise', 'hover': 'glow', 'intensity': 'medium'},
        'typography': {'pair': 'grotesk-clean', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'split', 'hero': 'centered', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'xl'},
        'rubros': ('tecnologia', 'servicios_profesionales', 'turismo', 'otro'),
        'tones': ('moderno', 'serio'),
        'accents': ('#6366f1', '#22d3ee', '#a78bfa'),
    },
    #Hecho a mano + Tierra y Papel (Kraft): cartón, sellos y tinta; el
    #paquete artesanal del oficio.
    'craft': {
        'label': 'Artesanal',
        'style': 'craft',
        'variants': (
            {'name': 'clay', 'label': 'Artesanal arcilla'},
            {'name': 'kraft', 'label': 'Artesanal kraft', 'palette': _p('#44403c', '#292524', '#a16207', '#f2ebdf', '#fbf7ee', '#1c1917', '#5f594f', '#ddd2bf')},
        ),
        'palette': _p('#8a4b28', '#6f3a1d', '#b45309', '#fbf6ef', '#fffdf8', '#241d16', '#7a6a58', '#e9dcc9'),
        'containers': {'radius': 'lg', 'shadow': 'none', 'border': 'thin', 'density': 'comfortable', 'surface': 'outlined'},
        'buttons': {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'pattern', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-book', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'split', 'hero': 'split', 'gutter': 'lg', 'measure': 'normal', 'radiusScale': 'lg'},
        'rubros': ('gastronomia', 'mascotas', 'belleza', 'comercio'),
        'tones': ('calido',),
        'accents': ('#b45309', '#8a4b28', '#0f766e'),
    },
    #Retro años 70 + Art Déco + Y2K: mostaza, cromo y geometría de época.
    #Dos variantes para que el estilo sirva a una pizzería y a un estudio.
    'nostalgia': {
        'label': 'Nostalgia',
        'style': 'retro',
        'variants': (
            {'name': 'sunset', 'label': 'Nostalgia atardecer'},
            {'name': 'chrome', 'label': 'Nostalgia cromada', 'palette': _p('#0f766e', '#115e59', '#c0c8d4', '#0d1117', '#161c24', '#f1f5f9', '#a5b0c1', '#2b3441')},
        ),
        'palette': _p('#9a3412', '#7c2d12', '#d97706', '#fdf3e3', '#fffaf0', '#271c10', '#74624e', '#ebdcc2'),
        'containers': {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'flat'},
        'buttons': {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'gradient', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'retro-display', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'asym', 'hero': 'centered', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'md'},
        'rubros': ('gastronomia', 'comercio', 'arte', 'mascotas'),
        'tones': ('calido', 'audaz'),
        'accents': ('#d97706', '#9a3412', '#0f766e'),
    },
    #Monocromo Premium + Boutique Elegante + Galería de arte: aire extremo,
    #serif y ningún adorno de más.
    'prestige': {
        'label': 'Prestigio',
        'style': 'luxury',
        'variants': (
            {'name': 'ivory', 'label': 'Prestigio marfil'},
            {'name': 'charcoal', 'label': 'Prestigio grafito', 'palette': _p('#e5e2da', '#cfcbc1', '#b8912f', '#0d0d0d', '#161616', '#f7f5f0', '#b0aaa0', '#2c2c2c')},
        ),
        'palette': _p('#141414', '#2f2f2f', '#a8842f', '#faf8f4', '#ffffff', '#111111', '#6b675f', '#e5e0d5'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-luxe', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'cinema', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
        'rubros': ('arte', 'belleza', 'indumentaria', 'servicios_profesionales'),
        'tones': ('serio', 'calido'),
        'accents': ('#a8842f', '#141414', '#7c2d12'),
    },
    #Showroom visual + Colección por temporadas: la imagen manda y la
    #cardiografía del catálogo se lee sola.
    'showcase': {
        'label': 'Showroom',
        'style': 'catalog',
        'variants': (
            {'name': 'room', 'label': 'Showroom claro'},
            {'name': 'gallery', 'label': 'Showroom galería', 'palette': _p('#1f2937', '#111827', '#78716c', '#fbfbfa', '#ffffff', '#0f172a', '#5f6672', '#e6e8ea')},
        ),
        'palette': _p('#334155', '#1e293b', '#0f766e', '#f8fafc', '#ffffff', '#0f172a', '#5b6678', '#e2e8f0'),
        'containers': {'radius': 'sm', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'modern-sans', 'scale': 'balanced'},
        'layout': {'density': 'comfortable', 'grid': 'bento', 'hero': 'cinema', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'sm'},
        'rubros': ('comercio', 'indumentaria', 'tecnologia', 'arte'),
        'tones': ('moderno', 'serio'),
        'accents': ('#0f766e', '#334155', '#1d4ed8'),
    },
    #===== EXCLUSIVAS DE LA IA (retiradas del diseño manual) =====
    #Identidades del catálogo viejo que el dueño ya no puede elegir a mano
    #(TEMPLATE_RETIRED_MAP): el motor las sigue proponiendo como pieles.
    #Nunca aparecen en el selector del Studio.
    'atelier': {
        'label': 'Atelier',
        'style': 'luxury',
        'variants': (
            {'name': 'lino', 'label': 'Atelier lino'},
            {'name': 'tinta', 'label': 'Atelier tinta', 'palette': _dark(_p('#1c1917', '#292524', '#b91c1c', '', '', '', '', ''))},
        ),
        'palette': _p('#1c1917', '#44403c', '#b91c1c', '#faf7f2', '#fffdf9', '#171412', '#6b625a', '#e6ded2'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
        'typography': {'pair': 'serif-luxe', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'editorial', 'gutter': 'lg', 'measure': 'narrow', 'radiusScale': 'none'},
        'rubros': ('indumentaria', 'arte', 'belleza', 'comercio'),
        'tones': ('serio', 'calido'),
        'accents': ('#b91c1c', '#1c1917', '#a16207'),
    },
    'terminal': {
        'label': 'Terminal',
        'style': 'tech',
        'variants': (
            {'name': 'fosforo', 'label': 'Terminal fósforo'},
            {'name': 'ambar', 'label': 'Terminal ámbar', 'palette': _p('#0b0d0c', '#151a17', '#f59e0b', '#080a09', '#101512', '#eef3ef', '#9fb3a6', '#25312b')},
        ),
        'palette': _p('#0b0d0c', '#151a17', '#22d3ee', '#080a09', '#101512', '#eef3ef', '#9fb3a6', '#25312b'),
        'containers': {'radius': 'none', 'shadow': 'none', 'border': 'bold', 'density': 'compact', 'surface': 'outlined'},
        'buttons': {'shape': 'square', 'style': 'outline', 'size': 'sm'},
        'background': {'type': 'gradient', 'value': 'linear-gradient(180deg, #0c1210 0%, #080a09 60%, #050706 100%)', 'overlay': 'strong'},
        'motion': {'reveal': 'none', 'hover': 'glow', 'intensity': 'subtle'},
        'typography': {'pair': 'mono-tech', 'scale': 'compact'},
        'layout': {'density': 'compact', 'grid': '12', 'hero': 'split', 'gutter': 'sm', 'measure': 'wide', 'radiusScale': 'none'},
        'rubros': ('tecnologia', 'servicios_profesionales', 'construccion', 'otro'),
        'tones': ('serio', 'moderno'),
        'accents': ('#22d3ee', '#84cc16', '#f59e0b'),
    },
    'riso': {
        'label': 'Riso',
        'style': 'retro',
        'variants': (
            {'name': 'duo', 'label': 'Riso duotono'},
            {'name': 'noche', 'label': 'Riso nocturno', 'palette': _dark(_p('#111827', '#1f2937', '#f43f5e', '', '', '', '', ''))},
        ),
        'palette': _p('#1f2937', '#374151', '#e11d48', '#fdf6ec', '#fffdf8', '#181410', '#6b6358', '#e8ddcb'),
        'containers': {'radius': 'sm', 'shadow': 'none', 'border': 'bold', 'density': 'comfortable', 'surface': 'flat'},
        'buttons': {'shape': 'square', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'stagger', 'hover': 'none', 'intensity': 'medium'},
        'typography': {'pair': 'retro-display', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'bento', 'hero': 'centered', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'sm'},
        'rubros': ('arte', 'comercio', 'gastronomia', 'mascotas'),
        'tones': ('calido', 'audaz'),
        'accents': ('#e11d48', '#2563eb', '#16a34a'),
    },
    'vitrina': {
        'label': 'Vitrina',
        'style': 'catalog',
        'variants': (
            {'name': 'dia', 'label': 'Vitrina de día'},
            {'name': 'noche', 'label': 'Vitrina nocturna', 'palette': _dark(_p('#334155', '#1e293b', '#0ea5e9', '', '', '', '', ''))},
        ),
        'palette': _p('#334155', '#1e293b', '#0f766e', '#f7f9fb', '#ffffff', '#0f172a', '#5b6678', '#dfe6ee'),
        'containers': {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'compact', 'surface': 'elevated'},
        'buttons': {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'solid', 'overlay': 'none'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'modern-sans', 'scale': 'balanced'},
        'layout': {'density': 'compact', 'grid': 'bento', 'hero': 'split', 'gutter': 'md', 'measure': 'normal', 'radiusScale': 'md'},
        'rubros': ('comercio', 'indumentaria', 'tecnologia', 'mascotas'),
        'tones': ('moderno', 'calido'),
        'accents': ('#0f766e', '#1d4ed8', '#b45309'),
    },
    'cobre': {
        'label': 'Cobre',
        'style': 'craft',
        'variants': (
            {'name': 'pulido', 'label': 'Cobre pulido'},
            {'name': 'patina', 'label': 'Cobre pátina', 'palette': _p('#2f2a24', '#3f372e', '#0f766e', '#f6f1e8', '#fffaf1', '#1b1712', '#6a6055', '#e5d9c6')},
        ),
        'palette': _p('#2f2a24', '#3f372e', '#b45309', '#f8f2e8', '#fffaf2', '#1b1712', '#6a6055', '#e6d8c4'),
        'containers': {'radius': 'sm', 'shadow': 'medium', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'buttons': {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background': {'type': 'gradient', 'value': 'linear-gradient(160deg, #f8f2e8 0%, #f1e3cf 55%, #e9d6bd 100%)', 'overlay': 'none'},
        'motion': {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
        'typography': {'pair': 'warm-serif', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'editorial', 'hero': 'split', 'gutter': 'lg', 'measure': 'normal', 'radiusScale': 'sm'},
        'rubros': ('gastronomia', 'construccion', 'arte', 'comercio'),
        'tones': ('calido', 'serio'),
        'accents': ('#b45309', '#92400e', '#0f766e'),
    },
    'lumen': {
        'label': 'Lumen',
        'style': 'editorial',
        'variants': (
            {'name': 'cine', 'label': 'Lumen cinematográfico'},
            {'name': 'sala', 'label': 'Lumen de sala', 'palette': _p('#0c0f14', '#151b24', '#e2b04a', '#0a0d12', '#121821', '#f3f6fa', '#a4b0c0', '#232c39')},
        ),
        'palette': _p('#0c0f14', '#151b24', '#e2b04a', '#0a0d12', '#121821', '#f3f6fa', '#a4b0c0', '#232c39'),
        'containers': {'radius': 'sm', 'shadow': 'deep', 'border': 'thin', 'density': 'comfortable', 'surface': 'glass'},
        'buttons': {'shape': 'square', 'style': 'ghost', 'size': 'lg'},
        'background': {'type': 'mesh', 'value': 'radial-gradient(70% 60% at 78% 8%, #1b2436 0%, #0a0d12 62%), radial-gradient(50% 45% at 12% 92%, #2a2114 0%, #0a0d12 58%)', 'overlay': 'strong'},
        'motion': {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'medium'},
        'typography': {'pair': 'editorial-display', 'scale': 'editorial'},
        'layout': {'density': 'comfortable', 'grid': 'asym', 'hero': 'cinema', 'gutter': 'lg', 'measure': 'wide', 'radiusScale': 'sm'},
        'rubros': ('turismo', 'gastronomia', 'arte', 'belleza'),
        'tones': ('audaz', 'serio'),
        'accents': ('#e2b04a', '#f3f4f6', '#38bdf8'),
    },
}

#Pieles que el diseño manual ya no ofrece: solo las propone el motor de IA.
AI_ONLY_FAMILIES    =   frozenset({'atelier', 'terminal', 'riso', 'vitrina', 'cobre', 'lumen'})


def _build_skins():
    """
    Aplana las familias a SKINS: {id: piel completa}. El id es
    "<family>-<variant>" y SIEMPRE sale de acá (nunca se inventa).
    """
    out     =   {}
    for family in SKIN_FAMILIES:
        data    =   _FAMILIES[family]
        for variant in data['variants']:
            skin_id     =   f'{family}-{variant["name"]}'
            palette     =   variant.get('palette') or data['palette']
            out[skin_id] =   {
                'id'            :   skin_id,
                'family'        :   family,
                'label'         :   variant['label'],
                'palette'       :   dict(palette),
                'containers'    :   dict(data['containers']),
                'buttons'       :   dict(data['buttons']),
                'background'    :   dict(data['background']),
                'motion'        :   dict(data['motion']),
                'typography'    :   dict(data['typography']),
                'layout'        :   dict(data['layout']),
                'rubros'        :   tuple(data['rubros']),
                'tones'         :   tuple(data['tones']),
                'accents'       :   tuple(data['accents']),
                #Estilo del entrenamiento de diseño: lo consume el motor, no
                #viaja en site_theme (ahí `skin` es {id, family}).
                'style'         :   data.get('style') or 'catalog',
            }
    return out


SKINS       =   _build_skins()
SKIN_IDS    =   tuple(SKINS)

#Familias del catálogo (para validar skin.family en site_theme).
SKIN_FAMILY_OF  =   {skin_id: skin['family'] for skin_id, skin in SKINS.items()}


#=========================================
# PUBLICACIÓN DEL LOOK (estilo del Studio + par tipográfico)
#=========================================
#site_theme.style.id es el id de un preset del Studio (frontend/src/studio/
#presets/catalog.js). El motor NO inventa presets: cada familia apunta al
#preset más cercano. Con eso una tienda Básica —que solo persiste style.id +
#styleColors— recibe igual el aire visual que eligió el motor.
SKIN_STYLE_PRESET   =   {
    'minimal':      'editorial-minima',
    'swiss':        'suizo-editorial',
    'corporate':    'corporativo',
    'tech':         'neon-tech',
    'glass':        'vidrio-nocturno',
    'neon':         'cobalto-nocturno',
    'gradient':     'aurora-degradada',
    'kinetic':      'retail-vibrante',
    'showcase':     'bento',
    'editorial':    'gourmet-calido',
    'magazine':     'terracota',
    'paper':        'papel-riso',
    'nostalgia':    'consola-retro',
    'retro':        'consola-retro',
    'brutal':       'neo-brutalista',
    'pop':          'urbano-sticker',
    'playful':      'kids-ludico',
    'warm':         'gourmet-calido',
    'craft':        'terracota',
    'organic':      'pastel-suave',
    'soft':         'belleza-rosa',
    'luxury':       'lujo-serif',
    'prestige':     'lujo-serif',
    'aurora':       'aurora-degradada',
    'cinematic':    'vidrio-nocturno',
    'mono':         'monocromo',
    #Exclusivas de la IA: el preset solo publica el aire visual (style.id);
    #la identidad completa la lleva la piel.
    'atelier':      'lujo-serif',
    'terminal':     'neon-tech',
    'riso':         'papel-riso',
    'vitrina':      'retail-vibrante',
    'cobre':        'terracota',
    'lumen':        'cobalto-nocturno',
}
#Plantilla de cada preset del Studio: fuente ÚNICA (la consumen
#site_theme._style_preset_templates y el motor). El style.id solo se guarda
#si su plantilla entra en el nivel del plan vigente. Los presets de familia
#se mapean al diseño del catálogo que les da su aire: luxury -> boutique,
#craft -> alimentos, bold -> seguridad.
STYLE_PRESET_TEMPLATES  =   {
    'editorial-minima'  :   'raiz',
    'vidrio-nocturno'   :   'circuito',
    'bento'             :   'trama',
    'neo-brutalista'    :   'seguridad',
    'lujo-serif'        :   'boutique',
    'pastel-suave'      :   'raiz',
    'neon-tech'         :   'circuito',
    'terracota'         :   'alimentos',
    'monocromo'         :   'raiz',
    'retail-vibrante'   :   'trama',
    'aurora-degradada'  :   'trama',
    'papel-riso'        :   'trama',
    'corporativo'       :   'raiz',
    'gourmet-calido'    :   'alimentos',
    'belleza-rosa'      :   'boutique',
    'kids-ludico'       :   'trama',
    'urbano-sticker'    :   'seguridad',
    'consola-retro'     :   'circuito',
    'denim-urbano'      :   'trama',
    'atelier-moda'      :   'boutique',
    'suizo-editorial'   :   'raiz',
    'cobalto-nocturno'  :   'circuito',
}
#Par tipográfico por familia (ids de ai_design_typography.TYPE_PAIRS). Es el
#par con el que arranca el motor para esa piel; la elección final la cierra
#el par de la propuesta (nunca uno incompatible con el estilo).
SKIN_TYPE_PAIR  =   {
    'minimal':      'grotesk-clean',
    'swiss':        'grotesk-clean',
    'corporate':    'grotesk-clean',
    'tech':         'grotesk-clean',
    'glass':        'grotesk-clean',
    'neon':         'grotesk-clean',
    'gradient':     'grotesk-clean',
    'kinetic':      'grotesk-clean',
    'showcase':     'grotesk-clean',
    'editorial':    'serif-editorial',
    'magazine':     'serif-editorial',
    'paper':        'serif-editorial',
    'nostalgia':    'serif-editorial',
    'retro':        'serif-editorial',
    'brutal':       'grotesk-clean',
    'pop':          'grotesk-clean',
    'playful':      'grotesk-clean',
    'warm':         'serif-editorial',
    'craft':        'serif-editorial',
    'organic':      'serif-editorial',
    'soft':         'serif-editorial',
    'luxury':       'serif-editorial',
    'prestige':     'serif-editorial',
    'aurora':       'serif-editorial',
    'cinematic':    'serif-editorial',
    'mono':         'grotesk-clean',
    #Exclusivas de la IA.
    'atelier':      'serif-luxe',
    'terminal':     'mono-tech',
    'riso':         'retro-display',
    'vitrina':      'modern-sans',
    'cobre':        'warm-serif',
    'lumen':        'editorial-display',
}
#Variante de layout alternativa por piel: lo que hace que dos propuestas de
#la misma familia no compartan composición. Solo valores que existen en el
#contrato (site_theme.layout) y que el catálogo de variantes de bloque
#reconoce.
SKIN_LAYOUT_ALT =   {
    'minimal':      {'hero': 'centered', 'grid': 'asym'},
    'swiss':        {'hero': 'editorial', 'grid': 'bento'},
    'corporate':    {'hero': 'split', 'grid': '12'},
    'tech':         {'hero': 'cinema', 'grid': 'bento'},
    'glass':        {'hero': 'split', 'grid': 'asym'},
    'neon':         {'hero': 'cinema', 'grid': 'split'},
    'gradient':     {'hero': 'cinema', 'grid': 'editorial'},
    'kinetic':      {'hero': 'centered', 'grid': 'bento'},
    'showcase':     {'hero': 'cinema', 'grid': 'editorial'},
    'editorial':    {'hero': 'editorial', 'grid': '12'},
    'magazine':     {'hero': 'split', 'grid': 'editorial'},
    'paper':        {'hero': 'centered', 'grid': 'asym'},
    'nostalgia':    {'hero': 'centered', 'grid': 'split'},
    'retro':        {'hero': 'editorial', 'grid': '12'},
    'brutal':       {'hero': 'centered', 'grid': 'split'},
    'pop':          {'hero': 'split', 'grid': 'bento'},
    'playful':      {'hero': 'split', 'grid': 'asym'},
    'warm':         {'hero': 'split', 'grid': '12'},
    'craft':        {'hero': 'editorial', 'grid': 'asym'},
    'organic':      {'hero': 'centered', 'grid': 'bento'},
    'soft':         {'hero': 'centered', 'grid': 'editorial'},
    'luxury':       {'hero': 'cinema', 'grid': '12'},
    'prestige':     {'hero': 'cinema', 'grid': 'asym'},
    'aurora':       {'hero': 'cinema', 'grid': 'split'},
    'cinematic':    {'hero': 'editorial', 'grid': 'bento'},
    'mono':         {'hero': 'editorial', 'grid': '12'},
    #Exclusivas de la IA.
    'atelier':      {'hero': 'split', 'grid': 'editorial'},
    'terminal':     {'hero': 'cinema', 'grid': 'bento'},
    'riso':         {'hero': 'editorial', 'grid': 'asym'},
    'vitrina':      {'hero': 'cinema', 'grid': 'split'},
    'cobre':        {'hero': 'centered', 'grid': 'bento'},
    'lumen':        {'hero': 'editorial', 'grid': 'split'},
}


def skins_for(rubro = None, tone = None):
    """Pieles afines al rubro y/o al tono (sin filtro: el catálogo entero)."""
    return tuple(
        skin_id for skin_id, skin in SKINS.items()
        if (rubro is None or rubro in skin['rubros']) and (tone is None or tone in skin['tones'])
    )


def skin_of(skin_id):
    return SKINS.get(skin_id)


def style_preset_of(skin_id):
    """Preset del Studio que representa la piel (style.id del site_theme)."""
    skin = SKINS.get(skin_id)
    return SKIN_STYLE_PRESET.get(skin['family']) if skin else None


def style_preset_for_plan(skin_id, template, allowed):
    """
    Preset del Studio que representa la piel — SIEMPRE dentro del nivel del
    plan. Un plan Básico solo persiste style.id + styleColors, así que si el
    preset de la familia usa una plantilla de otro nivel el motor elige uno
    admitido (el de la propia plantilla si existe) y la web no pierde el aire.
    """
    allowed     =   tuple(allowed or ())
    preset      =   style_preset_of(skin_id)
    if preset and STYLE_PRESET_TEMPLATES.get(preset) in allowed:
        return preset
    for candidate, candidate_tpl in STYLE_PRESET_TEMPLATES.items():
        if candidate_tpl in allowed and candidate_tpl == template:
            return candidate
    for candidate, candidate_tpl in STYLE_PRESET_TEMPLATES.items():
        if candidate_tpl in allowed:
            return candidate
    return None


def type_pair_of(skin_id):
    """Par tipográfico con el que la piel arranca (luego manda la propuesta)."""
    skin = SKINS.get(skin_id)
    return SKIN_TYPE_PAIR.get(skin['family']) if skin else None
