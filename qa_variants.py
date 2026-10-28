"""QA de variantes de bloques: inyecta layout_config via ?studio=1 + postMessage
(sin tocar la DB ni esperar el cache público). Recorre los 7 anchos exigidos,
mide scrollWidth <= innerWidth, desbordes de elementos y presencia de las
clases/attrs de cada variante. Uso: venv/Scripts/python.exe qa_variants.py
"""
import sys, json, pathlib, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

# Token del usuario QA: los throttles anónimos (store_visit 120/h) no aplican
# a requests autenticados — sin esto las ~90 cargas agotan el rate.
TOKEN = json.load(urllib.request.urlopen(urllib.request.Request(
    'http://127.0.0.1:8000/api/token/', method='POST',
    data=json.dumps({'username': 'qablocks2', 'password': 'QaBlocks2026!'}).encode(),
    headers={'Content-Type': 'application/json'}), timeout=10))['access']

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'qa_out' / 'variants'
OUT.mkdir(parents=True, exist_ok=True)

BASE = 'http://localhost:5173/bench-store'
CAT = BASE + '/catalogo'
EMPTY = 'http://localhost:5173/qatienda2'
WIDTHS = [320, 360, 390, 768, 1024, 1280, 1920]

def surface(name, *items):
    blocks = []
    for i, b in enumerate(items):
        blk = {'id': b[0], 'enabled': True, 'order': i}
        if len(b) > 1 and b[1]: blk['variant'] = b[1]
        blocks.append(blk)
    return {name: {'blocks': blocks}}

# Layouts de landing por escenario (los bloques sin datos se ocultan solos).
LANDING_BASE = [
    ('hero', 'compact'), ('announcements', None), ('categories', None), ('featured', None),
    ('about', None), ('services', None), ('stats', 'cards'), ('benefits', 'cards'),
    ('offers', None), ('brands', 'marquee'), ('countdown', 'card'), ('timeline', None),
    ('team', None), ('gallery', 'grid'), ('testimonials', 'cards'), ('faq', 'accordion'),
    ('video', None), ('cta', 'card'), ('contact', 'card')
]
def landing(hero='compact', **variants):
    blocks = []
    for bid, default in LANDING_BASE:
        v = variants.get(bid, hero if bid == 'hero' else default)
        blocks.append((bid, v))
    return surface('landing', *blocks)

HEROES = ['centered', 'split', 'cinema', 'editorial', 'search', 'slides']
COMBO_A = landing('centered', categories='rail', featured='cats', benefits='bento',
                  testimonials='carousel', brands='logos', gallery='masonry', faq='cols',
                  offers='rail', countdown='band', cta='band', contact='map', announcements='static')
COMBO_B = landing('search', featured='lead', testimonials='masonry', gallery='rail',
                  faq='list', offers='quick', stats='band', cta='band')
COMBO_C = landing('editorial', featured='masonry', benefits='bento', faq='cols', contact='map')
COMBO_D = landing('split', featured='rail', testimonials='carousel', brands='logos')

CATALOG_VARIANTS = ['cols2', 'cols3', 'cols4', 'masonry', 'list', 'lead', 'quick']
def catalog_layout(grid='auto', filters='panel'):
    return {'catalog': {'blocks': [
        {'id': 'note', 'enabled': True, 'order': 0},
        {'id': 'filters', 'enabled': True, 'order': 1, 'variant': filters},
        {'id': 'sort', 'enabled': True, 'order': 2},
        {'id': 'grid', 'enabled': True, 'order': 3, 'variant': grid},
        {'id': 'promo', 'enabled': True, 'order': 4},
        {'id': 'banner', 'enabled': True, 'order': 5},
    ]}}

CHECK_JS = """() => {
  const out = { sw: document.documentElement.scrollWidth, iw: window.innerWidth, over: [], past: [] };
  document.querySelectorAll('*').forEach(e => {
    const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
    const tag = e.tagName.toLowerCase();
    if (!r.width || !r.height || cs.visibility === 'hidden' || cs.display === 'none') return;
    if (['svg','path','circle','rect','line','polyline','polygon','script','style','meta','link','title','br','option'].includes(tag)) return;
    if (e.scrollWidth > e.clientWidth + 1 && cs.overflowX === 'visible' && r.right > innerWidth + 1)
      out.over.push(String(e.className.baseVal || e.className || tag).slice(0, 70));
  });
  // Controles que se cortan en el borde (quedan invisibles/inusables por
  // un ancestro overflow:hidden) — los rieles con snap se excluyen porque
  // su desborde es intencional y se alcanza con scroll propio.
  document.querySelectorAll('button, a[href], input, select, textarea').forEach(e => {
    if (e.closest('.sp-ann, [class*="-rail"], [class*="-track"], [class*="marquee"], .sp-hal-bg, .cf-chipbar, [aria-hidden="true"]')) return;
    const r = e.getBoundingClientRect();
    if (r.width > 4 && r.height > 4 && r.right > innerWidth + 1)
      out.past.push(String(e.className.baseVal || e.className || e.tagName).slice(0, 70) + '@' + (r.right | 0));
  });
  out.hal = !!document.querySelector('.sp-hal');
  out.variants = [...new Set([...document.querySelectorAll('[data-blk-variant]')].map(e => e.dataset.blkVariant))];
  out.cvGrid = document.querySelector('[data-cv-grid]')?.dataset.cvGrid || null;
  out.chips = !!document.querySelector('.cf-chipbar');
  out.tpcs = document.querySelectorAll('.tpc').length;
  return out;
}"""

