"""
Catálogo base de estilos de diseño (20 estilos gratuitos).

Cada preset declara tokens de diseño y el builder arma los bloques HTML
con clases Tailwind derivadas de esos tokens. Los estilos son datos, no
código: el seed los inserta/actualiza por slug de forma idempotente.
"""


#=========================================
# PRESETS
#=========================================
PRESETS = [
    {
        'slug': 'cyberpunk-dark', 'nombre': 'Cyberpunk Premium Dark', 'categoria': 'tecnologia',
        'tags': ['oscuro', 'neon', 'gamer', 'futurista', 'cyberpunk'],
        'tokens': {
            'primary': '#00ffcc', 'secondary': '#ff00a8', 'background': '#07070d', 'surface': '#111120',
            'text': '#eef2ff', 'muted': '#8b93b5', 'border': '#23233a', 'font': 'Inter',
            'heading_font': 'Orbitron', 'radius': '14px', 'shadow': '0 0 40px rgba(0,255,204,.18)',
        },
    },
    {
        'slug': 'minimal-nordic', 'nombre': 'Minimal Nordic', 'categoria': 'hogar',
        'tags': ['minimal', 'claro', 'nordico', 'calmo', 'escandinavo'],
        'tokens': {
            'primary': '#2f6f6b', 'secondary': '#c9b8a3', 'background': '#f7f6f2', 'surface': '#ffffff',
            'text': '#1f2421', 'muted': '#6f7672', 'border': '#e4e1da', 'font': 'Inter',
            'heading_font': 'Fraunces', 'radius': '10px', 'shadow': '0 12px 30px rgba(31,36,33,.08)',
        },
    },
    {
        'slug': 'luxury-gold', 'nombre': 'Luxury Gold', 'categoria': 'moda',
        'tags': ['lujo', 'dorado', 'elegante', 'premium', 'oscuro'],
        'tokens': {
            'primary': '#c9a227', 'secondary': '#f1e3b5', 'background': '#0e0d0b', 'surface': '#1a1814',
            'text': '#f5f1e8', 'muted': '#a39a86', 'border': '#2c2820', 'font': 'Jost',
            'heading_font': 'Cormorant Garamond', 'radius': '4px', 'shadow': '0 18px 50px rgba(201,162,39,.18)',
        },
    },
    {
        'slug': 'organic-terracotta', 'nombre': 'Organic Terracotta', 'categoria': 'alimentos',
        'tags': ['calido', 'artesanal', 'organico', 'terracota', 'natural'],
        'tokens': {
            'primary': '#b4532a', 'secondary': '#7c8a5a', 'background': '#fbf3e7', 'surface': '#fffaf1',
            'text': '#3b2a20', 'muted': '#8a7565', 'border': '#ead9c5', 'font': 'Nunito Sans',
            'heading_font': 'Playfair Display', 'radius': '18px', 'shadow': '0 14px 34px rgba(59,42,32,.10)',
        },
    },
    {
        'slug': 'streetwear-bold', 'nombre': 'Streetwear Bold', 'categoria': 'moda',
        'tags': ['urbano', 'street', 'bold', 'contraste', 'juvenil'],
        'tokens': {
            'primary': '#ff3b30', 'secondary': '#ffe600', 'background': '#f2f2f2', 'surface': '#ffffff',
            'text': '#0a0a0a', 'muted': '#5c5c5c', 'border': '#111111', 'font': 'Archivo',
            'heading_font': 'Archivo Black', 'radius': '0px', 'shadow': '8px 8px 0 #111111',
        },
    },
    {
        'slug': 'tech-saas-clean', 'nombre': 'Tech SaaS Clean', 'categoria': 'tecnologia',
        'tags': ['saas', 'limpio', 'claro', 'producto', 'moderno'],
        'tokens': {
            'primary': '#4f46e5', 'secondary': '#22d3ee', 'background': '#ffffff', 'surface': '#f8fafc',
            'text': '#0f172a', 'muted': '#64748b', 'border': '#e2e8f0', 'font': 'Inter',
            'heading_font': 'Inter', 'radius': '12px', 'shadow': '0 10px 30px rgba(15,23,42,.08)',
        },
    },
    {
        'slug': 'pastel-bakery', 'nombre': 'Pastel Bakery', 'categoria': 'alimentos',
        'tags': ['pastel', 'dulce', 'bakery', 'suave', 'rosa'],
        'tokens': {
            'primary': '#e98aa8', 'secondary': '#8fd3c7', 'background': '#fff7f9', 'surface': '#ffffff',
            'text': '#4a2c36', 'muted': '#967680', 'border': '#f5dce4', 'font': 'Quicksand',
            'heading_font': 'Pacifico', 'radius': '24px', 'shadow': '0 12px 26px rgba(233,138,168,.18)',
        },
    },
    {
        'slug': 'monochrome-editorial', 'nombre': 'Monochrome Editorial', 'categoria': 'fotografia',
        'tags': ['editorial', 'blanco', 'negro', 'tipografia', 'galeria'],
        'tokens': {
            'primary': '#111111', 'secondary': '#777777', 'background': '#fafafa', 'surface': '#ffffff',
            'text': '#111111', 'muted': '#6b6b6b', 'border': '#dddddd', 'font': 'Libre Franklin',
            'heading_font': 'DM Serif Display', 'radius': '0px', 'shadow': 'none',
        },
    },
    {
        'slug': 'retro-arcade', 'nombre': 'Retro Arcade', 'categoria': 'gaming',
        'tags': ['retro', 'arcade', '8bit', 'pixel', 'nostalgia'],
        'tokens': {
            'primary': '#ffcc00', 'secondary': '#ff4d6d', 'background': '#14102b', 'surface': '#1e1840',
            'text': '#f7f3ff', 'muted': '#a49bc9', 'border': '#3a2f6b', 'font': 'VT323',
            'heading_font': 'Press Start 2P', 'radius': '0px', 'shadow': '0 0 0 4px #3a2f6b',
        },
    },
    {
        'slug': 'glass-frost', 'nombre': 'Glass Frost', 'categoria': 'tecnologia',
        'tags': ['glass', 'cristal', 'blur', 'moderno', 'oscuro'],
        'tokens': {
            'primary': '#7dd3fc', 'secondary': '#c084fc', 'background': '#0b1220', 'surface': 'rgba(255,255,255,.08)',
            'text': '#e6edf7', 'muted': '#9aa8bd', 'border': 'rgba(255,255,255,.16)', 'font': 'Manrope',
            'heading_font': 'Manrope', 'radius': '20px', 'shadow': '0 20px 60px rgba(0,0,0,.35)',
        },
    },
    {
        'slug': 'brutalist-raw', 'nombre': 'Brutalist Raw', 'categoria': 'arte',
        'tags': ['brutalista', 'crudo', 'contraste', 'experimental', 'tipografia'],
        'tokens': {
            'primary': '#0000ff', 'secondary': '#ff0000', 'background': '#ffffff', 'surface': '#f0f0f0',
            'text': '#000000', 'muted': '#444444', 'border': '#000000', 'font': 'Space Mono',
            'heading_font': 'Space Grotesk', 'radius': '0px', 'shadow': '6px 6px 0 #000000',
        },
    },
    {
        'slug': 'tropical-vibrant', 'nombre': 'Tropical Vibrant', 'categoria': 'turismo',
        'tags': ['tropical', 'colorido', 'playa', 'verano', 'energia'],
        'tokens': {
            'primary': '#ff7a00', 'secondary': '#00c2a8', 'background': '#fffaf2', 'surface': '#ffffff',
            'text': '#173a3a', 'muted': '#5f7d7d', 'border': '#ffe3c2', 'font': 'Poppins',
            'heading_font': 'Baloo 2', 'radius': '22px', 'shadow': '0 16px 36px rgba(255,122,0,.16)',
        },
    },
    {
        'slug': 'barber-vintage', 'nombre': 'Barber Vintage', 'categoria': 'servicios',
        'tags': ['vintage', 'barberia', 'clasico', 'masculino', 'retro'],
        'tokens': {
            'primary': '#a63a2b', 'secondary': '#d8c39a', 'background': '#f4efe4', 'surface': '#fffdf7',
            'text': '#2b2118', 'muted': '#7d6c58', 'border': '#dfd2bb', 'font': 'Barlow',
            'heading_font': 'Bebas Neue', 'radius': '6px', 'shadow': '0 10px 24px rgba(43,33,24,.12)',
        },
    },
    {
        'slug': 'clinic-trust', 'nombre': 'Clinic Trust', 'categoria': 'salud',
        'tags': ['salud', 'clinico', 'confianza', 'limpio', 'azul'],
        'tokens': {
            'primary': '#0e7490', 'secondary': '#38bdf8', 'background': '#f6fbfd', 'surface': '#ffffff',
            'text': '#0b2b36', 'muted': '#5b7c88', 'border': '#d7e9ef', 'font': 'Source Sans 3',
            'heading_font': 'Source Sans 3', 'radius': '14px', 'shadow': '0 12px 28px rgba(11,43,54,.08)',
        },
    },
    {
        'slug': 'gym-power', 'nombre': 'Gym Power', 'categoria': 'fitness',
        'tags': ['gym', 'energia', 'oscuro', 'deporte', 'fuerza'],
        'tokens': {
            'primary': '#d4ff00', 'secondary': '#ff5c00', 'background': '#0c0c0c', 'surface': '#161616',
            'text': '#f4f4f4', 'muted': '#9a9a9a', 'border': '#262626', 'font': 'Barlow Condensed',
            'heading_font': 'Anton', 'radius': '4px', 'shadow': '0 14px 40px rgba(212,255,0,.12)',
        },
    },
    {
        'slug': 'jewelry-rose', 'nombre': 'Jewelry Rose', 'categoria': 'joyeria',
        'tags': ['joyeria', 'rosa', 'delicado', 'elegante', 'romantico'],
        'tokens': {
            'primary': '#b76e79', 'secondary': '#e8c9c4', 'background': '#fdf8f7', 'surface': '#ffffff',
            'text': '#3d2b2e', 'muted': '#8b7175', 'border': '#f0dedb', 'font': 'Lato',
            'heading_font': 'Cormorant Garamond', 'radius': '12px', 'shadow': '0 14px 34px rgba(183,110,121,.14)',
        },
    },
    {
        'slug': 'coffee-warm', 'nombre': 'Coffee Warm', 'categoria': 'cafeteria',
        'tags': ['cafe', 'calido', 'marron', 'acogedor', 'artesanal'],
        'tokens': {
            'primary': '#6f4e37', 'secondary': '#c8a27a', 'background': '#f8f1e7', 'surface': '#fffdf9',
            'text': '#2f2219', 'muted': '#7c6653', 'border': '#e6d7c4', 'font': 'Karla',
            'heading_font': 'Lora', 'radius': '16px', 'shadow': '0 12px 30px rgba(47,34,25,.10)',
        },
    },
    {
        'slug': 'kids-playful', 'nombre': 'Kids Playful', 'categoria': 'infantil',
        'tags': ['infantil', 'jugueton', 'colorido', 'redondo', 'divertido'],
        'tokens': {
            'primary': '#ff6b6b', 'secondary': '#4ecdc4', 'background': '#fffdf5', 'surface': '#ffffff',
            'text': '#2f2a4a', 'muted': '#77719b', 'border': '#ffe8a3', 'font': 'Baloo 2',
            'heading_font': 'Fredoka One', 'radius': '28px', 'shadow': '0 14px 0 #ffe8a3',
        },
    },
    {
        'slug': 'automotive-steel', 'nombre': 'Automotive Steel', 'categoria': 'automotriz',
        'tags': ['auto', 'industrial', 'acero', 'tecnico', 'oscuro'],
        'tokens': {
            'primary': '#e10600', 'secondary': '#9aa4ad', 'background': '#111417', 'surface': '#1b2025',
            'text': '#eef1f4', 'muted': '#8d979f', 'border': '#2c333a', 'font': 'Roboto',
            'heading_font': 'Oswald', 'radius': '6px', 'shadow': '0 16px 40px rgba(0,0,0,.45)',
        },
    },
    {
        'slug': 'green-eco', 'nombre': 'Green Eco', 'categoria': 'sustentable',
        'tags': ['eco', 'verde', 'natural', 'sustentable', 'organico'],
        'tokens': {
            'primary': '#2f7d32', 'secondary': '#a3c585', 'background': '#f6faf3', 'surface': '#ffffff',
            'text': '#1d2b1c', 'muted': '#61735f', 'border': '#dbe7d3', 'font': 'Work Sans',
            'heading_font': 'Sora', 'radius': '16px', 'shadow': '0 12px 30px rgba(29,43,28,.08)',
        },
    },
]


