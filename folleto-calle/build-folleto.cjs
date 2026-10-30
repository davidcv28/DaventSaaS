/**
 * Folleto DAVENT para repartir en la calle · A6 (105 × 148 mm)
 * Frente + dorso en SVG vectorial, renderizado a PNG 300 dpi.
 * Uso: node folleto-calle/build-folleto.cjs
 */
const fs = require('fs')
const path = require('path')
const QR = require('../frontend/node_modules/qrcode')
const sharp = require('../frontend/node_modules/sharp')

const DIR = __dirname
const M = JSON.parse(fs.readFileSync(path.join(DIR, 'metrics.json'), 'utf8'))

const W = 105
const H = 148
const PT = 25.4 / 72
const mm = (pt) => +(pt * PT).toFixed(4)
const n = (v) => +v.toFixed(3)
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

const C = {
  ink: '#1b1740',
  ink2: '#221c4a',
  indigo: '#4338ca',
  indigo2: '#4f46e5',
  violet: '#7c3aed',
  violet2: '#8b5cf6',
  yellow: '#fde047',
  yellow2: '#facc15',
  green: '#16a34a',
  line: '#e7e1fb',
  paper: '#f8f6ff',
  muted: '#5b5476',
  dark: '#141231'
}

/* ---------------- CONFIGURACIÓN EDITABLE ---------------- */
const CFG = {
  brand: 'DAVENT',
  tagline: 'TU NEGOCIO EN INTERNET',
  url: 'www.davent.com.ar',
  loginUrl: 'https://www.davent.com.ar/login',
  phone: '387 518-1791',
  promoCode: 'PROMO',
  promoDays: 30,
  plans: [
    { name: 'Básico', desc: 'Web con catálogo · hasta 100 productos · estadísticas', price: '$25.000' },
    { name: 'Estándar', desc: '+ QR, folletos, mapa y página de servicios', price: '$30.000', top: true, tag: 'MÁS ELEGIDO' },
    { name: 'Premium', desc: '+ asistencia en vivo, IA de diseño y sin límites', price: '$40.000' }
  ]
}

/* ---------------- QR vectorial ---------------- */
function qrPath(url) {
  const qr = QR.create(url, { errorCorrectionLevel: 'H' })
  const { size, data } = qr.modules
  let d = ''
  for (let y = 0; y < size; y++) {
    let x = 0
    while (x < size) {
      if (!data[y * size + x]) { x++; continue }
      let run = 1
      while (x + run < size && data[y * size + x + run]) run++
      d += `M${x} ${y}h${run}v1h-${run}z`
      x += run
    }
  }
  return { d, size }
}
const QR_URL = CFG.loginUrl
const QRV = qrPath(QR_URL)

function qrGroup(x, y, size, color = '#000') {
  const k = size / QRV.size
  return `<g transform="translate(${n(x)} ${n(y)}) scale(${n(k)})" shape-rendering="crispEdges"><path d="${QRV.d}" fill="${color}"/></g>`
}

/* ---------------- helpers de dibujo ---------------- */
function text({ x, y, s, size, font = 'ui', weight = 400, fill = C.ink, ls = 0, anchor = 'start', opacity }) {
  const fam = font === 'black' ? 'Segoe UI Black' : 'Segoe UI'
  const spacing = ls ? ` letter-spacing="${n(ls * size * PT)}"` : ''
  const op = opacity != null ? ` opacity="${opacity}"` : ''
  return `<text x="${n(x)}" y="${n(y)}" font-family="${fam}" font-weight="${weight}" font-size="${n(size * PT)}" fill="${fill}"${spacing} text-anchor="${anchor}"${op}>${esc(s)}</text>`
}

