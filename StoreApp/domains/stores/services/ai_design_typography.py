#=========================================
# TIPOGRAFÍA POR ROL — catálogo cerrado del motor "Diseñar con IA" (v4)
#=========================================
#Datos puros (sin Django): el motor elige UN par tipográfico por propuesta
#y este módulo lo expande a los 13 roles del contrato de site_theme v2.
#Cada rol declara {font, size, weight, tracking, leading, case} con los
#enums exactos de site_theme — el frontend los consume como variables CSS,
#nunca como CSS libre.
#
#Reglas del contrato (no negociables):
#- display/h1/h2/h3 usan la familia de display del par; el resto de los
#  roles de texto usan la familia de cuerpo (nunca dos familias distintas
#  para roles de cuerpo).
#- body siempre legible: peso 400-500, tamaño md, leading relaxed/normal.
#- price: peso 700, tracking normal (números tabulares del lado del render).
#- eyebrow: mayúsculas con tracking wider.
#
#El catálogo de fuentes (24 familias Google Fonts) es el mismo que valida
#site_theme: un slug de acá es el único font aceptado en typography.roles.

FONT_KINDS      =   ('serif', 'sans', 'display', 'mono')

#24 familias exactas (una por par tipográfico del catálogo): el motor
#elige por rol, no una sola familia para todo el sitio.
FONT_FAMILIES   =   {
    #sans
    'inter':                {'label': 'Inter',                'kind': 'sans'},
    'manrope':              {'label': 'Manrope',              'kind': 'sans'},
    'figtree':              {'label': 'Figtree',              'kind': 'sans'},
    'dm-sans':              {'label': 'DM Sans',              'kind': 'sans'},
    'space-grotesk':        {'label': 'Space Grotesk',        'kind': 'sans'},
    'archivo':              {'label': 'Archivo',              'kind': 'sans'},
    'sora':                 {'label': 'Sora',                 'kind': 'sans'},
    'work-sans':            {'label': 'Work Sans',            'kind': 'sans'},
    'outfit':               {'label': 'Outfit',               'kind': 'sans'},
    'plus-jakarta-sans':    {'label': 'Plus Jakarta Sans',    'kind': 'sans'},
    'nunito':               {'label': 'Nunito',               'kind': 'sans'},
    'raleway':              {'label': 'Raleway',              'kind': 'sans'},
    #serif
    'playfair-display':     {'label': 'Playfair Display',     'kind': 'serif'},
    'fraunces':             {'label': 'Fraunces',             'kind': 'serif'},
    'lora':                 {'label': 'Lora',                 'kind': 'serif'},
    'cormorant-garamond':   {'label': 'Cormorant Garamond',   'kind': 'serif'},
    'dm-serif-display':     {'label': 'DM Serif Display',     'kind': 'serif'},
    'libre-baskerville':    {'label': 'Libre Baskerville',    'kind': 'serif'},
    'cinzel':               {'label': 'Cinzel',               'kind': 'serif'},
    #display
    'oswald':               {'label': 'Oswald',               'kind': 'display'},
    'archivo-black':        {'label': 'Archivo Black',        'kind': 'display'},
    'bebas-neue':           {'label': 'Bebas Neue',           'kind': 'display'},
    #mono
    'space-mono':           {'label': 'Space Mono',           'kind': 'mono'},
    'jetbrains-mono':       {'label': 'JetBrains Mono',       'kind': 'mono'},
}

FONT_SLUGS      =   tuple(FONT_FAMILIES)

#Rango de pesos REALES de cada familia (Google Fonts). Pedir un 900 a una
#fuente de 400 hace que el navegador invente la negrita (faux bold): se ve
#pesado y sucio. El motor recorta el peso al escalón más cercano que la
#familia soporta de verdad.
FONT_WEIGHTS    =   {
    'inter':                (300, 900),
    'manrope':              (300, 800),
    'figtree':              (300, 700),
    'dm-sans':              (300, 900),
    'space-grotesk':        (300, 700),
    'archivo':              (400, 900),
    'sora':                 (300, 800),
    'work-sans':            (300, 800),
    'outfit':               (300, 900),
    'plus-jakarta-sans':    (300, 800),
    'nunito':               (300, 800),
    'raleway':              (300, 800),
    'playfair-display':     (400, 800),
    'fraunces':             (300, 900),
    'lora':                 (400, 700),
    'cormorant-garamond':   (400, 700),
    'dm-serif-display':     (400, 400),
    'libre-baskerville':    (400, 700),
    'cinzel':               (400, 800),
    'oswald':               (300, 700),
    'archivo-black':        (400, 400),
    'bebas-neue':           (400, 400),
    'space-mono':           (400, 700),
    'jetbrains-mono':       (400, 800),
}

