<script setup>
// Galería de presets del Studio (panel "Estilos"): tarjetas con la
// miniatura web real del look (PresetThumb), buscador, filtros por
// rubro/estilo/tier, favoritos y las tres acciones del contrato de fase:
//   Probar  -> aplica el preset al borrador + preview en vivo, deshacible;
//   Aplicar -> persiste por el flujo de guardado existente (emit('save')
//              del shell — el backend gatea site_theme/template por plan);
//   Combinar-> trae solo la paleta, solo la tipografía o solo la
//              distribución del preset sin tocar el resto.
// Los presets bloqueados se ven y se prueban igual; "Aplicar" se cambia
// por "Ver planes" (el guardado sería parcial por el gate del backend).
import { ref, computed, inject, onMounted, onBeforeUnmount, watch } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import PresetThumb from './PresetThumb.vue'
import {
  RUBRO_LABELS, detectRubro, ensurePresetFonts, filterPresets, presetLock
} from './catalog.js'
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
  ensurePresetFonts()
  // Catálogo diferido (mismo criterio que LayoutEditor): alimenta las
  // miniaturas y la detección de rubro sin competir con el primer paint.
  setTimeout(() => { if (!catalog.products.length) catalog.loadAll() }, 600)
})

// ---------------------------------------------------------------------------
// Datos de la tienda para las miniaturas reales
// ---------------------------------------------------------------------------
const custom = computed(() => store.customization || {})
const shopName = computed(() => custom.value.display_name || store.store?.business_name || 'Tu tienda')
const items = computed(() => catalog.products.slice(0, 3))

// ---------------------------------------------------------------------------
// Rubro recomendado (inferido del negocio + categorías del catálogo)
// ---------------------------------------------------------------------------
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
// Favoritos (localStorage: sobrevive sesiones; por usuario del navegador)
// ---------------------------------------------------------------------------
const FAV_KEY = 'davent:preset-favs:v1'
const favs = ref(new Set(loadFavs()))
function loadFavs() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY) || '[]') } catch { return [] }
}
function toggleFav(p) {
  const next = new Set(favs.value)
  next.has(p.id) ? next.delete(p.id) : next.add(p.id)
  favs.value = next
  try { localStorage.setItem(FAV_KEY, JSON.stringify([...next])) } catch { /* storage lleno/bloqueado */ }
}

// ---------------------------------------------------------------------------
// Filtros
// ---------------------------------------------------------------------------
const q = ref('')
const fRubro = ref('')
const fStyle = ref('')
const fTier = ref('')
const fFav = ref(false)
const fUsable = ref(false)
const styleOptions = computed(() => [...new Set(api.presets.map((p) => p.style))])
const rubroOptions = computed(() => {
  const used = new Set(api.presets.flatMap((p) => p.rubros))
  return Object.keys(RUBRO_LABELS).filter((k) => used.has(k))
})
const shown = computed(() => {
  const list = filterPresets(api.presets, {
    q: q.value, rubro: fRubro.value, style: fStyle.value, tier: fTier.value,
    favs: fFav.value ? favs.value : null, usable: fUsable.value, benefits: props.benefits
  })
  // Los recomendados para el rubro van primero (orden estable dentro).
  return [...list].sort((a, b) => (recommended.value.has(b.id) ? 1 : 0) - (recommended.value.has(a.id) ? 1 : 0))
})