const ICONS = {
  cart: '<path d="M3 4h2l2.3 10.4h10L20 7H6"/><circle cx="9.5" cy="19" r="1.5"/><circle cx="17" cy="19" r="1.5"/>',
  chat: '<path d="M21 11.5a8.2 8.2 0 0 1-11.9 7.2L4 20l1.4-4.9A8.2 8.2 0 1 1 21 11.5Z"/><path d="M8.6 9.4c.4 3.1 2.9 5.6 6 6"/>',
  qr: '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M20 9V5.5A1.5 1.5 0 0 0 18.5 4H15M4 15v3.5A1.5 1.5 0 0 0 5.5 20H9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15"/><rect x="9" y="9" width="2.6" height="2.6" fill="currentColor" stroke="none"/><rect x="12.4" y="12.4" width="2.6" height="2.6" fill="currentColor" stroke="none"/>',
  chart: '<path d="M4 20V11M10 20V5M16 20v-6M22 20H2"/>',
  gift: '<path d="M3 11h18v9H3z"/><path d="M2 7.5h20V11H2z"/><path d="M12 7.5V20"/><path d="M12 7.5C9.5 7.5 6 6.4 6 4.6 6 3.4 7 2.6 8.2 2.8 10 3.1 11.4 5.2 12 7.5Z"/><path d="M12 7.5c2.5 0 6-1.1 6-2.9 0-1.2-1-2-2.2-1.8C14 3.1 12.6 5.2 12 7.5Z"/>',
  plus: '<path d="M12 3l1.9 5.4L19.3 10l-5.4 1.9L12 17.3l-1.9-5.4L4.7 10l5.4-1.6z"/><path d="M18.6 15.4l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>'
}
function icon(name, cx, cy, size, color, sw = 2.2) {
  const s = size / 24
  return `<g transform="translate(${n(cx)} ${n(cy)}) scale(${n(s)}) translate(-12 -12)" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" color="${color}">${ICONS[name]}</g>`
}

function logoPlate(x, y, size, id) {
  const inner = size * 0.85
  const off = (size - inner) / 2
  return `<g>
    <rect x="${n(x)}" y="${n(y)}" width="${n(size)}" height="${n(size)}" rx="${n(size * 0.26)}" fill="#fff"/>
    <g transform="translate(${n(x + off)} ${n(y + off)}) scale(${n(inner / 40)})">
      <rect width="40" height="40" rx="10" fill="url(#logoGrad${id})"/>
      <path d="M12 10h8.5c5.2 0 9 3.8 9 10s-3.8 10-9 10H12V10Z" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/>
      <path d="M12 20h8" stroke="#c7d2fe" stroke-width="3" stroke-linecap="round"/>
    </g>
  </g>`
}

const phoneIcon = (x, y, size, color = '#fff') =>
  `<g transform="translate(${n(x)} ${n(y)}) scale(${n(size / 24)})" fill="${color}"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.2.2 2.4.6 3.6.1.4 0 .8-.2 1l-2.3 2.2Z"/></g>`

/* ---------------- FRENTE ---------------- */
const hook2W = M.hook2
const hlX = 5.0
const hlY = 32.4
const hlW = n(hook2W + 2.2)
const hlH = 7.9

const promoTitle = `${CFG.promoDays} DÍAS DE PREMIUM DE REGALO`
const chipX = n(20.2 + M.promo2a + 0.6)
const chipW = n(M.promo2b + 2.9)
const postX = n(chipX + chipW + 0.4)
const wppW = n(2.0 + 3.1 + 1.5 + M.wpp + 2.2)

const bandGradient = `
  <radialGradient id="band" cx="100" cy="-2" r="120" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="${C.violet2}"/>
    <stop offset="0.42" stop-color="#6d28d9"/>
    <stop offset="1" stop-color="${C.indigo}"/>
  </radialGradient>
  <linearGradient id="logoGradF" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="${C.indigo}"/>
  </linearGradient>
  <linearGradient id="logoGradB" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="${C.indigo}"/>
  </linearGradient>
  <linearGradient id="yellowBand" x1="6" y1="0" x2="99" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="${C.yellow}"/><stop offset="1" stop-color="${C.yellow2}"/>
  </linearGradient>
  <linearGradient id="topPlan" x1="6" y1="0" x2="99" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="${C.indigo}"/><stop offset="1" stop-color="${C.violet}"/>
  </linearGradient>
  <pattern id="dots" width="2.2" height="2.2" patternUnits="userSpaceOnUse">
    <circle cx="0.5" cy="0.5" r="0.27" fill="#fff"/>
  </pattern>
  <clipPath id="clipHead"><rect x="0" y="0" width="${W}" height="58"/></clipPath>
  <clipPath id="clipPromo"><rect x="6" y="99.2" width="93" height="14.2" rx="2.2"/></clipPath>
  <clipPath id="clipCta"><rect x="0" y="117.4" width="${W}" height="30.6"/></clipPath>
`

