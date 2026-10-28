<script setup>
// Editor interactivo de bloques (Diseño web → Bloques). El dueño activa,
// desactiva y reordena bloques del catálogo cerrado TEMPLATE_BLOCKS por
// superficie (Inicio / Catálogo / Servicios) — nunca HTML/CSS libre.
// El draft se serializa a `layout_config` y viaja por el PATCH normal de
// customization con debounce adaptativo; ante error el draft se conserva
// (nunca rollback destructivo) y el usuario puede reintentar. Los ids
// que la plantilla actual no soporta se preservan verbatim en el
// payload, así cambiar de plantilla no pierde la configuración de
// bloques equivalentes.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { useCatalogStore } from '../stores/catalog.store.js'
import { LAYOUT_SURFACES, SURFACE_LABELS, TEMPLATE_BLOCKS, blockSpec } from '../templates/blocks.js'
import { resolveLayout, defaultLayout } from '../templates/index.js'
import { env } from '../config/env.js'
import { tokenStorage } from '../api/http.js'
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
const previewState = ref('loading') // loading | ready | failed
let dirtyTick = 0
let lastSaveMs = 600
let saveTimer = null
let savedTimer = null
let previewTimer = null
let previewPushTimer = null
let lazyTimer = null
let saving = false
let resave = false
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
  undoStack.value = []
  redoStack.value = []
  saveState.value = 'idle'
}
buildDraft()

// Cambio de plantilla: primero se pide guardar lo pendiente (el PATCH
// sale con la config vieja, que conserva los ids que la plantilla nueva
// no soporta verbatim) y después se reconstruye el draft — los bloques
// equivalentes conservan su estado guardado y los no soportados quedan
// en la config para un eventual regreso (se avisa por toast).
watch(() => props.template, (tpl, prev) => {
  if (tpl === prev) return
  flushPending()
  const dropped = LAYOUT_SURFACES.reduce((n, s) =>
    n + (draft.value[s] || []).filter((b) => !defaultLayout(tpl, s).some((d) => d.id === b.id)).length, 0)
  buildDraft()
  previewKey.value++
  if (dropped) {
    emit('notify', dropped === 1
      ? 'Un bloque no forma parte de esta plantilla: su estado queda guardado por si volvés.'
      : `${dropped} bloques no forman parte de esta plantilla: su estado queda guardado por si volvés.`)
  }
})

const blocks = computed(() => draft.value[surface.value] || [])
const specOf = (b) => blockSpec(surface.value, b.id) || {}
const isLocked = (b) => Boolean(specOf(b).locked)
const isPremiumLocked = (b) => Boolean(specOf(b).premium && !props.premium)
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

// La lista se muestra en dos grupos — activos (ordenables por drag con
// el asa o Alt+flechas) y disponibles (apagados). El draft es una sola
// lista por superficie: los apagados conservan su posición relativa y
// al reactivarse van al final (igual que "agregar").
const activeItems = computed(() => blocks.value.filter((b) => b.enabled))
const availableItems = computed(() => blocks.value.filter((b) => !b.enabled))
const selectedId = ref('')
const announce = ref('')
function say(msg) { announce.value = msg }

// Historial por superficie y acotado: cada entrada clona solo la lista
// activa (los bloques son planos: {id, enabled, order, variant, title}),
// nunca el draft completo ni JSON.
const HISTORY_MAX = 40
const snapBlocks = (list) => list.map((b) => ({ ...b }))
const snapCurrent = () => ({ s: surface.value, blocks: snapBlocks(draft.value[surface.value]) })
function pushHistory() {
  undoStack.value.push(snapCurrent())
  if (undoStack.value.length > HISTORY_MAX) undoStack.value.shift()
  redoStack.value = []
}
function applySnapshot(snap) {
  draft.value[snap.s] = snapBlocks(snap.blocks)
  if (snap.s !== surface.value) surface.value = snap.s
  scheduleSave()
}
function undo() {
  if (!canUndo.value) return
  redoStack.value.push(snapCurrent())
  applySnapshot(undoStack.value.pop())
  say('Cambio deshecho.')
}
function redo() {
  if (!canRedo.value) return
  undoStack.value.push(snapCurrent())
  applySnapshot(redoStack.value.pop())
  say('Cambio rehecho.')
}

