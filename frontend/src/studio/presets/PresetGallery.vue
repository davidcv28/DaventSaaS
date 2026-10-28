<script setup>
// Selector de presets del Studio (nivel 1 del flujo guiado de "Estilos"):
// un select agrupado por nivel de plan. Al elegir un estilo se prueba en
// vivo en la vista previa (ensayo deshacible — nada se guarda hasta el
// Guardar de la barra). La cinta "Probando" ofrece Deshacer / Quedarla y,
// si el preset supera el plan, el atajo a Ver planes (el gate real corre
// en el backend al guardar).
import { ref, computed, inject, onMounted, watch } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { detectRubro, presetLock } from './catalog.js'
import { STORE_TEMPLATES } from '../../api/stores.api.js'
import { useStoreStore } from '../../stores/store.store.js'
import { useCatalogStore } from '../../stores/catalog.store.js'

const props = defineProps({
  benefits: { type: Object, default: () => {} }
})

const api = inject('studioPresets')
const store = useStoreStore()
const catalog = useCatalogStore()

onMounted(() => {
  // Catálogo diferido (mismo criterio que LayoutEditor): solo alimenta la
  // detección de rubro para marcar los recomendados en las opciones.
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
// Select agrupado por nivel de plan (Básico / Estándar / Premium)
// ---------------------------------------------------------------------------
const TIER_LABEL = { base: 'Básico', plus: 'Estándar', advanced: 'Premium' }
const TIER_ORDER = ['base', 'plus', 'advanced']
const lockOf = (p) => presetLock(p, props.benefits)
const tplLabel = (p) => STORE_TEMPLATES[p.template]?.label || p.template
// "En uso": la plantilla guardada coincide y no hay prueba en vivo.
const isCurrent = (p) => !api.tryingId.value && custom.value.template === p.template

const groups = computed(() => TIER_ORDER
  .map((t) => ({ id: t, label: TIER_LABEL[t], items: api.presets.filter((p) => p.tier === t) }))
  .filter((g) => g.items.length))
function optionLabel(p) {
  return `${p.name} — ${tplLabel(p)}`
    + (recommended.value.has(p.id) ? ' · tu rubro' : '')
    + (isCurrent(p) ? ' · en uso' : '')
    + (lockOf(p) ? ' · requiere plan superior' : '')
}

// Valor del select: el preset cuya plantilla coincide con la guardada; al
// probar otro sigue al ensayo. Tras Deshacer vuelve al "en uso".
const inUseId = computed(() => api.presets.find((p) => custom.value.template === p.template)?.id || '')
const sel = ref(inUseId.value)
watch(inUseId, (id) => { if (!api.tryingId.value) sel.value = id })
watch(() => api.tryingId.value, (id) => { if (id) sel.value = id })

function onPick() {
  const p = api.presets.find((x) => x.id === sel.value)
  if (p) api.tryIt(p)
}
function onRevert() {
  api.revertTrial()
  sel.value = inUseId.value
}

const trialPreset = computed(() => (api.tryingId.value ? api.presets.find((p) => p.id === api.tryingId.value) : null))
</script>

<template>
  <div class="psg">
    <div class="psg-pick">
      <label for="psg-style" class="psg-lbl">Estilo prediseñado</label>
      <select id="psg-style" v-model="sel" class="stp-select psg-select" @change="onPick">
        <option value="" disabled>Elegí un estilo…</option>
        <optgroup v-for="g in groups" :key="g.id" :label="g.label">
          <option v-for="p in g.items" :key="p.id" :value="p.id">{{ optionLabel(p) }}</option>
        </optgroup>
      </select>
      <p class="psg-hint">Se aplica en la vista previa al elegirlo. Nada se guarda hasta que guardás vos.</p>
    </div>

    <!-- ===== Probando ===== -->
    <div v-if="trialPreset" class="psg-trial" role="status">
      <AppIcon name="eye" :size="15" />
      <span class="psg-trial-tx">Probando <b>{{ trialPreset.name }}</b><template v-if="lockOf(trialPreset)"> — para guardarla completa hace falta {{ TIER_LABEL.advanced }}</template></span>
      <span class="psg-trial-acts">
        <button v-if="lockOf(trialPreset)" type="button" class="psg-mini" @click="api.goPlans()"><AppIcon name="crown" :size="13" /> Ver planes</button>
        <button type="button" class="psg-mini" @click="onRevert"><AppIcon name="undo" :size="13" /> Deshacer</button>
        <button type="button" class="psg-mini is-keep" @click="api.keepTrial()"><AppIcon name="check" :size="13" /> Quedarla</button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.psg { display: flex; flex-direction: column; gap: 12px; }

/* ===== Select ===== */
.psg-pick { display: flex; flex-direction: column; gap: 6px; }
.psg-lbl { font-size: 12px; font-weight: 700; color: var(--ink-2); }
.psg-select { width: 100%; min-height: 44px; font-size: 15px; }
.psg-hint { margin: 0; font-size: 11.5px; color: var(--muted); line-height: 1.45; }

/* ===== Probando ===== */
.psg-trial {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 10px 12px; border: 1px solid var(--brand-500); border-radius: 10px;
  background: var(--brand-soft); color: var(--brand-ink); font-size: 12.5px;
}
.psg-trial-tx { flex: 1 1 auto; min-width: 0; line-height: 1.4; }
.psg-trial-acts { display: flex; gap: 6px; flex: none; flex-wrap: wrap; }
.psg-mini {
  display: inline-flex; align-items: center; gap: 5px; min-height: 44px;
  padding: 4px 12px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
}
.psg-mini:hover { border-color: var(--brand-500); }
.psg-mini.is-keep { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.psg-mini:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
</style>