// ---------------------------------------------------------------------------
// Acciones y estado por tarjeta
// ---------------------------------------------------------------------------
const TIER_LABEL = { base: 'Básico', plus: 'Estándar', advanced: 'Premium' }
const lockOf = (p) => presetLock(p, props.benefits)
const combineOpen = ref(null)
// Cierre del menú Combinar por click fuera o Escape (no hay directiva
// outside en el proyecto: listeners de document solo mientras está abierto).
let offDoc = null
function onDocDown(e) { if (!e.target.closest?.('.psg-comb-wrap')) combineOpen.value = null }
function onDocKey(e) { if (e.key === 'Escape') combineOpen.value = null }
watch(combineOpen, (open) => {
  offDoc?.(); offDoc = null
  if (open) {
    document.addEventListener('pointerdown', onDocDown)
    document.addEventListener('keydown', onDocKey)
    offDoc = () => {
      document.removeEventListener('pointerdown', onDocDown)
      document.removeEventListener('keydown', onDocKey)
    }
  }
})
onBeforeUnmount(() => offDoc?.())
function combine(p, part) {
  combineOpen.value = null
  api.apply(p, part)
}
const tplLabel = (p) => STORE_TEMPLATES[p.template]?.label || p.template
const trialPreset = computed(() => (api.tryingId.value ? api.presets.find((p) => p.id === api.tryingId.value) : null))
</script>

<template>
  <div class="psg">
    <header class="psg-head">
      <h3>Estilos prediseñados</h3>
      <p class="stp-hint">Un look completo en un click: colores, fuente, diseño y bloques. <b>Probar</b> lo ves en vivo y se puede deshacer; nada se guarda hasta que guardás vos.</p>
    </header>

    <!-- ===== Probando ===== -->
    <div v-if="trialPreset" class="psg-trial" role="status">
      <AppIcon name="eye" :size="15" />
      <span class="psg-trial-tx">Probando <b>{{ trialPreset.name }}</b><template v-if="lockOf(trialPreset)"> — para guardarla completa hace falta {{ TIER_LABEL.advanced }}</template></span>
      <span class="psg-trial-acts">
        <button type="button" class="psg-mini" @click="api.revertTrial()"><AppIcon name="undo" :size="13" /> Deshacer</button>
        <button type="button" class="psg-mini is-keep" @click="api.keepTrial()"><AppIcon name="check" :size="13" /> Quedarla</button>
      </span>
    </div>

    <!-- ===== Buscador + filtros ===== -->
    <div class="psg-search">
      <AppIcon name="search" :size="15" />
      <input v-model="q" type="search" placeholder="Buscar estilo…" aria-label="Buscar preset por nombre, estilo o rubro" />
    </div>
    <div class="psg-filters">
      <select v-model="fRubro" class="stp-select" aria-label="Filtrar por rubro">
        <option value="">Todos los rubros</option>
        <option v-if="rubro" :value="rubro">Recomendados ({{ RUBRO_LABELS[rubro] }})</option>
        <option v-for="r in rubroOptions" :key="r" :value="r">{{ RUBRO_LABELS[r] }}</option>
      </select>
      <select v-model="fStyle" class="stp-select" aria-label="Filtrar por estilo">
        <option value="">Todos los estilos</option>
        <option v-for="s in styleOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="fTier" class="stp-select" aria-label="Filtrar por nivel de plan">
        <option value="">Todos los niveles</option>
        <option value="base">Básico</option>
        <option value="plus">Estándar</option>
        <option value="advanced">Premium</option>
      </select>
      <div class="psg-toggles">
        <button type="button" class="stp-opt" :class="{ active: fUsable }" :aria-pressed="fUsable" @click="fUsable = !fUsable">
          <AppIcon name="check" :size="14" /> En mi plan
        </button>
        <button type="button" class="stp-opt" :class="{ active: fFav }" :aria-pressed="fFav" @click="fFav = !fFav">
          <AppIcon name="heart" :size="14" /> Favoritos
        </button>
      </div>
    </div>

    <!-- ===== Tarjetas ===== -->
    <div class="psg-grid" role="list">
      <article
        v-for="p in shown" :key="p.id" class="psg-card" role="listitem"
        :class="{ 'is-trying': api.tryingId.value === p.id, 'is-locked': lockOf(p) }"
      >
        <PresetThumb
          :preset="p" :name="shopName" :headline="custom.headline || ''"
          :logo="custom.logo || ''" :cover="custom.cover || ''" :products="items"
        />
        <div class="psg-card-head">
          <h4>{{ p.name }}</h4>
          <button
            type="button" class="psg-fav" :class="{ on: favs.has(p.id) }" :aria-pressed="favs.has(p.id)"
            :aria-label="favs.has(p.id) ? `Quitar ${p.name} de favoritos` : `Marcar ${p.name} como favorito`"
            @click="toggleFav(p)"
          ><AppIcon name="heart" :size="15" /></button>
        </div>
        <p class="psg-desc">{{ p.desc }}</p>
        <div class="psg-badges">
          <span class="psg-chip">{{ TIER_LABEL[p.tier] }}</span>
          <span class="psg-chip is-tpl">{{ tplLabel(p) }}</span>
          <span v-if="recommended.has(p.id)" class="psg-chip is-reco"><AppIcon name="sparkles" :size="11" /> Tu rubro</span>
          <span v-if="lockOf(p)" class="psg-chip is-lock"><AppIcon name="lock" :size="11" /> {{ lockOf(p) === 'plan' ? `Plan ${TIER_LABEL.advanced}` : 'Tema Premium' }}</span>
        </div>
        <div class="psg-acts">
          <button type="button" class="psg-btn is-try" @click="api.tryIt(p)">
            <AppIcon name="eye" :size="14" /> Probar
          </button>
          <button v-if="!lockOf(p)" type="button" class="psg-btn is-apply" @click="api.applyAndSave(p)">
            <AppIcon name="check" :size="14" /> Aplicar
          </button>
          <button v-else type="button" class="psg-btn is-plans" @click="api.goPlans()">
            <AppIcon name="crown" :size="14" /> Ver planes
          </button>
          <div class="psg-comb-wrap">
            <button
              type="button" class="psg-btn is-comb" :aria-expanded="combineOpen === p.id"
              :aria-label="`Combinar ${p.name}`" @click="combineOpen = combineOpen === p.id ? null : p.id"
            ><AppIcon name="sliders" :size="14" /></button>
            <div v-if="combineOpen === p.id" class="psg-comb" role="menu">
              <button type="button" role="menuitem" @click="combine(p, 'palette')"><AppIcon name="palette" :size="13" /> Solo la paleta</button>
              <button type="button" role="menuitem" @click="combine(p, 'typography')"><AppIcon name="type" :size="13" /> Solo la tipografía</button>
              <button type="button" role="menuitem" @click="combine(p, 'layout')"><AppIcon name="list-ordered" :size="13" /> Solo la distribución</button>
            </div>
          </div>
        </div>
      </article>
    </div>
    <p v-if="!shown.length" class="stp-hint psg-empty">No hay estilos con esos filtros. Probá otra búsqueda o limpiá los filtros.</p>
  </div>
