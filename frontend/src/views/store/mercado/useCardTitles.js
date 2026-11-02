// Tooltip de las tarjetas de producto del diseño MERCADO.
// TplProductCard recorta el nombre a 2 líneas por contrato de geometría pero
// no expone el nombre completo. La vista observa su subárbol y copia el texto
// a `title`: el recorte sigue siendo visual y el texto del DOM queda intacto.
import { onBeforeUnmount, onMounted } from 'vue'

export function useCardTitles(rootRef) {
  let observer = null

  function stamp() {
    const root = rootRef.value
    if (!root) return
    root.querySelectorAll('.tpc-name').forEach((el) => {
      const text = (el.textContent || '').trim()
      if (text && el.getAttribute('title') !== text) el.setAttribute('title', text)
    })
  }

  onMounted(() => {
    stamp()
    if (typeof MutationObserver !== 'undefined' && rootRef.value) {
      observer = new MutationObserver(stamp)
      observer.observe(rootRef.value, { childList: true, subtree: true, characterData: true })
    }
  })
  onBeforeUnmount(() => observer?.disconnect())
}