#Display que ya vienen en mayúsculas por diseño: no se les pide tracking
#negativo (se ve apretado) ni un peso que no tienen.
_DISPLAY_TRACKING   =   {
    'bebas-neue':       'tight',
    'archivo-black':    'tight',
    'cinzel':           'wide',
}


#Roles cerrados de site_theme v2 (typography.roles).
TYPOGRAPHY_ROLES    =   (
    'display', 'h1', 'h2', 'h3', 'body', 'lead', 'eyebrow',
    'label', 'quote', 'price', 'nav', 'button', 'footer',
)
#Roles de cuerpo: SIEMPRE la misma familia (nunca dos familias distintas).
BODY_ROLES      =   ('body', 'lead', 'eyebrow', 'label', 'price', 'nav', 'button', 'footer')
DISPLAY_ROLES   =   ('display', 'h1', 'h2', 'h3', 'quote')

TYPE_SIZES      =   ('xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', 'display')
TYPE_TRACKING   =   ('tighter', 'tight', 'normal', 'wide', 'wider')
TYPE_LEADING    =   ('tight', 'snug', 'normal', 'relaxed')
TYPE_CASES      =   ('none', 'upper')

#Par tipográfico: familia de display + familia de cuerpo. 24 pares con
#firmas (display, body) distintas — la diversidad de una generación se
#valida comparando esa firma.
TYPE_PAIRS      =   {
    #Regla de oro: el CUERPO siempre es una sans legible (mono solo como
    #acento en titulares) y el display nunca repite la familia del cuerpo.
    #Un sitio entero en monoespaciada o dos pesos negros enfrentados se lee
    #como maqueta, no como negocio.
    'grotesk-clean':        {'label': 'Grotesk limpio',        'display': 'space-grotesk',        'body': 'inter'},
    'condensed-bold':       {'label': 'Condensada enérgica',   'display': 'oswald',               'body': 'inter'},
    'display-heavy':        {'label': 'Peso máximo',           'display': 'archivo-black',        'body': 'manrope'},
    'serif-editorial':      {'label': 'Serif editorial',       'display': 'fraunces',             'body': 'inter'},
    'serif-classic':        {'label': 'Serif clásico',         'display': 'playfair-display',     'body': 'inter'},
    'serif-book':           {'label': 'Serif de libro',        'display': 'lora',                 'body': 'inter'},
    'display-mono':         {'label': 'Mono en titulares',     'display': 'jetbrains-mono',       'body': 'inter'},
    'modern-sans':          {'label': 'Sans moderna',          'display': 'figtree',              'body': 'inter'},
    'geometric':            {'label': 'Geométrica',            'display': 'outfit',               'body': 'dm-sans'},
    'soft-round':           {'label': 'Redondeada suave',      'display': 'nunito',               'body': 'figtree'},
    'serif-luxe':           {'label': 'Serif de lujo',         'display': 'cinzel',               'body': 'raleway'},
    'technical':            {'label': 'Técnica',               'display': 'space-grotesk',        'body': 'work-sans'},
    'brutal':               {'label': 'Brutal',                'display': 'archivo-black',        'body': 'work-sans'},
    'retro-display':        {'label': 'Retro',                 'display': 'bebas-neue',           'body': 'work-sans'},
    'warm-serif':           {'label': 'Serif cálida',          'display': 'cormorant-garamond',   'body': 'manrope'},
    'humanist':             {'label': 'Humanista',             'display': 'sora',                 'body': 'figtree'},
    'editorial-display':    {'label': 'Display editorial',     'display': 'dm-serif-display',     'body': 'dm-sans'},
    'mono-tech':            {'label': 'Mono de acento',        'display': 'space-mono',           'body': 'inter'},
    'friendly':             {'label': 'Cercana',               'display': 'figtree',              'body': 'nunito'},
    'luxe-sans':            {'label': 'Sans de lujo',          'display': 'manrope',              'body': 'plus-jakarta-sans'},
    'classic-serif':        {'label': 'Serif sobria',          'display': 'libre-baskerville',    'body': 'inter'},
    'bold-sans':            {'label': 'Sans pesada',           'display': 'archivo',              'body': 'figtree'},
    'display-condensed':    {'label': 'Condensada neutra',     'display': 'bebas-neue',           'body': 'inter'},
    'display-serif':        {'label': 'Serif display',         'display': 'dm-serif-display',     'body': 'outfit'},
}

