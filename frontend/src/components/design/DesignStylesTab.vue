<script setup>
// Sub-sección "Diseño": dos columnas — a la izquierda el selector de Diseño
// (patrón) y el de Estilo (tema del diseño), debajo las plantillas de la
// web; a la derecha la vista previa en vivo con Guardar/Ver web.
// TODOS los diseños quedan habilitados para el usuario (sin recorte por
// plan): es el diseño elegido el que bloquea las plantillas que no cubre.
// Colores y fuentes sueltos son SOLO del Studio: acá no hay control de
// paleta ni tipografía, y las imágenes viven en la pestaña Fotos.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import { designApi } from '../../api/design.api.js'
import { ensureStoreFont, STORE_TEMPLATE_RETIRED_MAP } from '../../api/stores.api.js'
import { resolveSiteTheme } from '../../studio/contract.js'
import { normalizeLayoutConfig, templateBlocks, templateOf } from '../../templates/index.js'
import { LAYOUT_SURFACES, SURFACE_LABELS, blockSpec } from '../../templates/blocks.js'
import DesignLivePreview from './DesignLivePreview.vue'
import DesignSelect from './DesignSelect.vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  canStudio: { type: Boolean, default: false },
  siteTemplates: { type: Array, default: () => [] },
  // Opciones de páginas para el modal "Qué mostrar": las arma el padre
  // ({key,label,desc,on,lock,disabled,busy}) y el toggle viaja por evento.
  pageOptions: { type: Array, default: () => [] },
  // Estado del panel de vista previa: lo controla el padre para que la
  // savebar sticky también pueda abrirlo en mobile.
  previewOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'ring', 'open-studio', 'update:previewOpen', 'toggle-page'])

const { patterns, styles, status, load } = useDesignCatalog()
// Cada elección de diseño/estilo recarga la vista previa (el iframe hace un
// refresh real, no solo postMessage): contador que DesignLivePreview mira.
const previewReload = ref(0)
// Revalidar contra la base al entrar: los diseños/estilos nuevos se ven sin
// recargar la página.
onMounted(() => load(true))

// "Patrones de diseño" se alimenta directo del modelo DesignPattern
// (/api/design/patterns/), no del catálogo resumido: así aparece todo lo
// cargado en la base, incluidos los patrones importados con html/css/js.
const modelPatterns = ref([])
onMounted(() => {
  designApi.listPatterns()
    .then((list) => { modelPatterns.value = list })
    .catch(() => { modelPatterns.value = [] })
})

// Catálogo completo, sin filtros de plan ni de páginas: todas las opciones
// se habilitan siempre.
const patternOptions = computed(() => (
  (modelPatterns.value.length ? modelPatterns.value : patterns.value)
    .filter((p) => p.is_active !== false)
))
// Cada diseño trae sus propios estilos (DesignStyle.pattern): con un diseño
// elegido solo se listan los suyos (los sin vínculo siguen disponibles).
const styleOptions = computed(() => styles.value.filter((s) => (
  s.is_active !== false
  && (!currentPattern.value || !s.pattern || s.pattern === currentPattern.value)
)))

// La tienda puede tener guardado un diseño retirado (todavía no remapeado
// por el backend): el select y la vista previa trabajan siempre con el id
// nuevo al que apunta STORE_TEMPLATE_RETIRED_MAP.
const normTemplate = (t) => STORE_TEMPLATE_RETIRED_MAP[t] || t

const patternLayout = (p) => normalizeLayoutConfig(p.layout)
const sameJson = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})

const currentPattern = computed(() => {
  const tpl = normTemplate(props.form.template)
  return patternOptions.value.find((p) => p.slug === tpl)?.slug
    || patternOptions.value.find((p) => (
      p.template === tpl && sameJson(patternLayout(p), props.form.layout_config)
    ))?.slug
    || patternOptions.value.find((p) => p.template === tpl)?.slug
    || ''
})
const currentStyle = computed(() => props.form.site_theme?.style?.id || '')

