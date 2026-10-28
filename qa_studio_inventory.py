"""PASO 0 — Inventario verificado en navegador: para CADA opción del contrato
del Studio, ¿la vista previa (?studio=1 + studio:update) la refleja en el
render? ¿La web pública la aplica?

Estrategia: cargar /bench-store?studio=1, medir estilos computados ANTES y
DESPUÉS de postear un studio:update con TODAS las opciones en valores no
default. Una propiedad que cambia = la opción está implementada en esa
superficie. Después se repite sin ?studio=1 (web pública) y en /catalogo y
/servicios, desktop 1280 y móvil 390.
"""
import json
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5173/bench-store'

# Tema de prueba: TODAS las opciones del contrato en valores no-default.
THEME = {
    'palette': {
        'primary': '#e11d48', 'secondary': '#be123c', 'accent': '#e11d48',
        'bg': '#fff7ed', 'surface': '#fefce8', 'text': '#1c1917',
        'muted': '#78716c', 'border': '#e7e5e4', 'success': '#15803d',
        'danger': '#b91c1c',
    },
    'containers': {'radius': 'xl', 'shadow': 'deep', 'border': 'bold', 'density': 'spacious', 'surface': 'outlined'},
    'typography': {'heading': 'playfair-display', 'body': 'lora', 'scale': 'editorial', 'weightHeading': 600, 'letterSpacing': '0.03em'},
    'buttons': {'shape': 'square', 'style': 'outline', 'size': 'lg'},
    'background': {'type': 'gradient', 'value': 'linear-gradient(120deg,#fff7ed,#fecdd3)', 'overlay': 'soft'},
    'motion': {'reveal': 'fade', 'hover': 'glow', 'intensity': 'bold'},
    'mobile': {'nav': 'bottom', 'gridCols': 2, 'cardStyle': 'overlay', 'stickyCta': True, 'heroHeight': 'tall'},
}

MSG = {'type': 'studio:update', 'theme': THEME, 'layout': {}, 'template': 'aurora', 'device': 'desktop', 'mode': 'light'}

# Sondeos: (etiqueta opción, selector, propiedad computada). Se mide en el
# elemento más representativo de cada superficie.
PROBES_LANDING = [
    ('palette.accent->.sp-btn bg',        '.sp-btn',          'backgroundColor'),
    ('palette.primary->.sp-btn bg',       '.sp-btn',          'backgroundColor'),
    ('palette.bg->page bg',               '.store-page',      'backgroundColor'),
    ('palette.surface->.tpc bg',          '.tpc',             'backgroundColor'),
    ('palette.text->page color',          '.store-page',      'color'),
    ('palette.muted->.sp-muted?',         '.sp-section-kicker, .sp-about-text, .tpc-desc', 'color'),
    ('palette.border->.sp-card border',   '.sp-card, .tpc',   'borderTopColor'),
    ('typography.heading->h1 font',       '.sp-hero-title, h1', 'fontFamily'),
    ('typography.body->page font',        '.store-page',      'fontFamily'),
    ('typography.scale->h1 size',         '.sp-hero-title, h1', 'fontSize'),
    ('typography.scale->body size',       '.store-page',      'fontSize'),
    ('typography.weightHeading->h1',      '.sp-hero-title, h1', 'fontWeight'),
    ('typography.letterSpacing->h1',      '.sp-hero-title, h1', 'letterSpacing'),
    ('containers.radius->.tpc radius',    '.tpc',             'borderTopLeftRadius'),
    ('containers.radius->.sp-card radius','.sp-card, .tpc',   'borderTopLeftRadius'),
    ('containers.shadow->.tpc shadow',    '.tpc',             'boxShadow'),
    ('containers.shadow->.sp-card shadow','.sp-card, .tpc',   'boxShadow'),
    ('containers.border->.tpc border-w',  '.tpc',             'borderTopWidth'),
    ('containers.density->.tpc padding',  '.tpc',             'paddingTop'),
    ('containers.surface->.tpc bg/border','.tpc',             'borderTopWidth'),
    ('buttons.shape->.sp-btn radius',     '.sp-btn',          'borderTopLeftRadius'),
    ('buttons.style->.sp-btn bg/border',  '.sp-btn',          'backgroundColor'),
    ('buttons.style->.sp-btn border',     '.sp-btn',          'borderTopWidth'),
    ('buttons.size->.sp-btn height',      '.sp-btn',          'height'),
    ('buttons.size->.sp-btn font-size',   '.sp-btn',          'fontSize'),
    ('background.type->page bg-image',    '.store-page',      'backgroundImage'),
    ('motion.reveal->.sp-rv opacity',     '.sp-rv',           'opacity'),
    ('motion.reveal->.sp-rv translate',   '.sp-rv',           'translate'),
    ('motion.hover->.tpc:hover transform','.tpc',             'transform'),
    ('motion.intensity->.sp-rv dur',      '.sp-rv',           'transitionDuration'),
]

