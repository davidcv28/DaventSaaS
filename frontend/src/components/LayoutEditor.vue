<script setup>
// Editor interactivo de bloques (Diseño web → Bloques). El dueño activa,
// desactiva y reordena bloques del catálogo cerrado TEMPLATE_BLOCKS por
// superficie (Inicio / Catálogo / Servicios) — nunca HTML/CSS libre.
// El draft se serializa a `layout_config` y viaja por el PATCH normal de
// customization con debounce; ante error se restaura el último guardado
// (rollback optimista). Los ids que la plantilla actual no soporta se
// preservan verbatim en el payload, así cambiar de plantilla no pierde
// la configuración de bloques equivalentes.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { useCatalogStore } from '../stores/catalog.store.js'
import { LAYOUT_SURFACES, SURFACE_LABELS, TEMPLATE_BLOCKS, blockSpec } from '../templates/blocks.js'
import { resolveLayout, defaultLayout } from '../templates/index.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  template: { type: String, default: 'classic' },
  premium: { type: Boolean, default: false },
  publicUrl: { type: String, default: '' },
  siteTemplates: { type: Array, default: () => ['landing', 'catalog'] }
})
const emit = defineEmits(['notify', 'navigate'])

const store = useStoreStore()
const catalog = useCatalogStore()

// Sección del panel donde vive el contenido de un bloque (spec.edit).
const SRC_LABELS = {
  company: 'Mi empresa',
  catalogs: 'Mis catálogos',
  services: 'Mis servicios',
  design: 'Diseño'
}
const srcLabel = (b) => SRC_LABELS[specOf(b).edit] || ''

const surface = ref('landing')
const draft = ref({ landing: [], catalog: [], services: [] })
const undoStack = ref([])
const redoStack = ref([])
const saveState = ref('idle') // idle | dirty | saving | saved | error
const device = ref('desktop')
const previewKey = ref(0)
let savedSnap = ''
let saveTimer = null
let savedTimer = null
let titleSnapDone = false

// Bloques que dependen de contenido del negocio: el aviso "sin contenido"
// anticipa que el bloque se oculta solo en la web hasta cargar esos datos.
const hasProducts = computed(() => catalog.products.length > 0)
const hasOffers = computed(() => catalog.discounts.length > 0)
const hasBrands = computed(() => catalog.brands.length > 0 || catalog.products.some((p) => p.brand))
const DATA_CHECKS = {
  landing: {
    announcements: (c) => Boolean(c.announcements?.length),
    highlights: (c) => Boolean(c.whatsapp || (c.show_hours && c.hours?.length)),
    categories: () => hasProducts.value,
    featured: () => hasProducts.value,
    about: (c) => Boolean(c.about_title || c.about_text || c.about_years || c.about_mission || c.about_specialties),
    services: (c) => Boolean(c.services?.length),
    stats: (c) => Boolean(c.stats?.length),
    benefits: (c) => Boolean(c.benefits?.length),
    offers: () => hasOffers.value,
    brands: () => hasBrands.value,
    countdown: () => hasOffers.value,
    timeline: (c) => Boolean(c.timeline?.length),
    team: (c) => Boolean(c.team?.length),
    gallery: (c) => Boolean(c.gallery?.length),
    testimonials: (c) => Boolean(c.testimonials?.length),
    faq: (c) => Boolean(c.faqs?.length),
    video: (c) => Boolean(c.video_url),
    steps: () => true,
    compare: () => true,
    cta: (c) => Boolean(c.cta_title || c.cta_text),
    contact: () => true,
    hero: () => true
  },
  catalog: {
    note: (c) => Boolean((c.catalog_note || '').trim()),
    banner: (c) => Boolean(c.carousel?.length),
    promo: () => hasOffers.value,
    filters: () => true,
    sort: () => true,
    grid: () => true
  },
  services: {
    hero: () => true,
    band: (c) => Boolean(c.services?.length),
    picker: () => true,
    steps: (c) => Boolean(c.service_steps?.length),
    form: (c) => Boolean(c.service_days?.length && c.service_slots?.length),
    faq: (c) => Boolean(c.faqs?.length)
  }
}
function blockEmpty(b) {
  const check = DATA_CHECKS[surface.value]?.[b.id]
  return check ? !check(store.customization || {}) : false
}