#=========================================
# FUENTES DE DISEÑO (repos de referencia)
#=========================================
#Cada fuente es una variación de página de un repo Tailwind real. El seed
#la convierte en un DesignModelMcp completo: tokens (color de acento de la
#fuente + base neutra del repo) y bloques HTML del tipo de página.
FUENTES_DISEÑO = [
    # ---- REPO 1: bbulakh/tailwind-ecommerce (Variaciones) ----
    {"slug": "bb-minimal-home", "url": "https://githubusercontent.com", "cat": "moda", "tag": ["home", "azul", "limpio"], "col": "#3b82f6"},
    {"slug": "bb-minimal-catalog", "url": "https://githubusercontent.com", "cat": "moda", "tag": ["grid", "filtros", "catalogo"], "col": "#3b82f6"},
    {"slug": "bb-minimal-product", "url": "https://githubusercontent.com", "cat": "moda", "tag": ["detalle", "galeria", "producto"], "col": "#3b82f6"},
    {"slug": "bb-minimal-cart", "url": "https://githubusercontent.com", "cat": "moda", "tag": ["checkout", "lista", "carrito"], "col": "#3b82f6"},
    {"slug": "bb-minimal-account", "url": "https://githubusercontent.com", "cat": "admin", "tag": ["perfil", "usuario", "dashboard"], "col": "#3b82f6"},

    # ---- REPO 2: spacemadev/Tailstore (Variaciones) ----
    {"slug": "ts-premium-home", "url": "https://githubusercontent.com", "cat": "general", "tag": ["moderno", "swiper", "premium"], "col": "#10b981"},
    {"slug": "ts-premium-shop", "url": "https://githubusercontent.com", "cat": "general", "tag": ["tienda", "sidebar", "galeria"], "col": "#10b981"},
    {"slug": "ts-premium-detail", "url": "https://githubusercontent.com", "cat": "general", "tag": ["tabs", "reviews", "compras"], "col": "#10b981"},
    {"slug": "ts-premium-checkout", "url": "https://githubusercontent.com", "cat": "checkout", "tag": ["pago", "formulario", "envio"], "col": "#10b981"},
    {"slug": "ts-premium-auth", "url": "https://githubusercontent.com", "cat": "seguridad", "tag": ["login", "registro", "ingreso"], "col": "#10b981"},

    # ---- REPO 3: codescandy/freshcart (Variaciones) ----
    {"slug": "fc-grocery-home", "url": "https://githubusercontent.com", "cat": "alimentos", "tag": ["retail", "fresco", "grocery"], "col": "#0aad0a"},
    {"slug": "fc-grocery-shop", "url": "https://githubusercontent.com", "cat": "alimentos", "tag": ["sidebar", "desplegable", "productos"], "col": "#0aad0a"},
    {"slug": "fc-grocery-single", "url": "https://githubusercontent.com", "cat": "alimentos", "tag": ["zoom", "informacion", "stock"], "col": "#0aad0a"},
    {"slug": "fc-grocery-checkout", "url": "https://githubusercontent.com", "cat": "checkout", "tag": ["resumen", "cupon", "tarjeta"], "col": "#0aad0a"},
    {"slug": "fc-grocery-dashboard", "url": "https://githubusercontent.com", "cat": "admin", "tag": ["metricas", "ordenes", "graficos"], "col": "#0aad0a"},

    # ---- REPO 4: jluterek/tailwind-ecommerce-template (Variaciones) ----
    {"slug": "jl-alpine-home", "url": "https://githubusercontent.com", "cat": "tecnologia", "tag": ["alpine", "ligero", "minimal"], "col": "#4f46e5"},
    {"slug": "jl-alpine-category", "url": "https://githubusercontent.com", "cat": "tecnologia", "tag": ["categorias", "filtros", "cuadrícula"], "col": "#4f46e5"},
    {"slug": "jl-alpine-product", "url": "https://githubusercontent.com", "cat": "tecnologia", "tag": ["galeria", "botones", "descripcion"], "col": "#4f46e5"},
    {"slug": "jl-alpine-cart", "url": "https://githubusercontent.com", "cat": "checkout", "tag": ["tabla", "totales", "comprar"], "col": "#4f46e5"},
    {"slug": "jl-alpine-contact", "url": "https://githubusercontent.com", "cat": "soporte", "tag": ["contacto", "mapa", "formulario"], "col": "#4f46e5"},
]

