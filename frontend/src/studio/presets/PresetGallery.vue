<script setup>
// Selector de estilos del Studio (nivel 1 de "Estilos"): grilla compacta de
// tiles (2 columnas) con una mini muestra de colores del set vigente. Al
// elegir un estilo se prueba en vivo (ensayo deshacible — nada se guarda
// hasta el Guardar de la barra). Las acciones de la prueba viven en una
// barra de una sola línea: Deshacer / Quedarla y, si el preset supera el
// plan, el atajo a Ver planes (el gate real corre en el backend al guardar).
import { computed, inject, onMounted } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { detectRubro, presetLock, PRESET_PICKER_IDS } from './catalog.js'
import { resolveStyleColors } from '../contract.js'
import { STORE_TEMPLATES } from '../../api/stores.api.js'
import { useStoreStore } from '../../stores/store.store.js'
import { useCatalogStore } from '../../stores/catalog.store.js'

const props = defineProps({
  benefits: { type: Object, default: () => {} },
  mode: { type: String, default: 'light' }
})

const api = inject('studioPresets')
const store = useStoreStore()
const catalog = useCatalogStore()

onMounted(() => {
  // Catálogo diferido (mismo criterio que LayoutEditor): solo alimenta la
  // detección de rubro para marcar los recomendados.
  setTimeout(() => { if (!catalog.products.length) catalog.loadAll() }, 600)
})

// ---------------------------------------------------------------------------
// Datos de la tienda (template guardado + rubro inferido)
// ---------------------------------------------------------------------------
const custom = computed(() => store.customization || {})
const shopName = computed(() => custom.value.display_name || store.store?.business_name || 'Tu tienda')
const rubro = computed(() => detectRubro({
  name: `${shopName.value} ${store.store?.business_name || ''}`,
  headline: `${custom.value.headline || ''} ${custom.value.description || ''}`,
  categories: [
    ...catalog.categories.map((c) => c.name || ''),
    ...catalog.products.map((p) => p.category_name || '')
  ]
}))
const recommended = computed(() => {
  if (!rubro.value) return new Set()
  return new Set(api.presets.filter((p) => p.rubros.includes(rubro.value)).map((p) => p.id))
})

// ---------------------------------------------------------------------------
// Tiles
// ---------------------------------------------------------------------------
const TIER_LABEL = { base: 'Básico', plus: 'Estándar', advanced: 'Premium' }
const lockOf = (p) => presetLock(p, props.benefits)
const tplLabel = (p) => STORE_TEMPLATES[p.template]?.label || p.template
// "En uso": la plantilla guardada coincide y no hay prueba en vivo.
const isCurrent = (p) => !api.tryingId.value && custom.value.template === p.template
const isTrying = (p) => api.tryingId.value === p.id

const pickerItems = computed(() => PRESET_PICKER_IDS
  .map((id) => api.presets.find((p) => p.id === id))
  .filter(Boolean))
const inUseId = computed(() => api.presets.find((p) => custom.value.template === p.template)?.id || '')
// Estilos en uso / en prueba que no están entre los 8: se agregan al final
// para que la grilla nunca deje sin tile al estilo vigente.
const extraItems = computed(() => {
  const picked = new Set(PRESET_PICKER_IDS)
  const ids = [...new Set([inUseId.value, api.tryingId.value].filter((id) => id && !picked.has(id)))]
  return ids.map((id) => api.presets.find((p) => p.id === id)).filter(Boolean)
})
const items = computed(() => [...pickerItems.value, ...extraItems.value])

// Mini muestra del set vigente: fondo, superficie, borde y color de fuente.
function chipsOf(p) {
  const sc = resolveStyleColors(p.theme, props.mode)
  return [sc.containers.bg, sc.containers.surface, sc.containers.border, sc.fonts.heading]
}
function stateOf(p) {
  if (isTrying(p)) return 'probando'
  if (isCurrent(p)) return 'en uso'
  if (lockOf(p)) return 'bloqueado'
  return ''
}
function ariaOf(p) {
  const state = stateOf(p)
  return `${p.name}${state ? `, ${state}` : ''}`
}
function titleOf(p) {
  return `${p.name} — ${tplLabel(p)} · ${TIER_LABEL[p.tier] || TIER_LABEL.base}`
    + (recommended.value.has(p.id) ? ' · tu rubro' : '')
    + (lockOf(p) ? ' · requiere plan superior' : '')
}

