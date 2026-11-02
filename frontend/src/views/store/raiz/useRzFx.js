// Capa premium RAÍZ/ESENCIAL (JS): tilt 3D en tarjetas con seguimiento de
// puntero, parallax suave del media del hero, contadores animados en stats
// y pausa de loops ambientales (pestaña oculta o bloque fuera de viewport).
// Todo es opt-in por estilo: `rz-fx` marca la página y `rz-fx-rich` sube la
// intensidad (esencial-noche + esencial-premium). Sin libs: listeners
// pasivos, rAF y observers — mismo patrón que mercado/useMcFx.
import { onBeforeUnmount, onMounted } from 'vue'

const reduceMotion = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
const finePointer = typeof window !== 'undefined'
  && window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches

const RICH_STYLES = new Set(['esencial-noche', 'esencial-premium'])
const TILT_MAX = 4 // grados, tope del brief

function styleOf(page) { return page?.dataset?.style || '' }

// ---- Tilt 3D: un listener delegado en la raíz; la tarjeta bajo el puntero
// recibe --rx/--ry y el CSS (transform con perspective) hace el resto.
function bindTilt(rootEl, page) {
  if (reduceMotion || !finePointer || !RICH_STYLES.has(styleOf(page))) return null
  let current = null
  const reset = () => {
    if (!current) return
    current.style.removeProperty('--rx')
    current.style.removeProperty('--ry')
    current.classList.remove('is-tilting')
    current = null
  }
  const move = (e) => {
    const card = e.target.closest?.('.tpc, .sp-card, .rz-tilt')
    if (card !== current) {
      reset()
      current = card
      if (current) current.classList.add('is-tilting')
    }
    if (!current) return
    const r = current.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width - .5
    const py = (e.clientY - r.top) / r.height - .5
    current.style.setProperty('--ry', `${(px * TILT_MAX).toFixed(2)}deg`)
    current.style.setProperty('--rx', `${(-py * TILT_MAX).toFixed(2)}deg`)
  }
  rootEl.addEventListener('pointermove', move, { passive: true })
  rootEl.addEventListener('pointerleave', reset, { passive: true })
  rootEl.addEventListener('pointercancel', reset, { passive: true })
  return () => {
    rootEl.removeEventListener('pointermove', move)
    rootEl.removeEventListener('pointerleave', reset)
    rootEl.removeEventListener('pointercancel', reset)
    reset()
  }
}

// ---- Parallax del hero: el media baja ~12% del scroll (cap 80px) mientras
// la página lo tiene a la vista. Solo transform; rAF sobre scroll pasivo.
function bindParallax(page) {
  if (reduceMotion || !RICH_STYLES.has(styleOf(page))) return null
  const media = page.querySelector('.rh-hero-media, .rh-hero-block')
  if (!media) return null
  media.classList.add('rz-parallax')
  let raf = 0
  const apply = () => {
    raf = 0
    const y = Math.min(window.scrollY * .12, 80)
    media.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`
  }
  const onScroll = () => { if (!raf) raf = requestAnimationFrame(apply) }
  window.addEventListener('scroll', onScroll, { passive: true })
  return () => {
    window.removeEventListener('scroll', onScroll)
    if (raf) cancelAnimationFrame(raf)
    media.classList.remove('rz-parallax')
    media.style.transform = ''
  }
}

// ---- Contadores: .rh-stat-value con texto numérico ("1.200+", "98%") sube
// desde 0 la primera vez que entra al viewport.
function bindCounters(rootEl) {
  if (reduceMotion || !('IntersectionObserver' in window)) return null
  const targets = [...rootEl.querySelectorAll('.rh-stat-value')]
    .map((el) => {
      const m = el.textContent.trim().match(/^([\d.,]+)(.*)$/)
      if (!m) return null
      const num = parseFloat(m[1].replace(/\./g, '').replace(',', '.'))
      if (!Number.isFinite(num) || num <= 0) return null
      return { el, num, suffix: m[2] || '', fmt: m[1] }
    })
    .filter(Boolean)
  if (!targets.length) return null
  const ease = (t) => 1 - Math.pow(1 - t, 3)
  const render = (t, n) => {
    const v = Math.round(n * ease(t))
    return t.fmt.includes('.') ? v.toLocaleString('es-AR') : String(v)
  }
  const run = ({ el, num, suffix, fmt }) => {
    const t0 = performance.now()
    const dur = 900
    const tick = (now) => {
      const t = Math.min((now - t0) / dur, 1)
      el.textContent = render(t, num) + (t >= 1 ? suffix : '')
      if (t < 1) requestAnimationFrame(tick)
      else el.textContent = fmt + suffix
    }
    requestAnimationFrame(tick)
  }
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return
      const t = targets.find((x) => x.el === en.target)
      if (t) run(t)
      obs.unobserve(en.target)
    })
  }, { threshold: .6 })
  targets.forEach((t) => obs.observe(t.el))
  return () => obs.disconnect()
}

// ---- Pausa ambiental: misma mecánica que mercado — clases .rz-fx-off en
// bloques fuera de viewport y .rz-fx-paused en la página con pestaña oculta;
// el CSS las lee para congelar loops (aurora, sheen, conic, marquee…).
export function useRzFx(rootRef) {
  let obs = null
  let page = null
  let cleanups = []
  const onVis = () => page?.classList.toggle('rz-fx-paused', document.hidden)
  onMounted(() => {
    const rootEl = rootRef?.value
    page = rootEl?.closest?.('.store-page') || null
    if (!page) return
    page.classList.add('rz-fx')
    if (RICH_STYLES.has(styleOf(page))) page.classList.add('rz-fx-rich')
    if (reduceMotion) return
    document.addEventListener('visibilitychange', onVis)
    cleanups = [
      bindTilt(rootEl, page),
      bindParallax(page),
      bindCounters(rootEl),
    ].filter(Boolean)
    if ('IntersectionObserver' in window) {
      obs = new IntersectionObserver((entries) => {
        entries.forEach((en) => en.target.classList.toggle('rz-fx-off', !en.isIntersecting))
      }, { threshold: 0 })
      page.querySelectorAll('.rh-hero, .sp-ann, .rz-band, .sp-cta').forEach((el) => obs.observe(el))
    }
  })
  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVis)
    cleanups.forEach((fn) => fn())
    cleanups = []
    obs?.disconnect()
    page?.classList.remove('rz-fx', 'rz-fx-rich', 'rz-fx-paused')
  })
}
