"""QA probe: internals del StudioShell tras Descartar (qué queda dirty)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, locale='es-AR')
    page = ctx.new_page()

    page.goto('http://localhost:5173/login', wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.fill('input[name="username"]', 'qablocks2')
    page.fill('input[name="password"]', 'QaBlocks2026!')
    page.evaluate('() => { document.querySelector("form")?.requestSubmit?.() }')
    page.wait_for_timeout(4500)
    page.evaluate('''() => { localStorage.setItem("davent:tour:done","1");
      document.querySelectorAll('[class*="tour"]').forEach(e => e.remove()) }''')
    page.wait_for_selector('.sidebar, .tabbar', timeout=20000)
    page.evaluate('''() => {
      const b=[...document.querySelectorAll('.sidebar button,.sidebar a,.tabbar button,.tabbar a')]
        .find(x=>/mi p[aá]gina|mi web/i.test(x.innerText))
      b?.click() }''')
    page.wait_for_timeout(1000)
    page.locator('.sec-tab', has_text='Cómo se ve').first.click()
    page.wait_for_timeout(800)
    page.locator('.dsg-tab', has_text='Studio').first.click()
    page.wait_for_selector('.sts', timeout=20000)
    page.wait_for_timeout(4000)

    probe = '''() => {
      const el = document.querySelector('.sts')
      let c = el && el.__vueParentComponent
      while (c && !(c.setupState && 'themeDirty' in c.setupState)) c = c.parent
      if (!c) return 'no-shell-component'
      const s = c.setupState
      const J = (v) => JSON.stringify(v)
      return {
        themeDirty: s.themeDirty,
        layoutDirty: s.layoutDirty,
        anyDirty: s.anyDirty,
        propDirty: c.props.dirty,
        formTheme: c.props.form.theme,
        formTemplate: c.props.form.template,
        formAccentCustom: c.props.form.accent_custom,
        formNameFont: c.props.form.name_font,
        draftTemplate: s.draft?.template,
        // diferencias campo a campo del theme draft vs base
        themeDiff: (() => {
          const d = s.draft?.theme || {}, bs = s.base || {}
          const diff = {}
          for (const k of new Set([...Object.keys(d), ...Object.keys(bs)])) {
            if (J(d[k]) !== J(bs[k])) diff[k] = { draft: d[k], base: bs[k] }
          }
          return diff
        })(),
        layoutEq: J(s.draft?.layout) === J(s.savedLayout)
      }
    }'''
    print('estado interno (mount):', page.evaluate(probe))

    page.evaluate('''() => {
      const card=[...document.querySelectorAll('.psg-card')]
        .find(c=>c.querySelector('h4')?.textContent.includes('Vidrio'))
      card?.querySelector('.psg-btn.is-try')?.click() }''')
    page.wait_for_timeout(1800)
    print('tras Probar Vidrio:', page.evaluate(probe))
    page.locator('.sts button', has_text='Descartar').first.click()
    page.wait_for_timeout(1800)
    print('tras Descartar:', page.evaluate(probe))
    b.close()