// Opciones de los selectboxes con icono/color: el select nativo no puede
// mostrar muestras, por eso el menú usa DesignSelect.
const patternSelectOptions = computed(() => patternOptions.value.map((p) => ({
  value: p.slug,
  label: `${p.nombre} · ${p.categoria}`,
  icon: 'layout-grid'
})))
const styleSelectOptions = computed(() => styleOptions.value.map((s) => ({
  value: s.slug,
  label: `${s.nombre} · ${s.categoria}`,
  icon: 'palette',
  swatch: s.tokens?.palette?.accent || ''
})))

// Un patrón sin tema elegido trae sus fuentes (tokens del DesignPattern).
function patternTheme(p) {
  const tokens = p.tokens || {}
  const theme = { ...(props.form.site_theme || {}) }
  const fonts = Array.isArray(tokens.fonts) ? tokens.fonts.filter(Boolean) : []
  if (fonts.length) {
    theme.typography = { ...(theme.typography || {}), body: fonts[0], heading: fonts[1] || fonts[0] }
    fonts.forEach((f) => ensureStoreFont(f))
  }
  return theme
}

function defaultStyleFor(patternSlug) {
  const list = styleOptions.value.filter((s) => !s.pattern || s.pattern === patternSlug)
  return list.find((s) => s.is_default) || list[0] || null
}

function applyStyle(s) {
  const theme = resolveSiteTheme(s.tokens || {})
  props.form.site_theme = { ...theme, style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
  props.form.accent_custom = ''
  const heading = theme.typography?.heading
  const body = theme.typography?.body
  if (heading) ensureStoreFont(heading)
  if (body) {
    props.form.name_font = body
    ensureStoreFont(body)
  }
}

function onPatternPick(value) {
  const p = patternOptions.value.find((x) => x.slug === value)
  if (!p) return
  // El template guarda el SLUG del patrón (pattern_for_template del
  // backend lo resuelve por slug primero): así cada diseño aplica el suyo.
  props.form.template = p.slug
  props.form.layout_config = patternLayout(p)
  // Al cambiar de diseño el estilo siempre queda seleccionado: primero el
  // default del diseño (o su estilo vinculado), nunca el tema de otro
  // diseño ni un select vacío.
  const linked = styles.value.find((s) => s.slug === p.style && s.is_active !== false)
  const style = linked || defaultStyleFor(p.slug)
  if (style) applyStyle(style)
  else props.form.site_theme = patternTheme(p)
  previewReload.value++
}

// Cada diseño trae sus propios temas (DesignStyle): el elegido aplica el
// tema COMPLETO — paleta, tipografía, contenedores, botones, fondo, modo y
// movimiento — para que la web publicada se vea igual que la vista previa.
// El dueño ya no elige colores sueltos: los colores son del tema.
function onStylePick(value) {
  const s = styleOptions.value.find((x) => x.slug === value)
  if (!s) return
  applyStyle(s)
  previewReload.value++
}

// Diseño y estilo nunca quedan vacíos: si el diseño guardado es retirado o
// no está en el catálogo se cae al default (o al primero), y si el estilo
// no pertenece al diseño elegido se selecciona el default de ese diseño.
watch([patternOptions, styles], () => {
  if (!patternOptions.value.length) return
  const tpl = normTemplate(props.form.template)
  if (STORE_TEMPLATE_RETIRED_MAP[props.form.template]) props.form.template = tpl
  if (!currentPattern.value) {
    const p = patternOptions.value.find((x) => x.is_default) || patternOptions.value[0]
    if (p) { onPatternPick(p.slug); return }
  }
  const hasStyle = styleOptions.value.some((s) => s.slug === currentStyle.value)
  if (!hasStyle) {
    const s = defaultStyleFor(currentPattern.value)
    if (s) applyStyle(s)
  }
}, { immediate: true })

// --- "Qué mostrar": modal con las páginas y las secciones que el diseño
// elegido soporta (sus bloques por superficie). Apagar una sección escribe
// enabled:false en layout_config — el diseño declara la whitelist, el
// renderer público respeta el flag y saveDesign lo publica.
const showOpen = ref(false)
const closeShowBtn = ref(null)
let lastShowFocus = null
function openShow() {
  lastShowFocus = document.activeElement
  showOpen.value = true
}
function closeShow() { showOpen.value = false }
watch(showOpen, async (open) => {
  if (props.previewOpen) return
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    await nextTick()
    closeShowBtn.value?.focus()
  } else {
    lastShowFocus?.focus?.()
    lastShowFocus = null
  }
})
// Capacidades del diseño: las superficies/bloques que declara el patrón
// (su layout normalizado) o, si no declara una, la composición canónica
// del template base. Cada bloque muestra su enabled efectivo (canónico ∪
// layout_config guardado).
const showGroups = computed(() => {
  const p = patternOptions.value.find((x) => x.slug === currentPattern.value)
  const declared = p ? normalizeLayoutConfig(p.layout) : {}
  const tpl = templateOf(p?.template || props.form.template)
  return LAYOUT_SURFACES.map((surface) => {
    let blocks = declared[surface]?.blocks
    const saved = props.form.layout_config?.[surface]?.blocks || []
    const byId = new Map(saved.filter((b) => b && b.id != null).map((b) => [String(b.id), b]))
    if (Array.isArray(blocks) && blocks.length) {
      blocks = blocks.map((b) => ({ ...b, enabled: byId.get(b.id) ? byId.get(b.id).enabled !== false : b.enabled !== false }))
    } else {
      blocks = templateBlocks(tpl, surface, props.form.layout_config)
    }
    const rows = blocks
      .map((b) => ({ block: b, spec: blockSpec(surface, b.id) }))
      .filter((r) => r.spec && (!r.spec.aiOnly || props.benefits.has_ai_design))
    return { surface, label: SURFACE_LABELS[surface] || surface, rows }
  }).filter((g) => g.rows.length)
})
function blockLocked(spec) {
  if (spec.locked) return 'Fijo en el diseño'
  if (spec.premium && !props.benefits.has_design_advanced) return 'Plan premium'
  return ''
}
function toggleBlock(surface, id) {
  const lc = props.form.layout_config && typeof props.form.layout_config === 'object'
    ? props.form.layout_config : (props.form.layout_config = {})
  const surf = lc[surface] && typeof lc[surface] === 'object' ? lc[surface] : (lc[surface] = { blocks: [] })
  if (!Array.isArray(surf.blocks)) surf.blocks = []
  const found = surf.blocks.find((b) => b && String(b.id) === id)
  if (found) found.enabled = !(found.enabled !== false)
  else surf.blocks.push({ id, enabled: false, order: surf.blocks.length })
}
function onShowKey(e) { if (e.key === 'Escape' && showOpen.value) closeShow() }

