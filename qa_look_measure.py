"""Mide que elementos del tab 'Logo y colores' desbordan su contenedor en movil."""
import pathlib
from playwright.sync_api import sync_playwright

URL = pathlib.Path('frontend/qa-look-harness.html').resolve().as_uri()
WIDTHS = [320, 360, 390, 430, 560, 620, 768]

JS = """
() => {
  const out = [];
  const vw = document.documentElement.clientWidth;
  const doc = document.documentElement.getBoundingClientRect();
  const report = (el, name) => {
    const r = el.getBoundingClientRect();
    out.push({
      name, left: Math.round(r.left * 10) / 10, right: Math.round(r.right * 10) / 10,
      width: Math.round(r.width * 10) / 10,
      overRight: r.right > vw + 0.5, overDoc: r.right > doc.right + 0.5
    });
  };
  document.querySelectorAll('.dsg-card, .dsg-preview, .pick-preview, .pick-preview-info, .pick-nav, .logo-box, .logo-actions, .cover-box, .dsg-tabs, .design-preview, .dp-nav, .dp-nav-brand, .dp-nav-links, .dp-hero, .size-slider, .theme-options, .sec-tabs, .select').forEach((el, i) => report(el, el.className.split(' ').slice(0,3).join('.') + '#' + i));
  return { vw, docW: Math.round(doc.width * 10) / 10, scrollW: document.documentElement.scrollWidth, items: out };
}
"""

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for w in WIDTHS:
        page = browser.new_page(viewport={'width': w, 'height': 900})
        page.goto(URL, wait_until='networkidle')
        page.wait_for_timeout(300)
        data = page.evaluate(JS)
        over = [i for i in data['items'] if i['overRight']]
        print(f"=== {w}px (docW={data['docW']}, scrollW={data['scrollW']}) ===")
        for i in data['items']:
            flag = '  << OVERFLOW' if i['overRight'] else ''
            print(f"  {i['name']:44s} L={i['left']:>7} R={i['right']:>7} W={i['width']:>7}{flag}")
        page.close()
    browser.close()