#Base neutra por repo: el acento sale de la fuente, el resto del sistema visual del repo.
FUENTES_REPOS = {
    'bb': {
        'nombre': 'Tailwind Ecommerce', 'repo': 'bbulakh/tailwind-ecommerce', 'secondary': '#0ea5e9',
        'background': '#ffffff', 'surface': '#f8fafc', 'text': '#0f172a', 'muted': '#64748b',
        'border': '#e2e8f0', 'font': 'Inter', 'heading_font': 'Inter', 'radius': '12px',
        'shadow': '0 10px 30px rgba(15,23,42,.08)',
    },
    'ts': {
        'nombre': 'Tailstore', 'repo': 'spacemadev/Tailstore', 'secondary': '#065f46',
        'background': '#ffffff', 'surface': '#f9fafb', 'text': '#111827', 'muted': '#6b7280',
        'border': '#e5e7eb', 'font': 'Plus Jakarta Sans', 'heading_font': 'Sora', 'radius': '16px',
        'shadow': '0 18px 40px rgba(17,24,39,.08)',
    },
    'fc': {
        'nombre': 'Freshcart', 'repo': 'codescandy/freshcart', 'secondary': '#065f46',
        'background': '#ffffff', 'surface': '#f6fbf6', 'text': '#111827', 'muted': '#6b7280',
        'border': '#e6f0e6', 'font': 'Inter', 'heading_font': 'Inter', 'radius': '10px',
        'shadow': '0 12px 28px rgba(10,173,10,.10)',
    },
    'jl': {
        'nombre': 'Alpine Ecommerce', 'repo': 'jluterek/tailwind-ecommerce-template', 'secondary': '#312e81',
        'background': '#ffffff', 'surface': '#f8fafc', 'text': '#0f172a', 'muted': '#64748b',
        'border': '#e2e8f0', 'font': 'Inter', 'heading_font': 'Manrope', 'radius': '8px',
        'shadow': '0 10px 26px rgba(79,70,229,.10)',
    },
}

