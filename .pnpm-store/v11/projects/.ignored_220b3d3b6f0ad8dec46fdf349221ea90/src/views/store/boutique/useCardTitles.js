// Tooltip de las tarjetas de producto del diseño BOUTIQUE.
// TplProductCard (componente compartido) recorta el nombre a 2 líneas por
// contrato de geometría pero no expone el nombre completo. Para no tocar el
// componente compartido, la vista observa su propio subárbol y copia el texto
// del nombre a `title`: el navegador muestra el nombre completo al pasar el
// puntero y el recorte sigue siendo visual (el texto del DOM queda intacto
// para lectores de pantalla).
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
    // El contenido llega async (catálogo público): se observa el subárbol en
    // vez de asumir que las tarjetas ya existen al montar.
    if (typeof MutationObserver !== 'undefined' && rootRef.value) {
      observer = new MutationObserver(stamp)
      observer.observe(rootRef.value, { childList: true, subtree: true, characterData: true })
    }
  })
  onBeforeUnmount(() => observer?.disconnect())
}
