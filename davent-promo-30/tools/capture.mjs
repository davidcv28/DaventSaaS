import pw from 'file:///C:/Users/David/AppData/Roaming/devin/skills/motion-showreel/scripts/node_modules/playwright/index.js';
const { chromium } = pw;
import { mkdirSync, readFileSync } from 'node:fs';

import { fileURLToPath } from 'node:url';
const OUT = fileURLToPath(new URL('../assets/', import.meta.url)) + '/';
mkdirSync(OUT, { recursive: true });

const REFRESH = null;

const PUBLIC = process.env.ONLY ? [] : [
  { name: 'landing', url: 'http://localhost:5173/', scrolls: [900, 1800] },
  { name: 'register', url: 'http://localhost:5173/register', scrolls: [] },
  { name: 'gym', url: 'http://localhost:5173/gym-qa', scrolls: [900, 1800] },
  { name: 'gym-catalogo', url: 'http://localhost:5173/gym-qa/catalogo', scrolls: [700] },
  { name: 'gym-servicios', url: 'http://localhost:5173/gym-qa/servicios', scrolls: [700] },
];
const PRIVATE = [
  { name: 'dashboard', url: 'http://localhost:5173/dashboard', scrolls: [700], skipTour: true },
];

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  locale: 'es-AR',
});
const ctxAuth = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  locale: 'es-AR',
});
const page = await ctx.newPage();
const pageAuth = await ctxAuth.newPage();
await pageAuth.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
const loginRes = await pageAuth.evaluate(async () => {
  const r = await fetch('/api/token/', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'gymqa', password: 'QaDavent2026!', remember: true }),
  });
  return r.status;
});
console.log('login status', loginRes);
await pageAuth.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
await pageAuth.waitForTimeout(1500);

for (const [t, pg] of [...PUBLIC.map(t => [t, page]), ...PRIVATE.map(t => [t, pageAuth])]) {
  try {
    await pg.goto(t.url, { waitUntil: 'networkidle', timeout: 45000 });
    await pg.waitForTimeout(800);
    if (t.skipTour) {
      try { await pg.click('text=Saltar', { timeout: 3000 }); await pg.waitForTimeout(600); } catch {}
    }
    for (const y of t.scrolls) {
      await pg.evaluate(v => window.scrollTo(0, v), y);
      await pg.waitForTimeout(700);
    }
    await pg.evaluate(() => window.scrollTo(0, 0));
    await pg.waitForTimeout(1200);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(400);
    await pg.screenshot({ path: `${OUT}${t.name}.png`, fullPage: true });
    const dims = await pg.evaluate(() => [location.href, document.documentElement.scrollWidth, document.documentElement.scrollHeight]);
    console.log(`ok ${t.name} ${dims.join(' ')}`);
  } catch (e) {
    console.log(`fail ${t.name}: ${e.message.split('\n')[0]}`);
  }
}

await browser.close();