results = []
def shot(page, name, w, check=True):
    page.set_viewport_size({'width': w, 'height': 900})
    page.wait_for_timeout(500)
    data = page.evaluate(CHECK_JS) if check else {}
    ok = not data or (data['sw'] <= data['iw'] and not data['over'] and not data.get('past'))
    results.append((name, w, ok, data))
    flag = 'OK ' if ok else 'FAIL'
    print(f"{flag} {name:38s} w={w:4d} sw={data.get('sw')} over={data.get('over', [])[:3]} past={data.get('past', [])[:3]}", flush=True)
    page.screenshot(path=str(OUT / f"{name}-{w}.png"))

def update(page, layout=None, template='classic', theme=None):
    msg = {'type': 'studio:update', 'template': template}
    if layout: msg['layout'] = layout
    if theme: msg['theme'] = theme
    page.evaluate("(m) => window.postMessage(m, window.location.origin)", msg)
    page.wait_for_timeout(900)

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR',
                       reduced_motion='reduce',
                       extra_http_headers={'Authorization': f'Bearer {TOKEN}'}).new_page()

    print('== baseline: layout por defecto (sin config nueva) ==', flush=True)
    page.goto(BASE + '?studio=1', wait_until='domcontentloaded')
    page.wait_for_selector('.sp-hero, .sp-hal', timeout=30000)
    page.wait_for_timeout(1500)
    for w in [1280, 390]: shot(page, 'base-default', w)

    print('== hero variants ==', flush=True)
    for v in HEROES:
        update(page, layout=landing(v))
        for w in [1280, 390]: shot(page, f'hero-{v}', w)

    print('== combos de landing ==', flush=True)
    for name, cfg in [('combo-a', COMBO_A), ('combo-b', COMBO_B), ('combo-c', COMBO_C), ('combo-d', COMBO_D)]:
        update(page, layout=cfg)
        for w in WIDTHS: shot(page, name, w)

    print('== combo-a en otra plantilla (shop) ==', flush=True)
    update(page, layout=COMBO_A, template='shop')
    for w in [1280, 768, 390]: shot(page, 'combo-a-shop', w)

    print('== combo-a con siteTheme (variables --st-*) ==', flush=True)
    update(page, layout=COMBO_A, template='classic',
           theme={'palette': {'accent': '#b45309', 'bg': '#fff7ed', 'surface': '#ffffff',
                              'text': '#1c1917', 'muted': '#57534e', 'border': '#e7e5e4'}})
    for w in [1280, 390]: shot(page, 'combo-a-theme', w)

    print('== catálogo: grid variants + chips ==', flush=True)
    page.goto(CAT + '?studio=1', wait_until='domcontentloaded')
    page.wait_for_selector('.tpc, .cv-outer', timeout=30000)
    page.wait_for_timeout(1500)
    update(page, layout=catalog_layout('auto', 'panel'))
    for w in [1280, 390]: shot(page, 'cat-auto', w)
    for g in CATALOG_VARIANTS:
        update(page, layout=catalog_layout(g, 'chips'))
        for w in [1280, 768, 390, 320]: shot(page, f'cat-{g}-chips', w)
    update(page, layout=catalog_layout('cols3', 'panel'))
    for w in [1280, 390]: shot(page, 'cat-cols3-panel', w)

    print('== tienda vacía (sin datos) ==', flush=True)
    page.goto(EMPTY + '?studio=1', wait_until='domcontentloaded')
    page.wait_for_timeout(2500)
    update(page, layout=landing('centered', featured='cats', benefits='bento',
                                testimonials='carousel', gallery='masonry', faq='cols',
                                cta='band', contact='map'))
    for w in [1280, 390]: shot(page, 'empty-centered', w)
    update(page, layout=landing('search'))
    for w in [1280, 390]: shot(page, 'empty-search', w)
    update(page, layout=landing('slides'))
    for w in [1280, 390]: shot(page, 'empty-slides', w)

    b.close()

fails = [r for r in results if not r[2]]
print('\n== RESUMEN ==')
print(f"checks: {len(results)} | fails: {len(fails)}")
for name, w, ok, data in fails:
    print(f"  FAIL {name} w={w} over={data.get('over', [])[:6]}")
sys.exit(1 if fails else 0)