// Reordena solo dentro de los activos: los apagados conservan su
// posición relativa en el draft (el renderer público solo usa los
// habilitados, así que el orden visible es el que importa).
function reorderActive(from, to) {
  const list = draft.value[surface.value]
  const ids = list.filter((b) => b.enabled).map((b) => b.id)
  const [moved] = ids.splice(from, 1)
  ids.splice(to, 0, moved)
  pushHistory()
  const byId = new Map(list.map((b) => [b.id, b]))
  let k = 0
  draft.value[surface.value] = list.map((b) => (b.enabled ? byId.get(ids[k++]) : b))
  draft.value[surface.value].forEach((b, i) => { b.order = i })
  selectedId.value = moved
  say(`"${specOf({ id: moved }).label}" movido a la posición ${to + 1}.`)
  scheduleSave()
}
function moveActiveDelta(k, dir) {
  const to = k + dir
  if (to < 0 || to >= activeItems.value.length) return
  reorderActive(k, to)
}
function addBlock(b) {
  if (isLocked(b) || isPremiumLocked(b) || b.enabled) return
  pushHistory()
  const list = draft.value[surface.value]
  const i = list.indexOf(b)
  if (i !== -1) list.splice(i, 1)
  b.enabled = true
  list.push(b)
  list.forEach((x, idx) => { x.order = idx })
  selectedId.value = b.id
  say(`"${specOf(b).label}" agregado al final de la página.`)
  if (blockEmpty(b)) {
    emit('notify', `"${specOf(b).label}" se activó pero no tiene contenido: va a aparecer recién cuando cargues esos datos.`)
  }
  scheduleSave()
}
function removeBlock(b) {
  if (isLocked(b) || isPremiumLocked(b) || !b.enabled) return
  pushHistory()
  b.enabled = false
  say(`"${specOf(b).label}" pasó a disponibles.`)
  scheduleSave()
}
function toggleBlock(b) {
  if (b.enabled) removeBlock(b)
  else addBlock(b)
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
  say('Se restableció el orden de la plantilla.')
  scheduleSave()
}

// Drag & drop con Pointer Events desde el asa (.blk-grip): funciona con
// mouse y táctil (touch-action:none en el asa). Mientras dura el gesto
// la fila sigue al puntero y la fila de destino queda marcada; al soltar
// se hace un único commit (una entrada de historial + un guardado).
const rootEl = ref(null)
const listEl = ref(null)
const iframeEl = ref(null)
const drag = ref(null) // {id, from, over, startY, deltaY, up, down, mids}

