"""Capturas QA del tab 'Logo y colores' del dashboard (harness estatico).
Uso: venv/Scripts/python.exe qa_look_shots.py <tag>
Guarda qa/look-<tag>/<w>.png
"""
import os, sys, pathlib
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else 'before'
WIDTHS = [320, 360, 390, 430, 560, 620, 768]
URL = pathlib.Path('frontend/qa-look-harness.html').resolve().as_uri()

os.makedirs(f'qa/look-{OUT}', exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for w in WIDTHS:
        page = browser.new_page(viewport={'width': w, 'height': 900})
        try:
            page.goto(URL, wait_until='networkidle', timeout=15000)
            page.wait_for_timeout(400)
            page.screenshot(path=f'qa/look-{OUT}/{w}.png', full_page=True)
        except Exception as e:
            print(f'FAIL {w}: {e}')
        finally:
            page.close()
        print(f'done {w}', flush=True)
    browser.close()
print('listo')