function perks() {
  const cw = 45.3
  const ch = 14.2
  const gx = 2.4
  const gy = 2.0
  const x1 = 6
  const y1 = 65.6
  const items = [
    { ic: 'cart', t: 'Tu web con catálogo', s1: 'Productos, fotos y precios', s2: 'en un link propio.' },
    { ic: 'chat', t: 'Pedidos por WhatsApp', s1: 'El cliente consulta y pide', s2: 'sin salir de tu web.' },
    { ic: 'qr', t: 'QR y folletos', s1: 'Para tu local, tu vidriera', s2: 'y tus redes.' },
    { ic: 'chart', t: 'Estadísticas de visitas', s1: 'Cuánta gente ve tu web', s2: 'cada día.' }
  ]
  return items.map((it, i) => {
    const cx = i % 2 === 0 ? x1 : x1 + cw + gx
    const cy = i < 2 ? y1 : y1 + ch + gy
    return `<g>
      <rect x="${n(cx)}" y="${n(cy)}" width="${n(cw)}" height="${n(ch)}" rx="2" fill="${C.paper}" stroke="${C.line}" stroke-width="0.3"/>
      <rect x="${n(cx + 2.4)}" y="${n(cy + 2.5)}" width="5.6" height="5.6" rx="1.6" fill="${C.indigo}"/>
      ${icon(it.ic, cx + 5.2, cy + 5.3, 3.4, '#fff')}
      ${text({ x: cx + 9.9, y: cy + 6.0, s: it.t, size: 7.3, weight: 700, fill: C.ink2 })}
      ${text({ x: cx + 9.9, y: cy + 9.0, s: it.s1, size: 6.1, fill: C.muted })}
      ${text({ x: cx + 9.9, y: cy + 11.4, s: it.s2, size: 6.1, fill: C.muted })}
    </g>`
  }).join('\n')
}

