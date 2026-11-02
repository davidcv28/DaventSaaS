// Capa premium MERCADO (JS): spotlight de puntero en tarjetas (v-spot, solo
// desktop con puntero fino) y pausa de loops — con la pestaña oculta o con
// el bloque fuera del viewport. Sin libs: listeners pasivos + observers.
import { onBeforeUnmount, onMounted } from 'vue'

const reduceMotion = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
const finePointer = typeof window !== 'undefined'
  && window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches

export const vSpot = {
  mounted(el) {
    if (reduceMotion || !finePointer) return
    el.classList.add('mc-spot')
    const move = (e) => {
      const r = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${e.clientX - r.left}px`)
      el.style.setProperty('--my', `${e.clientY - r.top}px`)
    }
    const enter = () => el.classList.add('is-spot')
    const leave = () => el.classList.remove('is-spot')
    el.addEventListener('pointermove', move, { passive: true })
    el.addEventListener('pointerenter', enter, { passive: true })
    el.addEventListener('pointerleave', leave, { passive: true })
    el._mcSpot = { move, enter, leave }
  },
  unmounted(el) {
    const fx = el._mcSpot
    if (!fx) return
    el.removeEventListener('pointermove', fx.move)
    el.removeEventListener('pointerenter', fx.enter)
    el.removeEventListener('pointerleave', fx.leave)
    el._mcSpot = null
  }
}

// rootRef = ref al root de la vista (.sp-page-root): la pausa viaja como
// clases en .store-page (.mc-fx-paused / .mc-fx-off, ver store-mercado.css).
export function useMcFx(rootRef) {
  let obs = null
  let root = null
  const onVis = () => root?.classList.toggle('mc-fx-paused', document.hidden)
  onMounted(() => {
    root = rootRef?.value?.closest?.('.store-page') || null
    if (!root || reduceMotion) return
    document.addEventListener('visibilitychange', onVis)
    if ('IntersectionObserver' in window) {
      obs = new IntersectionObserver((entries) => {
        entries.forEach((en) => en.target.classList.toggle('mc-fx-off', !en.isIntersecting))
      }, { threshold: 0 })
      root.querySelectorAll('.sp-ann').forEach((el) => obs.observe(el))
    }
  })
  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVis)
    obs?.disconnect()
    root?.classList.remove('mc-fx-paused')
  })
}
