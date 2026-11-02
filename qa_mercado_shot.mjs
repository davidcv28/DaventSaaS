export default async function run(page) {
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.waitForTimeout(800)
  await page.screenshot({ path: 'qa_mercado_top.png' })
  await page.evaluate(() => window.scrollTo(0, 1100))
  await page.waitForTimeout(500)
  await page.screenshot({ path: 'qa_mercado_mid.png' })
  return { ok: true, height: await page.evaluate(() => document.body.scrollHeight) }
}