const front = `<svg xmlns="http://www.w3.org/2000/svg" width="105mm" height="148mm" viewBox="0 0 105 148">
<title>DAVENT · folleto para la calle · frente</title>
<defs>${bandGradient}</defs>
<rect width="${W}" height="${H}" fill="#fff"/>

<!-- CABECERA -->
<rect width="${W}" height="58" fill="url(#band)"/>
<g clip-path="url(#clipHead)">
  <rect width="${W}" height="58" fill="url(#dots)" opacity="0.42"/>
  <circle cx="100" cy="-3" r="25" fill="none" stroke="#fff" stroke-width="9" opacity="0.08"/>
</g>
${logoPlate(6, 5.0, 9.4, 'F')}
${text({ x: 18.0, y: 10.8, s: CFG.brand, size: 12, font: 'black', fill: '#fff', ls: 0.2 })}
${text({ x: 18.0, y: 13.9, s: CFG.tagline, size: 5.2, weight: 700, fill: '#cfc6ff', ls: 0.14 })}
<rect x="6" y="19.3" width="6" height="0.5" rx="0.25" fill="${C.yellow}"/>
${text({ x: 13.6, y: 20.4, s: 'PARA LOCALES, EMPRENDEDORES Y PROFESIONALES', size: 5.6, weight: 700, fill: C.yellow, ls: 0.13 })}
${text({ x: 6, y: 31.2, s: 'TU NEGOCIO', size: 25, font: 'black', fill: '#fff', ls: -0.03 })}
<rect x="${hlX}" y="${hlY}" width="${hlW}" height="${hlH}" rx="1.2" fill="${C.yellow}"/>
${text({ x: 6.2, y: 38.9, s: 'EN INTERNET.', size: 25, font: 'black', fill: C.ink, ls: -0.03 })}
${text({ x: 6, y: 46.0, s: 'Creá tu web con catálogo, QR y pedidos por WhatsApp.', size: 8, fill: '#e6e0ff' })}
${text({ x: 6, y: 50.2, s: 'La armás en minutos y sin saber de tecnología.', size: 8, fill: '#e6e0ff' })}

<!-- BENEFICIOS -->
${text({ x: 6, y: 63.4, s: 'LO QUE PODÉS HACER CON DAVENT', size: 5.6, weight: 700, fill: C.indigo, ls: 0.15 })}
<rect x="${n(6 + M.eyebrow + 2.6)}" y="62.8" width="${n(99 - (6 + M.eyebrow + 2.6))}" height="0.3" fill="#ddd6fe"/>
${perks()}

<!-- PROMO -->
<rect x="6" y="99.2" width="93" height="14.2" rx="2.2" fill="url(#yellowBand)" stroke="#e0b400" stroke-width="0.35"/>
<g clip-path="url(#clipPromo)">
  <circle cx="96" cy="96.5" r="9.5" fill="none" stroke="#fff" stroke-width="3.4" opacity="0.35"/>
</g>
<rect x="8.8" y="102.2" width="8.4" height="8.4" rx="2.2" fill="${C.ink}"/>
${icon('gift', 13.0, 106.4, 4.9, C.yellow, 2.1)}
${text({ x: 20.2, y: 106.4, s: promoTitle, size: 9.4, font: 'black', fill: '#2a1f00', ls: -0.01 })}
${text({ x: 20.2, y: 110.6, s: 'Registrate y canjeá el código', size: 6.5, fill: '#4a3600' })}
<rect x="${chipX}" y="107.4" width="${chipW}" height="4.0" rx="0.9" fill="${C.ink}"/>
${text({ x: n(chipX + chipW / 2), y: 110.5, s: CFG.promoCode, size: 7, font: 'black', fill: C.yellow, ls: 0.04, anchor: 'middle' })}
${text({ x: postX, y: 110.6, s: '. Sin tarjeta ni débito.', size: 6.5, fill: '#4a3600' })}

<!-- CTA -->
<rect x="0" y="116" width="${W}" height="1.4" fill="${C.yellow}"/>
<rect x="0" y="117.4" width="${W}" height="30.6" fill="${C.dark}"/>
<g clip-path="url(#clipCta)"><rect x="0" y="117.4" width="${W}" height="30.6" fill="url(#dots)" opacity="0.3"/></g>
<rect x="6" y="120.7" width="20.0" height="21.7" rx="2.0" fill="#fff"/>
${qrGroup(8.0, 122.7, 16.0)}
${text({ x: 16.0, y: 141.1, s: 'ESCANEÁ', size: 5, font: 'black', fill: C.ink, ls: 0.12, anchor: 'middle' })}
${text({ x: 29.6, y: 125.6, s: 'CREÁ TU WEB GRATIS', size: 5.7, weight: 700, fill: C.yellow, ls: 0.15 })}
${text({ x: 29.6, y: 131.2, s: CFG.url, size: 9.4, font: 'black', fill: '#fff' })}
${text({ x: 29.6, y: 134.9, s: 'Apuntá la cámara al QR y empezá hoy.', size: 6.1, fill: '#bdb6dd' })}
<rect x="29.6" y="137.1" width="${wppW}" height="6.1" rx="3.05" fill="${C.green}"/>
${phoneIcon(31.6, 138.6, 3.1)}
${text({ x: 36.2, y: 141.7, s: CFG.phone, size: 7, weight: 700, fill: '#fff' })}
</svg>`