#Sufijo de la variación → tipo de página (define qué bloques se generan).
FUENTES_TIPOS = {
    'home': 'home', 'catalog': 'catalog', 'shop': 'catalog', 'category': 'catalog',
    'product': 'product', 'detail': 'product', 'single': 'product',
    'cart': 'checkout', 'checkout': 'checkout',
    'account': 'dashboard', 'dashboard': 'dashboard',
    'auth': 'auth', 'contact': 'contact',
}


def _fuente_partes(slug : str) -> tuple[str, str]:
    prefix, _, variation = slug.partition('-')
    return prefix, variation


def _fuente_tokens(fuente : dict) -> dict:
    prefix, _    =   _fuente_partes(fuente['slug'])
    repo        =   FUENTES_REPOS[prefix]
    return {
        'primary'       :   fuente['col'],
        'secondary'     :   repo['secondary'],
        'background'    :   repo['background'],
        'surface'       :   repo['surface'],
        'text'          :   repo['text'],
        'muted'         :   repo['muted'],
        'border'        :   repo['border'],
        'font'          :   repo['font'],
        'heading_font'  :   repo['heading_font'],
        'radius'        :   repo['radius'],
        'shadow'        :   repo['shadow'],
        'source_repo'   :   repo['repo'],
        'source_url'    :   fuente['url'],
    }


def _fuente_nombre(fuente : dict) -> str:
    prefix, variation  =   _fuente_partes(fuente['slug'])
    return f"{FUENTES_REPOS[prefix]['nombre']} · {variation.replace('-', ' ').title()}"


def _fuente_tipo(slug : str) -> str:
    return FUENTES_TIPOS.get(slug.rpartition('-')[2], 'home')