function buildDraft() {
  const cfg = store.customization?.layout_config
  const next = {}
  for (const s of LAYOUT_SURFACES) {
    next[s] = resolveLayout(props.template, s, cfg).map((b, i) => ({
      id: b.id,
      enabled: b.enabled !== false,
      order: i,
      variant: b.variant || '',
      title: b.props?.title || ''
    }))
  }
  draft.value = next
  savedSnap = JSON.stringify(next)
  undoStack.value = []
  redoStack.value = []
  saveState.value = 'idle'
}
buildDraft()

// Cambio de plantilla: se reconstruye el draft con los bloques que la
// nueva plantilla soporta (los equivalentes conservan su estado guardado);
// el draft anterior queda en el historial por si fue un error.
watch(() => props.template, () => { buildDraft() })

const blocks = computed(() => draft.value[surface.value] || [])
const specOf = (b) => blockSpec(surface.value, b.id) || {}
const isLocked = (b) => Boolean(specOf(b).locked)
const isPremiumLocked = (b) => Boolean(specOf(b).premium && !props.premium)
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

function pushHistory() {
  undoStack.value.push(JSON.stringify(draft.value))
  if (undoStack.value.length > 60) undoStack.value.shift()
  redoStack.value = []
}
function applySnapshot(snap) {
  draft.value = JSON.parse(snap)
  scheduleSave()
}
function undo() {
  if (!canUndo.value) return
  redoStack.value.push(JSON.stringify(draft.value))
  applySnapshot(undoStack.value.pop())
}
function redo() {
  if (!canRedo.value) return
  undoStack.value.push(JSON.stringify(draft.value))
  applySnapshot(redoStack.value.pop())
}

function moveBlock(i, dir) {
  const j = i + dir
  const list = draft.value[surface.value]
  if (j < 0 || j >= list.length) return
  pushHistory()
  ;[list[i], list[j]] = [list[j], list[i]]
  list.forEach((b, idx) => { b.order = idx })
  scheduleSave()
}
function toggleBlock(b) {
  if (isLocked(b) || isPremiumLocked(b)) return
  pushHistory()
  b.enabled = !b.enabled
  if (b.enabled && blockEmpty(b)) {
    emit('notify', `"${specOf(b).label}" se activó pero no tiene contenido: va a aparecer recién cuando cargues esos datos.`)
  }
  scheduleSave()
}
function setVariant(b, v) {
  const variants = specOf(b).variants || {}
  if (!variants[v]) return
  pushHistory()
  b.variant = v === Object.keys(variants)[0] ? '' : v
  scheduleSave()
}
function onTitleFocus() {
  if (titleSnapDone) return
  titleSnapDone = true
  pushHistory()
}
function onTitleBlur() {
  titleSnapDone = false
  scheduleSave()
}
function resetSurface() {
  pushHistory()
  draft.value[surface.value] = defaultLayout(props.template, surface.value).map((b, i) => ({
    id: b.id, enabled: true, order: i, variant: '', title: ''
  }))
  emit('notify', `"${SURFACE_LABELS[surface.value]}" volvió al orden original de la plantilla.`)
  scheduleSave()
}

// Serializa el draft a layout_config. Los bloques guardados que la
// plantilla actual no soporta se conservan al final, verbatim: así el
// estado sobrevive a un ida y vuelta de plantilla.
function serialize() {
  const saved = store.customization?.layout_config || {}
  const out = {}
  for (const s of LAYOUT_SURFACES) {
    const items = []
    const seen = new Set()
    ;(draft.value[s] || []).forEach((b, i) => {
      const spec = TEMPLATE_BLOCKS[s]?.[b.id]
      if (!spec || seen.has(b.id)) return
      seen.add(b.id)
      const item = { id: b.id, enabled: Boolean(b.enabled) || Boolean(spec.locked), order: i }
      const variants = Object.keys(spec.variants || {})
      if (b.variant && variants.includes(b.variant)) item.variant = b.variant
      const title = (b.title || '').trim()
      if (spec.props && title) item.props = { title: title.slice(0, spec.props.title || 80) }
      items.push(item)
    })
    for (const raw of saved?.[s]?.blocks || []) {
      if (raw?.id && !seen.has(raw.id)) { items.push(raw); seen.add(raw.id) }
    }
    out[s] = { blocks: items }
  }
  return out
}

