import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

JS = r"""
async () => {
  const out = {};
  const el = document.querySelector('.studio-sheet .fc');
  const parts = [];
  for (const sheet of document.styleSheets) {
    try { for (const r of sheet.cssRules) parts.push(r.cssText) } catch (e) {}
  }
  const cssApp = parts.join('\n');
  const blobToDataUrl = (b) => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(b) });
  async function inlineFontUrls(css) {
    const urls = [...css.matchAll(/url\((https:[^)]+)\)/g)].map(m => m[1]).slice(0, 40);
    for (const url of urls) {
      try { const b = await (await fetch(url)).blob(); css = css.split(url).join(await blobToDataUrl(b)) } catch (e) {}
    }
    return css;
  }
  const fontCssParts = [];
  const links = [...document.querySelectorAll('link[rel~="stylesheet"]')].map(l => l.href).filter(h => h.includes('fonts.googleapis'));
  out.fontLinks = links;
  for (const href of links.slice(0, 4)) {
    try { fontCssParts.push(await inlineFontUrls(await (await fetch(href)).text())) } catch (e) {}
  }
  const trySvg = async (css, images) => {
    const clone = el.cloneNode(true);
    clone.setAttribute('style', 'width:600px;height:848px;');
    if (images) {
      for (const img of clone.querySelectorAll('img')) {
        const src = img.getAttribute('src') || '';
        if (src.startsWith('data:') || src.startsWith('blob:')) continue;
        try { img.setAttribute('src', await blobToDataUrl(await (await fetch(src, { mode: 'cors' })).blob())) }
        catch (e) { img.remove() }
      }
    }
    const doc = clone.ownerDocument;
    const wrap = doc.createElement('div');
    wrap.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
    const st = doc.createElement('style'); st.textContent = css;
    wrap.appendChild(st); wrap.appendChild(clone);
    const html = new XMLSerializer().serializeToString(wrap);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="848" viewBox="0 0 600 848"><foreignObject width="100%" height="100%">${html}</foreignObject></svg>`;
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
    try {
      const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej('svgload'); i.src = url });
      const c = document.createElement('canvas'); c.width = 600; c.height = 848;
      c.getContext('2d').drawImage(img, 0, 0);
      const b = await new Promise(r => c.toBlob(r, 'image/png'));
      return b ? 'ok:' + b.size : 'blob-null';
    } catch (e) { return 'fail:' + String(e).slice(0, 140) } finally { URL.revokeObjectURL(url) }
  };
  out.noCss = await trySvg('', false);
  out.appCss = await trySvg(cssApp, false);
  out.appCssFonts = await trySvg(cssApp + '\n' + fontCssParts.join('\n'), false);
  out.full = await trySvg(cssApp + '\n' + fontCssParts.join('\n'), true);
  out.imgs = [...el.querySelectorAll('img')].map(i => (i.getAttribute('src') || '').slice(0, 80));
  return out;
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_context(viewport={'width': 1440, 'height': 980}, locale='es-AR', accept_downloads=True).new_page()
    page.goto('http://localhost:5173/login', wait_until='domcontentloaded'); page.wait_for_timeout(900)
    page.fill('input[name="username"]', 'qablocks2'); page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('()=>{document.querySelector("form")?.requestSubmit?.()}'); page.wait_for_timeout(4500)
    page.evaluate('()=>{localStorage.setItem("davent:tour:done","1");document.querySelectorAll("[class*=tour]").forEach(e=>e.remove())}')
    page.evaluate('''()=>{const b=[...document.querySelectorAll('button,a')].find(x=>/Promocionar|QR y folletos/i.test(x.innerText)&&x.closest('.sidebar')); b?.click()}''')
    page.wait_for_timeout(1600)
    page.click('button:has-text("Diseñá tu folleto")')
    page.wait_for_selector('.studio', timeout=20000); page.wait_for_timeout(2000)
    diag = page.evaluate(JS)
    print(json.dumps(diag, ensure_ascii=False, indent=1)[:2500])
    b.close()
