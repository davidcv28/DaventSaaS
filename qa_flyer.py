"""QA flyer generator: seed + screenshots multi-formato. Uso: qa_flyer.py [seed|shots|all]"""
import sys, json, pathlib, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'qa_out' / 'flyer'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://localhost:8000'
FRONT = 'http://localhost:5173'
USER, PASS = 'qablocks2', 'QaBlocks2026!'
SLUG = 'qatienda2'
MODE = sys.argv[1] if len(sys.argv) > 1 else 'all'


def img_bytes(color_a, color_b, w=800, h=800):
    im = Image.new('RGB', (w, h), color_a)
    d = ImageDraw.Draw(im)
    d.ellipse((w // 5, h // 5, w * 4 // 5, h * 4 // 5), fill=color_b)
    b = io.BytesIO(); im.save(b, 'JPEG')
    return b.getvalue()


def seed():
    tok = requests.post(f'{BASE}/api/token/', json={'username': USER, 'password': PASS}).json()['access']
    H = {'Authorization': f'Bearer {tok}'}
    prods = requests.get(f'{BASE}/api/products/', headers=H, params={'page_size': 200}).json()
    prods = prods if isinstance(prods, list) else prods.get('results', [])
    print('productos existentes:', len(prods))
    specs = [
        ('Combo Almacén Familiar Premium con Aceite y Harina 60k', 18900, 15500, True),
        ('Coca Cola 2.25L retornable', 3400, None, True),
        ('Pack Yerba Mate 1kg x2', 9800, 8500, True),
        ('Fernet Branca 750ml', 14500, None, True),
        ('Queso cremoso por kg', 7200, 6100, False),
        ('Pan de campo artesanal', 2100, None, False),
        ('Dulce de leche repostero 1kg', 5400, 4700, False),
        ('Aceite de oliva extra virgen 500ml', 8600, None, False),
        ('Harina de almendras 250g', 6300, None, False),
    ]
    existing = {p['name'] for p in prods}
    palette = [(200, 90, 60), (60, 120, 180), (90, 160, 90), (180, 150, 60), (150, 80, 160), (60, 160, 160)]
    for i, (name, price, offer, with_img) in enumerate(specs):
        if name in existing:
            continue
        files = {'image': ('p.jpg', img_bytes(palette[i % len(palette)], (240, 230, 215)), 'image/jpeg')} if with_img else None
        data = {'name': name, 'price': price, 'is_active': 'true'}
        if offer:
            data['offer_price'] = offer
        r = requests.post(f'{BASE}/api/products/', headers=H, data=data, files=files)
        print(' producto', name[:28], r.status_code)
    svcs = requests.get(f'{BASE}/api/services/', headers=H, params={'page_size': 200}).json()
    svcs = svcs if isinstance(svcs, list) else svcs.get('results', [])
    print('servicios existentes:', len(svcs))
    svc_specs = [
        ('Reparto a domicilio en el día', 'Zona centro y alrededores', 1500, 'truck'),
        ('Instalación y puesta en marcha', 'Incluye prueba y garantía', None, 'wrench'),
        ('Corte y confección a medida', 'Por pedido, con muestra', 4500, 'scissors'),
        ('Asesoría personalizada', 'Te ayudamos a elegir', None, 'sparkles'),
        ('Grabado y personalización', 'Regalos empresariales', 2800, 'crown'),
        ('Mantenimiento mensual', 'Plan recurrente con prioridad', 12000, 'flame'),
    ]
    sexisting = {s['name'] for s in svcs}
    for name, desc, price, icon in svc_specs:
        if name in sexisting:
            continue
        payload = {'name': name, 'description': desc, 'price': price, 'icon': icon, 'is_active': True}
        r = requests.post(f'{BASE}/api/services/', headers=H, json=payload)
        print(' servicio', name[:28], r.status_code)
    cust = requests.get(f'{BASE}/api/stores/customization/', headers=H).json()
    patch = {}
    if not (cust.get('headline') or '').strip():
        patch['headline'] = 'Calidad y precio, siempre cerca tuyo'
    if not (cust.get('whatsapp') or '').strip():
        patch['whatsapp'] = '+54 9 387 155 1234'
    if not cust.get('benefits'):
        patch['benefits'] = [
            {'icon': 'truck', 'title': 'Envíos en el día', 'text': 'Zona centro'},
            {'icon': 'credit-card', 'title': 'Todas las tarjetas', 'text': ''},
            {'icon': 'shield-check', 'title': 'Garantía real', 'text': ''},
            {'icon': 'users', 'title': 'Atención personalizada', 'text': ''},
        ]
    if not cust.get('services'):
        patch['services'] = [
            {'icon': 'truck', 'title': 'Reparto a domicilio', 'text': 'Zona centro'},
            {'icon': 'wrench', 'title': 'Instalación', 'text': 'A convenir'},
            {'icon': 'scissors', 'title': 'Corte a medida', 'text': 'Por pedido'},
        ]
    if patch:
        r = requests.patch(f'{BASE}/api/stores/customization/', headers=H, json=patch)
        print('customization patch', r.status_code, list(patch.keys()))
    # galería: una foto de muestra para el diseñador
    gal = requests.get(f'{BASE}/api/stores/customization/', headers=H).json().get('gallery') or []
    if not gal:
        r = requests.post(f'{BASE}/api/stores/customization/gallery/', headers=H,
                          files={'image': ('g.jpg', img_bytes((40, 80, 140), (220, 200, 160), 1200, 800), 'image/jpeg')})
        print('galería', r.status_code)


DRAFT_KEY = f'davent:flyer-draft:{SLUG}'

CHECK_JS = """
() => {
  const out = { sw: document.documentElement.scrollWidth, iw: window.innerWidth, over: [] };
  document.querySelectorAll('.studio, .studio *').forEach((e) => {
    const r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const cs = getComputedStyle(e);
    if (e.scrollWidth > e.clientWidth + 1 && cs.overflowX === 'visible') out.over.push(e.className || e.tagName);
  });
  const fc = document.querySelector('.studio-sheet .fc');
  if (fc) {
    const r = fc.getBoundingClientRect();
    out.fc = { w: Math.round(r.width), h: Math.round(r.height), ratio: +(r.width / r.height).toFixed(3) };
  }
  const bar = [...document.querySelectorAll('h3')].map(h => h.innerText).join(' | ');
  out.h3 = bar;
  return out;
}
"""

CASES = [
    ('a4-corporativo',   {'kind': 'empresa',   'layout': 'corporativo', 'size': 'a4',   'sheet': 'own', 'source': 'landing'}),
    ('carta-carta',      {'kind': 'catalogo',  'layout': 'carta',       'size': 'carta','sheet': 'own', 'source': 'landing'}),
    ('a5-impacto',       {'kind': 'marketing', 'layout': 'impacto',     'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a6-vitrina',       {'kind': 'catalogo',  'layout': 'vitrina',     'size': 'a6',   'sheet': 'a4',  'source': 'landing'}),
    ('a7-anuncio',       {'kind': 'empresa',   'layout': 'anuncio',     'size': 'a7',   'sheet': 'a4',  'source': 'landing'}),
    ('post-oferta',      {'kind': 'marketing', 'layout': 'oferta',      'size': 'post', 'sheet': 'a4',  'source': 'landing'}),
    ('story-story',      {'kind': 'marketing', 'layout': 'story',       'size': 'story','sheet': 'a4',  'source': 'landing'}),
    ('banner-banner',    {'kind': 'marketing', 'layout': 'banner',      'size': 'banner','sheet': 'a4', 'source': 'catalog'}),
    ('a5-nueve',         {'kind': 'catalogo',  'layout': 'nueve',       'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a4-servicios',     {'kind': 'empresa',   'layout': 'servicios',   'size': 'a4',   'sheet': 'own', 'source': 'landing'}),
    ('a5-ficha-svc',     {'kind': 'empresa',   'layout': 'ficha',       'size': 'a5',   'sheet': 'a4',  'source': 'services'}),
    ('a4-lista-cat',     {'kind': 'catalogo',  'layout': 'lista',       'size': 'a4',   'sheet': 'own', 'source': 'catalog'}),
    ('post-portada',     {'kind': 'empresa',   'layout': 'portada',     'size': 'post', 'sheet': 'a4',  'source': 'landing'}),
    ('a5-destacado',     {'kind': 'catalogo',  'layout': 'destacado',   'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a5-ofertazo',      {'kind': 'electro',   'layout': 'ofertazo',    'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a5-urbano',        {'kind': 'indumentaria','layout': 'urbano',    'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a6-moda',          {'kind': 'indumentaria','layout': 'moda',      'size': 'a6',   'sheet': 'a4',  'source': 'landing'}),
    ('a6-electro',       {'kind': 'electro',   'layout': 'electro',     'size': 'a6',   'sheet': 'a4',  'source': 'landing'}),
    ('a5-editorial',     {'kind': 'marketing', 'layout': 'editorial',   'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
    ('a5-manifiesto',    {'kind': 'empresa',   'layout': 'manifiesto',  'size': 'a5',   'sheet': 'a4',  'source': 'landing'}),
]

WIDTHS = [320, 360, 390, 768, 1024, 1280, 1920]


def login(page):
    page.goto(f'{FRONT}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', USER)
    page.fill('input[name="password"]', PASS)
    page.evaluate('() => { document.querySelector("form")?.requestSubmit?.() }')
    page.wait_for_timeout(4500)
    page.evaluate('() => { localStorage.setItem("davent:tour:done","1"); document.querySelectorAll("[class*=tour]").forEach(e => e.remove()) }')


def goto_studio(page):
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('button,a')].find(x=>/Promocionar|QR y folletos/i.test(x.innerText)&&x.closest('.sidebar,.tabbar,nav'))
      b?.click() }''')
    page.wait_for_timeout(1500)
    page.click('button:has-text("Diseñá tu folleto")')
    page.wait_for_selector('.studio', timeout=20000)
    page.wait_for_timeout(1800)


def set_draft(page, extra):
    base = {
        'kind': 'marketing', 'layout': 'impacto', 'size': 'a5', 'sheet': 'a4', 'source': 'landing',
        'title': 'Semana de ofertas', 'subtitle': 'Mirá todo lo que tenemos para vos', 'badge': '-30%',
        'bullets': ['Envíos en el día', 'Todas las tarjetas', 'Garantía real', ''],
        'cta': 'Escaneá y mirá todo el catálogo', 'contact': '+54 9 387 155 1234',
        'photo': '', 'productIds': [], 'serviceIds': [], 'showQr': True, 'showLogo': True
    }
    base.update(extra)
    page.evaluate(f'() => localStorage.setItem("{DRAFT_KEY}", {json.dumps(json.dumps(base))})')


def shots():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={'width': 1440, 'height': 980}, locale='es-AR', accept_downloads=True)
        page = ctx.new_page()
        page.on('pageerror', lambda e: print('  [PAGEERROR]', str(e)[:250]))
        page.on('console', lambda m: print('  [con]', m.type, m.text[:160]) if m.type == 'error' else None)
        login(page)
        page.wait_for_selector('.sidebar, .tabbar', timeout=20000)

        # --- formatos + diseños ---
        for name, extra in CASES:
            page.evaluate(f'() => localStorage.removeItem("{DRAFT_KEY}")')
            set_draft(page, extra)
            page.reload(wait_until='domcontentloaded')
            page.wait_for_timeout(2200)
            page.evaluate('() => localStorage.setItem("davent:tour:done","1")')
            goto_studio(page)
            r = page.evaluate(CHECK_JS)
            el = page.locator('.studio-sheet')
            el.screenshot(path=str(OUT / f'{name}.png'))
            print(name, json.dumps(r, ensure_ascii=False)[:400])

        # --- caso extremo: nombre 60c, sin logo, sin foto, sin ítems ---
        set_draft(page, {'kind': 'empresa', 'layout': 'corporativo', 'size': 'a5', 'source': 'catalog',
                         'productIds': [], 'showLogo': False, 'photo': '', 'title': 'T' * 60,
                         'subtitle': 'S' * 110, 'badge': 'M' * 14})
        page.reload(wait_until='domcontentloaded'); page.wait_for_timeout(2200)
        page.evaluate('() => localStorage.setItem("davent:tour:done","1")')
        goto_studio(page)
        r = page.evaluate(CHECK_JS)
        page.locator('.studio-sheet').screenshot(path=str(OUT / 'edge-largo.png'))
        print('edge-largo', json.dumps(r, ensure_ascii=False)[:400])

        # --- PNG export real ---
        set_draft(page, {'kind': 'marketing', 'layout': 'story', 'size': 'story', 'source': 'landing'})
        page.reload(wait_until='domcontentloaded'); page.wait_for_timeout(2200)
        page.evaluate('() => localStorage.setItem("davent:tour:done","1")')
        goto_studio(page)
        try:
            with page.expect_download(timeout=20000) as dl:
                page.click('button:has-text("Descargar PNG")')
            d = dl.value
            p = OUT / 'export-story.png'
            d.save_as(p)
            from PIL import Image as I
            im = I.open(p)
            print('PNG export:', d.suggested_filename, im.size)
        except Exception as e:
            print('PNG export FAIL:', str(e)[:200])

        # --- responsive: 7 anchos sobre el diseñador ---
        for w in WIDTHS:
            page.set_viewport_size({'width': w, 'height': 900})
            page.wait_for_timeout(900)
            r = page.evaluate(CHECK_JS)
            flag = 'OK' if r['sw'] <= r['iw'] else 'SCROLL-X'
            print(f'width {w}: {flag} sw={r["sw"]} over={r["over"][:5]} fc={r.get("fc")}')
            if w in (320, 768, 1440):
                page.screenshot(path=str(OUT / f'w{w}.png'), full_page=False)
        b.close()


if MODE in ('seed', 'all'):
    seed()
if MODE in ('shots', 'all'):
    shots()