function scheduleSave() {
  saveState.value = 'dirty'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(save, 900)
}
async function save() {
  if (saveState.value === 'saving') return
  saveState.value = 'saving'
  const snap = JSON.stringify(draft.value)
  const ok = await store.saveCustomization({ layout_config: serialize() })
  if (ok) {
    savedSnap = snap
    saveState.value = 'saved'
    previewKey.value++
    clearTimeout(savedTimer)
    savedTimer = setTimeout(() => { if (saveState.value === 'saved') saveState.value = 'idle' }, 2600)
  } else {
    // Rollback: el último estado válido vuelve al draft.
    draft.value = JSON.parse(savedSnap)
    saveState.value = 'error'
    emit('notify', store.lastError || 'No se pudo guardar el orden de bloques. Se restauró lo último guardado.')
  }
}
const saveLabel = computed(() => ({
  idle: 'Todo guardado', dirty: 'Cambios sin guardar…', saving: 'Guardando…',
  saved: 'Guardado ✓', error: 'Error al guardar'
}[saveState.value]))

// Vista previa real: la URL pública de cada superficie en un iframe con
// ancho desktop/mobile. Se recarga (previewKey) tras cada guardado. La CSP
// del SPA autoriza el iframe same-site (frame-src/frame-ancestors con apex
// + *.<dominio>) — un host ajeno seguiría bloqueado por frame-ancestors.
const PREVIEW_PATHS = { landing: '', catalog: '/catalogo', services: '/servicios' }
const previewSrc = computed(() => (props.publicUrl ? props.publicUrl + PREVIEW_PATHS[surface.value] : ''))
const surfacePublished = computed(() => props.siteTemplates.includes(surface.value))

onMounted(() => {
  // Para los avisos "sin contenido" de bloques ligados al catálogo.
  if (!catalog.products.length) catalog.loadAll()
})
onUnmounted(() => { clearTimeout(saveTimer); clearTimeout(savedTimer) })
</script>