const trialPreset = computed(() => (api.tryingId.value ? api.presets.find((p) => p.id === api.tryingId.value) : null))
const onPick = (p) => api.tryIt(p)
const onRevert = () => api.revertTrial()
</script>

<template>
  <div class="psg">
    <div class="psg-grid" role="group" aria-label="Estilos prediseñados">
      <button
        v-for="p in items" :key="p.id" type="button"
        class="psg-tile" :class="{ 'is-current': isCurrent(p), 'is-trying': isTrying(p), 'is-locked': lockOf(p) }"
        :aria-pressed="isTrying(p) || isCurrent(p)" :aria-label="ariaOf(p)" :title="titleOf(p)"
        @click="onPick(p)"
      >
        <span class="psg-tile-head">
          <span class="psg-tile-name">{{ p.name }}</span>
          <span v-if="isTrying(p)" class="psg-tag">probando</span>
          <span v-else-if="isCurrent(p)" class="psg-tag">en uso</span>
          <AppIcon v-if="lockOf(p)" class="psg-tile-lock" name="lock" :size="11" aria-hidden="true" />
        </span>
        <span class="psg-chips" aria-hidden="true">
          <span v-for="(c, i) in chipsOf(p)" :key="i" class="psg-chip" :style="{ background: c }" />
        </span>
      </button>
    </div>

    <!-- ===== Probando: una sola línea de acciones ===== -->
    <div v-if="trialPreset" class="psg-bar" role="status">
      <span class="psg-bar-tx">Probando <b>{{ trialPreset.name }}</b></span>
      <span class="psg-bar-acts">
        <button v-if="lockOf(trialPreset)" type="button" class="psg-mini" @click="api.goPlans()"><AppIcon name="crown" :size="13" /> Ver planes</button>
        <button type="button" class="psg-mini" @click="onRevert"><AppIcon name="undo" :size="13" /> Deshacer</button>
        <button type="button" class="psg-mini is-keep" @click="api.keepTrial()"><AppIcon name="check" :size="13" /> Quedarla</button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.psg { display: flex; flex-direction: column; gap: 8px; }

/* ===== Grilla de tiles ===== */
.psg-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.psg-tile {
  display: flex; flex-direction: column; gap: 4px; min-height: 46px;
  padding: 6px 7px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface); color: var(--ink-2); font: inherit; text-align: left;
  cursor: pointer; transition: border-color .15s, background .15s;
}
.psg-tile:hover { border-color: var(--brand-500); }
.psg-tile:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.psg-tile.is-current { border-color: var(--brand-500); background: var(--brand-soft); }
.psg-tile.is-trying { border-color: var(--brand-500); border-width: 2px; padding: 6px 7px; }
.psg-tile.is-locked { opacity: .78; }
.psg-tile.is-locked:hover { opacity: 1; }
.psg-tile-head { display: flex; align-items: center; gap: 4px; min-width: 0; }
.psg-tile-name {
  flex: 1; min-width: 0; font-size: 12.5px; font-weight: 700; line-height: 1.15;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.psg-tile-lock { flex: none; color: var(--muted); }
.psg-tag {
  flex: none; font-size: 9px; font-weight: 800; text-transform: uppercase;
  letter-spacing: .02em; color: var(--brand-ink);
}
.psg-chips { display: flex; gap: 3px; }
.psg-chip {
  width: 15px; height: 9px; border-radius: 3px;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, .14);
}

/* ===== Probando: barra de una línea ===== */
.psg-bar {
  display: flex; align-items: center; gap: 5px; flex-wrap: nowrap;
  padding: 4px 7px; border: 1px solid var(--brand-500); border-radius: 8px;
  background: var(--brand-soft); color: var(--brand-ink); font-size: 12px;
}
.psg-bar-tx { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.psg-bar-acts { display: flex; gap: 4px; flex: none; margin-left: auto; flex-wrap: nowrap; }
.psg-mini {
  display: inline-flex; align-items: center; gap: 3px; min-height: 40px;
  padding: 2px 7px; border: 1px solid var(--line); border-radius: 7px;
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 11px; font-weight: 600;
  cursor: pointer; white-space: nowrap;
}
.psg-mini:hover { border-color: var(--brand-500); }
.psg-mini.is-keep { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.psg-mini:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
</style>