#=========================================
# COMPONENT BUILDER
#=========================================
def _components(t : dict) -> dict:
    bg, surface, text, muted = t['background'], t['surface'], t['text'], t['muted']
    primary, secondary, border = t['primary'], t['secondary'], t['border']
    radius, heading = t['radius'], t['heading_font']
    head = heading.replace(' ', '_')
    return {
        'header': (
            f'<header class="sticky top-0 z-40 border-b border-[{border}] bg-[{bg}]/90 backdrop-blur">'
            f'<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">'
            f'<a href="/" class="font-[{head}] text-xl font-bold tracking-tight text-[{text}]">Tienda</a>'
            f'<nav class="hidden gap-6 text-sm text-[{muted}] md:flex">'
            f'<a href="#productos" class="hover:text-[{primary}]">Productos</a>'
            f'<a href="#nosotros" class="hover:text-[{primary}]">Nosotros</a>'
            f'<a href="#contacto" class="hover:text-[{primary}]">Contacto</a></nav>'
            f'<a href="#productos" class="rounded-[{radius}] bg-[{primary}] px-4 py-2 text-sm font-semibold text-[{bg}]" style="box-shadow:{t["shadow"]}">Comprar</a>'
            f'</div></header>'
        ),
        'hero': (
            f'<section class="relative overflow-hidden bg-[{bg}] px-6 py-24 text-[{text}]">'
            f'<div class="mx-auto grid max-w-6xl items-center gap-12 md:grid-cols-2">'
            f'<div><p class="mb-4 text-xs font-semibold uppercase tracking-[0.25em] text-[{primary}]">Nueva colección</p>'
            f'<h1 class="font-[{head}] text-4xl font-bold leading-tight md:text-6xl">Diseño que se siente tuyo</h1>'
            f'<p class="mt-6 max-w-md text-base text-[{muted}]">Productos seleccionados, envío a todo el país y atención personalizada.</p>'
            f'<div class="mt-8 flex flex-wrap gap-3">'
            f'<a href="#productos" class="rounded-[{radius}] bg-[{primary}] px-6 py-3 font-semibold text-[{bg}]" style="box-shadow:{t["shadow"]}">Ver catálogo</a>'
            f'<a href="#nosotros" class="rounded-[{radius}] border border-[{border}] px-6 py-3 font-semibold text-[{text}]">Conocer más</a>'
            f'</div></div>'
            f'<div class="aspect-[4/3] rounded-[{radius}] border border-[{border}] bg-[{surface}]" aria-hidden="true"></div>'
            f'</div></section>'
        ),
        'features': (
            f'<section class="bg-[{surface}] px-6 py-16 text-[{text}]"><div class="mx-auto grid max-w-6xl gap-6 md:grid-cols-3">'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Envío rápido</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Despachamos en 24 horas a todo el país.</p></article>'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Pago seguro</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Tarjetas, transferencia y cuotas sin interés.</p></article>'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Atención real</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Te respondemos por WhatsApp en minutos.</p></article>'
            f'</div></section>'
        ),
        'products': (
            f'<section id="productos" class="bg-[{bg}] px-6 py-20 text-[{text}]"><div class="mx-auto max-w-6xl">'
            f'<div class="mb-10 flex items-end justify-between"><h2 class="font-[{head}] text-3xl font-bold">Destacados</h2>'
            f'<a href="/productos" class="text-sm font-semibold text-[{primary}]">Ver todo</a></div>'
            f'<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">'
            + ''.join(
                f'<article class="overflow-hidden rounded-[{radius}] border border-[{border}] bg-[{surface}]">'
                f'<div class="aspect-square bg-[{bg}]" aria-hidden="true"></div>'
                f'<div class="p-4"><h3 class="font-semibold">Producto {i}</h3>'
                f'<p class="mt-1 text-sm text-[{muted}]">${i}900</p>'
                f'<button class="mt-4 w-full rounded-[{radius}] bg-[{secondary}] px-3 py-2 text-sm font-semibold text-[{bg}]">Agregar</button>'
                f'</div></article>'
                for i in range(1, 5)
            )
            + '</div></div></section>'
        ),
        'testimonials': (
            f'<section class="bg-[{surface}] px-6 py-16 text-[{text}]"><div class="mx-auto max-w-4xl text-center">'
            f'<h2 class="font-[{head}] text-3xl font-bold">Lo que dicen nuestros clientes</h2>'
            f'<blockquote class="mx-auto mt-8 max-w-2xl rounded-[{radius}] border border-[{border}] bg-[{bg}] p-8 text-lg">'
            f'“La calidad superó lo que esperaba y llegó antes de lo previsto.”'
            f'<footer class="mt-4 text-sm text-[{muted}]">— Cliente verificado</footer></blockquote>'
            f'</div></section>'
        ),
        'footer': (
            f'<footer id="contacto" class="border-t border-[{border}] bg-[{bg}] px-6 py-12 text-[{muted}]">'
            f'<div class="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">'
            f'<div><p class="font-[{head}] text-lg font-bold text-[{text}]">Tienda</p>'
            f'<p class="mt-2 text-sm">Tu negocio, con una web a la altura.</p></div>'
            f'<div><p class="font-semibold text-[{text}]">Contacto</p>'
            f'<p class="mt-2 text-sm">WhatsApp · Instagram · Email</p></div>'
            f'<div><p class="font-semibold text-[{text}]">Legal</p>'
            f'<p class="mt-2 text-sm">Términos y privacidad</p></div>'
            f'</div></footer>'
        ),
    }


