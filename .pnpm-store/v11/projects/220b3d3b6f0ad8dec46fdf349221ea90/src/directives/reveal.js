// Directiva v-reveal de la web pública: pone la clase .sp-rv (estado oculto)
// y registra el elemento en un IntersectionObserver compartido. El observer
// se registra tras DOBLE requestAnimationFrame: sin ese frame intermedio
// algunos navegadores entregan la primera observación antes de pintar el
// estado oculto y la transición nunca corre (animación "fantasma").
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

let revealObserver = null
function getObserver() {
  if (!revealObserver) {
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-in')
        revealObserver.unobserve(entry.target)
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' })
  }
  return revealObserver
}

export const vReveal = {
  mounted(el, binding) {
    el.classList.add('sp-rv')
    if (binding.value) el.style.setProperty('--rv-d', `${binding.value}ms`)
    if (reduceMotion || !('IntersectionObserver' in window)) { el.classList.add('is-in'); return }
    requestAnimationFrame(() => {
      requestAnimationFrame(() => getObserver().observe(el))
    })
  },
  unmounted(el) { revealObserver?.unobserve(el) }
}
