// Auditoría visual en página — fuente única para visual-qa.
// visual-qa.mjs la serializa con .toString() y se la pasa al driver de
// navegador (scripts/lib/pw_driver.py hoy; un driver node puede usar la
// misma función). Corre DENTRO del documento auditado (pattern document).
//
/* global getComputedStyle */
//
// Detecta:
//  - scroll horizontal: documentElement/body scrollWidth > clientWidth + 1
//  - texto que desborda su contenedor: scrollWidth > clientWidth + 2 con
//    overflow-x visible (los overflow hidden/auto/scroll clipan a propósito)
//  - contraste WCAG de nodos de texto contra su fondo efectivo:
//    >= contrastMin (4.5) o >= contrastMinLarge (3.0) cuando el texto es
//    grande (>= largePx, o bold >= boldWeight y >= largeBoldPx).
//    Fondos con imagen/gradiente no se pueden calcular: se cuentan como
//    `skipped`, no como fallo.

export default function auditPage(opts = {}) {
  const O = Object.assign(
    {
      maxNodes: 25,
      contrastMin: 4.5,
      contrastMinLarge: 3.0,
      largePx: 24,
      largeBoldPx: 19,
      boldWeight: 600,
      overflowSlack: 2,
      scrollSlack: 1
    },
    opts || {}
  )

  const result = {
    url: location.href,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scroll: { ok: true, scrollWidth: 0, clientWidth: 0 },
    textOverflow: [],
    contrast: { checked: 0, skipped: 0, failures: [] },
    stats: { elements: 0, textElements: 0 }
  }

  const de = document.documentElement
  const body = document.body
  result.scroll.clientWidth = de.clientWidth
  result.scroll.scrollWidth = Math.max(de.scrollWidth, body ? body.scrollWidth : 0, de.scrollWidth)
  result.scroll.ok = result.scroll.scrollWidth <= result.scroll.clientWidth + O.scrollSlack

  function selOf(el) {
    const parts = []
    let node = el
    while (node && node.nodeType === 1 && parts.length < 4) {
      let s = node.tagName.toLowerCase()
      const cls =
        typeof node.className === 'string' && node.className.trim()
          ? node.className.trim().split(/\s+/).slice(0, 2)
          : []
      if (cls.length) s += '.' + cls.join('.')
      const parent = node.parentElement
      if (parent) {
        const same = Array.prototype.filter.call(parent.children, (c) => c.tagName === node.tagName)
        if (same.length > 1) s += ':nth-of-type(' + (same.indexOf(node) + 1) + ')'
      }
      parts.unshift(s)
      node = parent
    }
    return parts.join(' > ').slice(0, 160)
  }

  function textSnippet(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60)
  }

  function hasDirectText(el) {
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent && n.textContent.trim()) return true
    }
    return false
  }

  function isHidden(el, cs) {
    if (!cs) cs = getComputedStyle(el)
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return true
    if (cs.opacity !== '' && parseFloat(cs.opacity) <= 0.02) return true
    const r = el.getBoundingClientRect()
    if (r.width < 2 || r.height < 2) return true
    return false
  }

  function inSkippable(el) {
    return Boolean(el.closest('svg, canvas, iframe, noscript, template, script, style, select, option'))
  }

  // Chrome del harness de preview (?preview=) — nunca se renderiza en la
  // tienda pública real, así que no es diseño bajo prueba.
  function inPreviewChrome(el) {
    return Boolean(el.closest('.sp-preview-badge'))
  }

  // rgb()/rgba() y color(srgb …) — lo que devuelve getComputedStyle.
  function parseColor(str) {
    if (!str) return null
    str = String(str).trim()
    let m = str.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+%?))?\s*\)$/)
    if (m) {
      let a = m[4] == null ? 1 : parseFloat(m[4])
      if (/%$/.test(m[4] || '')) a = a / 100
      return { r: +m[1], g: +m[2], b: +m[3], a }
    }
    m = str.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+%?))?\s*\)$/)
    if (m) {
      let a = m[4] == null ? 1 : parseFloat(m[4])
      if (/%$/.test(m[4] || '')) a = a / 100
      return { r: Math.round(+m[1] * 255), g: Math.round(+m[2] * 255), b: Math.round(+m[3] * 255), a }
    }
    return null
  }

  function blend(fg, bg) {
    const a = fg.a == null ? 1 : fg.a
    return {
      r: Math.round(fg.r * a + bg.r * (1 - a)),
      g: Math.round(fg.g * a + bg.g * (1 - a)),
      b: Math.round(fg.b * a + bg.b * (1 - a)),
      a: 1
    }
  }

  // Capas de fondo desde el elemento hacia la raíz (la primera con alfa
  // casi opaco corta). Devuelve null si hay imagen/gradiente de por medio
  // (contraste no calculable con precisión).
  function bgColorOf(el) {
    const layers = []
    let node = el
    while (node && node.nodeType === 1) {
      const cs = getComputedStyle(node)
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null
      const c = parseColor(cs.backgroundColor)
      if (c && c.a > 0.01) layers.push(c)
      if (c && c.a >= 0.99) break
      node = node.parentElement
    }
    let acc = { r: 255, g: 255, b: 255, a: 1 } // lienzo por defecto
    for (let i = layers.length - 1; i >= 0; i -= 1) acc = blend(layers[i], acc)
    return acc
  }

  function lum({ r, g, b }) {
    const f = (v) => {
      v /= 255
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
    }
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
  }

  function contrastRatio(c1, c2) {
    const l1 = lum(c1)
    const l2 = lum(c2)
    const hi = Math.max(l1, l2)
    const lo = Math.min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
  }

  function weightOf(cs) {
    const w = cs.fontWeight
    if (w === 'bold') return 700
    if (w === 'normal') return 400
    const n = parseInt(w, 10)
    return Number.isFinite(n) ? n : 400
  }

  function pushFailure(list, item, cap) {
    if (list.length < cap) list.push(item)
  }

  const all = document.querySelectorAll('body *')
  result.stats.elements = all.length

  for (const el of all) {
    if (result.textOverflow.length >= O.maxNodes && result.contrast.failures.length >= O.maxNodes) break
    if (inSkippable(el) || inPreviewChrome(el)) continue
    const cs = getComputedStyle(el)
    if (!hasDirectText(el)) continue
    if (isHidden(el, cs)) continue
    result.stats.textElements += 1

    // --- texto que desborda su caja con overflow visible ---
    if (
      cs.overflowX === 'visible' &&
      el.clientWidth > 0 &&
      el.scrollWidth > el.clientWidth + O.overflowSlack
    ) {
      pushFailure(
        result.textOverflow,
        {
          selector: selOf(el),
          text: textSnippet(el),
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
          whiteSpace: cs.whiteSpace
        },
        O.maxNodes
      )
    }

    // --- contraste ---
    const fg = parseColor(cs.color)
    if (!fg || fg.a <= 0.05) continue
    const bg = bgColorOf(el)
    if (!bg) {
      result.contrast.skipped += 1
      continue
    }
    const effFg = fg.a >= 0.99 ? fg : blend(fg, bg)
    const fs = parseFloat(cs.fontSize) || 16
    const wt = weightOf(cs)
    const large = fs >= O.largePx || (wt >= O.boldWeight && fs >= O.largeBoldPx)
    const min = large ? O.contrastMinLarge : O.contrastMin
    const ratio = contrastRatio(effFg, bg)
    result.contrast.checked += 1
    if (ratio + 1e-6 < min) {
      const key = selOf(el) + '|' + cs.color + '|' + (bg ? bg.r + ',' + bg.g + ',' + bg.b : '?')
      const dup = result.contrast.failures.some((f) => f.key === key)
      if (!dup) {
        pushFailure(
          result.contrast.failures,
          {
            key,
            selector: selOf(el),
            text: textSnippet(el),
            color: cs.color,
            bg: 'rgb(' + bg.r + ', ' + bg.g + ', ' + bg.b + ')',
            fontSize: fs,
            fontWeight: wt,
            large,
            ratio: Math.round(ratio * 100) / 100,
            min
          },
          O.maxNodes
        )
      }
    }
  }

  result.contrast.ok = result.contrast.failures.length === 0
  result.textOverflowOk = result.textOverflow.length === 0
  return result
}