PROBES_SERVICES = [
    ('containers.radius->.sv-item radius','.sv-item, .sv-step', 'borderTopLeftRadius'),
    ('containers.shadow->.sv-item shadow','.sv-item, .sv-step', 'boxShadow'),
    ('containers.border->.sv-item border','.sv-item, .sv-step', 'borderTopWidth'),
    ('containers.density->.sv-item pad',  '.sv-item, .sv-step', 'paddingTop'),
    ('containers.surface->.sv-item',      '.sv-item, .sv-step', 'borderTopColor'),
    ('buttons.style->.sv-btn bg',         '.sv-btn',          'backgroundColor'),
    ('buttons.shape->.sv-btn radius',     '.sv-btn',          'borderTopLeftRadius'),
    ('buttons.size->.sv-btn height',      '.sv-btn',          'minHeight'),
    ('typography.heading->h1 font',       '.sv-hero h1, .sv-title, h1', 'fontFamily'),
    ('typography.scale->h1 size',         '.sv-hero h1, .sv-title, h1', 'fontSize'),
    ('typography.weightHeading->h1',      '.sv-hero h1, .sv-title, h1', 'fontWeight'),
    ('typography.letterSpacing->h1',      '.sv-hero h1, .sv-title, h1', 'letterSpacing'),
    ('motion.reveal->.sv-rv opacity',     '.sv-rv',           'opacity'),
    ('motion.reveal->.sv-rv transform',   '.sv-rv',           'transform'),
    ('motion.hover->.sv-item:hover',      '.sv-item, .sv-step', 'transform'),
    ('background.type->.sv-page bg',      '.sv-page',         'backgroundImage'),
    ('mobile.gridCols->.sv-list cols',    '.sv-list',         'gridTemplateColumns'),
]

PROBES_MOBILE = [
    ('mobile.nav->.sp-top position',      '.sp-top',          'position'),
    ('mobile.nav->.sp-top display',       '.sp-top',          'display'),
    ('mobile.nav->.sp-dock display',      '.sp-dock',         'display'),
    ('mobile.gridCols->.sp-grid cols',    '.sp-grid',         'gridTemplateColumns'),
    ('mobile.cardStyle->.tpc layout',     '.tpc',             'display'),
    ('mobile.stickyCta->cta fijo',        '.sp-dock, .sp-sticky-cta, .tpc-add', 'display'),
    ('mobile.heroHeight->hero height',    '.sp-hero, .sp-hero-band, [class*="-hero"]', 'minHeight'),
]

def probe(page, probes):
    out = {}
    for label, sel, prop in probes:
        val = page.evaluate(
            """([sel, prop]) => {
                const el = document.querySelector(sel);
                if (!el) return '__NO_EL__';
                return getComputedStyle(el)[prop];
            }""", [sel, prop])
        out[label] = val
    return out

def post_theme(page):
    page.evaluate(f"() => window.postMessage({json.dumps(MSG)}, window.location.origin)")
    page.wait_for_timeout(1200)

