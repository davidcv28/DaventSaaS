// Genera los PNG fuente que consume `npx @capacitor/assets generate --android`
// a partir del logo de marca (mismo path "D" que BrandLogo.vue).
// Uso: node scripts/build-native-assets.mjs  →  escribe en ./assets/
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import sharp from 'sharp'

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'assets')
const BRAND = '#4f46e5'
const GRAD = `<defs><linearGradient id="dv-g" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#4338ca"/></linearGradient></defs>`
const D_GLYPH = `<path d="M12 10h8.5c5.2 0 9 3.8 9 10s-3.8 10-9 10H12V10Z" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/><path d="M12 20h8" stroke="#c7d2fe" stroke-width="3" stroke-linecap="round"/>`

// Adaptive icon: la D ocupa el máximo de la zona segura — el launcher aplica
// una máscara (círculo/squircle) y solo se garantiza el 66% central (~682px
// de 1024). El glyph mide 17.5×20u: scale(32) → 560×640px, al límite sin
// que el trazo toque el borde de la máscara.
const foreground = `<svg width="1024" height="1024" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-152 -128) scale(32)">${D_GLYPH}</g></svg>`
const background = `<svg width="1024" height="1024" xmlns="http://www.w3.org/2000/svg"><rect width="1024" height="1024" fill="${BRAND}"/></svg>`

// Legacy icon (pre-API26): cuadrado full-bleed con gradiente + D al ~90% del
// lado, centrada.
const icon = `<svg width="1024" height="1024" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">${GRAD}<rect width="40" height="40" fill="url(#dv-g)"/><g transform="translate(20 20) scale(1.75) translate(-20 -20)">${D_GLYPH}</g></svg>`

// Splash 2732² (fuente de @capacitor/assets): marca centrada ~530px.
const splash = (bg) => `<svg width="2732" height="2732" viewBox="0 0 2732 2732" xmlns="http://www.w3.org/2000/svg">${GRAD}<rect width="2732" height="2732" fill="${bg}"/><g transform="translate(1100 1100) scale(13.3)"><rect width="40" height="40" rx="11" fill="url(#dv-g)"/>${D_GLYPH}</g></svg>`

const files = {
  'icon-foreground.png': foreground,
  'icon-background.png': background,
  'icon.png': icon,
  'icon-only.png': icon,
  'splash.png': splash(BRAND),
  'splash-dark.png': splash(BRAND),
}

await mkdir(OUT, { recursive: true })
for (const [name, svg] of Object.entries(files)) {
  const buf = await sharp(Buffer.from(svg)).png().toBuffer()
  await writeFile(join(OUT, name), buf)
  console.log('assets/' + name, buf.length, 'bytes')
}
