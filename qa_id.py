import sys, pathlib, io, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'qa_out' / 'id'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://localhost:5175'
MODE = sys.argv[1] if len(sys.argv) > 1 else 'resp'
WIDTHS = [int(a) for a in sys.argv[2:] if a.isdigit()] or [320, 360, 390, 768, 1024, 1280, 1920]
LONG = 'Distribuidora Mayorista de Indumentaria Deportiva Salteña SRL'

im = Image.new('RGB', (1600, 700), (250, 240, 200)); d = ImageDraw.Draw(im)
for i in range(0, 1600, 40): d.rectangle((i, 0, i + 20, 700), fill=(250 - i // 10, 200, 120 + i // 12))
d.ellipse((1000, 150, 1300, 450), fill=(30, 90, 160))
cov = io.BytesIO(); im.save(cov, 'JPEG'); COVER = OUT / 'cover.jpg'; COVER.write_bytes(cov.getvalue())

JS_CHECK = """
() => {
  const root = document.querySelector('.dl-root');
  const out = { sw: document.documentElement.scrollWidth, iw: window.innerWidth, over: [], small: [] };
  if (!root) { out.noroot = true; return out; }
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
  root.querySelectorAll('*').forEach((e) => {
    if (!vis(e)) return;
    const cs = getComputedStyle(e); const tag = e.tagName.toLowerCase();
    if (['svg','path','circle','rect','line','polyline','input'].includes(tag)) return;
    if (e.scrollWidth > e.clientWidth + 1 && cs.overflowX === 'visible' && e.clientWidth > 0) out.over.push(e.className || tag);
    const r = e.getBoundingClientRect();
    if (r.right > window.innerWidth + 1 || r.left < -1) out.over.push('OUT:' + (e.className || tag));
  });
  document.querySelectorAll('.dl-root button, .dl-root .swatch, .dl-root .dl-colorpick, .dl-root .dl-hex, .dsg-savebar button, .dp-seg-btn').forEach((b) => {
    if (!vis(b)) return;
    const r = b.getBoundingClientRect();
    if (r.height < 43.5 || (r.width < 43.5 && !b.classList.contains('dl-hbtn'))) out.small.push(`${(b.className||b.tagName)} ${Math.round(r.width)}x${Math.round(r.height)} ${(b.innerText||b.getAttribute('aria-label')||'').slice(0,20)}`);
  });
  return out;
}
"""


def goto_look(page):
    if page.locator('.tabbar').count() and page.locator('.tabbar').is_visible():
        t = page.locator('.tabbar button', has_text='Mi página')
        if t.count(): t.first.click()
        else:
            page.locator('.tabbar button').last.dispatch_event('click'); page.wait_for_timeout(400)
            page.locator('.sheet-nav button, .more-sheet button, .more-sheet a', has_text='Mi página').first.click()
    else:
        page.click('.sidebar button:has-text("Mi página")')
    page.wait_for_timeout(900)
    page.locator('button:has-text("Cómo se ve")').first.click()
    page.wait_for_timeout(900)
    page.locator('.dsg-tab:has-text("Studio"), .dsg-tab:has-text("Logo y colores")').first.click()
    page.wait_for_timeout(1800)


def open_page(pw, W, touch=None):
    H = 800 if W < 700 else 900
    ctx = pw.new_context(viewport={'width': W, 'height': H}, locale='es-AR', has_touch=W < 800, is_mobile=W < 800)
    page = ctx.new_page(); msgs = []
    page.on('console', lambda m: msgs.append(f'{m.type}: {m.text[:200]}') if m.type == 'error' else None)
    page.on('pageerror', lambda e: msgs.append(f'PAGEERROR: {e}'))
    time.sleep(3)
    r = ctx.request.post(f'{BASE}/api/token/', data={'username': 'qablocks', 'password': 'QaBlocks2026!', 'remember': True})
    assert r.status == 200, r.text()
    page.goto(f'{BASE}/dashboard', wait_until='domcontentloaded'); page.wait_for_timeout(2000)
    page.evaluate('localStorage.setItem("davent:tour:done", "1")'); page.reload(wait_until='domcontentloaded')
    page.wait_for_selector('.sidebar nav button, .tabbar button', state='attached', timeout=20000); page.wait_for_timeout(3500)
    goto_look(page)
    return ctx, page, msgs


with sync_playwright() as p:
    browser = p.chromium.launch()
    if MODE == 'resp':
        for W in WIDTHS:
            ctx, page, msgs = open_page(browser, W)
            res = {}
            page.locator('.dsg-tab:has-text("Mis datos")').click(); page.fill('#design_display_name', LONG)
            page.locator('.dsg-tab:has-text("Studio"), .dsg-tab:has-text("Logo y colores")').first.click(); page.wait_for_timeout(1500)
            for sid in ['identity', 'colors', 'type', 'style']:
                b = page.locator(f'#dl-h-{sid}')
                if b.get_attribute('aria-expanded') != 'true':
                    b.click(); page.wait_for_timeout(400)
                if sid == 'style' and page.locator('.dl-crop').count() == 0:
                    page.set_input_files('#dl-p-style input[type=file]', str(COVER)); page.wait_for_timeout(2500)
                res[sid] = page.evaluate(JS_CHECK)
                page.screenshot(path=str(OUT / f'{W}-{sid}.png'))
            print('=== WIDTH', W)
            for k, v in res.items():
                print(f"  {k}: scrollW {v['sw']}/{v['iw']} {'HSCROLL!' if v['sw'] > v['iw'] else 'ok'} over={sorted(set(v['over']))[:6]} small={[x for x in v['small'] if 'dsg-tab' not in x and 'icon-btn' not in x][:6]}")
            print('  console:', msgs[:4])
            ctx.close()
    elif MODE == 'pub':
        for theme in ('dark', 'light'):
            ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
            time.sleep(3)
            tok = ctx.request.post(f'{BASE}/api/token/', data={'username': 'qablocks', 'password': 'QaBlocks2026!'}).json()['access']
            r = ctx.request.patch(f'{BASE}/api/stores/customization/', data={'theme': theme}, headers={'Authorization': f'Bearer {tok}'})
            print('theme', theme, r.status)
            page = ctx.new_page(); msgs = []
            page.on('pageerror', lambda e: msgs.append(str(e)))
            page.goto(f'{BASE}/qatienda', wait_until='domcontentloaded'); page.wait_for_timeout(3500)
            print(theme, page.evaluate("(() => { const s=getComputedStyle(document.querySelector('.store-page')); return [s.getPropertyValue('--store-accent'), s.getPropertyValue('--store-accent-ink'), s.getPropertyValue('--store-cover-overlay'), document.querySelector('.store-page').dataset.logoMode, document.querySelector('.store-page').dataset.storeTheme, !!document.querySelector('.sp-hero-cover img')] })()"), msgs[:3])
            page.screenshot(path=str(OUT / f'pub-{theme}.png'))
            ctx.close()
    else:
        W = 1280
        ctx, page, msgs = open_page(browser, W)
        page.locator('#dl-h-colors').click(); page.wait_for_timeout(300)
        # hex invalido y valido
        page.fill('#design-accent-hex', '#12'); print('hex invalido ->', page.locator('#design-accent-hex-err').inner_text())
        page.fill('#design-accent-hex', '#e6c200'); page.wait_for_timeout(300)
        print('hex valido -> custom activo:', page.locator('.dl-colorpick.active').count(), '| meters:', page.locator('.dl-meter').all_inner_texts())
        print('boton corregir visible:', page.locator('.dl-fix button').count())
        page.locator('.dl-fix button').click(); page.wait_for_timeout(300)
        print('tras corregir:', page.locator('#design-accent-hex').input_value(), '| meters ok:', page.locator('.dl-meter.ok').count(), '| msg:', page.locator('#dl-p-colors .hint[role=status]').first.inner_text())
        # paleta
        page.locator('.dl-pal', has_text='Tech').click(); page.wait_for_timeout(300)
        print('paleta Tech -> hex:', page.locator('#design-accent-hex').input_value(), '| theme dark pressed:', page.locator('.theme-option.active').inner_text())
        # sorprendeme + deshacer
        before = page.locator('#design-accent-hex').input_value()
        page.locator('.dl-surprise').click(); page.wait_for_timeout(300)
        mid = page.locator('#design-accent-hex').input_value()
        page.locator('.dl-link').click(); page.wait_for_timeout(300)
        print('sorprendeme:', before, '->', mid, '-> deshacer ->', page.locator('#design-accent-hex').input_value())
        # logo size / mode
        page.locator('#dl-h-identity').click(); page.wait_for_timeout(300)
        page.locator('.dl-seg-btn[aria-label="Grande"]').click(); page.locator('.dl-seg-btn', has_text='Solo logo').click(); page.wait_for_timeout(300)
        print('preview logo scale var:', page.evaluate("getComputedStyle(document.querySelector('.dp-frame')).getPropertyValue('--store-logo-scale')"), '| mode attr:', page.get_attribute('.dp-frame', 'data-logo-mode'))
        # portada
        page.locator('#dl-h-style').click(); page.wait_for_timeout(300)
        page.set_input_files('#dl-p-style input[type=file]', str(COVER)); page.wait_for_timeout(3000)
        stage = page.locator('.dl-crop-stage'); bb = stage.bounding_box()
        page.mouse.move(bb['x'] + bb['width'] * 0.5, bb['y'] + bb['height'] * 0.5); page.mouse.down()
        page.mouse.move(bb['x'] + bb['width'] * 0.9, bb['y'] + bb['height'] * 0.5, steps=8); page.mouse.up(); page.wait_for_timeout(300)
        print('focus tras drag:', page.get_attribute('.dl-crop-win', 'aria-valuetext'))
        page.locator('.dl-crop-win').focus(); page.keyboard.press('ArrowLeft'); page.wait_for_timeout(200)
        print('focus tras flecha:', page.get_attribute('.dl-crop-win', 'aria-valuetext'))
        page.locator('.dl-seg-btn', has_text='Móvil').click(); page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / 'func-crop-mobile.png'))
        page.evaluate("(() => { const r=document.getElementById('design-cover-overlay'); r.value=50; r.dispatchEvent(new Event('input',{bubbles:true})) })()"); page.wait_for_timeout(300)
        print('overlay var:', page.evaluate("getComputedStyle(document.querySelector('.dp-frame')).getPropertyValue('--store-cover-overlay')"), '| pos:', page.evaluate("getComputedStyle(document.querySelector('.dp-frame')).getPropertyValue('--store-cover-pos')"))
        # undo/redo atajos
        n0 = page.locator('.dl-hbtn:not(:disabled)').count()
        page.locator('.dl-seg-btn', has_text='Escritorio').focus()
        page.keyboard.press('Control+z'); page.wait_for_timeout(200)
        print('tras Ctrl+Z overlay:', page.input_value('#design-cover-overlay'), '| redo habilitado:', page.locator('.dl-hbtn[aria-label^="Rehacer"]:not(:disabled)').count())
        page.keyboard.press('Control+Shift+z'); page.wait_for_timeout(200)
        print('tras Ctrl+Shift+Z overlay:', page.input_value('#design-cover-overlay'))
        # guardar
        with page.expect_response(lambda r: 'customization' in r.url and r.request.method == 'PATCH') as ri:
            page.locator('.dsg-savebar button', has_text='Guardar diseño').click()
        resp = ri.value; body = resp.json()
        c = body.get('customization', {}); print('keys:', list(body.keys())[:6], len(c))
        print('PATCH', resp.status, {k: c.get(k) for k in ['accent_custom', 'logo_scale', 'logo_mode', 'cover_overlay', 'cover_focus_x', 'cover_focus_y', 'theme']})
        page.wait_for_timeout(800)
        slug = page.evaluate("document.querySelector('.sp-link, .url-chip')?.textContent || ''")
        print('console:', msgs[:4])
        ctx.close()
    browser.close()
