// Historial del Studio: snapshots JSON del draft (theme/layout/template),
// tope 60 pasos y coalescing por "qué cambió" — tipear en un color o
// arrastrar un slider agrupa en un solo paso tras 500ms sin cambios.
import { ref, computed } from 'vue'
import { clone } from './studioModel.js'

export function useStudioHistory({ max = 60, coalesceMs = 500 } = {}) {
  const past = ref([])
  const future = ref([])
  let current = null
  let timer = null
  let applying = false

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  // Clave de coalescing: qué campos cambiaron entre snapshots (misma
  // combinación dentro de la ventana = mismo paso de historial).
  function diffKeys(a, b) {
    const keys = []
    for (const group of new Set([...Object.keys(a || {}), ...Object.keys(b || {})])) {
      if (JSON.stringify(a?.[group]) !== JSON.stringify(b?.[group])) keys.push(group)
    }
    return keys.join()
  }

  function reset(snap) {
    past.value = []
    future.value = []
    current = clone(snap)
    clearTimeout(timer)
    timer = null
  }

  // Llamar en cada mutación del draft (el watcher del shell la dispara).
  // Coalescing por VENTANA: mientras el timer siga armado todo se mergea
  // en el paso vigente — necesario porque un solo gesto puede producir
  // writes encadenados en flushes distintos (p.ej. un control escribe
  // form + theme y el watcher form→theme del shell reinyecta el resto
  // del tema un flush después; con clave por campos eso partía el paso
  // en dos y el undo restauraba el estado ya cambiado).
  function observe(snap) {
    const s = clone(snap)
    if (applying) { applying = false; current = s; return }
    if (!current) { current = s; return }
    if (!diffKeys(current, s)) return
    if (!timer) {
      past.value = [...past.value, current].slice(-max)
      future.value = []
    }
    clearTimeout(timer)
    timer = setTimeout(() => { timer = null }, coalesceMs)
    current = s
  }

  function apply(snap) {
    applying = true
    clearTimeout(timer)
    timer = null
    current = clone(snap)
    return clone(snap)
  }

  function undo() {
    if (!canUndo.value) return null
    const prev = past.value[past.value.length - 1]
    past.value = past.value.slice(0, -1)
    future.value = [...future.value, current]
    return apply(prev)
  }

  function redo() {
    if (!canRedo.value) return null
    const next = future.value[future.value.length - 1]
    future.value = future.value.slice(0, -1)
    past.value = [...past.value, current].slice(-max)
    return apply(next)
  }

  // Si el punto de guardado se movió (markSaved tras PATCH) el historial
  // sigue: solo cambia el baseline de "dirty" (lo maneja el shell).
  function dispose() { clearTimeout(timer) }

  return { canUndo, canRedo, observe, undo, redo, reset, dispose }
}