</template>

<style scoped>
.psg { display: flex; flex-direction: column; gap: 12px; }
.psg-head h3 { margin: 0 0 4px; font-size: 14px; font-weight: 700; color: var(--ink); }
.psg-head .stp-hint b { color: var(--ink-2); }

/* ===== Probando ===== */
.psg-trial {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 10px 12px; border: 1px solid var(--brand-500); border-radius: 10px;
  background: var(--brand-soft); color: var(--brand-ink); font-size: 12.5px;
}
.psg-trial-tx { flex: 1 1 auto; min-width: 0; line-height: 1.4; }
.psg-trial-acts { display: flex; gap: 6px; flex: none; }
.psg-mini {
  display: inline-flex; align-items: center; gap: 5px; min-height: 32px;
  padding: 4px 10px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
}
.psg-mini:hover { border-color: var(--brand-500); }
.psg-mini.is-keep { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.psg-mini:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }

/* ===== Buscador + filtros ===== */
.psg-search {
  display: flex; align-items: center; gap: 8px;
  padding: 0 12px; min-height: 44px;
  border: 1px solid var(--line); border-radius: 9px; background: var(--surface);
  color: var(--muted);
}
.psg-search input { flex: 1; min-width: 0; height: 42px; border: 0; background: none; font: inherit; font-size: 16px; color: var(--ink); }
.psg-search input:focus { outline: none; }
.psg-search:focus-within { border-color: var(--brand-500); box-shadow: var(--ring); }
.psg-filters { display: flex; flex-direction: column; gap: 8px; }
.psg-filters .stp-select { height: 44px; }
.psg-toggles { display: flex; gap: 6px; }
.psg-toggles .stp-opt { min-height: 44px; flex: 1; justify-content: center; }

