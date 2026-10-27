<script setup>
// Búsqueda global del panel (⌘K / Ctrl+K o "/"): secciones y acciones
// frecuentes con sinónimos de lenguaje cotidiano. Sin dependencias.
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  commands: { type: Array, default: () => [] }
})
const open = defineModel('open', { type: Boolean, default: false })

const query = ref('')
const selIdx = ref(0)
const inputEl = ref(null)
const listEl = ref(null)

const norm = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')

const results = computed(() => {
  const q = norm(query.value).trim()
  const list = props.commands.map((c) => {
    if (!q) return { c, score: 1 }
    const label = norm(c.label)
    const kw = norm(c.kw)
    const hint = norm(c.hint)
    let score = 0
    if (label === q) score = 4
    else if (label.startsWith(q)) score = 3
    else if (label.includes(q)) score = 2
    else if (kw.includes(q)) score = 1.5
    else if (hint.includes(q)) score = 0.5
    return { c, score }
  })
  return list.filter((r) => r.score > 0).sort((a, b) => b.score - a.score).map((r) => r.c)
})

const grouped = computed(() => {
  const groups = []
  let cur = null
  for (const c of results.value) {
    if (!cur || cur.name !== c.group) { cur = { name: c.group, items: [] }; groups.push(cur) }
    cur.items.push(c)
  }
  return groups
})

const flat = computed(() => grouped.value.flatMap((g) => g.items))
const sel = computed(() => flat.value[selIdx.value] || null)

function pick(c) {
  if (!c) return
  open.value = false
  c.run?.()
}
function onInputKey(e) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    const n = flat.value.length
    if (!n) return
    selIdx.value = (selIdx.value + (e.key === 'ArrowDown' ? 1 : -1) + n) % n
    nextTick(() => listEl.value?.querySelector('.sel')?.scrollIntoView({ block: 'nearest' }))
  } else if (e.key === 'Enter') {
    e.preventDefault()
    pick(sel.value)
  } else if (e.key === 'Escape') {
    open.value = false
  }
}
function onGlobalKey(e) {
  const tag = document.activeElement?.tagName
  const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || document.activeElement?.isContentEditable
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value = !open.value
  } else if (!typing && !open.value && e.key === '/') {
    e.preventDefault()
    open.value = true
  } else if (e.key === 'Escape' && open.value) {
    open.value = false
  }
}

watch(open, async (v) => {
  if (v) {
    query.value = ''
    selIdx.value = 0
    await nextTick()
    inputEl.value?.focus()
  }
})
watch(query, () => { selIdx.value = 0 })

onMounted(() => window.addEventListener('keydown', onGlobalKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="gs">
      <div v-if="open" class="gs-overlay" @click.self="open = false">
        <div class="gs-modal" role="dialog" aria-modal="true" aria-label="Buscar en el panel">
          <div class="gs-input">
            <AppIcon name="search" :size="17" />
            <input
              ref="inputEl"
              v-model="query"
              type="text"
              placeholder="¿Qué querés hacer? Escribí “logo”, “factura”, “QR”…"
              role="combobox"
              aria-expanded="true"
              aria-controls="gs-list"
              aria-label="Buscar secciones y acciones"
              @keydown="onInputKey"
            />
            <kbd class="kbd" aria-hidden="true">Esc</kbd>
          </div>
          <div id="gs-list" ref="listEl" class="gs-list" role="listbox" aria-label="Resultados">
            <template v-for="g in grouped" :key="g.name">
              <p class="gs-group">{{ g.name }}</p>
              <button
                v-for="c in g.items"
                :key="c.id"
                type="button"
                role="option"
                :aria-selected="sel === c"
                :class="{ sel: sel === c, locked: c.locked }"
                @click="pick(c)"
                @mousemove="selIdx = flat.indexOf(c)"
              >
                <AppIcon :name="c.icon" :size="17" class="gs-icon" />
                <span class="gs-t"><strong>{{ c.label }}</strong><small v-if="c.hint">{{ c.hint }}</small></span>
                <AppIcon v-if="c.locked" name="lock" :size="13" class="gs-lock" />
                <kbd v-else-if="sel === c" class="kbd" aria-hidden="true">↵</kbd>
              </button>
            </template>
            <p v-if="!flat.length" class="gs-empty">No encontré nada con “{{ query }}”. Probá con otra palabra — “factura”, “logo”, “visita”…</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