// --- Vista previa en móvil: overlay a demanda ---------------------------
// En pantallas chicas no se muestra ningún panel embebido: la web real se
// abre desde el botón flotante en una hoja a pantalla completa.
const closePvBtn = ref(null)
let lastFocusEl = null
function openMobilePreview() {
  lastFocusEl = document.activeElement
  emit('update:previewOpen', true)
}
function closeMobilePreview() {
  emit('update:previewOpen', false)
}
watch(() => props.previewOpen, async (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    await nextTick()
    closePvBtn.value?.focus()
  } else {
    lastFocusEl?.focus?.()
    lastFocusEl = null
  }
})
function onMobilePreviewKey(e) {
  if (e.key === 'Escape' && props.previewOpen) closeMobilePreview()
  else if (e.key === 'Escape' && showOpen.value) closeShow()
}
// Si el viewport crece a escritorio, la hoja se cierra (ahí ya está el panel).
function onViewport() {
  if (props.previewOpen && window.matchMedia('(min-width: 1100px)').matches) closeMobilePreview()
}
onMounted(() => {
  window.addEventListener('keydown', onMobilePreviewKey)
  window.addEventListener('keydown', onShowKey)
  window.addEventListener('resize', onViewport, { passive: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onMobilePreviewKey)
  window.removeEventListener('keydown', onShowKey)
  window.removeEventListener('resize', onViewport)
  if (props.previewOpen || showOpen.value) document.body.style.overflow = ''
})
</script>

<template>
  <div class="dmenu">
    <div class="dmenu-grid">
      <div class="dmenu-main">
        <div class="card dmenu-card">
          <header class="dmenu-head">
            <div class="dmenu-head-row">
              <div class="dmenu-head-txt">
                <strong><AppIcon name="palette" :size="17" aria-hidden="true" /> Diseño</strong>
                <small>Elegí el diseño y el estilo de tu web. La vista previa muestra los cambios al instante.</small>
              </div>
              <button type="button" class="btn secondary btn-auto dmenu-show-btn" @click="openShow">
                <AppIcon name="layout-grid" :size="16" /> Qué mostrar
              </button>
            </div>
          </header>

          <div class="dmenu-fields">
            <div class="dmenu-field">
              <label>Diseño</label>
              <DesignSelect
                :model-value="currentPattern" :options="patternSelectOptions" icon="layout-grid"
                aria-label="Diseño" placeholder="Elegí un diseño…"
                :disabled="!patternOptions.length" @change="onPatternPick"
              />
            </div>

            <div class="dmenu-field">
              <label>Estilo</label>
              <DesignSelect
                :model-value="currentStyle" :options="styleSelectOptions" icon="palette"
                aria-label="Estilo" placeholder="Elegí un estilo…"
                :disabled="!styleOptions.length" @change="onStylePick"
              />
              <p class="dmenu-hint">Cada diseño trae sus estilos: color, tipografía y modo.</p>
            </div>
          </div>

          <p v-if="status === 'error'" class="dmenu-alert" role="alert">
            No pudimos cargar el catálogo de diseño.
            <button type="button" class="btn ghost btn-auto" @click="load(true)">Reintentar</button>
          </p>
          <p v-else-if="status === 'success' && !patternOptions.length && !styleOptions.length" class="dmenu-alert" role="status">
            El catálogo está vacío: corré <code>manage.py seed_design_catalog</code> en el servidor.
          </p>
        </div>
      </div>

      <aside class="dmenu-live">
        <DesignLivePreview :form="form" :reload-key="previewReload" />
        <slot name="actions" />
      </aside>
    </div>

    <!-- Punto de acceso único a la vista previa en pantallas chicas. -->
    <button
      v-if="!previewOpen" type="button" class="dmenu-fab"
      aria-label="Ver mi web en vista previa" @click="openMobilePreview"
    >
      <span class="dmenu-fab-ico" aria-hidden="true"><AppIcon name="eye" :size="18" /></span>
      <span>Ver mi web</span>
    </button>
  </div>

  <Teleport to="body">
    <Transition name="dmenu-pv">
      <div
        v-if="showOpen" class="dmenu-pv dshow" role="dialog" aria-modal="true"
        aria-label="Qué mostrar en tu web" @click.self="closeShow"
      >
        <div class="dshow-panel">
          <header class="dmenu-pv-head">
            <strong><AppIcon name="layout-grid" :size="16" aria-hidden="true" /> Qué mostrar</strong>
            <button
              ref="closeShowBtn" type="button" class="dmenu-pv-x"
              aria-label="Cerrar" @click="closeShow"
            >
              <AppIcon name="x" :size="18" />
            </button>
          </header>
          <div class="dshow-body">
            <p class="dshow-hint">Elegí qué páginas y secciones aparecen en tu web. Las opciones dependen del diseño que elegiste; los cambios se publican con «Guardar cambios».</p>

            <section v-if="pageOptions.length" class="dshow-group" aria-label="Páginas de tu web">
              <h3>Páginas</h3>
              <div class="check-list" role="group">
                <label v-for="opt in pageOptions" :key="opt.key" class="check-item" :class="{ disabled: opt.disabled }">
                  <input type="checkbox" :checked="opt.on" :disabled="opt.disabled" @change="emit('toggle-page', opt.key)" />
                  <span class="check-text">
                    <strong>{{ opt.label }} <span v-if="opt.lock" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> {{ opt.lock }}</span> <span v-if="opt.busy" class="spinner spinner-brand" aria-hidden="true"></span></strong>
                    <small>{{ opt.desc }}</small>
                  </span>
                </label>
              </div>
            </section>

            <section v-for="g in showGroups" :key="g.surface" class="dshow-group" :aria-label="`Secciones de ${g.label}`">
              <h3>{{ g.label }}</h3>
              <div class="check-list" role="group">
                <label
                  v-for="r in g.rows" :key="r.block.id" class="check-item"
                  :class="{ disabled: Boolean(blockLocked(r.spec)) }"
                >
                  <input
                    type="checkbox" :checked="r.block.enabled !== false"
                    :disabled="Boolean(blockLocked(r.spec))" @change="toggleBlock(g.surface, r.block.id)"
                  />
                  <span class="check-text">
                    <strong>
                      <AppIcon :name="r.spec.icon || 'package'" :size="14" aria-hidden="true" class="dshow-ico" />
                      {{ r.spec.label }}
                      <span v-if="blockLocked(r.spec)" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> {{ blockLocked(r.spec) }}</span>
                    </strong>
                    <small>{{ r.spec.desc }}</small>
                  </span>
                </label>
              </div>
            </section>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="dmenu-pv">
      <div
        v-if="previewOpen" class="dmenu-pv" role="dialog" aria-modal="true"
        aria-label="Vista previa de tu web"
      >
        <header class="dmenu-pv-head">
          <strong><AppIcon name="eye" :size="16" aria-hidden="true" /> Tu web en vivo</strong>
          <button
            ref="closePvBtn" type="button" class="dmenu-pv-x"
            aria-label="Cerrar la vista previa" @click="closeMobilePreview"
          >
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="dmenu-pv-body">
          <DesignLivePreview :form="form" initial-device="mobile" :reload-key="previewReload" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dmenu { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.dmenu-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; min-width: 0; }
.dmenu-main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.dmenu-live { min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.dmenu-card { padding: 18px; display: flex; flex-direction: column; gap: 16px; container-type: inline-size; }
.dmenu-head { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.dmenu-head-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; min-width: 0; }
.dmenu-head-txt { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.dmenu-show-btn { flex: none; }
.dmenu-head strong { display: inline-flex; align-items: center; gap: 7px; font-size: 15px; color: var(--ink); }
.dmenu-head strong .icon { color: var(--brand-600); flex: none; }
.dmenu-head small { font-size: 12.5px; line-height: 1.4; color: var(--muted); }
.dmenu-fields { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px 18px; min-width: 0; align-content: start; }
.dmenu-field { display: grid; gap: 7px; min-width: 0; align-content: start; }
.dmenu-field label { font-size: 13px; font-weight: 600; line-height: 1.3; color: var(--ink-2); }
.dmenu-field .select { width: 100%; min-width: 0; text-overflow: ellipsis; }
.dmenu-hint { margin: 0; font-size: 12px; line-height: 1.4; color: var(--muted); }
.dmenu-alert { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 0; font-size: 12px; color: var(--danger, #b91c1c); }
.dmenu-alert code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
@media (min-width: 1100px) {
  .dmenu-grid { grid-template-columns: minmax(0, 1fr) minmax(440px, 620px); align-items: start; }
  .dmenu-live { position: sticky; top: 12px; }
}
@media (max-width: 1099px) {
  /* Sin panel embebido: la vista previa vive en la hoja a pantalla completa. */
  .dmenu-live { display: none; }
}
@media (min-width: 1100px) {
  .dmenu-fab { display: none; }
}

/* Botón flotante de vista previa (solo < 1100px). Vive por encima de la
   savebar sticky y de la tab bar, sin tapar los controles del formulario. */
.dmenu-fab {
  position: fixed; right: calc(14px + env(safe-area-inset-right));
  bottom: calc(184px + env(safe-area-inset-bottom)); z-index: 45;
  display: inline-flex; align-items: center; gap: 8px; min-height: 46px;
  padding: 0 16px 0 12px; border: 0; border-radius: 999px;
  background: linear-gradient(135deg, var(--brand-500, #6366f1), var(--accent, #8b5cf6));
  color: #fff; font: inherit; font-size: 13.5px; font-weight: 650; letter-spacing: -.01em;
  box-shadow: 0 14px 30px -12px rgba(79, 70, 229, .75), 0 0 0 1px rgba(255, 255, 255, .16) inset;
  cursor: pointer; touch-action: manipulation; -webkit-tap-highlight-color: transparent;
  transition: transform .18s var(--ease-out, cubic-bezier(.2, .8, .2, 1)), box-shadow .18s, filter .18s;
}
.dmenu-fab:hover { filter: brightness(1.06); }
.dmenu-fab:active { transform: scale(.96); }
.dmenu-fab:focus-visible { outline: 2px solid var(--brand-500, #6366f1); outline-offset: 3px; }
.dmenu-fab-ico { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: rgba(255, 255, 255, .2); }

/* Hoja de vista previa a pantalla completa (móvil/tablet). */
.dmenu-pv {
  position: fixed; inset: 0; z-index: 1300; display: flex; flex-direction: column;
  background: color-mix(in srgb, var(--bg, #f8fafc) 94%, transparent);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  padding: calc(10px + env(safe-area-inset-top)) 12px calc(12px + env(safe-area-inset-bottom));
}
.dmenu-pv-head {
  flex: none; display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 2px 4px 10px;
}
.dmenu-pv-head strong {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 14px; letter-spacing: -.01em; color: var(--ink, #0f172a);
}
.dmenu-pv-head strong .icon { color: var(--brand-600, #4f46e5); }
.dmenu-pv-x {
  display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px;
  border: 1px solid var(--line, #e5e7eb); background: var(--card, #fff); color: var(--ink-2, #334155);
  cursor: pointer; touch-action: manipulation;
  transition: background .15s, transform .15s, border-color .15s;
}
.dmenu-pv-x:hover { border-color: var(--brand-soft-line, #c7d2fe); }
.dmenu-pv-x:active { transform: scale(.94); }
.dmenu-pv-body { flex: 1 1 auto; min-height: 0; display: flex; }
.dmenu-pv-body :deep(.dlp) {
  flex: 1 1 auto; min-height: 0; padding: 10px; border-radius: 18px;
  box-shadow: 0 20px 50px -26px rgba(9, 12, 24, .45);
}
.dmenu-pv-body :deep(.dlp-stage) { height: 100%; min-height: 0; }
.dmenu-pv-body :deep(.dlp-stage.mobile) { padding: 10px 0; }
.dmenu-pv-body :deep(.dlp-stage.mobile .dlp-device) { border-radius: 22px; }
.dmenu-pv-enter-active, .dmenu-pv-leave-active { transition: opacity .2s ease; }
.dmenu-pv-enter-active .dmenu-pv-body, .dmenu-pv-leave-active .dmenu-pv-body { transition: transform .22s var(--ease-out, cubic-bezier(.2, .8, .2, 1)); }
.dmenu-pv-enter-from, .dmenu-pv-leave-to { opacity: 0; }
.dmenu-pv-enter-from .dmenu-pv-body, .dmenu-pv-leave-to .dmenu-pv-body { transform: translateY(14px); }

/* Modal "Qué mostrar": hoja centrada que scrollea su contenido. */
.dshow { align-items: center; justify-content: center; }
.dshow-panel {
  display: flex; flex-direction: column; width: min(680px, 100%);
  max-height: min(720px, 100%); margin: auto; border-radius: 20px;
  border: 1px solid var(--line, #e5e7eb); background: var(--card, #fff);
  box-shadow: 0 30px 70px -30px rgba(9, 12, 24, .5); overflow: hidden;
}
.dshow-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 6px 18px 18px; display: flex; flex-direction: column; gap: 18px; }
.dshow-hint { margin: 0; font-size: 12.5px; line-height: 1.45; color: var(--muted, #64748b); }
.dshow-group { display: flex; flex-direction: column; gap: 10px; }
.dshow-group h3 { margin: 0; font-size: 13px; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; color: var(--muted, #64748b); }
.dshow-ico { vertical-align: -2px; margin-right: 5px; color: var(--brand-600, #4f46e5); }
@media (prefers-reduced-motion: reduce) {
  .dmenu-fab, .dmenu-pv, .dmenu-pv-body { transition: none !important; }
}
</style>