<template>
  <div class="blk-layout">
    <div class="blk-main">
      <nav class="dsg-tabs" role="tablist" aria-label="Superficie a editar">
        <button
          v-for="s in LAYOUT_SURFACES"
          :key="s"
          type="button"
          role="tab"
          class="dsg-tab"
          :class="{ active: surface === s }"
          :aria-selected="surface === s"
          @click="surface = s"
        >
          <AppIcon :name="{ landing: 'store', catalog: 'layout-grid', services: 'wrench' }[s]" :size="15" />
          {{ SURFACE_LABELS[s] }}
          <small v-if="!siteTemplates.includes(s)" class="blk-off-tag">sin publicar</small>
        </button>
      </nav>

      <p v-if="!surfacePublished" class="blk-note">
        <AppIcon name="info" :size="14" />
        La página {{ SURFACE_LABELS[surface] }} no está publicada en tu web (se activa en
        <button type="button" class="blk-link" @click="$emit('navigate', 'pages')">Plantillas</button>).
        Podés preparar su orden igual.
      </p>

      <div class="card blk-card">
        <div class="blk-card-head">
          <h3><AppIcon name="sliders" :size="17" /> Bloques de {{ SURFACE_LABELS[surface] }}</h3>
          <div class="blk-actions">
            <button type="button" class="btn ghost btn-auto btn-sm" :disabled="!canUndo" title="Deshacer" aria-label="Deshacer" @click="undo"><AppIcon name="undo" :size="14" /></button>
            <button type="button" class="btn ghost btn-auto btn-sm" :disabled="!canRedo" title="Rehacer" aria-label="Rehacer" @click="redo"><AppIcon name="redo" :size="14" /></button>
            <button type="button" class="btn ghost btn-auto btn-sm" @click="resetSurface"><AppIcon name="refresh" :size="14" /> Restablecer</button>
          </div>
        </div>
        <p class="blk-hint">Cada fila es una sección de la página, en el mismo orden en que aparece en tu web. Lo que apagás se oculta sin borrar nada; lo marcado «Sin contenido» aparece recién cuando cargás esos datos.</p>

        <ul class="blk-list">
          <li
            v-for="(b, i) in blocks"
            :key="b.id"
            class="blk-row"
            :class="{ off: !b.enabled, locked: isLocked(b) || isPremiumLocked(b) }"
          >
            <div class="blk-row-top">
              <span class="blk-move" aria-hidden="false">
                <button type="button" class="blk-mv" :disabled="i === 0" :aria-label="`Subir ${specOf(b).label}`" @click="moveBlock(i, -1)"><AppIcon name="chevron-up" :size="13" /></button>
                <button type="button" class="blk-mv" :disabled="i === blocks.length - 1" :aria-label="`Bajar ${specOf(b).label}`" @click="moveBlock(i, 1)"><AppIcon name="chevron-down" :size="13" /></button>
              </span>
              <span class="blk-name">
                <strong>{{ specOf(b).label || b.id }}</strong>
                <span v-if="isLocked(b)" class="blk-tag"><AppIcon name="lock" :size="10" /> Fijo</span>
                <span v-else-if="isPremiumLocked(b)" class="blk-tag premium"><AppIcon name="crown" :size="10" /> Premium</span>
                <span v-else-if="blockEmpty(b)" class="blk-tag empty" title="No tiene contenido cargado: en tu web no se muestra hasta que lo completes">Sin contenido</span>
                <small v-if="specOf(b).desc" class="blk-desc">
                  {{ specOf(b).desc }}
                  <button v-if="specOf(b).edit" type="button" class="blk-link" @click="$emit('navigate', specOf(b).edit)">Lo cargás en {{ srcLabel(b) }}</button>
                </small>
              </span>
              <label class="blk-toggle" :class="{ disabled: isLocked(b) || isPremiumLocked(b) }" :title="isLocked(b) ? 'Este bloque es parte de la página y no se puede apagar' : isPremiumLocked(b) ? 'Disponible con diseño avanzado (plan Premium)' : ''">
                <input type="checkbox" :checked="b.enabled" :disabled="isLocked(b) || isPremiumLocked(b)" @change="toggleBlock(b)" />
                <span class="blk-track" aria-hidden="true"></span>
              </label>
            </div>
            <div v-if="b.enabled && (specOf(b).variants || specOf(b).props)" class="blk-row-sub">
              <label v-if="specOf(b).variants" class="blk-sub">
                <span>Vista</span>
                <select class="blk-select" :value="b.variant || Object.keys(specOf(b).variants)[0]" @change="setVariant(b, $event.target.value)">
                  <option v-for="(label, key) in specOf(b).variants" :key="key" :value="key">{{ label }}</option>
                </select>
              </label>
              <label v-if="specOf(b).props?.title" class="blk-sub grow">
                <span>Título de la sección</span>
                <input
                  class="blk-input"
                  type="text"
                  :value="b.title"
                  :maxlength="specOf(b).props.title"
                  placeholder="Título por defecto"
                  @input="b.title = $event.target.value; scheduleSave()"
                  @focus="onTitleFocus"
                  @blur="onTitleBlur"
                />
              </label>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <aside class="card blk-preview">
      <div class="blk-card-head">
        <h3><AppIcon name="eye" :size="17" /> Vista previa</h3>
        <div class="blk-actions">
          <button type="button" class="blk-dev" :class="{ active: device === 'desktop' }" title="Escritorio" aria-label="Vista escritorio" @click="device = 'desktop'"><AppIcon name="monitor" :size="15" /></button>
          <button type="button" class="blk-dev" :class="{ active: device === 'mobile' }" title="Celular" aria-label="Vista celular" @click="device = 'mobile'"><AppIcon name="smartphone" :size="15" /></button>
        </div>
      </div>
      <p class="blk-save" :data-state="saveState"><span class="blk-dot" aria-hidden="true"></span>{{ saveLabel }}</p>
      <div class="blk-frame" :data-device="device">
        <iframe v-if="previewSrc && surfacePublished" :key="previewKey" :src="previewSrc" title="Vista previa de tu web" loading="lazy"></iframe>
        <div v-else class="blk-frame-empty">
          <AppIcon :name="surfacePublished ? 'lock' : 'eye-off'" :size="24" />
          <p>{{ surfacePublished ? 'Vista previa no disponible.' : 'Esta página no está publicada en tu web todavía.' }}</p>
        </div>
      </div>
      <a v-if="publicUrl && surfacePublished" class="btn ghost btn-auto blk-open" :href="previewSrc" target="_blank" rel="noopener"><AppIcon name="external-link" :size="14" /> Abrir en otra pestaña</a>
    </aside>
  </div>
</template>
