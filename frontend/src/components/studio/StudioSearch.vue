<script setup>
// Búsqueda de ajustes (Ctrl+K): paleta de comandos que salta a la
// herramienta y enfoca el control. `entries` la arma el shell con el índice
// de campos + las herramientas del riel.
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  entries: { type: Array, default: () => [] } // [{id,label,hint,icon,tool,focus,kw}]
})
const emit = defineEmits(['select', 'close'])

const q = ref('')
const active = ref(0)
const inputEl = ref(null)
const listEl = ref(null)

const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
const results = computed(() => {
  const needle = norm(q.value).trim()
  if (!needle) return props.entries
  const terms = needle.split(/\s+/)
  return props.entries.filter((e) => {
    const hay = norm(`${e.label} ${e.hint || ''} ${e.kw || ''}`)
    return terms.every((t) => hay.includes(t))
  })
})
watch(results, () => { active.value = 0 })

function pick(entry) {
  if (!entry) return
  emit('select', entry)
  emit('close')
}
function onKey(e) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    const n = results.value.length
    if (!n) return
    active.value = (active.value + (e.key === 'ArrowDown' ? 1 : -1) + n) % n
    nextTick(() => listEl.value?.querySelector(`[data-idx="${active.value}"]`)?.scrollIntoView({ block: 'nearest' }))
  } else if (e.key === 'Enter') {
    e.preventDefault()
    pick(results.value[active.value])
  }
}
onMounted(() => inputEl.value?.focus())
</script>

<template>
  <div class="stx-overlay stx-top" role="presentation" @click.self="emit('close')">
    <div class="stx-card stx-search" role="dialog" aria-modal="true" aria-label="Buscar ajustes del Studio">
      <div class="stx-search-box">
        <AppIcon name="search" :size="16" />
        <input
          ref="inputEl" v-model="q" type="text" role="combobox" aria-expanded="true"
          aria-controls="stx-results" :aria-activedescendant="results[active] ? `stx-r-${results[active].id}` : null"
          placeholder="Buscar ajuste: color, fuente, botones, publicar…" @keydown="onKey"
        />
        <kbd class="stx-esc">Esc</kbd>
      </div>
      <ul ref="listEl" id="stx-results" class="stx-results" role="listbox">
        <li
          v-for="(e, i) in results" :key="e.id" :id="`stx-r-${e.id}`" :data-idx="i" role="option"
          :aria-selected="i === active" class="stx-r" :class="{ active: i === active }"
          @mousemove="active = i" @click="pick(e)"
        >
          <span class="stx-r-ico"><AppIcon :name="e.icon" :size="15" /></span>
          <span class="stx-r-t">
            <strong>{{ e.label }}</strong>
            <small v-if="e.hint">{{ e.hint }}</small>
          </span>
          <AppIcon name="arrow-right" :size="13" class="stx-r-go" />
        </li>
        <li v-if="!results.length" class="stx-empty">Sin resultados para “{{ q }}”. Probá con “color”, “fuente”, “publicar”…</li>
      </ul>
    </div>
  </div>
</template>