def _fuente_components(tipo : str, t : dict) -> dict:
    bg, surface, text, muted = t['background'], t['surface'], t['text'], t['muted']
    primary, border = t['primary'], t['border']
    radius, head = t['radius'], t['heading_font'].replace(' ', '_')
    shadow = t['shadow']
    blocks = {
        'header': (
            f'<header class="sticky top-0 z-40 border-b border-[{border}] bg-[{bg}]/90 backdrop-blur">'
            f'<div class="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">'
            f'<a href="/" class="font-[{head}] text-xl font-bold tracking-tight text-[{text}]">Tienda</a>'
            f'<nav class="hidden gap-6 text-sm text-[{muted}] md:flex">'
            f'<a href="/catalogo" class="hover:text-[{primary}]">Catálogo</a>'
            f'<a href="/nosotros" class="hover:text-[{primary}]">Nosotros</a>'
            f'<a href="/contacto" class="hover:text-[{primary}]">Contacto</a></nav>'
            f'<a href="/carrito" class="rounded-[{radius}] bg-[{primary}] px-4 py-2 text-sm font-semibold text-[{bg}]" style="box-shadow:{shadow}">Comprar</a>'
            f'</div></header>'
        ),
        'footer': (
            f'<footer class="border-t border-[{border}] bg-[{surface}] px-6 py-12 text-[{muted}]">'
            f'<div class="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">'
            f'<div><p class="font-[{head}] text-lg font-bold text-[{text}]">Tienda</p>'
            f'<p class="mt-2 text-sm">Tu negocio, con una web a la altura.</p></div>'
            f'<div><p class="font-semibold text-[{text}]">Contacto</p>'
            f'<p class="mt-2 text-sm">WhatsApp · Instagram · Email</p></div>'
            f'<div><p class="font-semibold text-[{text}]">Legal</p>'
            f'<p class="mt-2 text-sm">Términos y privacidad</p></div>'
            f'</div></footer>'
        ),
    }
    if tipo == 'home':
        blocks['hero'] = (
            f'<section class="bg-[{bg}] px-6 py-24 text-[{text}]"><div class="mx-auto grid max-w-6xl items-center gap-12 md:grid-cols-2">'
            f'<div><p class="mb-4 text-xs font-semibold uppercase tracking-[0.25em] text-[{primary}]">Nueva colección</p>'
            f'<h1 class="font-[{head}] text-4xl font-bold leading-tight md:text-6xl">Diseño que se siente tuyo</h1>'
            f'<p class="mt-6 max-w-md text-base text-[{muted}]">Productos seleccionados, envío a todo el país y atención personalizada.</p>'
            f'<div class="mt-8 flex flex-wrap gap-3">'
            f'<a href="/catalogo" class="rounded-[{radius}] bg-[{primary}] px-6 py-3 font-semibold text-[{bg}]" style="box-shadow:{shadow}">Ver catálogo</a>'
            f'<a href="/nosotros" class="rounded-[{radius}] border border-[{border}] px-6 py-3 font-semibold text-[{text}]">Conocer más</a>'
            f'</div></div>'
            f'<div class="aspect-[4/3] rounded-[{radius}] border border-[{border}] bg-[{surface}]" aria-hidden="true"></div>'
            f'</div></section>'
        )
        blocks['benefits'] = (
            f'<section class="bg-[{surface}] px-6 py-16 text-[{text}]"><div class="mx-auto grid max-w-6xl gap-6 md:grid-cols-3">'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Envío rápido</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Despachamos en 24 horas a todo el país.</p></article>'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Pago seguro</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Tarjetas, transferencia y cuotas sin interés.</p></article>'
            f'<article class="rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h3 class="font-[{head}] text-lg font-semibold">Atención real</h3>'
            f'<p class="mt-2 text-sm text-[{muted}]">Te respondemos por WhatsApp en minutos.</p></article>'
            f'</div></section>'
        )
        blocks['featured'] = _product_grid(t, 'Destacados', 4)
    elif tipo == 'catalog':
        blocks['filters'] = (
            f'<section class="border-b border-[{border}] bg-[{surface}] px-6 py-6"><div class="mx-auto flex max-w-6xl flex-wrap items-center gap-3">'
            f'<span class="text-sm font-semibold text-[{text}]">Filtrar:</span>'
            f'<button class="rounded-full border border-[{border}] bg-[{bg}] px-4 py-1.5 text-sm text-[{muted}]">Categoría</button>'
            f'<button class="rounded-full border border-[{border}] bg-[{bg}] px-4 py-1.5 text-sm text-[{muted}]">Precio</button>'
            f'<button class="rounded-full border border-[{primary}] bg-[{primary}] px-4 py-1.5 text-sm font-semibold text-[{bg}]">Talle</button>'
            f'<select class="ml-auto rounded-[{radius}] border border-[{border}] bg-[{bg}] px-3 py-1.5 text-sm text-[{text}]">'
            f'<option>Ordenar: destacados</option><option>Menor precio</option><option>Mayor precio</option></select>'
            f'</div></section>'
        )
        blocks['grid'] = _product_grid(t, 'Catálogo', 8)
    elif tipo == 'product':
        blocks['gallery'] = (
            f'<section class="bg-[{bg}] px-6 py-16 text-[{text}]"><div class="mx-auto grid max-w-6xl gap-10 md:grid-cols-2">'
            f'<div><div class="aspect-square rounded-[{radius}] border border-[{border}] bg-[{surface}]" aria-hidden="true"></div>'
            f'<div class="mt-3 grid grid-cols-4 gap-3">'
            + ''.join(
                f'<button class="aspect-square rounded-[{radius}] border border-[{border}] bg-[{surface}]" aria-label="Miniatura {i}"></button>'
                for i in range(1, 5)
            )
            + f'</div></div>'
            f'<div><p class="text-xs font-semibold uppercase tracking-[0.25em] text-[{primary}]">Producto</p>'
            f'<h1 class="mt-3 font-[{head}] text-3xl font-bold md:text-4xl">Nombre del producto</h1>'
            f'<p class="mt-3 text-2xl font-semibold text-[{primary}]">$49.900</p>'
            f'<p class="mt-4 text-sm text-[{muted}]">Descripción breve del producto, materiales y cuidados.</p>'
            f'<div class="mt-6 flex gap-3">'
            f'<button class="rounded-[{radius}] border border-[{border}] px-4 py-2 text-sm text-[{text}]">Talle</button>'
            f'<button class="rounded-[{radius}] border border-[{border}] px-4 py-2 text-sm text-[{text}]">Color</button></div>'
            f'<button class="mt-6 w-full rounded-[{radius}] bg-[{primary}] px-6 py-3 font-semibold text-[{bg}]" style="box-shadow:{shadow}">Agregar al carrito</button>'
            f'<div class="mt-8 border-t border-[{border}] pt-6 text-sm text-[{muted}]">'
            f'<p><strong class="text-[{text}]">Envío:</strong> 24-48 h a todo el país.</p>'
            f'<p class="mt-2"><strong class="text-[{text}]">Cambios:</strong> 30 días sin costo.</p></div>'
            f'</div></div></section>'
        )
        blocks['related'] = _product_grid(t, 'También te puede gustar', 4)
    elif tipo == 'checkout':
        blocks['summary'] = (
            f'<section class="bg-[{bg}] px-6 py-16 text-[{text}]"><div class="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1.4fr_1fr]">'
            f'<div class="rounded-[{radius}] border border-[{border}] bg-[{surface}] p-6">'
            f'<h2 class="font-[{head}] text-xl font-bold">Tu carrito</h2>'
            + ''.join(
                f'<div class="mt-4 flex items-center gap-4 border-t border-[{border}] pt-4">'
                f'<div class="h-16 w-16 rounded-[{radius}] bg-[{bg}]" aria-hidden="true"></div>'
                f'<div class="flex-1"><p class="text-sm font-semibold">Producto {i}</p>'
                f'<p class="text-xs text-[{muted}]">Cantidad 1</p></div>'
                f'<p class="text-sm font-semibold">${i}900</p></div>'
                for i in range(1, 4)
            )
            + f'</div>'
            f'<aside class="h-fit rounded-[{radius}] border border-[{border}] bg-[{surface}] p-6">'
            f'<h2 class="font-[{head}] text-xl font-bold">Resumen</h2>'
            f'<dl class="mt-4 space-y-2 text-sm"><div class="flex justify-between"><dt class="text-[{muted}]">Subtotal</dt><dd>$12.700</dd></div>'
            f'<div class="flex justify-between"><dt class="text-[{muted}]">Envío</dt><dd>Gratis</dd></div>'
            f'<div class="flex justify-between border-t border-[{border}] pt-2 text-base font-semibold"><dt>Total</dt><dd>$12.700</dd></div></dl>'
            f'<div class="mt-4 flex gap-2"><input class="min-w-0 flex-1 rounded-[{radius}] border border-[{border}] bg-[{bg}] px-3 py-2 text-sm" placeholder="Cupón">'
            f'<button class="rounded-[{radius}] border border-[{border}] px-4 py-2 text-sm font-semibold text-[{text}]">Aplicar</button></div>'
            f'<button class="mt-4 w-full rounded-[{radius}] bg-[{primary}] px-4 py-3 font-semibold text-[{bg}]" style="box-shadow:{shadow}">Pagar</button>'
            f'</aside></div></section>'
        )
        blocks['shipping'] = (
            f'<section class="bg-[{surface}] px-6 py-16 text-[{text}]"><div class="mx-auto max-w-5xl rounded-[{radius}] border border-[{border}] bg-[{bg}] p-6">'
            f'<h2 class="font-[{head}] text-xl font-bold">Datos de envío</h2>'
            f'<form class="mt-6 grid gap-4 md:grid-cols-2">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Nombre" aria-label="Nombre">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Apellido" aria-label="Apellido">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Email" aria-label="Email">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Teléfono" aria-label="Teléfono">'
            f'<input class="md:col-span-2 rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Dirección" aria-label="Dirección">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Provincia" aria-label="Provincia">'
            f'<input class="rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Ciudad" aria-label="Ciudad">'
            f'<button type="button" class="md:col-span-2 rounded-[{radius}] bg-[{primary}] px-4 py-3 font-semibold text-[{bg}]">Continuar al pago</button>'
            f'</form></div></section>'
        )
    elif tipo == 'dashboard':
        blocks['sidebar'] = (
            f'<aside class="hidden w-60 shrink-0 border-r border-[{border}] bg-[{surface}] px-4 py-6 lg:block">'
            f'<p class="font-[{head}] text-lg font-bold text-[{text}]">Mi cuenta</p>'
            f'<nav class="mt-6 space-y-1 text-sm">'
            f'<a href="#" class="block rounded-[{radius}] bg-[{primary}] px-3 py-2 font-semibold text-[{bg}]">Resumen</a>'
            f'<a href="#" class="block rounded-[{radius}] px-3 py-2 text-[{muted}] hover:bg-[{bg}]">Pedidos</a>'
            f'<a href="#" class="block rounded-[{radius}] px-3 py-2 text-[{muted}] hover:bg-[{bg}]">Direcciones</a>'
            f'<a href="#" class="block rounded-[{radius}] px-3 py-2 text-[{muted}] hover:bg-[{bg}]">Datos personales</a>'
            f'</nav></aside>'
        )
        blocks['metrics'] = (
            f'<section class="flex-1 bg-[{bg}] px-6 py-10 text-[{text}]"><div class="mx-auto max-w-5xl">'
            f'<h1 class="font-[{head}] text-2xl font-bold">Hola de nuevo</h1>'
            f'<div class="mt-6 grid gap-4 sm:grid-cols-3">'
            + ''.join(
                f'<article class="rounded-[{radius}] border border-[{border}] bg-[{surface}] p-5">'
                f'<p class="text-xs uppercase tracking-wide text-[{muted}]">{label}</p>'
                f'<p class="mt-2 font-[{head}] text-2xl font-bold text-[{primary}]">{value}</p></article>'
                for label, value in (("Pedidos", "12"), ("En tránsito", "2"), ("Puntos", "340"))
            )
            + f'</div>'
            f'<div class="mt-8 rounded-[{radius}] border border-[{border}] bg-[{surface}] p-6">'
            f'<h2 class="font-[{head}] text-lg font-bold">Último pedido</h2>'
            f'<p class="mt-2 text-sm text-[{muted}]">#1042 · En camino · Llega el jueves</p></div>'
            f'</div></section>'
        )
    elif tipo == 'auth':
        blocks['auth'] = (
            f'<section class="grid min-h-[70vh] bg-[{bg}] text-[{text}] md:grid-cols-2">'
            f'<div class="hidden bg-[{primary}] p-12 text-[{bg}] md:flex md:flex-col md:justify-between">'
            f'<p class="font-[{head}] text-2xl font-bold">Tienda</p>'
            f'<p class="max-w-sm text-sm opacity-90">Tu cuenta, tus pedidos y tus direcciones en un solo lugar.</p></div>'
            f'<div class="flex items-center justify-center px-6 py-16"><div class="w-full max-w-sm">'
            f'<h1 class="font-[{head}] text-3xl font-bold">Ingresar</h1>'
            f'<form class="mt-8 space-y-4">'
            f'<input class="w-full rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Email" aria-label="Email">'
            f'<input type="password" class="w-full rounded-[{radius}] border border-[{border}] bg-[{surface}] px-4 py-2.5 text-sm" placeholder="Contraseña" aria-label="Contraseña">'
            f'<button type="button" class="w-full rounded-[{radius}] bg-[{primary}] px-4 py-3 font-semibold text-[{bg}]" style="box-shadow:{shadow}">Entrar</button>'
            f'</form>'
            f'<p class="mt-6 text-sm text-[{muted}]">¿No tenés cuenta? <a href="#" class="font-semibold text-[{primary}]">Registrate</a></p>'
            f'</div></div></section>'
        )
    elif tipo == 'contact':
        blocks['contact'] = (
            f'<section class="bg-[{bg}] px-6 py-16 text-[{text}]"><div class="mx-auto grid max-w-5xl gap-8 md:grid-cols-2">'
            f'<div><h1 class="font-[{head}] text-3xl font-bold">Contacto</h1>'
            f'<p class="mt-3 text-sm text-[{muted}]">Escribinos y te respondemos dentro del día.</p>'
            f'<dl class="mt-6 space-y-3 text-sm"><div><dt class="font-semibold">WhatsApp</dt><dd class="text-[{muted}]">+54 9 11 0000 0000</dd></div>'
            f'<div><dt class="font-semibold">Email</dt><dd class="text-[{muted}]">hola@tienda.com</dd></div>'
            f'<div><dt class="font-semibold">Horario</dt><dd class="text-[{muted}]">Lun a vie, 9 a 18 h</dd></div></dl>'
            f'<div class="mt-6 aspect-[4/3] rounded-[{radius}] border border-[{border}] bg-[{surface}]" aria-hidden="true"></div></div>'
            f'<form class="h-fit rounded-[{radius}] border border-[{border}] bg-[{surface}] p-6">'
            f'<input class="w-full rounded-[{radius}] border border-[{border}] bg-[{bg}] px-4 py-2.5 text-sm" placeholder="Nombre" aria-label="Nombre">'
            f'<input class="mt-4 w-full rounded-[{radius}] border border-[{border}] bg-[{bg}] px-4 py-2.5 text-sm" placeholder="Email" aria-label="Email">'
            f'<textarea rows="5" class="mt-4 w-full rounded-[{radius}] border border-[{border}] bg-[{bg}] px-4 py-2.5 text-sm" placeholder="Mensaje" aria-label="Mensaje"></textarea>'
            f'<button type="button" class="mt-4 w-full rounded-[{radius}] bg-[{primary}] px-4 py-3 font-semibold text-[{bg}]" style="box-shadow:{shadow}">Enviar</button>'
            f'</form></div></section>'
        )
    return blocks