#Pieles donde la cita puede usar la display (revista/lujo): el resto usa el
#cuerpo, porque una cita en Archivo Black a 22px se ve como un cartel.
QUOTE_DISPLAY_SKINS     =   frozenset({'editorial', 'luxury', 'cinematic', 'paper'})
#Presupuesto base por rol (antes del tono y de la piel).
_BASE_ROLES     =   {
    'display':  {'size': 'display', 'weight': 700, 'tracking': 'tighter', 'leading': 'tight',  'case': 'none'},
    'h1':       {'size': '3xl',     'weight': 700, 'tracking': 'tighter', 'leading': 'tight',  'case': 'none'},
    'h2':       {'size': '2xl',     'weight': 700, 'tracking': 'tight',   'leading': 'snug',   'case': 'none'},
    'h3':       {'size': 'xl',      'weight': 600, 'tracking': 'tight',   'leading': 'snug',   'case': 'none'},
    'body':     {'size': 'md',      'weight': 400, 'tracking': 'normal',  'leading': 'relaxed', 'case': 'none'},
    'lead':     {'size': 'lg',      'weight': 400, 'tracking': 'normal',  'leading': 'normal', 'case': 'none'},
    'eyebrow':  {'size': 'xs',      'weight': 600, 'tracking': 'wider',   'leading': 'normal', 'case': 'upper'},
    'label':    {'size': 'sm',      'weight': 500, 'tracking': 'wide',    'leading': 'normal', 'case': 'none'},
    'quote':    {'size': 'xl',      'weight': 400, 'tracking': 'normal',  'leading': 'relaxed', 'case': 'none'},
    'price':    {'size': '2xl',     'weight': 700, 'tracking': 'normal',  'leading': 'tight',  'case': 'none'},
    'nav':      {'size': 'sm',      'weight': 500, 'tracking': 'wide',    'leading': 'normal', 'case': 'none'},
    'button':   {'size': 'sm',      'weight': 600, 'tracking': 'wide',    'leading': 'normal', 'case': 'none'},
    'footer':   {'size': 'sm',      'weight': 400, 'tracking': 'normal',  'leading': 'normal', 'case': 'none'},
}

#El tono mueve energía (peso/tracking/leading), no la identidad.
_TONE_ROLES     =   {
    'calido':   {
        'display': {'weight': 600, 'tracking': 'tight'},
        'h1':      {'weight': 600, 'tracking': 'tight'},
        'h2':      {'weight': 600},
        'body':    {'leading': 'relaxed'},
        'quote':   {'leading': 'relaxed'},
    },
    'serio':    {
        'display': {'weight': 600, 'tracking': 'tight'},
        'h1':      {'weight': 600},
        'h2':      {'weight': 600},
        'eyebrow': {'tracking': 'wider'},
        'body':    {'leading': 'normal'},
    },
    'moderno':  {
        'display': {'weight': 700, 'tracking': 'tighter'},
        'h1':      {'weight': 700},
    },
    'audaz':    {
        'display': {'weight': 900, 'tracking': 'tighter', 'case': 'upper'},
        'h1':      {'weight': 900, 'tracking': 'tighter', 'case': 'upper'},
        'h2':      {'weight': 800, 'case': 'upper'},
        'eyebrow': {'weight': 700, 'tracking': 'wider'},
        'button':  {'weight': 700, 'case': 'upper'},
    },
}

