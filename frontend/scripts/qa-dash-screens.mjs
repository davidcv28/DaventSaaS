// QA visual del dashboard del dueño (plataforma) + auth de la plataforma.
//
// Uso:
//   node "C:\Users\David\.claude\skills\browser-automation\browser.mjs" \
//     http://localhost:5173/login --script frontend/scripts/qa-dash-screens.mjs
//
// Variables: QA_USER / QA_PASS (cuenta dueña QA), OUT (default
// frontend/visual-qa/dashboard).
import fs from 'node:fs'
import path from 'node:path'

const USER = process.env.QA_USER || 'mtqa'
const PASS = process.env.QA_PASS || 'QaVisual2026!'
const OUT = process.env.OUT || path.join('frontend', 'visual-qa', 'dashboard')
const WIDTHS = [1280, 768, 360]
const ROUTES = ['/dashboard', '/app/productos', '/app/visitas', '/app/opiniones', '/app/negocio', '/app/diseno']

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

async function covered(page) {
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  await page.waitForTimeout(300)
  const hit = await page.evaluate(() => {
    const fixed = [...document.querySelectorAll('body *')].filter((el) => {
      const s = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return (s.position === 'fixed' || s.position === 'sticky') && s.visibility !== 'hidden' && r.height > 24 && r.width > 24
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

async function dismissOverlays(page) {
  for (const label of ['Saltar', 'Omitir', 'Ahora no', 'Cerrar']) {
    const b = page.getByRole('button', { name: new RegExp(`^${label}$`, 'i') }).first()
    if (await b.count()) await b.click({ timeout: 2000 }).catch(() => {})
  }
  await page.waitForTimeout(300)
}

export default async function run(page, ui) {
  fs.mkdirSync(OUT, { recursive: true })
  const report = { screens: {}, overflow: {}, covered: {}, errors: [] }
  page.on('console', (m) => { if (m.type() === 'error') report.errors.push(m.text().slice(0, 200)) })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.waitForSelector('input[autocomplete="username"], #username, input[name="username"]', { timeout: 20000 })
  report.screens['auth-login-1280'] = await shot(page, 'auth-login-1280')

  for (const w of WIDTHS.slice(1)) {
    await page.setViewportSize({ width: w, height: 900 })
    await page.waitForTimeout(200)
    report.screens[`auth-login-${w}`] = await shot(page, `auth-login-${w}`)
    report.overflow[`auth-login-${w}`] = await overflow(page)
  }

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.fill('input[autocomplete="username"], #username, input[name="username"]', USER)
  await page.fill('input[type="password"]', PASS)
  await page.click('button[type="submit"], .auth-submit, button:has-text("Iniciar sesión")')
  await page.waitForURL((u) => !/\/login/.test(u.pathname), { timeout: 25000 }).catch(() => {})
  await page.waitForTimeout(1200)
  await dismissOverlays(page)

  for (const route of ROUTES) {
    await page.goto(`http://localhost:5173${route}`, { waitUntil: 'networkidle' }).catch(() => {})
    await page.waitForTimeout(1200)
    await dismissOverlays(page)
    const name = route.replace(/\//g, '_').replace(/^_/, '') || 'root'
    report.screens[`${name}-1280`] = await shot(page, `${name}-1280`)
    report.overflow[`${name}-1280`] = await overflow(page)
    for (const w of WIDTHS.slice(1)) {
      await page.setViewportSize({ width: w, height: 900 })
      await page.waitForTimeout(500)
      report.screens[`${name}-${w}`] = await shot(page, `${name}-${w}`)
      report.overflow[`${name}-${w}`] = await overflow(page)
      report.covered[`${name}-${w}`] = await covered(page)
    }
    await page.setViewportSize({ width: 1280, height: 900 })
  }

  return report
}
