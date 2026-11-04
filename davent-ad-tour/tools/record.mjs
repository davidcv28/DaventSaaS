import pw from 'file:///C:/Users/David/AppData/Roaming/devin/skills/motion-showreel/scripts/node_modules/playwright/index.js';
import { readFileSync, writeFileSync, mkdirSync, readdirSync, renameSync } from 'node:fs';
const { chromium } = pw;

const REC = new URL('../assets/rec/', import.meta.url).pathname.replace(/^\//, '').replace(/%20/g, ' ');
const ROOT = new URL('../', import.meta.url).pathname.replace(/^\//, '').replace(/%20/g, ' ');
mkdirSync(REC, { recursive: true });

const nar = JSON.parse(readFileSync(ROOT + 'audio/narration.json', 'utf8'));
const seg = nar.segments.map(s => s.end - s.start);
const [d1, d2, d3, d4, d5] = seg;

const BASE = 'http://localhost:5173';
const STEPS = [
  { url: `${BASE}/`, dwell: d1, scroll: 1700 },
  { url: `${BASE}/tienda/moda-qa`, dwell: d2 / 2, scroll: 1100 },
  { url: `${BASE}/tienda/mi-qa`, dwell: d2 / 2, scroll: 1000 },
  { url: `${BASE}/tienda/mt-qa`, dwell: d3 / 2, scroll: 900 },
  { url: `${BASE}/tienda/gym-qa`, dwell: d3 / 2, scroll: 850 },
  { url: `${BASE}/tienda/demo`, dwell: d4 / 2, scroll: 850 },
  { url: `${BASE}/tienda/bench-store`, dwell: d4 / 2, scroll: 950 },
];

const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 720, height: 1280 },
  deviceScaleFactor: 1,
  isMobile: true,
  hasTouch: false,
  locale: 'es-AR',
  recordVideo: { dir: REC, size: { width: 720, height: 1280 } },
});

await ctx.addInitScript(() => {
  const mount = () => {
    const d = document.createElement('div');
    Object.assign(d.style, {
      position: 'fixed', left: '50%', top: '60%', width: '26px', height: '26px',
      margin: '-13px 0 0 -13px', borderRadius: '50%',
      background: 'rgba(139,123,255,0.9)', border: '2.5px solid #fff',
      boxShadow: '0 8px 20px rgba(0,0,0,0.35)', pointerEvents: 'none',
      zIndex: 2147483647, transition: 'transform .08s linear', opacity: '0',
    });
    document.body.appendChild(d);
    window.addEventListener('mousemove', e => {
      d.style.opacity = '1';
      d.style.transform = `translate(${e.clientX - innerWidth / 2}px, ${e.clientY - innerHeight * 0.6}px)`;
    }, { passive: true });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
});

const page = await ctx.newPage();
const t0 = Date.now();
const log = [];

for (const [i, step] of STEPS.entries()) {
  await page.goto(step.url, { waitUntil: 'networkidle', timeout: 45000 });
  await sleep(400);
  log.push({ url: step.url, at: (Date.now() - t0) / 1000 });

  const start = Date.now();
  const target = step.dwell * 1000;
  const ready = start;
  const chunks = 9;
  await page.mouse.move(360, 820, { steps: 18 });
  await sleep(180);
  for (let c = 1; c <= chunks; c++) {
    await page.mouse.wheel(0, step.scroll / chunks);
    await page.mouse.move(360 - 50 + Math.sin(c) * 50, 820 + c * 7, { steps: 8 });
    await sleep(Math.max(60, (target - 600) / chunks));
  }
  const left = target - (Date.now() - ready);
  if (left > 0) await sleep(left);
  log.push({ url: step.url, end: (Date.now() - t0) / 1000 });
}

const video = page.video();
await ctx.close();
await browser.close();
const path = await video.path();
const out = ROOT + 'assets/tour.webm';
renameSync(path, out);
writeFileSync(ROOT + 'assets/tour.json', JSON.stringify({ duration: (Date.now() - t0) / 1000, log }, null, 2));
console.log('video', out);
console.log('segments', seg.map(s => s.toFixed(2)).join(' '));
console.log(log.map(l => `${(l.at ?? l.end).toFixed(2)}s ${l.url.replace('http://localhost:5173', '')}`).join('\n'));