def vars_and_attrs(page):
    return page.evaluate("""() => {
        const el = document.querySelector('.store-page');
        if (!el) return null;
        const st = [...el.style].filter((k) => k.startsWith('--st-') || k.startsWith('--sp-') || k.startsWith('--store-'));
        const at = [...el.attributes].filter((a) => a.name.startsWith('data-st-')).map((a) => `${a.name}=${a.value}`);
        return { vars: st.length, sample: st.slice(0, 4), attrs: at };
    }""")

def run_surface(pw, path, probes, width, label):
    page = pw.chromium.launch().new_page(viewport={'width': width, 'height': 900})
    page.goto(f'{BASE}{path}', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(900)
    before = probe(page, probes)
    post_theme(page)
    after = probe(page, probes)
    meta = vars_and_attrs(page)
    page.close()
    print(f'\n===== {label} ({path}, {width}px) =====')
    print('  meta después de update:', json.dumps(meta, ensure_ascii=False)[:300])
    for (name, sel, _p) in probes:
        b, a = before[name], after[name]
        mark = 'SÍ' if (b != a and a != '__NO_EL__') else ('  ·sin el' if a == '__NO_EL__' else 'NO')
        print(f'  [{mark:>6}] {name:42} {str(b)[:38]} -> {str(a)[:38]}')

with sync_playwright() as pw:
    # ---- Vista previa (studio=1 + postMessage), desktop ----
    run_surface(pw, '?studio=1', PROBES_LANDING, 1280, 'PREVIEW landing')

    # ---- Vista previa, servicios ----
    page = pw.chromium.launch().new_page(viewport={'width': 1280, 'height': 900})
    page.goto(f'{BASE}/servicios?studio=1', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(900)
    # Los servicios no tienen items en bench-store: medir lo que haya.
    before = probe(page, PROBES_SERVICES)
    post_theme(page)
    after = probe(page, PROBES_SERVICES)
    meta = vars_and_attrs(page)
    page.close()
    print('\n===== PREVIEW servicios (1280px) =====')
    print('  meta:', json.dumps(meta, ensure_ascii=False)[:300])
    for (name, sel, _p) in PROBES_SERVICES:
        b, a = before[name], after[name]
        mark = 'SÍ' if (b != a and a != '__NO_EL__') else ('  ·sin el' if a == '__NO_EL__' else 'NO')
        print(f'  [{mark:>6}] {name:42} {str(b)[:38]} -> {str(a)[:38]}')

    # ---- Vista previa móvil 390 (catálogo para la grilla) ----
    page = pw.chromium.launch().new_page(viewport={'width': 390, 'height': 844})
    page.goto(f'{BASE}/catalogo?studio=1', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(900)
    before = probe(page, PROBES_MOBILE)
    post_theme(page)
    after = probe(page, PROBES_MOBILE)
    page.close()
    print('\n===== PREVIEW catálogo móvil (390px) =====')
    for (name, sel, _p) in PROBES_MOBILE:
        b, a = before[name], after[name]
        mark = 'SÍ' if (b != a and a != '__NO_EL__') else ('  ·sin el' if a == '__NO_EL__' else 'NO')
        print(f'  [{mark:>6}] {name:42} {str(b)[:38]} -> {str(a)[:38]}')

    # ---- WEB PÚBLICA (sin ?studio=1): el tema ni siquiera viaja al DOM ----
    page = pw.chromium.launch().new_page(viewport={'width': 1280, 'height': 900})
    page.goto(BASE, wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(900)
    meta = vars_and_attrs(page)
    btn_r = page.evaluate("() => getComputedStyle(document.querySelector('.sp-btn')||document.body).borderTopLeftRadius")
    page.close()
    print('\n===== WEB PÚBLICA (sin studio) =====')
    print('  vars/attrs en .store-page:', json.dumps(meta, ensure_ascii=False))
    print('  .sp-btn radius:', btn_r, '(site_theme guardado = {} => debe ser el look actual)')
    print('\nDONE')
