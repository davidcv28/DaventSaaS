#=========================================
# SKINS — catálogo cerrado de 18 familias composibles (motor v4)
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

SKIN_FAMILIES   =   (
    'glass', 'editorial', 'brutal', 'soft', 'tech', 'warm', 'luxury',
    'kinetic', 'paper', 'neon', 'minimal', 'organic', 'retro', 'corporate',
    'playful', 'mono', 'gradient', 'cinematic',
)

SKIN_FAMILY_SET =   frozenset(SKIN_FAMILIES)


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
        'background': {'type': 'image', 'overlay': 'strong'},
        'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'medium'},
        'typography': {'pair': 'display-serif', 'scale': 'editorial'},
        'layout': {'density': 'spacious', 'grid': 'editorial', 'hero': 'cinema', 'gutter': 'lg', 'measure': 'wide', 'radiusScale': 'sm'},
        'rubros': ('turismo', 'gastronomia', 'arte', 'belleza'),
        'tones': ('serio', 'calido'),
        'accents': ('#f59e0b', '#e11d48', '#0ea5e9'),
    },
}


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
            }
    return out


SKINS       =   _build_skins()
SKIN_IDS    =   tuple(SKINS)

#Familias del catálogo (para validar skin.family en site_theme).
SKIN_FAMILY_OF  =   {skin_id: skin['family'] for skin_id, skin in SKINS.items()}


def skins_for(rubro = None, tone = None):
    """Pieles afines al rubro y/o al tono (sin filtro: el catálogo entero)."""
    return tuple(
        skin_id for skin_id, skin in SKINS.items()
        if (rubro is None or rubro in skin['rubros']) and (tone is None or tone in skin['tones'])
    )


def skin_of(skin_id):
    return SKINS.get(skin_id)
