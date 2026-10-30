#=========================================
# RECETAS DEL MOTOR DE DISEÑO (datos, sin lógica)
#=========================================
#Tabla de conocimiento del motor: qué plantilla y qué look le sientan a
#cada rubro, en qué orden conviene contar la historia según el objetivo
#del dueño, qué variante de bloque rinde mejor y qué bloques necesitan
#datos reales para no quedar vacíos.
#Es solo datos: ai_design.py los interpreta, ai_design_copy.py los usa
#para el texto. Nada de acá llega al cliente sin pasar por
#clean_layout_config y por la whitelist de plantillas del plan.

ENGINE_VERSION              =   'ai-design/8'

TONES                       =   ('calido', 'serio', 'moderno', 'audaz')
DEFAULT_TONE                =   'moderno'

GOALS                       =   ('vender_online', 'mostrar_servicios', 'conseguir_consultas', 'dar_confianza', 'mostrar_trabajos')
DEFAULT_GOAL                =   'mostrar_servicios'

#=========================================
# LOOKS (site_theme parcial, enums del Studio)
#=========================================
#Cada look es un presupuesto de piel: paleta + contenedores + tipografía +
#botones + fondo + movimiento. Los enums son los de STUDIO_ENUMS y los
#colores son hex de 6 dígitos — el frontend sanea igual, pero acá ya salen
#válidos para que el borrador se vea tal cual la propuesta.
LOOKS                       =   {
    'retail': {
        'palette':      {'primary': '#c2410c', 'secondary': '#9a3412', 'accent': '#ea580c', 'bg': '#fdf6f0', 'surface': '#ffffff', 'text': '#1c1917', 'muted': '#78716c', 'border': '#e7ded4'},
        'containers':   {'radius': 'lg', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography':   {'heading': 'figtree', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 800, 'letterSpacing': '-0.01em'},
        'buttons':      {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'gourmet': {
        'palette':      {'primary': '#7c2d12', 'secondary': '#9a3412', 'accent': '#b45309', 'bg': '#faf5ec', 'surface': '#fffdf8', 'text': '#241c14', 'muted': '#7c6f5f', 'border': '#e4d7c3'},
        'containers':   {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'typography':   {'heading': 'bricolage-grotesque', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 700, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'atelier': {
        'palette':      {'primary': '#111827', 'secondary': '#374151', 'accent': '#b91c1c', 'bg': '#f7f6f3', 'surface': '#ffffff', 'text': '#111111', 'muted': '#6b7280', 'border': '#dedbd4'},
        'containers':   {'radius': 'none', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'outlined'},
        'typography':   {'heading': 'manrope', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 700, 'letterSpacing': '-0.03em'},
        'buttons':      {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'rise', 'hover': 'none', 'intensity': 'subtle'},
    },
    'sobrio': {
        'palette':      {'primary': '#1e3a8a', 'secondary': '#1e40af', 'accent': '#2563eb', 'bg': '#f4f6fb', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#d5dbe8'},
        'containers':   {'radius': 'md', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography':   {'heading': 'inter', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 700, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'clinico': {
        'palette':      {'primary': '#0f766e', 'secondary': '#115e59', 'accent': '#0d9488', 'bg': '#f2faf8', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#cfe6e1'},
        'containers':   {'radius': 'xl', 'shadow': 'soft', 'border': 'none', 'density': 'comfortable', 'surface': 'flat'},
        'typography':   {'heading': 'figtree', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 600, 'letterSpacing': '-0.01em'},
        'buttons':      {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'belleza': {
        'palette':      {'primary': '#9d174d', 'secondary': '#831843', 'accent': '#db2777', 'bg': '#fdf3f7', 'surface': '#ffffff', 'text': '#1f1720', 'muted': '#7a6a74', 'border': '#f0d9e4'},
        'containers':   {'radius': 'xl', 'shadow': 'medium', 'border': 'none', 'density': 'spacious', 'surface': 'elevated'},
        'typography':   {'heading': 'manrope', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 700, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'pill', 'style': 'gradient', 'size': 'md'},
        'background':   {'type': 'gradient', 'overlay': 'none'},
        'motion':       {'reveal': 'rise', 'hover': 'glow', 'intensity': 'medium'},
    },
    'obra': {
        'palette':      {'primary': '#334155', 'secondary': '#1f2937', 'accent': '#f59e0b', 'bg': '#f5f6f7', 'surface': '#ffffff', 'text': '#111827', 'muted': '#64748b', 'border': '#d7dbe0'},
        'containers':   {'radius': 'sm', 'shadow': 'medium', 'border': 'bold', 'density': 'comfortable', 'surface': 'outlined'},
        'typography':   {'heading': 'archivo', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 800, 'letterSpacing': '-0.01em'},
        'buttons':      {'shape': 'rounded', 'style': 'solid', 'size': 'lg'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'tech': {
        'palette':      {'primary': '#4f46e5', 'secondary': '#4338ca', 'accent': '#6366f1', 'bg': '#0b1120', 'surface': '#141b2d', 'text': '#e6ebf5', 'muted': '#9aa6bd', 'border': '#26314a'},
        'containers':   {'radius': 'lg', 'shadow': 'deep', 'border': 'thin', 'density': 'comfortable', 'surface': 'glass'},
        'typography':   {'heading': 'inter', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 800, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'rounded', 'style': 'gradient', 'size': 'md'},
        'background':   {'type': 'mesh', 'overlay': 'soft'},
        'motion':       {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'medium'},
    },
    'aula': {
        'palette':      {'primary': '#1d4ed8', 'secondary': '#1e40af', 'accent': '#f59e0b', 'bg': '#f6f8fd', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#d9e1f2'},
        'containers':   {'radius': 'lg', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography':   {'heading': 'figtree', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 700, 'letterSpacing': '-0.01em'},
        'buttons':      {'shape': 'rounded', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'fade', 'hover': 'lift', 'intensity': 'subtle'},
    },
    'viaje': {
        'palette':      {'primary': '#0369a1', 'secondary': '#075985', 'accent': '#f97316', 'bg': '#f2f8fb', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#d3e3ec'},
        'containers':   {'radius': 'xl', 'shadow': 'medium', 'border': 'none', 'density': 'spacious', 'surface': 'elevated'},
        'typography':   {'heading': 'bricolage-grotesque', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 700, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'pill', 'style': 'solid', 'size': 'lg'},
        'background':   {'type': 'image', 'overlay': 'soft'},
        'motion':       {'reveal': 'rise', 'hover': 'lift', 'intensity': 'medium'},
    },
    'patitas': {
        'palette':      {'primary': '#0d9488', 'secondary': '#0f766e', 'accent': '#f59e0b', 'bg': '#f5fbf9', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#d3e8e3'},
        'containers':   {'radius': 'pill', 'shadow': 'soft', 'border': 'none', 'density': 'comfortable', 'surface': 'flat'},
        'typography':   {'heading': 'figtree', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 800, 'letterSpacing': '0em'},
        'buttons':      {'shape': 'pill', 'style': 'solid', 'size': 'lg'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'medium'},
    },
    'galeria': {
        'palette':      {'primary': '#1f2937', 'secondary': '#111827', 'accent': '#b45309', 'bg': '#faf9f7', 'surface': '#ffffff', 'text': '#111111', 'muted': '#6b7280', 'border': '#e3ded6'},
        'containers':   {'radius': 'sm', 'shadow': 'none', 'border': 'thin', 'density': 'spacious', 'surface': 'flat'},
        'typography':   {'heading': 'bricolage-grotesque', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 600, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'square', 'style': 'outline', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'},
    },
    'neutro': {
        'palette':      {'primary': '#4f46e5', 'secondary': '#4338ca', 'accent': '#4f46e5', 'bg': '#eaeef8', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#5b6678', 'border': '#aeb3dc'},
        'containers':   {'radius': 'lg', 'shadow': 'soft', 'border': 'thin', 'density': 'comfortable', 'surface': 'elevated'},
        'typography':   {'heading': 'inter', 'body': 'inter', 'scale': 'balanced', 'weightHeading': 800, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'pill', 'style': 'solid', 'size': 'md'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'},
    },
    #Los dos looks EXCLUSIVOS de IA (solo con has_ai_design). No son un
    #"tema más": son el presupuesto de piel de ai_lumen y ai_pulse, con la
    #energía que el resto de los looks no se permite (vidrio + luz vs.
    #tipografía XL sobre grilla).
    'lumen': {
        'palette':      {'primary': '#a78bfa', 'secondary': '#7c3aed', 'accent': '#a78bfa', 'bg': '#07070c', 'surface': '#12121c', 'text': '#f5f3ff', 'muted': '#a5a3b8', 'border': '#26243a'},
        'containers':   {'radius': 'lg', 'shadow': 'deep', 'border': 'thin', 'density': 'spacious', 'surface': 'glass'},
        'typography':   {'heading': 'bricolage-grotesque', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 600, 'letterSpacing': '-0.02em'},
        'buttons':      {'shape': 'pill', 'style': 'gradient', 'size': 'lg'},
        'background':   {'type': 'mesh', 'overlay': 'soft'},
        'motion':       {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'medium'},
    },
    'pulse': {
        'palette':      {'primary': '#0b0b0b', 'secondary': '#e11d48', 'accent': '#e11d48', 'bg': '#fbfaf7', 'surface': '#ffffff', 'text': '#0b0b0b', 'muted': '#5f5f5f', 'border': '#e5e2da'},
        'containers':   {'radius': 'none', 'shadow': 'none', 'border': 'bold', 'density': 'compact', 'surface': 'flat'},
        'typography':   {'heading': 'archivo', 'body': 'inter', 'scale': 'editorial', 'weightHeading': 800, 'letterSpacing': '-0.03em'},
        'buttons':      {'shape': 'square', 'style': 'solid', 'size': 'lg'},
        'background':   {'type': 'solid', 'overlay': 'none'},
        'motion':       {'reveal': 'stagger', 'hover': 'lift', 'intensity': 'bold'},
    },
}

#Acentos alternativos por look: la semilla elige uno para que dos
#propuestas del mismo rubro no salgan con el mismo color exacto.
ACCENTS                     =   {
    'retail':   ('#c2410c', '#0f766e', '#1d4ed8'),
    'gourmet':  ('#7c2d12', '#166534', '#1f2937'),
    'atelier':  ('#b91c1c', '#111827', '#7c3aed'),
    'sobrio':   ('#1e3a8a', '#0f766e', '#334155'),
    'clinico':  ('#0f766e', '#0369a1', '#4f46e5'),
    'belleza':  ('#9d174d', '#7c3aed', '#b45309'),
    'obra':     ('#f59e0b', '#1d4ed8', '#b91c1c'),
    'tech':     ('#4f46e5', '#0ea5e9', '#8b5cf6'),
    'aula':     ('#1d4ed8', '#0f766e', '#b45309'),
    'viaje':    ('#0369a1', '#c2410c', '#0f766e'),
    'patitas':  ('#0d9488', '#f59e0b', '#4f46e5'),
    'galeria':  ('#b45309', '#1f2937', '#7c3aed'),
    'neutro':   ('#4f46e5', '#0f766e', '#b45309'),
    'lumen':    ('#a78bfa', '#22d3ee', '#f472b6'),
    'pulse':    ('#e11d48', '#111111', '#2563eb'),
}

#El tono no cambia la paleta (esa la manda el rubro): cambia la energía —
#curvas, densidad del aire y cuánto se mueve la página.
TONE_TWEAKS                 =   {
    'calido':   {'containers': {'radius': 'xl', 'shadow': 'medium', 'density': 'spacious'}, 'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'subtle'}, 'buttons': {'shape': 'pill', 'style': 'solid'}},
    'serio':    {'containers': {'radius': 'sm', 'shadow': 'soft', 'density': 'comfortable', 'surface': 'outlined'}, 'motion': {'reveal': 'fade', 'hover': 'none', 'intensity': 'subtle'}, 'buttons': {'shape': 'rounded', 'style': 'solid'}},
    'moderno':  {'containers': {'radius': 'lg', 'shadow': 'soft', 'density': 'comfortable'}, 'motion': {'reveal': 'rise', 'hover': 'lift', 'intensity': 'medium'}, 'buttons': {'shape': 'rounded', 'style': 'solid'}},
    'audaz':    {'containers': {'radius': 'none', 'shadow': 'deep', 'density': 'compact', 'surface': 'flat'}, 'motion': {'reveal': 'stagger', 'hover': 'glow', 'intensity': 'bold'}, 'buttons': {'shape': 'square', 'style': 'gradient', 'size': 'lg'}},
}

#Afinidad plantilla ↔ tono: ajusta el puntaje, nunca decide solo.
TEMPLATE_TONE_AFFINITY      =   {
    'classic':  {'serio': 3, 'moderno': 1, 'calido': 1, 'audaz': 0},
    'duo':      {'audaz': 3, 'moderno': 2, 'calido': 1, 'serio': 0},
    'calma':    {'calido': 3, 'serio': 1, 'moderno': 1, 'audaz': 0},
    'vitrina':  {'moderno': 3, 'audaz': 2, 'calido': 1, 'serio': 1},
    'cobre':    {'calido': 3, 'audaz': 2, 'moderno': 1, 'serio': 0},
    'minimal':  {'serio': 3, 'moderno': 2, 'calido': 0, 'audaz': 1},
    'ai_lumen': {'moderno': 3, 'audaz': 2, 'serio': 1, 'calido': 0},
    'ai_pulse': {'audaz': 3, 'moderno': 3, 'calido': 1, 'serio': 0},
    #Retirados (solo IA): cada uno conserva el carácter de su época.
    'perspective': {'moderno': 2, 'audaz': 2, 'serio': 1, 'calido': 0},
    'bloque':      {'audaz': 3, 'moderno': 2, 'serio': 0, 'calido': 0},
    'riso':        {'calido': 3, 'audaz': 2, 'moderno': 1, 'serio': 0},
    'street':      {'audaz': 3, 'moderno': 2, 'calido': 1, 'serio': 0},
    'promo':       {'audaz': 3, 'moderno': 2, 'calido': 1, 'serio': 0},
    'atelier':     {'serio': 3, 'calido': 2, 'moderno': 1, 'audaz': 1},
    'circuit':     {'moderno': 3, 'audaz': 2, 'serio': 1, 'calido': 0},
    'arena':       {'audaz': 3, 'moderno': 2, 'serio': 1, 'calido': 0},
    'mercado':     {'calido': 3, 'moderno': 2, 'audaz': 1, 'serio': 0},
    'studio':      {'serio': 3, 'moderno': 2, 'calido': 1, 'audaz': 0},
    'lookbook':    {'serio': 3, 'calido': 2, 'moderno': 2, 'audaz': 1},
    'shop':        {'moderno': 3, 'calido': 2, 'audaz': 1, 'serio': 1},
    'boutique':    {'calido': 3, 'serio': 2, 'moderno': 1, 'audaz': 0},
    'signature':   {'serio': 3, 'calido': 2, 'moderno': 1, 'audaz': 1},
    'aurora':      {'moderno': 3, 'audaz': 3, 'calido': 1, 'serio': 0},
    'terminal':    {'audaz': 3, 'moderno': 3, 'serio': 1, 'calido': 0},
    'terra':       {'calido': 3, 'serio': 2, 'moderno': 1, 'audaz': 0},
    'lab':         {'moderno': 3, 'serio': 2, 'audaz': 1, 'calido': 0},
    'carta':       {'calido': 3, 'serio': 2, 'moderno': 1, 'audaz': 0},
    'proceso':     {'serio': 3, 'moderno': 2, 'calido': 1, 'audaz': 0},
}

TEMPLATE_LABELS             =   {
    'classic': 'Clásico', 'duo': 'Dúo', 'calma': 'Calma',
    'vitrina': 'Vitrina', 'cobre': 'Cobre', 'minimal': 'Minimal',
    'ai_lumen': 'Lumen', 'ai_pulse': 'Pulse',
    #Los 20 retirados del selector: la IA sí los usa (v4).
    'perspective': 'Perspectiva', 'bloque': 'Bloque', 'riso': 'Riso',
    'street': 'Calle', 'promo': 'Promo', 'atelier': 'Atelier',
    'circuit': 'Circuito', 'arena': 'Arena', 'mercado': 'Mercado',
    'studio': 'Estudio', 'lookbook': 'Lookbook', 'shop': 'Shop',
    'boutique': 'Boutique', 'signature': 'Signature', 'aurora': 'Aurora',
    'terminal': 'Terminal', 'terra': 'Terra', 'lab': 'Lab',
    'carta': 'Carta', 'proceso': 'Proceso',
}

#Afinidad plantilla ↔ objetivo: suma al puntaje la plantilla que mejor
#cuenta esa historia (vitrina para vender, cobre/minimal para mostrar obra).
TEMPLATE_GOAL_AFFINITY      =   {
    'vender_online':        ('vitrina', 'duo', 'ai_pulse', 'promo', 'shop', 'street'),
    'mostrar_servicios':    ('duo', 'vitrina', 'ai_lumen', 'lab', 'proceso', 'studio'),
    'conseguir_consultas':  ('calma', 'classic', 'ai_lumen', 'carta', 'boutique'),
    'dar_confianza':        ('classic', 'calma', 'ai_lumen', 'signature', 'atelier', 'terra'),
    'mostrar_trabajos':     ('cobre', 'minimal', 'ai_lumen', 'ai_pulse', 'lookbook', 'arena', 'perspective'),
}

#=========================================
# DISEÑOS EXCLUSIVOS DE IA (retirados)
#=========================================
#Rediseño generativo (fase 2): el motor ya no tiene diseños exclusivos ni
#retirados. Propone SOLO los 6 diseños del catálogo público, dos por nivel
#de plan (ver el bloque de normalización al final del archivo: las tablas
#de arriba conservan su historia y se remapean por afinidad al importar).
#El motor NO hardcodea la whitelist: consulta allowed_templates_of(plan).
AI_TEMPLATES                =   ()
AI_LOOKS                    =   {}
LEGACY_TEMPLATES            =   ()
#Fuentes de estilo del motor: ahora todas las propuestas son del catálogo.
STYLE_SOURCES               =   ('plan',)


def style_source_of(template):
    return 'plan'


#Matriz de estilos "firma" por rubro (v5): 3 combinaciones por rubro
#(plantilla + piel + par tipográfico) sobre el catálogo público de 6
#diseños. Garantías:
#- los 3 diseños nuevos (alimentos/boutique/seguridad) aparecen en la
#  matriz de su rubro firma;
#- dentro del rubro los 3 pares tipográficos son distintos y cada par es
#  compatible con el aire de la piel (test de tipografía);
#- el motor reordena estos estilos por tono/objetivo/datos: la matriz es
#  el piso de diversidad, no una elección fija.
RUBRO_STYLES                =   {
    'comercio': (
        {'template': 'raiz',      'skin': 'editorial-ink',   'pair': 'grotesk-clean'},
        {'template': 'alimentos', 'skin': 'warm-clay',       'pair': 'warm-serif'},
        {'template': 'trama',     'skin': 'neon-pulse',      'pair': 'condensed-bold'},
    ),
    'gastronomia': (
        {'template': 'alimentos', 'skin': 'craft-clay',      'pair': 'warm-serif'},
        {'template': 'raiz',      'skin': 'warm-ember',      'pair': 'serif-book'},
        {'template': 'trama',     'skin': 'editorial-paper', 'pair': 'editorial-display'},
    ),
    'indumentaria': (
        {'template': 'trama',     'skin': 'editorial-ink',   'pair': 'editorial-display'},
        {'template': 'boutique',  'skin': 'luxury-noir',     'pair': 'serif-luxe'},
        {'template': 'raiz',      'skin': 'minimal-chalk',   'pair': 'modern-sans'},
    ),
    'servicios_profesionales': (
        {'template': 'raiz',      'skin': 'corporate-blue',  'pair': 'classic-serif'},
        {'template': 'circuito',  'skin': 'gradient-plum',   'pair': 'mono-tech'},
        {'template': 'trama',     'skin': 'minimal-slate',   'pair': 'humanist'},
    ),
    'salud': (
        {'template': 'raiz',      'skin': 'soft-blush',      'pair': 'soft-round'},
        {'template': 'trama',     'skin': 'organic-sage',    'pair': 'humanist'},
        {'template': 'boutique',  'skin': 'prestige-ivory',  'pair': 'serif-book'},
    ),
    'belleza': (
        {'template': 'boutique',  'skin': 'luxury-gilt',     'pair': 'serif-luxe'},
        {'template': 'trama',     'skin': 'soft-dusk',       'pair': 'soft-round'},
        {'template': 'raiz',      'skin': 'editorial-paper', 'pair': 'editorial-display'},
    ),
    'construccion': (
        {'template': 'seguridad', 'skin': 'brutal-concrete', 'pair': 'brutal'},
        {'template': 'raiz',      'skin': 'mono-grey',       'pair': 'bold-sans'},
        {'template': 'circuito',  'skin': 'kinetic-flash',   'pair': 'technical'},
    ),
    'tecnologia': (
        {'template': 'circuito',  'skin': 'tech-neon',       'pair': 'technical'},
        {'template': 'raiz',      'skin': 'minimal-slate',   'pair': 'mono-tech'},
        {'template': 'trama',     'skin': 'magazine-cover',  'pair': 'grotesk-clean'},
    ),
    'educacion': (
        {'template': 'raiz',      'skin': 'playful-candy',   'pair': 'friendly'},
        {'template': 'trama',     'skin': 'paper-ink',       'pair': 'serif-book'},
        {'template': 'circuito',  'skin': 'corporate-steel', 'pair': 'humanist'},
    ),
    'turismo': (
        {'template': 'raiz',      'skin': 'organic-moss',    'pair': 'warm-serif'},
        {'template': 'trama',     'skin': 'cinematic-amber', 'pair': 'editorial-display'},
        {'template': 'boutique',  'skin': 'showcase-gallery','pair': 'grotesk-clean'},
    ),
    'mascotas': (
        {'template': 'raiz',      'skin': 'playful-pop',     'pair': 'friendly'},
        {'template': 'alimentos', 'skin': 'warm-clay',       'pair': 'soft-round'},
        {'template': 'trama',     'skin': 'soft-blush',      'pair': 'retro-display'},
    ),
    'arte': (
        {'template': 'boutique',  'skin': 'prestige-charcoal', 'pair': 'serif-luxe'},
        {'template': 'trama',     'skin': 'mono-black',        'pair': 'mono-tech'},
        {'template': 'raiz',      'skin': 'retro-sun',         'pair': 'retro-display'},
    ),
    'seguridad': (
        {'template': 'seguridad', 'skin': 'pop-poster',      'pair': 'bold-sans'},
        {'template': 'raiz',      'skin': 'brutal-acid',     'pair': 'condensed-bold'},
        {'template': 'circuito',  'skin': 'mono-grey',       'pair': 'technical'},
    ),
    'otro': (
        {'template': 'raiz',      'skin': 'corporate-steel', 'pair': 'classic-serif'},
        {'template': 'trama',     'skin': 'editorial-ink',   'pair': 'modern-sans'},
        {'template': 'circuito',  'skin': 'neon-night',      'pair': 'geometric'},
    ),
}

#Overrides de estilo por contenedor (site_theme.blocks) que acompañan a
#cada diseño de IA: solo claves del catálogo de site_theme (radius, shadow,
#border, density, surface, align, accent). El motor filtra además a los
#bloques que realmente están en el layout y resuelve `accent` con la
#paleta final (por eso el valor de acá es None).
AI_BLOCK_STYLES             =   {
    'ai_lumen': {
        'hero':     {'radius': 'xl', 'surface': 'glass', 'align': 'center', 'density': 'spacious'},
        'stats':    {'surface': 'glass'},
        'aigrid':   {'surface': 'outlined'},
        'aiquote':  {'align': 'center'},
        'aiband':   {'surface': 'glass', 'accent': None},
    },
    'ai_pulse': {
        'hero':     {'radius': 'none', 'align': 'left', 'density': 'compact'},
        'aigrid':   {'surface': 'flat', 'align': 'left'},
        'aicheck':  {'surface': 'outlined'},
        'aiband':   {'accent': None, 'border': 'bold'},
    },
}

#Bloques que suman los elementos solo-IA según la entrevista (reglas del
#motor v3): cada uno aporta como máximo 1 bloque y el total no pasa de 3.
#  aiquote <- objetivo dar_confianza (cita/testimonio destacado)
#  aicheck <- must_have 'offers' (precios) o 'benefits' (garantías)
#  aigrid  <- objetivo mostrar_servicios
#  aiband  <- vender_online con ofertas reales
#  aistrip <- 2+ datos de contacto en must_have (contact/faq/stats)
AI_ELEMENT_ORDER            =   ('aiquote', 'aicheck', 'aigrid', 'aiband', 'aistrip',
                                'aiprocess', 'aipricing', 'aimosaic')
AI_ELEMENT_ANCHORS          =   {
    'aiquote':  'testimonials',
    'aicheck':  'benefits',
    'aigrid':   'services',
    'aiband':   'offers',
    'aistrip':  'hero',
    'aiprocess': 'steps',
    'aipricing': 'featured',
    'aimosaic': 'gallery',
}
AI_ELEMENT_MAX              =   4

#Rubros donde la web ES la vidriera: la libertad visual de los ai_* suma.
VISUAL_RUBROS               =   frozenset({'belleza', 'arte', 'turismo', 'gastronomia', 'indumentaria', 'construccion', 'mascotas', 'seguridad'})

#Patrones "pro" de los diseños de IA: combinaciones de bloques/variantes
#que las recetas por objetivo no se permiten (galería masonry + banda de
#cifras, editorial + comparativa, carrusel de testimonios como cierre
#social...). `goals` ordena la afinidad; `off` apaga lo que rompe el ritmo.
#Todo id/variante de acá existe en layout_blocks.TEMPLATE_BLOCKS.
AI_PATTERNS                 =   {
    'ai_lumen': (
        {
            'id':       'lumen_cinema',
            'label':    'Lumen cinematográfico',
            'why':      'Portada cinema a sangre, galería masonry y una banda de cifras en vidrio: la web se lee como un trailer del negocio.',
            'goals':    ('mostrar_trabajos', 'dar_confianza', 'vender_online'),
            'order':    ('hero', 'announcements', 'gallery', 'stats', 'featured', 'benefits', 'testimonials', 'faq', 'cta', 'contact'),
            'off':      ('countdown', 'brands', 'compare'),
            'variants': {'hero': 'cinema', 'gallery': 'masonry', 'stats': 'band', 'benefits': 'bento', 'testimonials': 'carousel', 'cta': 'band'},
        },
        {
            'id':       'lumen_story',
            'label':    'Lumen historia',
            'why':      'Portada editorial con la trayectoria, el equipo y los testimonios en carrusel: la confianza se construye por relato.',
            'goals':    ('dar_confianza', 'conseguir_consultas', 'mostrar_servicios'),
            'order':    ('hero', 'about', 'timeline', 'gallery', 'team', 'stats', 'testimonials', 'faq', 'cta', 'contact'),
            'off':      ('countdown', 'brands', 'compare', 'offers'),
            'variants': {'hero': 'editorial', 'gallery': 'rail', 'testimonials': 'masonry', 'stats': 'cards', 'cta': 'card'},
        },
    ),
    'ai_pulse': (
        {
            'id':       'pulse_editorial',
            'label':    'Pulse editorial',
            'why':      'Titular XL, servicios en bloques grandes y comparativa antes de la prueba social: se entiende la propuesta en dos scrolls.',
            'goals':    ('mostrar_servicios', 'conseguir_consultas', 'vender_online'),
            'order':    ('hero', 'highlights', 'services', 'featured', 'compare', 'testimonials', 'faq', 'cta', 'contact'),
            'off':      ('countdown', 'brands'),
            'variants': {'hero': 'editorial', 'featured': 'masonry', 'testimonials': 'carousel', 'faq': 'cols', 'cta': 'band'},
        },
        {
            'id':       'pulse_grid',
            'label':    'Pulse grilla',
            'why':      'Portada a sangre y grilla de cuatro columnas con categorías y ofertas: ritmo de revista para un catálogo amplio.',
            'goals':    ('vender_online', 'mostrar_trabajos'),
            'order':    ('hero', 'categories', 'featured', 'offers', 'gallery', 'benefits', 'testimonials', 'faq', 'cta', 'contact'),
            'off':      ('countdown', 'brands', 'compare'),
            'variants': {'hero': 'full', 'categories': 'rail', 'featured': 'cols4', 'offers': 'rail', 'gallery': 'grid', 'benefits': 'bento', 'testimonials': 'carousel', 'faq': 'cols', 'cta': 'band'},
        },
    ),
}

#=========================================
# RUBROS
#=========================================
#`templates` va de más a menos afinidad (el motor puntúa igual, pero el
#orden desempata). `priority` es el orden de historia típico del rubro
#antes de aplicar la receta del objetivo.
RUBROS                      =   {
    'comercio': {
        'label': 'Comercio / tienda',
        'look': 'retail',
        'templates': ('raiz', 'alimentos', 'trama'),
        'goals': ('vender_online', 'mostrar_trabajos', 'dar_confianza'),
        'priority': {
            'landing':  ('hero', 'highlights', 'categories', 'featured', 'offers', 'benefits', 'brands', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('split', 'full', 'centered'), 'featured': ('grid', 'cols3', 'lead', 'quick'), 'categories': ('row', 'rail'), 'offers': ('grid', 'quick'), 'gallery': ('grid', 'masonry'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('band', 'card'), 'contact': ('card', 'map')},
    },
    'gastronomia': {
        'label': 'Gastronomía',
        'look': 'gourmet',
        'templates': ('alimentos', 'raiz', 'trama'),
        'goals': ('mostrar_servicios', 'conseguir_consultas', 'dar_confianza'),
        'priority': {
            'landing':  ('hero', 'highlights', 'about', 'services', 'gallery', 'featured', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('editorial', 'cinema', 'split'), 'featured': ('cols2', 'lead', 'grid'), 'gallery': ('masonry', 'grid'), 'testimonials': ('carousel', 'cards'), 'faq': ('list', 'accordion'), 'cta': ('band', 'card'), 'contact': ('map', 'card')},
    },
    'indumentaria': {
        'label': 'Indumentaria',
        'look': 'atelier',
        'templates': ('trama', 'boutique', 'raiz'),
        'goals': ('vender_online', 'mostrar_trabajos', 'dar_confianza'),
        'priority': {
            'landing':  ('hero', 'categories', 'featured', 'offers', 'gallery', 'about', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('full', 'cinema', 'split'), 'featured': ('masonry', 'cols3', 'grid', 'lead'), 'categories': ('rail', 'row'), 'gallery': ('masonry', 'rail'), 'testimonials': ('carousel', 'cards'), 'faq': ('accordion', 'cols'), 'cta': ('band', 'card'), 'contact': ('card', 'map')},
    },
    'servicios_profesionales': {
        'label': 'Servicios profesionales',
        'look': 'sobrio',
        'templates': ('raiz', 'circuito', 'trama'),
        'goals': ('conseguir_consultas', 'dar_confianza', 'mostrar_servicios'),
        'priority': {
            'landing':  ('hero', 'services', 'benefits', 'about', 'stats', 'testimonials', 'faq', 'steps', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('centered', 'split', 'compact'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('band', 'card'), 'contact': ('card', 'map')},
    },
    'salud': {
        'label': 'Salud',
        'look': 'clinico',
        'templates': ('raiz', 'trama', 'boutique'),
        'goals': ('conseguir_consultas', 'dar_confianza', 'mostrar_servicios'),
        'priority': {
            'landing':  ('hero', 'services', 'benefits', 'team', 'about', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('centered', 'compact', 'split'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'list'), 'cta': ('card', 'band'), 'contact': ('map', 'card')},
    },
    'belleza': {
        'label': 'Belleza y estética',
        'look': 'belleza',
        'templates': ('boutique', 'trama', 'raiz'),
        'goals': ('conseguir_consultas', 'mostrar_servicios', 'mostrar_trabajos'),
        'priority': {
            'landing':  ('hero', 'services', 'gallery', 'benefits', 'testimonials', 'team', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('cinema', 'editorial', 'split'), 'gallery': ('masonry', 'grid'), 'testimonials': ('carousel', 'cards'), 'faq': ('accordion', 'cols'), 'cta': ('band', 'card'), 'contact': ('map', 'card')},
    },
    'construccion': {
        'label': 'Construcción y oficios',
        'look': 'obra',
        'templates': ('seguridad', 'raiz', 'circuito'),
        'goals': ('mostrar_trabajos', 'conseguir_consultas', 'dar_confianza'),
        'priority': {
            'landing':  ('hero', 'services', 'gallery', 'stats', 'about', 'benefits', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('full', 'split', 'compact'), 'gallery': ('grid', 'masonry'), 'testimonials': ('cards', 'carousel'), 'faq': ('list', 'accordion'), 'cta': ('band', 'card'), 'contact': ('map', 'card')},
    },
    'tecnologia': {
        'label': 'Tecnología',
        'look': 'tech',
        'templates': ('circuito', 'raiz', 'trama'),
        'goals': ('vender_online', 'mostrar_servicios', 'conseguir_consultas'),
        'priority': {
            'landing':  ('hero', 'services', 'featured', 'benefits', 'stats', 'compare', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('split', 'cinema', 'centered'), 'featured': ('cols3', 'grid', 'quick'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('band', 'card'), 'contact': ('card', 'map')},
    },
    'educacion': {
        'label': 'Educación',
        'look': 'aula',
        'templates': ('raiz', 'trama', 'circuito'),
        'goals': ('conseguir_consultas', 'dar_confianza', 'mostrar_servicios'),
        'priority': {
            'landing':  ('hero', 'services', 'steps', 'benefits', 'stats', 'testimonials', 'team', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('centered', 'split', 'compact'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('card', 'band'), 'contact': ('card', 'map')},
    },
    'turismo': {
        'label': 'Turismo y experiencias',
        'look': 'viaje',
        'templates': ('raiz', 'trama', 'boutique'),
        'goals': ('mostrar_trabajos', 'conseguir_consultas', 'vender_online'),
        'priority': {
            'landing':  ('hero', 'gallery', 'services', 'about', 'stats', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('cinema', 'full', 'editorial'), 'gallery': ('masonry', 'rail'), 'testimonials': ('carousel', 'cards'), 'faq': ('accordion', 'list'), 'cta': ('band', 'card'), 'contact': ('map', 'card')},
    },
    'mascotas': {
        'label': 'Mascotas',
        'look': 'patitas',
        'templates': ('raiz', 'alimentos', 'trama'),
        'goals': ('mostrar_servicios', 'vender_online', 'conseguir_consultas'),
        'priority': {
            'landing':  ('hero', 'services', 'featured', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('split', 'centered', 'full'), 'featured': ('cols3', 'grid', 'quick'), 'gallery': ('grid', 'masonry'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('card', 'band'), 'contact': ('card', 'map')},
    },
    'arte': {
        'label': 'Arte y artesanías',
        'look': 'galeria',
        'templates': ('boutique', 'trama', 'raiz'),
        'goals': ('mostrar_trabajos', 'dar_confianza', 'vender_online'),
        'priority': {
            'landing':  ('hero', 'gallery', 'about', 'featured', 'timeline', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('editorial', 'cinema', 'full'), 'gallery': ('masonry', 'grid'), 'featured': ('masonry', 'cols2', 'grid'), 'testimonials': ('carousel', 'cards'), 'faq': ('list', 'accordion'), 'cta': ('band', 'card'), 'contact': ('card', 'map')},
    },
    'seguridad': {
        'label': 'Seguridad y bomberos',
        'look': 'seguridad',
        'templates': ('seguridad', 'raiz', 'circuito'),
        'goals': ('dar_confianza', 'mostrar_servicios', 'conseguir_consultas'),
        'priority': {
            'landing':  ('hero', 'highlights', 'categories', 'featured', 'services', 'steps', 'stats', 'gallery', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'promo', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('full', 'split', 'compact'), 'featured': ('grid', 'cols3', 'quick'), 'categories': ('row', 'rail'), 'gallery': ('grid', 'masonry'), 'testimonials': ('cards', 'carousel'), 'faq': ('list', 'accordion'), 'cta': ('band', 'card'), 'contact': ('map', 'card')},
    },
    'otro': {
        'label': 'Otro rubro',
        'look': 'neutro',
        'templates': ('raiz', 'trama', 'circuito'),
        'goals': ('mostrar_servicios', 'dar_confianza', 'conseguir_consultas'),
        'priority': {
            'landing':  ('hero', 'about', 'services', 'featured', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'),
            'catalog':  ('note', 'filters', 'sort', 'grid'),
            'services': ('hero', 'band', 'picker', 'steps', 'form', 'faq'),
        },
        'variants': {'hero': ('split', 'centered', 'full'), 'featured': ('grid', 'cols3'), 'gallery': ('grid', 'masonry'), 'testimonials': ('cards', 'carousel'), 'faq': ('accordion', 'cols'), 'cta': ('card', 'band'), 'contact': ('card', 'map')},
    },
}

#Pistas de rubro por palabra: el dueño puede no responder la entrevista y
#el motor deduce el rubro de lo que ya cargó (nombre, categorías, servicios).
RUBRO_HINTS                 =   {
    'comercio': ('tienda', 'almacen', 'kiosco', 'mercado', 'bazar', 'distribuidora', 'mayorista'),
    'gastronomia': ('resto', 'restaurant', 'cafe', 'bar', 'panaderia', 'pizzeria', 'heladeria', 'cocina', 'food', 'delivery'),
    'indumentaria': ('ropa', 'moda', 'indumentaria', 'calzado', 'zapatilla', 'boutique', 'taller textil'),
    'servicios_profesionales': ('estudio', 'consultora', 'abogad', 'contador', 'asesor', 'consultor', 'legal'),
    'salud': ('clinica', 'consultorio', 'salud', 'odontolog', 'kinesio', 'nutricion', 'psicolog', 'farmacia'),
    'belleza': ('peluqueria', 'estetica', 'belleza', 'manicur', 'barber', 'spa', 'maquillaje'),
    'construccion': ('construccion', 'obra', 'albanil', 'plomer', 'electric', 'pintur', 'carpinter', 'herrer'),
    'tecnologia': ('software', 'tecnologia', 'sistemas', 'digital', 'app', 'informatica', 'web'),
    'educacion': ('escuela', 'instituto', 'academia', 'curso', 'clases', 'educacion', 'profesor'),
    'turismo': ('turismo', 'viaje', 'hotel', 'cabaña', 'hostel', 'excursion', 'agencia de viajes'),
    'mascotas': ('veterinaria', 'mascota', 'pet', 'gato', 'perro', 'peluqueria canina'),
    'arte': ('arte', 'artesan', 'galeria', 'taller', 'ilustra', 'fotograf', 'ceramica'),
    'seguridad': ('seguridad', 'bombero', 'extintor', 'matafuego', 'epp', 'vigilancia', 'industrial', 'recarga', 'certificado', 'monitoreo'),
}

#=========================================
# RECETAS POR OBJETIVO
#=========================================
#`order` es el orden canónico de la portada para ese objetivo; `off`
#apaga lo que distrae de la meta (no se borra: queda desactivado en el
#borrador y el dueño lo reactiva). `hero_variant` fija la variante de la
#portada, y `labels` son los nombres de las propuestas (≤32).
#v6: `opening` es el grupo de bloques que enmarca la portada según el
#objetivo; el motor exige que la primera sección con contenido real después
#del hero salga de ese grupo (ai_design._rotate_to_opening).
GOAL_RECIPES                =   {
    'vender_online': {
        'label': 'Vender online',
        'hero_variant': 'split',
        'hero_variants': ('search', 'split'),
        'opening': ('categories', 'offers'),
        'order': ('hero', 'highlights', 'categories', 'featured', 'offers', 'countdown', 'benefits', 'brands', 'testimonials', 'faq', 'cta', 'contact'),
        'off': ('video', 'timeline', 'team', 'compare', 'steps'),
        'labels': ('Catálogo protagonista', 'Vitrina de ofertas', 'Compra guiada'),
        'why': 'Pusimos el catálogo arriba y el cierre de compra a la vista: menos scroll hasta el producto.',
    },
    'mostrar_servicios': {
        'label': 'Mostrar servicios',
        'hero_variant': 'centered',
        'hero_variants': ('centered', 'split'),
        'opening': ('services',),
        'order': ('hero', 'services', 'benefits', 'steps', 'gallery', 'stats', 'testimonials', 'faq', 'cta', 'contact'),
        'off': ('countdown', 'brands', 'compare'),
        'labels': ('Servicios al frente', 'Proceso claro', 'Oficio y detalle'),
        'why': 'Los servicios y los pasos quedan antes que la prueba social: se entiende qué hacés sin buscar.',
    },
    'conseguir_consultas': {
        'label': 'Conseguir consultas',
        'hero_variant': 'split',
        'hero_variants': ('split', 'centered'),
        'opening': ('services',),
        'order': ('hero', 'services', 'benefits', 'testimonials', 'faq', 'about', 'cta', 'contact'),
        'off': ('countdown', 'brands', 'featured', 'offers', 'compare'),
        'labels': ('Consultas primero', 'Respuesta rápida', 'Confianza y cierre'),
        'why': 'Cada bloque empuja al contacto: la duda se responde antes del botón y el cierre queda al final.',
    },
    'dar_confianza': {
        'label': 'Dar confianza',
        'hero_variant': 'centered',
        'hero_variants': ('centered', 'editorial'),
        'opening': ('stats', 'about'),
        'order': ('hero', 'about', 'stats', 'timeline', 'team', 'testimonials', 'benefits', 'faq', 'cta', 'contact'),
        'off': ('countdown', 'compare'),
        'labels': ('Confianza primero', 'Historia del negocio', 'Gente detrás'),
        'why': 'Abrimos con la historia, las cifras y el equipo: la trayectoria es el argumento de venta.',
    },
    'mostrar_trabajos': {
        'label': 'Mostrar trabajos',
        'hero_variant': 'cinema',
        'hero_variants': ('cinema', 'editorial'),
        'opening': ('gallery',),
        'order': ('hero', 'gallery', 'featured', 'services', 'testimonials', 'about', 'faq', 'cta', 'contact'),
        'off': ('countdown', 'compare', 'brands'),
        'labels': ('Trabajos primero', 'Galería amplia', 'Antes y después'),
        'why': 'La galería va justo debajo de la portada: el trabajo se muestra antes de explicarlo.',
    },
}

#Prueba social: _enforce_hierarchy la agrupa antes del cierre, así que el
#ritmo alternado no la usa como separador entre fotos.
SOCIAL_BLOCKS               =   frozenset({'testimonials', 'brands'})

#Bloques de "foto grande": el ritmo alternado nunca los pone seguidos (entre
#dos de ellos va un bloque de texto o de datos).
IMAGE_BLOCKS                =   frozenset({'featured', 'gallery', 'aimosaic'})

#Densidad por tono (B.2-5): bloques que el tono apaga cuando pide aire. Se
#excluyen los 'locking' (portada, cierre, contacto) y los ai_* (los suma D).
TONE_DENSITY                =   {
    'serio':    ('countdown', 'timeline', 'team', 'video', 'compare', 'steps'),
    'audaz':    (),
    'moderno':  (),
    'calido':   ('compare',),
}

#=========================================
# BLOQUES QUE EXIGEN DATOS REALES
#=========================================
#Cada id apunta a un hecho del negocio (ai_design._facts). Sin el hecho el
#bloque queda enabled=False: preferimos una web corta y verdadera a una
#sección vacía. `None` = siempre presente (hero, cta, contact, grid...).
BLOCK_GATES                 =   {
    'landing': {
        'hero':             None,
        'announcements':    'announcements',
        'highlights':       'highlights',
        'categories':       'categories',
        'featured':         'products',
        'about':            'about',
        'services':         'services',
        'stats':            'stats',
        'benefits':         'benefits',
        'offers':           'offers',
        'brands':           'brands',
        'countdown':        'countdown',
        'timeline':         'timeline',
        'team':             'team',
        'gallery':          'gallery',
        'testimonials':     'testimonials',
        'faq':              'faqs',
        'video':            'video',
        'steps':            'steps',
        'compare':          'compare',
        'cta':              None,
        'contact':          'contact',
    },
    'catalog': {
        'note':             'catalog_note',
        'banner':           'carousel',
        'promo':            'offers',
        'filters':          'catalog_dense',
        'sort':             'catalog_dense',
        'grid':             None,
    },
    'services': {
        'hero':             None,
        'band':             'services',
        'picker':           None,
        'steps':            'steps',
        'form':             'service_form',
        'faq':              'faqs',
    },
}

#Pasos de la entrevista (mismo orden que la UI): los usa la telemetría
#para informar abandono por paso sin traducir ids a mano.
STEP_LABELS                 =   (
    'A qué te dedicás',
    'Qué querés lograr',
    'Cómo se siente',
    'Tu marca',
    'Qué no puede faltar',
    'Tus propuestas',
)

#=========================================
# ENTREVISTA -> BLOQUES (contrato §2.1)
#=========================================
#La UI pregunta en lenguaje del dueño ("¿Qué no puede faltar?") y manda ids
#de DESEO; el motor compone con ids de BLOQUE. Este mapa es la única
#traducción válida: lo que no está acá no se inventa. Un deseo puede tocar
#más de un bloque (WhatsApp = contacto + cierre).
MUST_HAVE_BLOCKS            =   {
    'whatsapp':     ('contact', 'cta'),
    'hours':        ('contact',),
    'map':          ('contact',),
    'prices':       ('offers',),
    'testimonials': ('testimonials',),
    'faqs':         ('faq',),
}
#Etiquetas humanas para `notes` (nunca el id crudo del bloque).
MUST_HAVE_LABELS            =   {
    'whatsapp':     'Botón de WhatsApp',
    'hours':        'Horarios',
    'map':          'Mapa y dirección',
    'prices':       'Precios',
    'testimonials': 'Opiniones de clientes',
    'faqs':         'Preguntas frecuentes',
}
#Dato real que habilita el bloque pedido: sin esto la sección queda
#apagada (regla 2.5, nunca una sección que mienta). `()` = siempre.
MUST_HAVE_DATA              =   {
    'contact':      ('contact', 'hours'),
    'cta':          (),
    'offers':       ('offers',),
    'testimonials': ('testimonials',),
    'faq':          ('faqs',),
}

#Bloques que, si tienen datos, no deberían quedar fuera aunque la receta
#del objetivo no los mencione (el motor los agrega al final del grupo).
BLOCK_FALLBACKS             =   {
    'landing': ('about', 'gallery', 'testimonials', 'faq', 'benefits', 'stats'),
    'catalog': (),
    'services': ('steps', 'faq'),
}

#=========================================
# REGLAS DE JERARQUÍA (ordenadas)
#=========================================
#Documentación viva del criterio de armado: el motor las aplica en este
#orden y cada una tiene su reflejo en ai_design._build_layout. Si una
#regla cambia, cambia acá primero — el contrato con el frontend no.
HIERARCHY_RULES             =   (
    ('hero_first',      'La portada abre siempre; la variante la fija el objetivo.'),
    ('locked_blocks',   'Los bloques locked (grilla del catálogo, selector de servicios) están siempre.'),
    ('categories_two',  'Departamentos solo con 2+ categorías: una sola no es navegación.'),
    ('gated_data',      'Cada bloque con datos propios se apaga si el dato falta (no se muestra vacío).'),
    ('offers_real',     'Ofertas y cuenta regresiva solo con descuentos vigentes.'),
    ('opening_goal',    'La primera sección con contenido después del hero sale del grupo del objetivo (v6).'),
    ('alternating_rhythm', 'Dos bloques de foto grande (vitrina, galería, mosaico) nunca van seguidos (v6).'),
    ('social_before_cta', 'Testimonios y marcas quedan antes del cierre: la prueba social precede al pedido.'),
    ('contact_last',    'El contacto cierra la portada, después del llamado a la acción.'),
    ('distinct_signature', 'Dos propuestas de una misma generación nunca comparten firma de layout (v6).'),
    ('premium_flag',    'Los bloques premium se omiten sin has_design_advanced.'),
)

#Títulos de sección para props.title del borrador (se rellenan solo si el
#bloque no tiene título propio). Se indexan por rubro y caen al genérico.
BLOCK_TITLES                =   {
    'comercio':     {'featured': 'Los más pedidos', 'categories': 'Categorías', 'offers': 'Ofertas', 'benefits': 'Por qué elegirnos', 'testimonials': 'Clientes', 'gallery': 'Nuestro local'},
    'gastronomia':  {'services': 'Nuestra carta', 'gallery': 'El lugar', 'featured': 'Para probar', 'testimonials': 'Opiniones', 'about': 'Nuestra cocina'},
    'indumentaria': {'featured': 'Nueva colección', 'categories': 'Colecciones', 'gallery': 'Lookbook', 'offers': 'Ofertas', 'about': 'La marca'},
    'servicios_profesionales': {'services': 'Qué hacemos', 'benefits': 'Cómo trabajamos', 'faq': 'Consultas frecuentes', 'testimonials': 'Clientes', 'stats': 'Trayectoria'},
    'salud':        {'services': 'Especialidades', 'team': 'Profesionales', 'benefits': 'Cómo te cuidamos', 'faq': 'Preguntas frecuentes'},
    'belleza':      {'services': 'Servicios', 'gallery': 'Nuestros trabajos', 'team': 'El equipo', 'testimonials': 'Clientas', 'faq': 'Antes de tu turno'},
    'construccion': {'services': 'Qué construimos', 'gallery': 'Obras realizadas', 'stats': 'Años de oficio', 'benefits': 'Cómo trabajamos', 'faq': 'Preguntas frecuentes'},
    'tecnologia':   {'services': 'Soluciones', 'benefits': 'Por qué elegirnos', 'compare': 'Comparativa', 'faq': 'Preguntas frecuentes', 'stats': 'Resultados'},
    'educacion':    {'services': 'Cursos', 'steps': 'Cómo inscribirse', 'team': 'Docentes', 'faq': 'Preguntas frecuentes', 'testimonials': 'Alumnos'},
    'turismo':      {'gallery': 'Experiencias', 'services': 'Qué ofrecemos', 'about': 'Quiénes somos', 'faq': 'Antes de viajar', 'testimonials': 'Viajeros'},
    'mascotas':     {'services': 'Servicios', 'featured': 'Productos', 'gallery': 'Nuestros pacientes', 'benefits': 'Cuidado de verdad', 'faq': 'Preguntas frecuentes'},
    'arte':         {'gallery': 'Obras', 'about': 'El taller', 'featured': 'Piezas disponibles', 'timeline': 'Trayectoria', 'testimonials': 'Coleccionistas'},
    'seguridad':    {'services': 'Nuestros servicios', 'steps': 'Cómo contratar', 'stats': 'Respaldo y experiencia', 'benefits': 'Por qué elegirnos', 'faq': 'Preguntas frecuentes'},
    'otro':         {'services': 'Qué ofrecemos', 'benefits': 'Por qué elegirnos', 'gallery': 'Galería', 'testimonials': 'Opiniones', 'faq': 'Preguntas frecuentes'},
}

#=========================================
# NORMALIZACIÓN AL CATÁLOGO DE 6 DISEÑOS
#=========================================
#Las tablas de arriba conservan la historia del motor (afinidades de
#tono/objetivo, etc.) escritas con ids viejos. Acá se remapean por
#afinidad a los 6 diseños del catálogo al importar, así el motor propone
#SOLO ids públicos sin reescribir cada receta a mano.
#Espejo de StoreCustomization.TEMPLATE_RETIRED_MAP (fuente única).
PUBLIC_TEMPLATES            =   ('raiz', 'alimentos', 'trama', 'boutique', 'circuito', 'seguridad')
PUBLIC_TEMPLATE_MAP         =   {
    'classic': 'raiz', 'duo': 'raiz', 'minimal': 'raiz', 'calma': 'raiz',
    'mercado': 'raiz', 'studio': 'raiz', 'arena': 'raiz', 'proceso': 'raiz',
    'carta': 'raiz', 'terra': 'raiz', 'bloque': 'raiz', 'shop': 'raiz',
    'atelier': 'trama', 'lookbook': 'trama',
    'signature': 'trama', 'cobre': 'trama', 'vitrina': 'trama',
    'street': 'trama', 'riso': 'trama', 'promo': 'trama', 'aurora': 'trama',
    'perspective': 'circuito', 'circuit': 'circuito', 'terminal': 'circuito',
    'lab': 'circuito', 'ai_lumen': 'circuito', 'ai_pulse': 'trama',
    #'boutique' NO va acá: es un diseño del catálogo (plus) desde el rediseño.
}


def public_template(template):
    """Id del catálogo nuevo para un id (viejo o actual)."""
    return PUBLIC_TEMPLATE_MAP.get(template, template)


#Recetas por rubro: se remapean los templates y se conserva el orden de
#afinidad (deduplicado). Si el remapeo deja menos de 6, se completan los
#que falten para que el motor siempre tenga los 6 disponibles.
for _recipe in RUBROS.values():
    _mapped = []
    for _tpl in _recipe.get('templates', ()):
        _new = public_template(_tpl)
        if _new in PUBLIC_TEMPLATES and _new not in _mapped:
            _mapped.append(_new)
    for _tpl in PUBLIC_TEMPLATES:
        if _tpl not in _mapped:
            _mapped.append(_tpl)
    _recipe['templates'] = tuple(_mapped)

#Matriz "firma" por rubro: misma remapeada (la piel y el par se conservan).
for _rubro, _styles in RUBRO_STYLES.items():
    RUBRO_STYLES[_rubro] = tuple({**style, 'template': public_template(style['template'])} for style in _styles)

#Afinidades y etiquetas del catálogo nuevo (el motor las puntúa).
TEMPLATE_TONE_AFFINITY.update({
    'raiz':      {'serio': 2, 'moderno': 2, 'calido': 2, 'audaz': 1},
    'alimentos': {'calido': 3, 'moderno': 2, 'audaz': 1, 'serio': 1},
    'trama':     {'audaz': 3, 'moderno': 2, 'calido': 1, 'serio': 1},
    'boutique':  {'calido': 3, 'serio': 2, 'moderno': 1, 'audaz': 0},
    'circuito':  {'moderno': 3, 'serio': 2, 'audaz': 1, 'calido': 0},
    'seguridad': {'audaz': 3, 'serio': 3, 'moderno': 1, 'calido': 0},
})
TEMPLATE_LABELS.update({
    'raiz': 'Raíz', 'alimentos': 'Alimentos', 'trama': 'Trama',
    'boutique': 'Boutique', 'circuito': 'Circuito', 'seguridad': 'Seguridad',
})
TEMPLATE_GOAL_AFFINITY.update({
    #Cada objetivo tiene UN diseño que mejor cuenta esa historia (el resto
    #compite por tono/piel): así cambiar el objetivo mueve el puntaje.
    'vender_online':        ('trama', 'alimentos'),
    'mostrar_servicios':    ('raiz', 'seguridad'),
    'conseguir_consultas':  ('raiz', 'seguridad'),
    'dar_confianza':        ('raiz', 'circuito', 'seguridad'),
    'mostrar_trabajos':     ('trama', 'boutique', 'circuito'),
})
