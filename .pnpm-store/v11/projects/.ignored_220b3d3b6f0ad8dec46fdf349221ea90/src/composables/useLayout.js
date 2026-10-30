// useLayout(surface): layout efectivo de una superficie pública.
// Resuelve la Template Definition de la plantilla activa contra
// customization.layout_config (fallback: layout por defecto — una config
// ausente/corrupta jamás rompe la web). Devuelve:
//   blocks : [{id, enabled, order, variant?, props?}] ya ordenados
//   on(id) : el bloque está habilitado (el editor lo apagó -> false)
//   pos(id): posición CSS `order` dentro del contenedor flex de la página
//   st(id) : el estado completo del bloque (para variant/props)
// Las vistas declaran sus secciones con v-if="on('x')" y :style="{
// order: pos('x') }" — los bloques apagados no se montan y el orden del
// usuario manda; los bloques sin datos siguen auto-ocultándose solos
// (la vista conserva su propio v-if de contenido).
import { computed, inject } from 'vue'
import { resolveLayout } from '../templates/index.js'

export function useLayout(surface) {
  const ctx = inject('storePage')
  const layout = computed(() => resolveLayout(
    ctx.pageTemplate.value,
    surface,
    ctx.custom.value?.layout_config
  ))
  const byId = computed(() => new Map(layout.value.map((b) => [b.id, b])))
  return {
    blocks: layout,
    on: (id) => byId.value.get(id)?.enabled !== false,
    pos: (id) => byId.value.get(id)?.order ?? 999,
    st: (id) => byId.value.get(id) || { id, enabled: true }
  }
}
