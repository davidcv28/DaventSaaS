"""QA de guardado del Studio: cambia radius a 'square' (pill->square) y una
armonía de color, guarda y verifica que el PATCH viaja con site_theme y la
respuesta lo persiste saneado por el backend.
Uso: venv/Scripts/python.exe qa_studio_save.py
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5173'
patch_payloads, patch_responses = [], []

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
    page = ctx.new_page()

    def on_response(r):
        if r.request.method == 'PATCH' and 'customization' in r.url:
            try:
                patch_responses.append((r.status, r.json()))
                body = r.request.post_data_json
                patch_payloads.append(body)
            except Exception:
                pass
    page.on('response', on_response)

    page.goto(f'{BASE}/login', wait_until='domcontentloaded')
    page.wait_for_timeout(700)
    page.fill('input[name="username"]', 'qablocks')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('() => { const f = document.querySelector("form"); f?.requestSubmit?.() }')
    page.wait_for_timeout(3500)
    page.goto(f'{BASE}/dashboard', wait_until='domcontentloaded')
    page.wait_for_timeout(1800)
    skip = page.locator('.tour-skip')
    if skip.count() and skip.first.is_visible():
        skip.first.click()
        page.wait_for_timeout(400)
    page.locator('[data-tour="nav-store"]').first.click()
    page.wait_for_timeout(800)
    if skip.count() and skip.first.is_visible():
        skip.first.click()
        page.wait_for_timeout(400)
    page.get_by_role('tab', name='Cómo se ve').first.click()
    page.wait_for_timeout(500)
    page.get_by_role('tab', name='Studio').first.click()
    page.wait_for_selector('.sts', timeout=15000)
    page.wait_for_timeout(2000)

    # Contenedores > Forma de botones > Recto (default es pill).
    page.locator('.sts-tool', has_text='Contenedores').first.click()
    page.wait_for_timeout(500)
    page.locator('.stp-opt', has_text='Recto').first.click()
    page.wait_for_timeout(300)
    # Móvil > 2 columnas (default 1).
    page.locator('.sts-tool', has_text='Móvil').first.click()
    page.wait_for_timeout(500)
    page.locator('.stp-opt', has_text='2 columnas').first.click()
    page.wait_for_timeout(300)

    page.locator('.sts-acts .btn', has_text='Guardar').first.click()
    page.wait_for_timeout(2500)

    if not patch_payloads:
        print('!! no se detectó PATCH de customization')
    else:
        payload = patch_payloads[-1]
        st = payload.get('site_theme') or {}
        print('PATCH status:', patch_responses[-1][0])
        print('site_theme enviado:', json.dumps(st, ensure_ascii=False)[:400])
        resp = patch_responses[-1][1]
        cust = resp.get('customization') or resp if isinstance(resp, dict) else {}
        saved = (cust.get('site_theme') or {}) if isinstance(cust, dict) else {}
        print('site_theme guardado:', json.dumps(saved, ensure_ascii=False)[:400])
        ok = (patch_responses[-1][0] == 200
              and saved.get('buttons', {}).get('shape') == 'square'
              and saved.get('mobile', {}).get('gridCols') == 2)
        print('GUARDADO OK' if ok else 'GUARDADO INCOMPLETO')
    browser.close()