function onGripDown(e, b, k) {
  if ((e.button !== 0 && e.pointerType === 'mouse') || activeItems.value.length < 2) return
  const rows = [...listEl.value.querySelectorAll(':scope > .blk-row')]
  const mine = e.currentTarget.closest('.blk-row').getBoundingClientRect()
  const rects = rows.map((r) => r.getBoundingClientRect())
  drag.value = {
    id: b.id,
    from: k,
    over: k,
    startY: e.clientY,
    deltaY: 0,
    up: (rects[0]?.top ?? mine.top) - mine.top,
    down: (rects[rects.length - 1]?.bottom ?? mine.bottom) - mine.bottom,
    mids: rects.map((r) => r.top + r.height / 2)
  }
  e.currentTarget.setPointerCapture(e.pointerId)
  selectedId.value = b.id
  // Sin preventDefault: el botón tiene que recibir el foco para que
  // Alt+flechas funcione tras el click; la selección de texto durante el
  // drag se evita con user-select:none en el asa.
}
function onGripMove(e) {
  const d = drag.value
  if (!d) return
  d.deltaY = Math.min(Math.max(e.clientY - d.startY, d.up), d.down)
  const over = d.mids.findIndex((m) => e.clientY < m)
  d.over = over === -1 ? d.mids.length - 1 : over
}
function onGripUp(e) {
  const d = drag.value
  if (!d) return
  try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* captura ya liberada */ }
  drag.value = null
  if (d.over !== d.from) reorderActive(d.from, d.over)
}
function onRowKey(e, b, k) {
  if (!e.altKey || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return
  e.preventDefault()
  moveActiveDelta(k, e.key === 'ArrowUp' ? -1 : 1)
}

// Click en una fila (fuera de controles): la selecciona y lleva la vista
// previa al bloque — y al revés: clic dentro del iframe selecciona la fila.
function onRowClick(e, b) {
  if (e.target.closest('button, input, select, label, a')) return
  selectBlock(b)
}
function selectBlock(b, scrollPreview = true) {
  selectedId.value = b.id
  if (!scrollPreview || !b.enabled) return
  const doc = iframeEl.value?.contentDocument
  const mark = doc?.querySelector(`[data-blk="${b.id}"]`)
  // Los marcadores del BlockRenderer son display:contents (sin caja):
  // scroll/resaltado van al primer elemento real del bloque.
  const el = mark?.firstElementChild || mark
  if (!el?.scrollIntoView) return
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' })
  if (!calm) {
    el.animate?.([
      { boxShadow: '0 0 0 4px rgba(99,91,255,.8)' },
      { boxShadow: '0 0 0 4px rgba(99,91,255,0)' }
    ], { duration: 1100 })
  }
}
function onPreviewClick(ev) {
  const hit = ev.target?.closest?.('[data-blk]')
  const id = hit?.getAttribute('data-blk')
  if (!id || !blocks.value.some((b) => b.id === id)) return
  selectedId.value = id
  document.querySelector(`.blk-row[data-bid="${id}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

// Ctrl+Z / Ctrl+Shift+Z (o Ctrl+Y) para deshacer/rehacer. Solo con la
// sección visible y sin estar escribiendo en un campo (el navegador
// deshace el texto del input en ese caso).
function onGlobalKey(e) {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return
  if (!rootEl.value || rootEl.value.offsetParent === null) return
  if (e.target?.closest?.('input, textarea, select, [contenteditable="true"]')) return
  const k = e.key.toLowerCase()
  if (k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo() }
  else if (k === 'y') { e.preventDefault(); redo() }
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

// Debounce adaptativo: 500ms base + la mitad de la latencia del PATCH
// anterior (tope 1.8s). En redes lentas agrupa más cambios por request
// en vez de encolar guardados en cadena.
function scheduleSave(delay) {
  if (saveState.value !== 'error') saveState.value = 'dirty'
  dirtyTick++
  clearTimeout(saveTimer)
  saveTimer = setTimeout(save, delay ?? Math.min(1800, 500 + lastSaveMs / 2))
  schedulePreviewPush()
}
// Cola de un solo guardado en vuelo: los cambios que llegan mientras un
// PATCH está en el aire quedan marcados (resave + dirtyTick) y se
// re-guardan al aterrizar — nunca se descartan. En error NO hay
// rollback destructivo: el draft local se conserva y el usuario puede
// corregir o reintentar.
async function save() {
  if (saving) { resave = true; return }
  saving = true
  saveState.value = 'saving'
  const tick = dirtyTick
  const t0 = performance.now()
  const ok = await store.saveCustomization({ layout_config: serialize() })
  lastSaveMs = performance.now() - t0
  saving = false
  if (ok) pushLayoutToPreview()
  if (resave || (ok && dirtyTick !== tick)) {
    resave = false
    saveState.value = 'dirty'
    scheduleSave(350)
  } else if (ok) {
    saveState.value = 'saved'
    clearTimeout(savedTimer)
    savedTimer = setTimeout(() => { if (saveState.value === 'saved') saveState.value = 'idle' }, 2600)
  } else {
    saveState.value = 'error'
    emit('notify', store.lastError || 'No se pudo guardar el orden de bloques. Tus cambios siguen acá: probá Reintentar.')
  }
}
// Descarga el debounce pendiente (cambio de plantilla/superficie,
// desmontaje): el PATCH sigue aunque el componente muera después.
function flushPending() {
  clearTimeout(saveTimer)
  saveTimer = null
  if (saveState.value === 'dirty' && !saving) void save()
}
// Cierre de pestaña/recarga: un PATCH con keepalive viaja aunque el tab
// muera; si ya había un save en vuelo manda el mismo payload (idempotente).
function onPageHide() {
  if (!['dirty', 'saving'].includes(saveState.value) && !resave) return
  const token = tokenStorage.getAccess()
  if (!token) return
  try {
    fetch(`${env.apiBaseUrl.replace(/\/$/, '')}/stores/customization/`, {
      method: 'PATCH',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ layout_config: serialize() })
    })
  } catch { /* el cierre no espera respuesta */ }
}
function onVisibility() {
  if (document.visibilityState === 'hidden') flushPending()
}
function retrySave() {
  resave = false
  saveState.value = 'dirty'
  save()
}
const saveLabel = computed(() => ({
  idle: 'Todo guardado', dirty: 'Cambios sin guardar…', saving: 'Guardando…',
  saved: 'Guardado ✓', error: 'Error al guardar'
}[saveState.value]))
const saveIcon = computed(() => ({
  idle: 'circle-check', dirty: 'clock', saving: 'loader',
  saved: 'circle-check', error: 'triangle-alert'
}[saveState.value]))

// Vista previa real: la página pública dentro de un iframe con ancho
// desktop/mobile. Usa el alias same-origin <origen>/<slug> (no el link
// canónico de subdominio): la CSP (frame-src/frame-ancestors 'self') lo
// autoriza siempre — en dev evita depender de que *.<dominio> resuelva —
// y permite al editor hablar con la página (scroll al bloque, clic de
// vuelta). "Abrir en otra pestaña" sigue usando el link canónico.
// previewState: loading -> ready; si el load no llega en ~12s (CSP, DNS,
// red) pasa a failed y se muestra el fallback con salida a pestaña nueva.
const PREVIEW_PATHS = { landing: '', catalog: '/catalogo', services: '/servicios' }
const storeSlug = computed(() => store.store?.slug || '')
const previewSrc = computed(() => (storeSlug.value ? `${env.appUrl}/${storeSlug.value}${PREVIEW_PATHS[surface.value]}` : ''))
const canonicalSrc = computed(() => (props.publicUrl ? props.publicUrl + PREVIEW_PATHS[surface.value] : ''))
const surfacePublished = computed(() => props.siteTemplates.includes(surface.value))
// En pantallas chicas la vista previa pasa a ser una hoja que se abre
// desde un botón flotante — la lista ocupa todo el ancho.
const previewOpen = ref(false)
const SURFACE_ICONS = { landing: 'store', catalog: 'layout-grid', services: 'wrench' }
function enabledCount(s) {
  return (draft.value[s] || []).filter((b) => b.enabled !== false).length
}
// En pantallas chicas el iframe no se monta hasta abrir la hoja: la
// página pública pesa y competiría con la lista por red y CPU.
const isNarrow = ref(false)
const previewVisible = computed(() => !isNarrow.value || previewOpen.value)
function onMedia(e) { isNarrow.value = e.matches }
let mql = null

// La vista previa se actualiza por postMessage (el StorePublicLayout
// aplica el layout_config del draft reactivo): cero recargas del iframe,
// sin parpadeo ni requests abortados en cada guardado.
function pushLayoutToPreview() {
  iframeEl.value?.contentWindow?.postMessage(
    { type: 'davent:layout', layout: serialize() },
    window.location.origin
  )
}
function schedulePreviewPush() {
  clearTimeout(previewPushTimer)
  previewPushTimer = setTimeout(pushLayoutToPreview, 500)
}

function armPreviewTimeout() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    if (previewState.value === 'loading') previewState.value = 'failed'
  }, 12000)
}
function onPreviewLoad(e) {
  clearTimeout(previewTimer)
  previewState.value = 'ready'
  // Clic dentro de la vista previa → selecciona la fila del editor (el
  // clic sigue su curso: la preview sigue siendo navegable).
  e.target.contentDocument?.addEventListener('click', onPreviewClick, true)
  // Un remount (reintento, cambio de superficie/plantilla) arranca con el
  // layout guardado: se le empuja el draft vigente apenas carga.
  pushLayoutToPreview()
}
watch(previewSrc, () => {
  previewState.value = previewSrc.value ? 'loading' : 'failed'
  armPreviewTimeout()
})
watch(previewKey, () => {
  previewState.value = 'loading'
  armPreviewTimeout()
})
watch(previewVisible, (v) => {
  if (!v) return
  previewState.value = 'loading'
  armPreviewTimeout()
})

onMounted(() => {
  // Catálogo diferido: alimenta los avisos "sin contenido" pero no
  // compite con el primer paint del editor.
  lazyTimer = setTimeout(() => { if (!catalog.products.length) catalog.loadAll() }, 800)
  previewState.value = previewSrc.value ? 'loading' : 'failed'
  armPreviewTimeout()
  mql = window.matchMedia('(max-width: 1100px)')
  isNarrow.value = mql.matches
  mql.addEventListener('change', onMedia)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('keydown', onGlobalKey)
  document.addEventListener('visibilitychange', onVisibility)
})
onUnmounted(() => {
  flushPending()
  clearTimeout(saveTimer)
  clearTimeout(savedTimer)
  clearTimeout(previewTimer)
  clearTimeout(previewPushTimer)
  clearTimeout(lazyTimer)
  mql?.removeEventListener('change', onMedia)
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('keydown', onGlobalKey)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <div ref="rootEl" class="blk-layout" :class="{ 'pv-open': previewOpen }">
    <p class="sr-only" role="status" aria-live="polite">{{ announce }}</p>
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
          <AppIcon :name="SURFACE_ICONS[s]" :size="15" />
          {{ SURFACE_LABELS[s] }}
          <span class="blk-tab-count" :title="`${enabledCount(s)} bloques activos`">{{ enabledCount(s) }}</span>
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
        <p class="blk-hint">Cada tarjeta es una sección de la página, en el mismo orden en que aparece en tu web. Arrastrá del asa para reordenar (con el foco en el asa, Alt+↑↓ también mueve). Lo que apagás pasa a «Disponibles» sin borrar nada; lo marcado «Sin contenido» aparece recién cuando cargás esos datos.</p>

        <div class="blk-group-head">
          <h4>Bloques activos <span class="blk-count">{{ activeItems.length }}</span></h4>
          <small>En el orden en que salen en tu web</small>
        </div>
        <p v-if="!activeItems.length" class="blk-empty">Sin bloques activos: agregalos desde «Disponibles».</p>
        <ul v-else ref="listEl" class="blk-list" aria-label="Bloques activos, en orden de la página">
          <li
            v-for="(b, k) in activeItems"
            :key="b.id"
            :data-bid="b.id"
            class="blk-row"
            :class="{ sel: selectedId === b.id, locked: isLocked(b) || isPremiumLocked(b), dragging: drag?.id === b.id, 'drop-to': drag && drag.id !== b.id && drag.over === k }"
            :style="drag?.id === b.id ? { transform: `translateY(${drag.deltaY}px)` } : null"
            @click="onRowClick($event, b)"
          >
            <div class="blk-row-top">
              <button
                type="button"
                class="blk-grip"
                :aria-label="`Reordenar ${specOf(b).label}: arrastrá o usá Alt+flecha arriba/abajo`"
                title="Arrastrá para reordenar (Alt+↑↓ con el foco acá)"
                @pointerdown="onGripDown($event, b, k)"
                @pointermove="onGripMove"
                @pointerup="onGripUp"
                @pointercancel="onGripUp"
                @keydown="onRowKey($event, b, k)"
              ><AppIcon name="grip-vertical" :size="15" /></button>
              <span class="blk-ico" aria-hidden="true"><AppIcon :name="specOf(b).icon || 'layout-grid'" :size="16" /></span>
              <span class="blk-name">
                <strong>{{ specOf(b).label || b.id }}</strong>
                <span v-if="isLocked(b)" class="blk-tag"><AppIcon name="lock" :size="10" /> Fijo</span>
                <span v-else-if="isPremiumLocked(b)" class="blk-tag premium"><AppIcon name="crown" :size="10" /> Premium</span>
                <span v-else-if="blockEmpty(b)" class="blk-tag empty" title="No tiene contenido cargado: en tu web no se muestra hasta que lo completes"><AppIcon name="info" :size="10" /> Sin contenido</span>
                <small v-if="specOf(b).desc || (specOf(b).edit && blockEmpty(b))" class="blk-desc">
                  {{ specOf(b).desc }}
                  <button v-if="specOf(b).edit && !blockEmpty(b)" type="button" class="blk-link" @click="$emit('navigate', specOf(b).edit)">Lo cargás en {{ srcLabel(b) }}</button>
                  <button v-if="specOf(b).edit && blockEmpty(b)" type="button" class="blk-cta" @click.stop="$emit('navigate', specOf(b).edit)"><AppIcon name="arrow-right" :size="11" /> Cargar contenido</button>
                </small>
              </span>
              <button v-if="!isLocked(b) && !isPremiumLocked(b)" type="button" class="blk-quit" :aria-label="`Quitar ${specOf(b).label}`" title="Quitar de la página" @click="removeBlock(b)"><AppIcon name="minus" :size="14" /></button>
              <label class="blk-toggle" :class="{ disabled: isLocked(b) || isPremiumLocked(b) }" :title="isLocked(b) ? 'Este bloque es parte de la página y no se puede apagar' : isPremiumLocked(b) ? 'Disponible con diseño avanzado (plan Premium)' : ''">
                <input type="checkbox" :checked="b.enabled" :disabled="isLocked(b) || isPremiumLocked(b)" @change="toggleBlock(b)" />
                <span class="blk-track" aria-hidden="true"></span>
              </label>
            </div>
            <div v-if="specOf(b).variants || specOf(b).props" class="blk-row-sub">
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

        <div class="blk-group-head">
          <h4>Bloques disponibles <span class="blk-count">{{ availableItems.length }}</span></h4>
          <small>Apagados: no salen en tu web hasta que los agregues</small>
        </div>
        <p v-if="!availableItems.length" class="blk-empty">Ya está todo en la página.</p>
        <ul v-else class="blk-list avail">
          <li
            v-for="b in availableItems"
            :key="b.id"
            :data-bid="b.id"
            class="blk-row avail"
            :class="{ sel: selectedId === b.id, locked: isPremiumLocked(b) }"
            @click="onRowClick($event, b)"
          >
            <div class="blk-row-top">
              <span class="blk-ico dim" aria-hidden="true"><AppIcon :name="specOf(b).icon || 'layout-grid'" :size="16" /></span>
              <span class="blk-name">
                <strong>{{ specOf(b).label || b.id }}</strong>
                <span v-if="isPremiumLocked(b)" class="blk-tag premium"><AppIcon name="crown" :size="10" /> Premium</span>
                <span v-else-if="blockEmpty(b)" class="blk-tag empty" title="No tiene contenido cargado: en tu web no se muestra hasta que lo completes"><AppIcon name="info" :size="10" /> Sin contenido</span>
                <small v-if="specOf(b).desc || (specOf(b).edit && blockEmpty(b))" class="blk-desc">
                  {{ specOf(b).desc }}
                  <button v-if="specOf(b).edit && blockEmpty(b) && !isPremiumLocked(b)" type="button" class="blk-cta" @click.stop="$emit('navigate', specOf(b).edit)"><AppIcon name="arrow-right" :size="11" /> Cargar contenido</button>
                </small>
              </span>
              <button v-if="!isPremiumLocked(b)" type="button" class="btn ghost btn-auto btn-sm blk-add" @click="addBlock(b)"><AppIcon name="plus" :size="12" /> Agregar</button>
              <label class="blk-toggle" :class="{ disabled: isPremiumLocked(b) }" :title="isPremiumLocked(b) ? 'Disponible con diseño avanzado (plan Premium)' : ''">
                <input type="checkbox" :checked="b.enabled" :disabled="isPremiumLocked(b)" @change="addBlock(b)" />
                <span class="blk-track" aria-hidden="true"></span>
              </label>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <aside class="card blk-preview" :class="{ open: previewOpen }">
      <div class="blk-card-head">
        <h3><AppIcon name="eye" :size="17" /> Vista previa</h3>
        <div class="blk-actions">
          <button type="button" class="blk-dev" :class="{ active: device === 'desktop' }" title="Escritorio" :aria-pressed="device === 'desktop'" aria-label="Vista escritorio" @click="device = 'desktop'"><AppIcon name="monitor" :size="15" /></button>
          <button type="button" class="blk-dev" :class="{ active: device === 'tablet' }" title="Tablet" :aria-pressed="device === 'tablet'" aria-label="Vista tablet" @click="device = 'tablet'"><AppIcon name="tablet" :size="15" /></button>
          <button type="button" class="blk-dev" :class="{ active: device === 'mobile' }" title="Celular" :aria-pressed="device === 'mobile'" aria-label="Vista celular" @click="device = 'mobile'"><AppIcon name="smartphone" :size="15" /></button>
          <button type="button" class="blk-dev blk-sheet-close" aria-label="Cerrar vista previa" @click="previewOpen = false"><AppIcon name="x" :size="15" /></button>
        </div>
      </div>
      <p class="blk-save" :data-state="saveState"><AppIcon :name="saveIcon" :size="14" class="blk-save-icon" :class="{ spin: saveState === 'saving' }" aria-hidden="true" />{{ saveLabel }}
        <button v-if="saveState === 'error'" type="button" class="blk-link" @click="retrySave">Reintentar</button>
      </p>
      <div class="blk-frame" :data-device="device" :data-state="previewState">
        <template v-if="previewSrc && surfacePublished">
          <div v-show="previewState === 'loading'" class="blk-frame-skel" aria-hidden="true">
            <span class="blk-skel-bar"></span><span class="blk-skel-bar mid"></span><span class="blk-skel-bar short"></span>
          </div>
          <iframe v-if="previewVisible" ref="iframeEl" :key="previewKey" :src="previewSrc" title="Vista previa de tu web" loading="lazy" @load="onPreviewLoad"></iframe>
          <div v-if="previewState === 'failed'" class="blk-frame-fail" role="status">
            <AppIcon name="triangle-alert" :size="18" />
            <p>La vista previa no respondió. Podés abrirla en otra pestaña o recargarla.</p>
            <button type="button" class="blk-link" @click="previewKey++">Recargar vista previa</button>
          </div>
        </template>
        <div v-else class="blk-frame-empty">
          <AppIcon :name="surfacePublished ? 'lock' : 'eye-off'" :size="24" />
          <p>{{ surfacePublished ? 'Vista previa no disponible.' : 'Esta página no está publicada en tu web todavía.' }}</p>
          <a v-if="canonicalSrc" class="blk-link" :href="canonicalSrc" target="_blank" rel="noopener">Abrir en otra pestaña</a>
        </div>
      </div>
      <a v-if="publicUrl && surfacePublished" class="btn ghost btn-auto blk-open" :href="canonicalSrc" target="_blank" rel="noopener"><AppIcon name="external-link" :size="14" /> Abrir en otra pestaña</a>
    </aside>

    <button type="button" class="blk-fab" @click="previewOpen = true"><AppIcon name="eye" :size="16" /> Vista previa</button>
    <div v-if="previewOpen" class="blk-scrim" aria-hidden="true" @click="previewOpen = false"></div>
  </div>
</template>
