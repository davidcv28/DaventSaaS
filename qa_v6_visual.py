"""QA visual v6 — antes/después de una tienda real con propuesta del motor.

Toma `qa-v6-comercio` (creada por qa_ai_design_v6.py), guarda su estado
publicado, arma el "antes" (sin site_theme, plantilla Cobre), captura y audita,
restaura el "después" (piel + estilo + colores del motor) y repite.

Salida: qa_out/v6/{before,after}-{390,768,1280}.png + visual-report.json
Uso: venv/Scripts/python.exe qa_v6_visual.py   (con `npm run dev` en :5173)
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django

django.setup()

from playwright.sync_api import sync_playwright

from StoreApp.domains.stores.models import Store, StoreCustomization

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'venv', 'Scripts', 'python.exe')
SLUG = 'qa-v6-comercio'
BASE = f'http://localhost:5173/{SLUG}'
API = f'http://127.0.0.1:8000/api/stores/public/{SLUG}/'
OUT = os.path.join('qa_out', 'v6')
WIDTHS = [390, 768, 1280]
PAGES = [('home', ''), ('catalogo', '/catalogo'), ('servicios', '/servicios')]
STATE_FILE = os.path.join('.qa-tmp', 'v6-state.json')

AUDIT = r"""() => {
  const issues = []
  const vis = (el) => {
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'
  }
  for (const img of document.querySelectorAll('img')) {
    if (vis(img) && !img.hasAttribute('alt')) issues.push(`img sin alt: ${(img.getAttribute('src')||'').slice(-40)}`)
    if (issues.length > 40) break
  }
  for (const el of document.querySelectorAll('button, a[href], [role="button"]')) {
    if (!vis(el)) continue
    const name = (el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || '').trim()
    const img = el.querySelector('img[alt]')
    const svg = el.querySelector('svg[aria-label], svg title')
    if (!name && !img && !svg) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 50)
      issues.push(`interactivo sin nombre: ${el.tagName.toLowerCase()}.${cls}`)
    }
    if (issues.length > 40) break
  }
  for (const el of document.querySelectorAll('input:not([type=hidden]), textarea, select')) {
    if (!vis(el)) continue
    const id = el.id
    const labelled = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') ||
      (id && document.querySelector(`label[for="${id}"]`)) || el.closest('label') || el.placeholder
    if (!labelled) issues.push(`input sin label: ${el.name || el.type}`)
    if (parseFloat(getComputedStyle(el).fontSize) < 16) issues.push(`input font <16px: ${el.name || el.type}`)
  }
  for (const el of document.querySelectorAll('button, a[href], [role="button"], input, select')) {
    if (!vis(el)) continue
    const r = el.getBoundingClientRect()
    if (r.width < 40 || r.height < 40) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 40)
      issues.push(`target <44px: ${el.tagName.toLowerCase()}.${cls} ${Math.round(r.width)}x${Math.round(r.height)}`)
    }
    if (issues.length > 40) break
  }
  for (const el of document.querySelectorAll('.tpc')) {
    if (el.tagName !== 'A' && el.tagName !== 'BUTTON' &&
        el.getAttribute('tabindex') !== '0' && el.getAttribute('role') !== 'link' && el.getAttribute('role') !== 'button') {
      issues.push('card .tpc no teclado-activable'); break
    }
  }
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(vis)
  const h1s = hs.filter(h => h.tagName === 'H1').length
  if (h1s === 0) issues.push('sin h1')
  if (h1s > 1) issues.push(`${h1s} h1 en la página`)
  let prev = 0
  for (const h of hs) {
    const lvl = +h.tagName[1]
    if (prev && lvl > prev + 1) { issues.push(`salto de jerarquía h${prev}→h${lvl}: "${(h.innerText||'').slice(0,30)}"`); break }
    prev = lvl
  }
  return issues
}"""

CONTRAST = r"""() => {
  const lum = (c) => {
    if (!/^rgba?\(/.test(c)) return null
    const m = c.match(/[\d.]+/g); if (!m || m.length < 3) return null
    const [r, g, b] = m.slice(0, 3).map(v => +v / 255)
    const f = (x) => x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }
  const bgOf = (el) => {
    let p = el
    while (p) {
      const cs = getComputedStyle(p)
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null
      const bg = cs.backgroundColor
      const parts = bg && bg.match(/[\d.]+/g)
      const alpha = parts && parts.length > 3 ? +parts[3] : 1
      // Un fondo translúcido no es el fondo real: se compone con el de arriba.
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && alpha >= 0.9) return bg
      p = p.parentElement
    }
    return 'rgb(255, 255, 255)'
  }
  // Solo lo que el visitante ve en el viewport: descarta drawers fuera de
  // pantalla (transform), menús con aria-hidden/inert y cadenas opacity 0.
  const inView = (el) => {
    const r = el.getBoundingClientRect()
    if (r.width < 1 || r.height < 1) return false
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return false
    if (el.closest('[aria-hidden="true"], [inert]')) return false
    let p = el
    while (p) {
      const cs = getComputedStyle(p)
      if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false
      p = p.parentElement
    }
    return true
  }
  const out = []
  for (const el of document.querySelectorAll('p, h1, h2, h3, li, span, a')) {
    if (out.length >= 12) break
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    if (!inView(el) || !el.innerText?.trim() || el.innerText.length > 200) continue
    const bgC = bgOf(el)
    if (bgC == null) continue
    const fg = lum(cs.color), bg = lum(bgC)
    if (fg == null || bg == null) continue
    const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05)
    if (ratio < 4.5 && parseFloat(cs.fontSize) < 24) {
      const cls = (el.className?.baseVal ?? el.className?.toString() ?? '').slice(0, 40)
      out.push(`contraste ${ratio.toFixed(2)} <4.5: ${el.tagName.toLowerCase()}.${cls} "${el.innerText.trim().slice(0,25)}"`)
    }
  }
  return out
}"""

THEME = r"""() => {
  const page = document.querySelector('.store-page')
  const h1 = document.querySelector('h1')
  const cs = page ? getComputedStyle(page) : null
  return {
    skin: page?.dataset?.stSkin || null,
    style: page?.dataset?.stStyle || null,
    template: page?.dataset?.storeTemplate || null,
    ink: cs?.getPropertyValue('--sp-ink').trim() || null,
    accent: cs?.getPropertyValue('--store-accent').trim() || null,
    bodyFont: cs?.getPropertyValue('--store-font').trim() || null,
    h1Font: h1 ? getComputedStyle(h1).fontFamily : null,
  }
}"""


def with_db(fn):
    """ORM en un thread: sync_playwright deja un event loop vivo en el main."""
    box = {}

    def work():
        try:
            box['value'] = fn()
        except Exception as error:
            box['error'] = error

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    if 'error' in box:
        raise box['error']
    return box.get('value')


def snapshot():
    def work():
        custom = StoreCustomization.objects.get(store__slug=SLUG)
        return {
            'template': custom.template,
            'site_theme': custom.site_theme or {},
            'layout_config': custom.layout_config or {},
        }
    data = with_db(work)
    os.makedirs('.qa-tmp', exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False)
    return data


def set_state(template, site_theme, layout_config):
    def work():
        custom = StoreCustomization.objects.get(store__slug=SLUG)
        custom.template = template
        custom.site_theme = site_theme
        custom.layout_config = layout_config
        custom.save(update_fields=['template', 'site_theme', 'layout_config'])
    with_db(work)


def free_port():
    try:
        out = subprocess.check_output(['netstat', '-ano']).decode('cp1252', 'replace')
    except Exception:
        return
    for line in out.splitlines():
        if ':8000' in line and 'LISTENING' in line:
            try:
                os.kill(int(line.split()[-1]), 9)
            except Exception:
                pass
    time.sleep(0.6)


def start_server():
    free_port()
    env = dict(os.environ)
    env['TEMP'] = os.path.join(ROOT, '.qa-tmp', 'tmp')
    env['TMP'] = env['TEMP']
    log = open(os.path.join('.qa-tmp', 'v6-server.log'), 'ab')
    return subprocess.Popen(
        [PY, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
        cwd=ROOT, env=env, stdout=log, stderr=log,
    )


def stop_server(server):
    try:
        server.kill()
        server.wait(timeout=10)
    except Exception:
        pass
    free_port()


def wait_api(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(API, timeout=3) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.5)
    return None


def audit(browser, width, tag, path, shot):
    ctx = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
    page = ctx.new_page()
    data = {'issues': [], 'contrast': [], 'theme': None}
    try:
        page.goto(BASE + path, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(500)
        data['issues'] = sorted(set(page.evaluate(AUDIT)))
        data['contrast'] = page.evaluate(CONTRAST)
        if tag == 'home':
            data['theme'] = page.evaluate(THEME)
        if shot:
            page.screenshot(path=os.path.join(OUT, shot), full_page=True)
    finally:
        ctx.close()
    return data


def run_state(browser, label, server):
    report = {}
    for tag, path in PAGES:
        for width in WIDTHS:
            shot = f'{label}-{tag}-{width}.png' if tag == 'home' else None
            result = audit(browser, width, tag, path, shot)
            key = f'{tag}@{width}'
            report[key] = result
            if result['contrast']:
                print(f'  {label} {key}: {len(result["contrast"])} contraste(s) <4.5')
            if result['issues'] and width == 390:
                print(f'  {label} {key}: {len(result["issues"])} issue(s) a11y')
    return report


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join('.qa-tmp', 'tmp'), exist_ok=True)
    state = snapshot()
    print(f'estado publicado: template={state["template"]} skin={(state["site_theme"].get("skin") or {}).get("id")}')
    if not (state['site_theme'].get('skin') or {}).get('id'):
        print('ERROR: la tienda no tiene piel aplicada; corré qa_ai_design_v6.py primero.')
        return 1

    report = {'slug': SLUG, 'before': {}, 'after': {}, 'theme': None}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            # ANTES: la web original (sin site_theme, Cobre) para comparar.
            set_state('cobre', {}, {})
            server = start_server()
            try:
                if not wait_api():
                    print('ERROR: el runserver no levantó (antes)')
                    return 1
                print('capturando ANTES')
                report['before'] = run_state(browser, 'before', server)
            finally:
                stop_server(server)

            # DESPUÉS: la propuesta aplicada por el motor.
            set_state(state['template'], state['site_theme'], state['layout_config'])
            server = start_server()
            try:
                payload = wait_api()
                if not payload:
                    print('ERROR: el runserver no levantó (después)')
                    return 1
                published = (payload.get('customization') or {}).get('site_theme') or {}
                report['published_skin'] = (published.get('skin') or {}).get('id')
                print('capturando DESPUÉS')
                report['after'] = run_state(browser, 'after', server)
                report['theme'] = (report['after'].get('home@390') or {}).get('theme')
            finally:
                stop_server(server)
        finally:
            browser.close()

    with open(os.path.join(OUT, 'visual-report.json'), 'w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    contrast_fail = [
        f'{label}/{key}: {item}'
        for label in ('before', 'after')
        for key, result in report[label].items()
        for item in result['contrast']
    ]
    issues_after = {
        key: result['issues'] for key, result in report['after'].items()
        if result['issues'] and key.endswith('@390')
    }
    print('\nRESUMEN')
    print('theme publicado:', report.get('theme'))
    print('piel publicada:', report.get('published_skin'))
    print('contrastes <4.5:', len(contrast_fail))
    for item in contrast_fail[:10]:
        print(' -', item)
    print('issues a11y después:', sum(len(v) for v in issues_after.values()))
    for key, items in list(issues_after.items())[:6]:
        print(f' - {key}: {items[:3]}')
    print('capturas en', OUT)
    return 0 if not contrast_fail and report.get('published_skin') else 1


if __name__ == '__main__':
    sys.exit(main())
