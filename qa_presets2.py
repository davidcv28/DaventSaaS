"""QA FASE presets #2: guardado real (PATCH), locks por plan, anchos."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

patches = []
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    page = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR').new_page()
    page.on('pageerror', lambda e: print('  [PAGEERROR]', str(e)[:300]))

    def on_req(r):
        if '/api/stores/customization' in r.url and r.method == 'PATCH':
            try: patches.append(r.post_data_json)
            except Exception: patches.append({'raw': (r.post_data or '')[:400]})
    page.on('request', on_req)

    page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('() => { const f = document.querySelector("form"); f?.requestSubmit?.() }')
    page.wait_for_timeout(4500)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)

    # beneficios del plan (desde la app)
    benefits = page.evaluate('''() => {
      const pinia = JSON.parse(localStorage.getItem('davent:swr:plans') || '{}')
      return pinia.v?.plan?.benefits || null
    }''')
    print('plan benefits (swr):', benefits)

    page.evaluate('''() => {
      const b=[...document.querySelectorAll('button,a')].find(x=>/mi p[aá]gina/i.test(x.innerText)&&x.closest('.sidebar,.tabbar,nav'))
      b?.click() }''')
    page.wait_for_timeout(1500)
    page.wait_for_selector('text=/Cómo se ve/').click()
    page.wait_for_timeout(1500)
    page.wait_for_selector('button:has-text("Studio")').click()
    page.wait_for_selector('.sts', timeout=20000)
    page.wait_for_timeout(3000)

    # locks visibles
    print('chips lock:', page.locator('.psg-chip.is-lock').count())
    print('botones Ver planes:', page.locator('.psg-btn.is-plans').count())
    print('botones Aplicar:', page.locator('.psg-btn.is-apply').count())

    # Aplicar un preset NO bloqueado -> save real
    apply_btn = page.locator('.psg-btn.is-apply').first
    card = apply_btn.locator('xpath=ancestor::article')
    print('aplicando:', card.locator('h4').inner_text())
    apply_btn.click()
    page.wait_for_timeout(3500)
    print('patches:', len(patches))
    if patches:
        p = patches[-1]
        keys = sorted(p.keys())
        print('keys del patch:', keys)
        st = p.get('site_theme') or {}
        print('site_theme secciones:', sorted(st.keys()) if isinstance(st, dict) else st)
        print('template:', p.get('template'), '| layout_config superficies:', sorted((p.get('layout_config') or {}).keys()))
        print('name_font:', p.get('name_font'), '| accent_custom:', p.get('accent_custom'), '| theme:', p.get('theme'))

    # Estado post-save
    print('savebar dirty post-save:', page.locator('.sts-state.dirty').count())
    page.screenshot(path='qa_out/presets-save.png')
    b.close()