/* ===== Tarjetas ===== */
.psg-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; }
.psg-card {
  display: flex; flex-direction: column; gap: 8px; min-width: 0;
  padding: 10px; border: 1px solid var(--line); border-radius: 12px; background: var(--card);
  transition: border-color .15s, box-shadow .15s;
}
.psg-card.is-trying { border-color: var(--brand-500); box-shadow: var(--ring); }
.psg-card.is-locked .psth { opacity: .92; }
.psg-card-head { display: flex; align-items: center; gap: 8px; }
.psg-card-head h4 { margin: 0; flex: 1; min-width: 0; font-size: 13.5px; font-weight: 700; color: var(--ink); }
.psg-fav {
  display: grid; place-items: center; width: 36px; height: 36px; flex: none;
  border: 1px solid var(--line); border-radius: 8px; background: var(--surface);
  color: var(--muted); cursor: pointer; transition: color .12s, border-color .12s;
}
.psg-fav:hover { color: #e11d48; border-color: #e11d48; }
.psg-fav.on { color: #e11d48; border-color: #e11d48; }
.psg-fav.on :deep(svg) { fill: currentColor; }
.psg-fav:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.psg-desc { margin: 0; font-size: 12px; color: var(--muted); line-height: 1.4; }
.psg-badges { display: flex; flex-wrap: wrap; gap: 5px; }
.psg-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; border-radius: 99px; font-size: 10.5px; font-weight: 700;
  background: var(--surface); border: 1px solid var(--line); color: var(--ink-2);
}
.psg-chip.is-tpl { color: var(--muted); font-weight: 600; }
.psg-chip.is-reco { background: var(--brand-soft); border-color: transparent; color: var(--brand-ink); }
.psg-chip.is-lock { background: rgba(217, 119, 6, .1); border-color: rgba(217, 119, 6, .35); color: #b45309; }
.psg-acts { display: flex; gap: 6px; align-items: center; }
.psg-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  min-height: 44px; padding: 8px 12px; border-radius: 9px;
  font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer;
  border: 1px solid var(--line); background: var(--surface); color: var(--ink-2);
  transition: border-color .12s, background .12s, color .12s;
}
.psg-btn:hover { border-color: var(--brand-500); color: var(--ink); }
.psg-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.psg-btn.is-try { flex: 1 1 auto; }
.psg-btn.is-apply { flex: 1 1 auto; background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.psg-btn.is-apply:hover { background: var(--brand-600, var(--brand-500)); color: #fff; }
.psg-btn.is-plans { flex: 1 1 auto; background: rgba(217, 119, 6, .12); border-color: rgba(217, 119, 6, .4); color: #b45309; }
.psg-btn.is-plans:hover { color: #92400e; }
.psg-btn.is-comb { flex: none; width: 44px; padding: 0; }
.psg-comb-wrap { position: relative; flex: none; }
.psg-comb {
  position: absolute; right: 0; bottom: calc(100% + 6px); z-index: 20;
  display: flex; flex-direction: column; min-width: 180px; padding: 4px;
  border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); box-shadow: 0 8px 24px rgba(15, 23, 42, .14);
}
.psg-comb button {
  display: flex; align-items: center; gap: 8px; min-height: 40px; padding: 8px 10px;
  border: 0; border-radius: 7px; background: none; font: inherit; font-size: 12.5px;
  color: var(--ink-2); cursor: pointer; text-align: left;
}
.psg-comb button:hover { background: var(--brand-soft); color: var(--brand-ink); }
.psg-comb button:focus-visible { outline: 2px solid var(--brand-500); }
.psg-empty { padding: 8px 2px; }
</style>
