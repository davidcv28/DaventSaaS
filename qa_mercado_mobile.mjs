export default async function run(page) {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('http://localhost:5174/demo/', { waitUntil: 'networkidle' })
  await page.waitForSelector('.mc-home')
  await page.waitForTimeout(600)
  await page.screenshot({ path: 'qa_mercado_mob.png' })
  return { ok: true }
}
