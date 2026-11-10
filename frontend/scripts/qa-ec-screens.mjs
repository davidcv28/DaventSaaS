// QA visual de auth + cuenta del comprador por diseño.
//
// Uso (desde la raíz del repo):
//   STORE=maison-vela DESIGN=moda \
//   node "C:\Users\David\.claude\skills\browser-automation\browser.mjs" \
//     http://localhost:5173/maison-vela/ingresar --script frontend/scripts/qa-ec-screens.mjs
//
// Variables: STORE (slug de la tienda), DESIGN (slug del diseño, para la carpeta
// de salida), QA_EMAIL / QA_PASSWORD (cuenta de comprador QA), OUT (default
// frontend/visual-qa/<design>).
//
// Carga la tienda UNA sola vez: los modos de auth y las secciones de la cuenta
// se cambian dentro de la página (router), no con recargas — el endpoint
// público tiene rate-limit de 120 visitas/hora por IP.
import fs from 'node:fs'
import path from 'node:path'

const STORE = process.env.STORE || 'maison-vela'
const DESIGN = process.env.DESIGN || STORE
const EMAIL = process.env.QA_EMAIL || 'qa.visual@davent.test'
const PASSWORD = process.env.QA_PASSWORD || 'QaVisual2026!'
const OUT = process.env.OUT || path.join('frontend', 'visual-qa', DESIGN)
const BASE = `http://localhost:5173/${STORE}`
const WIDTHS = [1280, 768, 360]

function shot(page, name) {
  const file = path.join(OUT, `${name}.png`)
  return page.screenshot({ path: file, fullPage: true }).then(() => file)
}

async function overflow(page) {
  return page.evaluate(() => {
    const de = document.documentElement
    const scrollable = (el) => {
      for (let p = el.parentElement; p; p = p.parentElement) {
        const o = getComputedStyle(p).overflowX
        if (o === 'auto' || o === 'scroll') return true
      }
      return false
    }
    const wide = [...document.querySelectorAll('body *')]
      .filter((el) => {
        const r = el.getBoundingClientRect()
        return r.width > 0 && r.right > de.clientWidth + 1 && getComputedStyle(el).position !== 'fixed' && !scrollable(el)
      })
      .slice(0, 6)
      .map((el) => `${el.tagName.toLowerCase()}.${String(el.className).split(' ').slice(0, 2).join('.')}`)
    return { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, wide }
  })
}

// Con el scroll al pie, ningún control puede quedar debajo de una barra fija
// (tab bar del diseño, FAB, banner): eso es texto/icono tapado.
async function covered(page) {
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  await page.waitForTimeout(350)
  const hit = await page.evaluate(() => {
    const fixed = [...document.querySelectorAll('body *')].filter((el) => {
      const s = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return s.position === 'fixed' && s.visibility !== 'hidden' && r.height > 24 && r.width > 24 && r.bottom > innerHeight - 160
    })
    const out = []
    for (const el of document.querySelectorAll('input, select, textarea, button, a, h1, h2, p')) {
      const r = el.getBoundingClientRect()
      if (!r.width || !r.height) continue
      for (const f of fixed) {
        if (f.contains(el)) continue
        const fr = f.getBoundingClientRect()
        if (r.top < fr.bottom && r.bottom > fr.top && r.left < fr.right && r.right > fr.left) {
          out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]} <- ${String(f.className).split(' ')[0]}`)
          break
        }
      }
    }
    return [...new Set(out)].slice(0, 8)
  })
  await page.evaluate(() => window.scrollTo(0, 0))
  return hit
}

async function clickText(page, text) {
  const btn = page.getByRole('button', { name: new RegExp(text, 'i') }).first()
  if (await btn.count()) { await btn.click(); await page.waitForTimeout(250); return true }
  return false
}

export default async function run(page, ui) {
  fs.mkdirSync(OUT, { recursive: true })
  const report = { store: STORE, design: DESIGN, screens: {}, overflow: {}, covered: {}, errors: [] }
  page.on('console', (m) => { if (m.type() === 'error') report.errors.push(m.text().slice(0, 200)) })

  await page.setViewportSize({ width: WIDTHS[0], height: 900 })
  await page.goto(`${BASE}/ingresar`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.ec-auth-panel', { timeout: 25000 })

  // --- Auth: tres modos sin recargar
  report.screens['auth-login-1280'] = await shot(page, 'auth-login-1280')
  report.overflow['auth-login-1280'] = await overflow(page)
  if (await clickText(page, 'Registrate|Regístrate')) {
    report.screens['auth-register-1280'] = await shot(page, 'auth-register-1280')
  }
  if (await clickText(page, 'Ya tenés cuenta')) await page.waitForTimeout(150)
  if (await clickText(page, 'Olvidaste tu contraseña')) {
    report.screens['auth-forgot-1280'] = await shot(page, 'auth-forgot-1280')
  }
  await clickText(page, 'Volver a ingresar')
  await page.waitForSelector('#ec-auth-email', { timeout: 10000 })

  // --- Auth responsive (mismo documento)
  for (const w of WIDTHS.slice(1)) {
    await page.setViewportSize({ width: w, height: 900 })
    await page.waitForTimeout(250)
    report.screens[`auth-login-${w}`] = await shot(page, `auth-login-${w}`)
    report.overflow[`auth-login-${w}`] = await overflow(page)
    report.covered[`auth-login-${w}`] = await covered(page)
  }

  // --- Login real y cuenta
  await page.setViewportSize({ width: WIDTHS[0], height: 900 })
  await page.fill('#ec-auth-email', EMAIL)
  await page.fill('.ecaf-pass input', PASSWORD)
  await page.click('.ecaf-submit')
  await page.waitForURL(/\/cuenta/, { timeout: 25000 }).catch(() => {})
  await page.waitForSelector('.acc-shell, .acc-gate-card', { timeout: 20000 })

  if (!(await page.locator('.acc-shell').count())) {
    report.screens['account-gate-1280'] = await shot(page, 'account-gate-1280')
    report.errors.push('login falló: quedó el gate de auth')
    return report
  }

  const views = ['pedidos', 'suscripciones', 'direcciones', 'soporte', 'perfil']
  for (const view of views) {
    const nav = page.locator('.acc-navitem', { hasText: new RegExp(view, 'i') }).first()
    if (await nav.count()) await nav.click()
    else {
      const tab = page.locator('.acc-tab', { hasText: new RegExp(view, 'i') }).first()
      if (await tab.count()) await tab.click()
    }
    await page.waitForTimeout(700)
    report.screens[`account-${view}-1280`] = await shot(page, `account-${view}-1280`)
    report.overflow[`account-${view}-1280`] = await overflow(page)
  }

  for (const w of WIDTHS.slice(1)) {
    await page.setViewportSize({ width: w, height: 900 })
    await page.waitForTimeout(350)
    const tab = page.locator('.acc-tab', { hasText: /perfil/i }).first()
    if (await tab.count()) await tab.click()
    await page.waitForTimeout(400)
    report.screens[`account-perfil-${w}`] = await shot(page, `account-perfil-${w}`)
    report.overflow[`account-perfil-${w}`] = await overflow(page)
    report.covered[`account-perfil-${w}`] = await covered(page)
  }

  return report
}
