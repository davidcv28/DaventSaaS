import pw from 'file:///C:/Users/David/AppData/Roaming/devin/skills/motion-showreel/scripts/node_modules/playwright/index.js';
const { chromium } = pw;
import { mkdirSync } from 'node:fs';

const OUT = new URL('../assets/', import.meta.url).pathname.replace(/^\//, '');
mkdirSync(OUT, { recursive: true });

const TARGETS = [
  { name: 'landing', url: 'http://localhost:5173/', scrolls: [0, 900, 1800] },
  { name: 'moda', url: 'http://localhost:5173/tienda/moda-qa', scrolls: [0, 800, 1600] },
  { name: 'moda-catalogo', url: 'http://localhost:5173/tienda/moda-qa/catalogo', scrolls: [0, 700] },
  { name: 'gym', url: 'http://localhost:5173/tienda/gym-qa', scrolls: [0, 900, 1800] },
  { name: 'servicios', url: 'http://localhost:5173/tienda/demo/servicios', scrolls: [0, 800] },
  { name: 'demo', url: 'http://localhost:5173/tienda/demo', scrolls: [0, 800] },
  { name: 'tech', url: 'http://localhost:5173/tienda/mt-qa', scrolls: [0, 900] },
  { name: 'impacto', url: 'http://localhost:5173/tienda/mi-qa', scrolls: [0, 900] },
];

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  locale: 'es-AR',
});
const page = await ctx.newPage();

for (const t of TARGETS) {
  try {
    await page.goto(t.url, { waitUntil: 'networkidle', timeout: 45000 });
    // trigger scroll-reveal animations
    for (const y of t.scrolls) {
      await page.evaluate(v => window.scrollTo(0, v), y);
      await page.waitForTimeout(700);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1200);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}${t.name}.png`, fullPage: true });
    const dims = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight]);
    console.log(`ok ${t.name} ${dims.join('x')}`);
  } catch (e) {
    console.log(`fail ${t.name}: ${e.message.split('\n')[0]}`);
  }
}

await browser.close();
