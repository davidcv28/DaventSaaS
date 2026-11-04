/* global getComputedStyle */
export default async function run(page, ui) {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)
  const snap = await ui.snapshot()
  const user = snap.match(/@(e\d+) textbox "Nombre de usuario/)?.[1]
  const pass = snap.match(/@(e\d+) textbox "Contraseña/)?.[1]
  const submit = snap.match(/@(e\d+) button "Iniciar sesión"/)?.[1]
  if (user) await ui.fill(user, 'qablocks')
  if (pass) await ui.fill(pass, 'StudioQA2026!')
  if (submit) await ui.click(submit)
  await page.waitForTimeout(2500)
  await page.goto('http://localhost:5173/dashboard/diseno/studio', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(3500)
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === 'Omitir')
    if (b) b.click()
  })
  await page.waitForTimeout(600)
  await page.screenshot({ path: 'C:/Users/David/OneDrive/Escritorio/SaaS DAVENT/frontend/.qa-now.png' })
  return await page.evaluate(() => {
    const sts = document.querySelector('.sts')
    const panel = document.querySelector('.sts-panel')
    const rail = document.querySelector('.sts-rail')
    const save = document.querySelector('.sts-savebar')
    const r = (el) => el && { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) }
    return {
      sts: r(sts), panel: r(panel), rail: r(rail), save: r(save),
      cols: sts && getComputedStyle(sts).gridTemplateColumns,
      rows: sts && getComputedStyle(sts).gridTemplateRows,
      panelFont: panel && getComputedStyle(panel).fontFamily,
      bodyScrollX: document.documentElement.scrollWidth > window.innerWidth
    }
  })
}