def _product_grid(t : dict, title : str, total : int) -> str:
    bg, surface, text, muted = t['background'], t['surface'], t['text'], t['muted']
    primary, secondary, border = t['primary'], t['secondary'], t['border']
    radius, head = t['radius'], t['heading_font'].replace(' ', '_')
    return (
        f'<section class="bg-[{bg}] px-6 py-20 text-[{text}]"><div class="mx-auto max-w-6xl">'
        f'<div class="mb-10 flex items-end justify-between"><h2 class="font-[{head}] text-3xl font-bold">{title}</h2>'
        f'<a href="/catalogo" class="text-sm font-semibold text-[{primary}]">Ver todo</a></div>'
        f'<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">'
        + ''.join(
            f'<article class="overflow-hidden rounded-[{radius}] border border-[{border}] bg-[{surface}]">'
            f'<div class="aspect-square bg-[{bg}]" aria-hidden="true"></div>'
            f'<div class="p-4"><h3 class="font-semibold">Producto {i}</h3>'
            f'<p class="mt-1 text-sm text-[{muted}]">${i}900</p>'
            f'<button class="mt-4 w-full rounded-[{radius}] bg-[{secondary}] px-3 py-2 text-sm font-semibold text-[{bg}]">Agregar</button>'
            f'</div></article>'
            for i in range(1, total + 1)
        )
        + '</div></div></section>'
    )


def build_styles() -> list[dict]:
    styles  =   [
        {
            'slug'              :   preset['slug'],
            'nombre'            :   preset['nombre'],
            'categoria'         :   preset['categoria'],
            'tags'              :   preset['tags'],
            'tokens_diseno'     :   preset['tokens'],
            'html_componentes'  :   _components(preset['tokens']),
        }
        for preset in PRESETS
    ]
    #Fuentes externas: tokens del repo + color de acento de la variación y
    #bloques del tipo de página que representa el slug.
    for fuente in FUENTES_DISEÑO:
        tokens  =   _fuente_tokens(fuente)
        styles.append({
            'slug'              :   fuente['slug'],
            'nombre'            :   _fuente_nombre(fuente),
            'categoria'         :   fuente['cat'],
            'tags'              :   fuente['tag'],
            'tokens_diseno'     :   tokens,
            'html_componentes'  :   _fuente_components(_fuente_tipo(fuente['slug']), tokens),
        })
    return styles