/* ---------------- DORSO ---------------- */
function planRow({ y, name, desc, price, top, tag }) {
  const bg = top ? 'url(#topPlan)' : C.paper
  const stroke = top ? 'none' : C.line
  const nameFill = top ? '#fff' : C.ink
  const descFill = top ? '#dcd5ff' : C.muted
  const priceFill = top ? C.yellow : C.indigo
  const perFill = top ? '#dcd5ff' : '#7a7295'
  const nameW = M['plan_' + name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')] || 0
  const tagW = tag ? M.tag + 2.4 : 0
  const tagX = 6 + 3 + nameW + 1.8
  return `<g>
    <rect x="6" y="${n(y)}" width="93" height="16.4" rx="2.2" fill="${bg}" ${top ? '' : `stroke="${stroke}" stroke-width="0.35"`}/>
    ${text({ x: 9, y: y + 6.4, s: name, size: 9, font: 'black', fill: nameFill })}
    ${
      tag
        ? `<rect x="${n(tagX)}" y="${n(y + 4.0)}" width="${n(tagW)}" height="3.5" rx="1.75" fill="${C.yellow}"/>
    ${text({ x: n(tagX + tagW / 2), y: n(y + 6.45), s: tag, size: 4.9, weight: 700, fill: C.ink, ls: 0.08, anchor: 'middle' })}`
        : ''
    }
    ${text({ x: 9, y: y + 10.9, s: desc, size: 6.2, fill: descFill })}
    ${text({ x: 96, y: y + 8.1, s: price, size: 10.6, font: 'black', fill: priceFill, anchor: 'end' })}
    ${text({ x: 96, y: y + 11.9, s: '/mes', size: 5.6, weight: 700, fill: perFill, anchor: 'end' })}
  </g>`
}

const back = `<svg xmlns="http://www.w3.org/2000/svg" width="105mm" height="148mm" viewBox="0 0 105 148">
<title>DAVENT · folleto para la calle · dorso</title>
<defs>${bandGradient}</defs>
<rect width="${W}" height="${H}" fill="#fff"/>

<!-- CABECERA -->
<rect width="${W}" height="17.6" fill="url(#band)"/>
<g clip-path="url(#clipHeadBack)">
  <rect width="${W}" height="17.6" fill="url(#dots)" opacity="0.4"/>
  <circle cx="99" cy="-8" r="15" fill="none" stroke="#fff" stroke-width="6" opacity="0.08"/>
</g>
<clipPath id="clipHeadBack"><rect width="${W}" height="17.6"/></clipPath>
${logoPlate(6, 4.0, 8.0, 'B')}
${text({ x: 16.6, y: 10.4, s: CFG.brand, size: 9.6, font: 'black', fill: '#fff', ls: 0.18 })}
${text({ x: 16.6, y: 13.4, s: CFG.tagline, size: 4.8, weight: 700, fill: '#cfc6ff', ls: 0.14 })}
<rect x="74" y="6.0" width="25" height="5.8" rx="2.9" fill="none" stroke="${C.yellow}" stroke-width="0.35" opacity="0.9"/>
${text({ x: 86.5, y: 9.95, s: 'PLANES Y PRECIOS', size: 5.4, weight: 700, fill: C.yellow, ls: 0.14, anchor: 'middle' })}

<!-- TITULO -->
${text({ x: 6, y: 25.8, s: 'Elegí tu plan.', size: 15, font: 'black', fill: C.ink, ls: -0.03 })}
${text({ x: 6, y: 31.2, s: 'Sin contratos.', size: 15, font: 'black', fill: C.indigo, ls: -0.03 })}
${text({ x: 6, y: 35.0, s: 'Pago mensual en pesos. Cambiás de plan o das de baja cuando quieras.', size: 6.7, fill: C.muted })}

<!-- PLANES -->
${CFG.plans.map((p, i) => planRow({ y: 38.2 + i * 18.3, ...p })).join('\n')}

<!-- PRUEBA -->
<rect x="6" y="94.4" width="93" height="12.0" rx="2.2" fill="#f4f1ff" stroke="#c4b5fd" stroke-width="0.35" stroke-dasharray="1.2 0.9"/>
<rect x="8.6" y="97.6" width="5.6" height="5.6" rx="1.5" fill="${C.indigo}"/>
${icon('plus', 11.4, 100.4, 3.4, '#fff')}
${text({ x: 16.4, y: 100.0, s: '¿Primera vez? Probá sin pagar', size: 7, weight: 700, fill: C.ink })}
${text({ x: 16.4, y: 103.3, s: 'Al registrarte arrancás con un plan de prueba, sin tarjeta.', size: 6.1, fill: C.muted })}

<!-- PASOS -->
${text({ x: 6, y: 111.7, s: 'EMPEZÁ HOY EN 3 PASOS', size: 5.6, weight: 700, fill: C.indigo, ls: 0.15 })}
<rect x="${n(6 + M.steps_title + 2.6)}" y="111.1" width="${n(99 - (6 + M.steps_title + 2.6))}" height="0.3" fill="#ddd6fe"/>
<g>
  <circle cx="9" cy="116.2" r="3" fill="${C.yellow}"/>
  ${text({ x: 9, y: 117.4, s: '1', size: 7.6, font: 'black', fill: C.ink, anchor: 'middle' })}
  ${text({ x: 6, y: 122.4, s: 'Escaneá el QR', size: 6.5, weight: 700, fill: C.ink })}
  ${text({ x: 6, y: 125.0, s: 'Entrás a la web', size: 5.9, fill: C.muted })}
  ${text({ x: 6, y: 127.4, s: 'de DAVENT.', size: 5.9, fill: C.muted })}
</g>
<g>
  <circle cx="40.5" cy="116.2" r="3" fill="${C.yellow}"/>
  ${text({ x: 40.5, y: 117.4, s: '2', size: 7.6, font: 'black', fill: C.ink, anchor: 'middle' })}
  ${text({ x: 37.5, y: 122.4, s: 'Registrate', size: 6.5, weight: 700, fill: C.ink })}
  ${text({ x: 37.5, y: 125.0, s: 'Con tu email', size: 5.9, fill: C.muted })}
  ${text({ x: 37.5, y: 127.4, s: 'y tu celular.', size: 5.9, fill: C.muted })}
</g>
<g>
  <circle cx="72" cy="116.2" r="3" fill="${C.yellow}"/>
  ${text({ x: 72, y: 117.4, s: '3', size: 7.6, font: 'black', fill: C.ink, anchor: 'middle' })}
  ${text({ x: 69, y: 122.4, s: 'Publicá tu web', size: 6.5, weight: 700, fill: C.ink })}
  ${text({ x: 69, y: 125.0, s: 'Compartí el link', size: 5.9, fill: C.muted })}
  ${text({ x: 69, y: 127.4, s: 'y empezá a vender.', size: 5.9, fill: C.muted })}
</g>

<!-- PIE -->
<rect x="0" y="131" width="${W}" height="1.1" fill="${C.yellow}"/>
<rect x="0" y="132.1" width="${W}" height="15.9" fill="${C.dark}"/>
<rect x="6" y="134.0" width="13.0" height="12.6" rx="1.8" fill="#fff"/>
${qrGroup(7.3, 135.1, 10.4)}
${text({ x: 22.6, y: 137.4, s: CFG.url, size: 8, font: 'black', fill: '#fff' })}
${phoneIcon(22.6, 139.5, 2.9, '#25d366')}
${text({ x: 26.4, y: 141.5, s: `WhatsApp ${CFG.phone}`, size: 6.6, weight: 700, fill: '#8ee7ab' })}
${text({ x: 22.6, y: 145.6, s: 'Precios en ARS por mes · renovación mensual · baja cuando quieras.', size: 4.6, fill: '#a9a3c4' })}
</svg>`

/* ---------------- render ---------------- */
async function main() {
  fs.writeFileSync(path.join(DIR, 'frente.svg'), front)
  fs.writeFileSync(path.join(DIR, 'dorso.svg'), back)

  for (const [name, svg] of [['frente', front], ['dorso', back]]) {
    await sharp(Buffer.from(svg), { density: 300 })
      .png({ compressionLevel: 9 })
      .toFile(path.join(DIR, name + '.png'))
  }
  console.log('SVG + PNG listos')
}
main().catch((e) => { console.error(e); process.exit(1) })