#La piel puede imponer su firma tipográfica (brutal en mayúsculas, mono en
#todo, lujo con tracking amplio). Claves = rol, valores = override parcial.
SKIN_ROLE_OVERRIDES     =   {
    'brutal':   {'h1': {'case': 'upper', 'weight': 900}, 'h2': {'case': 'upper'}, 'button': {'case': 'upper'}},
    'mono':     {'body': {'tracking': 'normal'}, 'label': {'tracking': 'wider'}, 'nav': {'case': 'upper'}},
    'luxury':   {'h1': {'tracking': 'wide', 'weight': 500}, 'h2': {'tracking': 'wide'}, 'eyebrow': {'tracking': 'wider'}},
    'editorial': {'quote': {'size': '2xl', 'leading': 'relaxed'}, 'lead': {'size': 'xl'}},
    'kinetic':  {'display': {'case': 'upper', 'weight': 900}, 'h1': {'case': 'upper'}},
    'retro':    {'h2': {'case': 'upper'}, 'eyebrow': {'tracking': 'wider'}},
    'corporate': {'h1': {'weight': 600}, 'h2': {'weight': 600}},
    'paper':    {'body': {'leading': 'relaxed'}, 'h3': {'weight': 500}},
    'organic':  {'h1': {'weight': 500}, 'quote': {'leading': 'relaxed'}},
    'soft':     {'h1': {'weight': 600}, 'body': {'leading': 'relaxed'}},
    'glass':    {'h1': {'weight': 600, 'tracking': 'tight'}},
    'tech':     {'eyebrow': {'tracking': 'wider'}, 'label': {'tracking': 'wide'}},
    'neon':     {'h1': {'case': 'upper', 'weight': 800}, 'button': {'case': 'upper'}},
    'minimal':  {'h1': {'weight': 500, 'tracking': 'tight'}, 'h2': {'weight': 500}},
    'gradient': {'h1': {'weight': 800}},
    'cinematic': {'display': {'tracking': 'wide', 'weight': 500}, 'quote': {'size': '2xl'}},
    'warm':     {'h1': {'weight': 600}},
    'playful':  {'h2': {'weight': 700}, 'button': {'case': 'none'}},
}


def _clamp_weight(font, weight):
    """
    Escalón de peso que la familia soporta de verdad (300..900, paso 100).
    Una familia de un solo peso devuelve su único peso: nada de faux bold.
    """
    low, high   =   FONT_WEIGHTS.get(font, (400, 700))
    snapped     =   int(round(int(weight) / 100.0)) * 100
    return max(low, min(high, snapped))


def pair_of(name):
    """Par tipográfico del catálogo (None si el nombre no existe)."""
    return TYPE_PAIRS.get(name)


def roles_for(pair_name, tone, skin_family = None):
    """
    Expande un par tipográfico a los 13 roles: {font, size, weight,
    tracking, leading, case}. Determinista y siempre completo (un par
    desconocido cae al par por defecto).
    """
    pair    =   TYPE_PAIRS.get(pair_name) or TYPE_PAIRS['grotesk-clean']
    roles   =   {}
    for role in TYPOGRAPHY_ROLES:
        base    =   dict(_BASE_ROLES[role])
        base.update(_TONE_ROLES.get(tone, {}).get(role) or {})
        base.update((SKIN_ROLE_OVERRIDES.get(skin_family) or {}).get(role) or {})
        #La display solo manda en display/h1/h2 (y en la cita de las pieles
        #de revista). h3, precio y navegación van con el cuerpo: una display
        #pesada en un título chico se ve como un error, no como diseño.
        display_role = role in ('display', 'h1', 'h2')
        if role == 'quote' and skin_family in QUOTE_DISPLAY_SKINS:
            display_role = True
        font    =   pair['display'] if display_role else pair['body']
        tracking    =   _DISPLAY_TRACKING.get(font, base['tracking']) if display_role else base['tracking']
        roles[role] =   {
            'font'      :   font,
            'size'      :   base['size'],
            'weight'    :   _clamp_weight(font, base['weight']),
            'tracking'  :   tracking,
            'leading'   :   base['leading'],
            'case'      :   base['case'],
        }
    #Invariantes del contrato (defensa en profundidad: el preset podría
    #traer un override raro y el rol no puede salirse de las reglas).
    roles['body'].update({'size': 'md', 'weight': min(max(roles['body']['weight'], 400), 500), 'leading': roles['body']['leading'] if roles['body']['leading'] in ('normal', 'relaxed') else 'relaxed'})
    roles['price'].update({'weight': 700, 'tracking': 'normal'})
    roles['eyebrow'].update({'case': 'upper', 'tracking': 'wider'})
    return roles


def type_pair_signature(pair_name):
    """Firma del par (display, body) para comparar diversidad entre propuestas."""
    pair    =   TYPE_PAIRS.get(pair_name) or TYPE_PAIRS['grotesk-clean']
    return (pair['display'], pair['body'])
