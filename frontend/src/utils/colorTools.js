const SAMPLE_SIZE = 56

export function hexToRgb(hex) {
  const h = String(hex).replace('#', '')
  const n = parseInt(h.length === 3 ? h.replace(/./g, '$&$&') : h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgbToHex([r, g, b]) {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`
}

function channel(v) {
  const s = v / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

export function luminance(hex) {
  const [r, g, b] = hexToRgb(hex)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

export function contrastRatio(a, b) {
  const la = luminance(a)
  const lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

function saturation([r, g, b]) {
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  return max === 0 ? 0 : (max - min) / max
}

function rgbToLab([r, g, b]) {
  const [lr, lg, lb] = [r, g, b].map(channel)
  const x = (lr * 0.4124 + lg * 0.3576 + lb * 0.1805) / 0.95047
  const y = lr * 0.2126 + lg * 0.7152 + lb * 0.0722
  const z = (lr * 0.0193 + lg * 0.1192 + lb * 0.9505) / 1.08883
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116)
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))]
}

function labDistance(a, b) {
  const la = rgbToLab(a)
  const lb = rgbToLab(b)
  return Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2])
}

export function nearestAccent(rgb, accents) {
  let best = null
  let bestDist = Infinity
  for (const [key, a] of Object.entries(accents)) {
    const d = labDistance(rgb, hexToRgb(a.hex))
    if (d < bestDist) { best = key; bestDist = d }
  }
  return best
}

function loadImage(src, cors) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    if (cors) img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image'))
    img.src = src
  })
}

export function quantizeColors(data, max = 5) {
  const buckets = new Map()
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue
    const key = ((data[i] >> 4) << 8) | ((data[i + 1] >> 4) << 4) | (data[i + 2] >> 4)
    const b = buckets.get(key) || { n: 0, r: 0, g: 0, b: 0 }
    b.n += 1
    b.r += data[i]
    b.g += data[i + 1]
    b.b += data[i + 2]
    buckets.set(key, b)
  }
  const ranked = [...buckets.values()]
    .map((b) => {
      const rgb = [b.r / b.n, b.g / b.n, b.b / b.n]
      const max3 = Math.max(...rgb)
      const min3 = Math.min(...rgb)
      const neutral = max3 > 235 && min3 > 225
      return { rgb, score: b.n * (neutral ? 0.15 : 0.35 + saturation(rgb)) }
    })
    .sort((a, b) => b.score - a.score)
  const picked = []
  for (const c of ranked) {
    if (picked.every((p) => labDistance(p.rgb, c.rgb) > 18)) picked.push(c)
    if (picked.length === max) break
  }
  return picked.map((c) => rgbToHex(c.rgb))
}

export async function extractLogoColors(src, { cors = true, max = 5 } = {}) {
  const img = await loadImage(src, cors)
  const scale = Math.min(1, SAMPLE_SIZE / Math.max(img.naturalWidth, img.naturalHeight, 1))
  const w = Math.max(1, Math.round(img.naturalWidth * scale))
  const h = Math.max(1, Math.round(img.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(img, 0, 0, w, h)
  return quantizeColors(ctx.getImageData(0, 0, w, h).data, max)
}
