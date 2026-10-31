<script setup>
// Sub-sección "Diseño" (todos los planes con has_customization).
// Menú compacto: siete selectboxes con las estructuras de datos del catálogo
// (diseño, estilo, colores, color de fuente y las tres familias tipográficas).
// Sin subidas de imágenes: logo, portada y galería viven en la pestaña Fotos.
// Escribe los mismos campos de `form` que el Studio y dispara los mismos
// eventos (ring/navigate), así el guardado sigue siendo uno solo.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import { designApi } from '../../api/design.api.js'
import {
  STORE_ACCENTS, STORE_THEMES, STORE_FONTS, STORE_FONT_GROUPS, STORE_TEMPLATES,
  allowedTemplatesFor, ensureStoreFont
} from '../../api/stores.api.js'
import { deriveAccent } from '../../utils/colorTools.js'
import { resolveSiteTheme } from '../../studio/contract.js'
import { normalizeLayoutConfig } from '../../templates/index.js'
import DesignLivePreview from './DesignLivePreview.vue'
import DesignSelect from './DesignSelect.vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  canStudio: { type: Boolean, default: false },
  // Estado del panel de vista previa: lo controla el padre para que la
  // savebar sticky también pueda abrirlo en mobile.
  previewOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'ring', 'open-studio', 'update:previewOpen'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const allowed = computed(() => allowedTemplatesFor(props.benefits || {}))
const allowedTemplate = (tpl) => allowed.value.includes(tpl)
const tierOf = (tpl) => STORE_TEMPLATES[tpl]?.tier || 'base'
const tierLabel = (tpl) => {
  const tier = tierOf(tpl)
  return tier === 'plus' ? 'Desde Estándar' : tier === 'advanced' ? 'Premium' : 'Incluido'
}

const { patterns, styles, iconStyles, status, load } = useDesignCatalog()
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

const patternOptions = computed(() => (
  modelPatterns.value.length ? modelPatterns.value : patterns.value
))
// Cada diseño trae sus propios estilos (DesignStyle.pattern): con un diseño
// elegido solo se listan los suyos (los sin vínculo siguen disponibles).
const styleOptions = computed(() => styles.value.filter((s) => (
  s.is_active !== false
  && (!currentPattern.value || !s.pattern || s.pattern === currentPattern.value)
)))
const patternLayout = (p) => normalizeLayoutConfig(p.layout)
const sameJson = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})

const currentPattern = computed(() => (
  patternOptions.value.find((p) => (
    p.template === props.form.template && sameJson(patternLayout(p), props.form.layout_config)
  ))?.slug
  || patternOptions.value.find((p) => p.template === props.form.template)?.slug
  || ''
))
const currentStyle = computed(() => props.form.site_theme?.style?.id || '')
// Set de iconos de los controles (menú, buscador, carrito, tema): vacío =
// hereda el que trae el diseño elegido.
const iconStyleOptions = computed(() => [
  { value: '', label: 'Heredar del diseño', icon: 'layout-grid' },
  ...iconStyles.value.map((s) => ({ value: s.slug, label: s.nombre, icon: 'menu' }))
])
const currentIconStyle = computed(() => props.form.icon_style || '')
function onIconStylePick(value) {
  props.form.icon_style = value || ''
}
const currentPatternMeta = computed(() => patternOptions.value.find((p) => p.slug === currentPattern.value) || null)

// Vista del HTML propio del patrón (el diseño fuente, con su menú y sus
// animaciones), en un iframe aislado. El listado no trae el markup: se pide
// el detalle recién al abrir.
const patternPreview = ref(null) // { nombre, html, css, js, theme }
const previewBusy = ref(false)
const previewErr = ref('')
// Tema de la vista previa: arranca con el de la tienda y se puede alternar
// sin volver a pedir el patrón (la hoja ya trae las reglas de modo noche).
const previewTheme = ref('light')
const previewAccent = computed(() => {
  const hex = props.form?.accent_custom
  return typeof hex === 'string' && hex.startsWith('#') ? hex : ''
})
const previewDoc = computed(() => (
  patternPreview.value ? patternDoc(patternPreview.value) : ''
))

function patternDoc(p) {
  const html = String(p.html || '')
  if (/^\s*(<!doctype|<html)/i.test(html)) return html
  const css = p.css ? `<style>${p.css}</style>` : ''
  const js = p.js ? `<script>${p.js}<` + `/script>` : ''
  const theme = p.theme === 'dark' ? 'dark' : 'light'
  return `<!doctype html><html lang="es" data-ds-surface="landing" data-ds-theme="${theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">${css}</head><body>${html}${js}</body></html>`
}

async function openPatternPreview() {
  const meta = currentPatternMeta.value
  if (!meta?.has_markup || previewBusy.value) return
  previewBusy.value = true
  previewErr.value = ''
  previewTheme.value = props.form?.theme === 'dark' ? 'dark' : 'light'
  try {
    const detail = await designApi.patternPreview(meta.slug, {
      theme: previewTheme.value,
      accent: previewAccent.value,
      style: props.form?.site_theme?.style?.id || '',
    })
    patternPreview.value = {
      nombre: detail.nombre || meta.nombre,
      html: detail.html || '',
      css: detail.css || '',
      js: detail.js || '',
      theme: detail.theme || previewTheme.value,
    }
  } catch {
    previewErr.value = 'No pudimos cargar el diseño del patrón.'
  } finally {
    previewBusy.value = false
  }
}
function setPreviewTheme(theme) {
  previewTheme.value = theme === 'dark' ? 'dark' : 'light'
  if (patternPreview.value) patternPreview.value.theme = previewTheme.value
}
function closePatternPreview() {
  patternPreview.value = null
  previewErr.value = ''
}
function onPreviewKey(e) { if (e.key === 'Escape') closePatternPreview() }
onMounted(() => window.addEventListener('keydown', onPreviewKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onPreviewKey))

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
function onMobilePreviewKey(e) { if (e.key === 'Escape' && props.previewOpen) closeMobilePreview() }
// Si el viewport crece a escritorio, la hoja se cierra (ahí ya está el panel).
function onViewport() {
  if (props.previewOpen && window.matchMedia('(min-width: 1100px)').matches) closeMobilePreview()
}
onMounted(() => {
  window.addEventListener('keydown', onMobilePreviewKey)
  window.addEventListener('resize', onViewport, { passive: true })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onMobilePreviewKey)
  window.removeEventListener('resize', onViewport)
  if (props.previewOpen) document.body.style.overflow = ''
})

// Opciones de los selectboxes con icono/color: el select nativo no puede
// mostrar muestras, por eso el menú usa DesignSelect.
const patternSelectOptions = computed(() => patternOptions.value.map((p) => ({
  value: p.slug,
  label: `${p.nombre} · ${p.categoria} · ${tierLabel(p.template)}`,
  icon: 'layout-grid',
  disabled: !allowedTemplate(p.template)
})))
const styleSelectOptions = computed(() => styleOptions.value.map((s) => ({
  value: s.slug,
  label: `${s.nombre} · ${s.categoria} · ${tierLabel(s.template)}`,
  icon: 'palette',
  disabled: !allowedTemplate(s.template)
})))

// Un patrón sin estilo elegido trae sus fuentes (tokens del DesignPattern).
// La paleta NO se aplica sola: el color queda en "Usa estilo base" hasta que
// el dueño elija uno en el select de Colores.
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

function onPatternPick(value) {
  const p = patternOptions.value.find((x) => x.slug === value)
  if (!p) return
  if (!allowedTemplate(p.template)) {
    emit('navigate', 'plans')
    return
  }
  props.form.template = p.template
  props.form.layout_config = patternLayout(p)
  if (!props.form.site_theme?.style?.id) props.form.site_theme = patternTheme(p)
}

function onStylePick(value) {
  const s = styleOptions.value.find((x) => x.slug === value)
  if (!s) return
  if (!allowedTemplate(s.template)) {
    emit('navigate', 'plans')
    return
  }
  // El estilo es un tema completo: se aplican sus tokens (tipografía,
  // contenedores, botones, fondo, movimiento y móvil) para que el look
  // elegido se vea igual acá, en el Studio y en la web publicada. La paleta
  // NO viaja: los colores quedan en "Usa estilo base" hasta que se elijan a
  // mano, así el diseño no pisa los colores de la tienda. La estructura
  // tampoco se toca: el template y el layout son del diseño.
  const theme = resolveSiteTheme(s.tokens || {})
  delete theme.palette
  props.form.site_theme = { ...theme, style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
  const heading = theme.typography?.heading
  const body = theme.typography?.body
  if (heading) ensureStoreFont(heading)
  if (body) {
    props.form.name_font = body
    ensureStoreFont(body)
  }
}

// --- Colores: tema + acento en un solo selectbox --------------------------
// Cada opción fija el par completo (claro/oscuro + acento). "Usa estilo base"
// es el estado por defecto: sin paleta forzada en site_theme (el diseño
// elegido no pisa los colores de la tienda).
const currentMode = computed(() => (props.form.theme === 'dark' ? 'dark' : 'light'))
const forcedPalette = computed(() => Boolean(
  props.form.accent_custom || props.form.site_theme?.palette?.accent
))
const colorGroups = computed(() => Object.entries(STORE_THEMES).map(([mode, theme]) => {
  const options = [{
    value: `${mode}:base`,
    label: 'Usa estilo base',
    icon: 'palette'
  }, ...Object.entries(STORE_ACCENTS).map(([key, a]) => ({
    value: `${mode}:${key}`,
    label: `${a.label} · ${a.hex}`,
    swatch: a.hex
  }))]
  if (props.form.accent_custom) {
    options.splice(1, 0, {
      value: `${mode}:custom`,
      label: `Personalizado · ${props.form.accent_custom}`,
      swatch: props.form.accent_custom
    })
  }
  return { label: theme.label, options }
}))
const currentColors = computed(() => (
  forcedPalette.value
    ? `${currentMode.value}:${props.form.accent_custom ? 'custom' : (props.form.accent || 'indigo')}`
    : `${currentMode.value}:base`
))

function withTheme(mutate) {
  const theme = { ...(props.form.site_theme || {}) }
  mutate(theme)
  props.form.site_theme = theme
}

function onColorsPick(value) {
  const [mode, key] = String(value).split(':')
  if (STORE_THEMES[mode]) props.form.theme = mode
  if (key === 'base') {
    props.form.accent_custom = ''
    withTheme((theme) => { delete theme.palette })
    return
  }
  if (key === 'custom' || !advanced.value) return
  const hex = STORE_ACCENTS[key]?.hex
  if (!hex) return
  props.form.accent = key
  props.form.accent_custom = ''
  // El estilo aplicado fija su propia paleta en site_theme: si solo se
  // cambiara `accent`, la web seguiría mostrando el color del estilo.
  const a = deriveAccent(hex)
  withTheme((theme) => {
    theme.palette = { ...(theme.palette || {}), accent: a.hex, primary: a.hex, secondary: a.ink }
  })
}

// --- Tipografía: títulos y descripciones ---------------------------------
// Las familias salen del selector del catálogo (mismas fuentes que la web).
// Se guardan como slug: el contrato las resuelve a familia al render.
const FONT_ROLES = [
  { key: 'heading', label: 'Fuente de títulos', ring: 'typo' },
  { key: 'body', label: 'Fuente de descripciones', ring: 'page' }
]
const fontGroups = computed(() => {
  const groups = STORE_FONT_GROUPS.map((g) => ({ label: g.label, keys: g.keys.slice() }))
  // Fuentes guardadas fuera del selector (estilos del catálogo que traen su
  // propia familia): se muestran igual para no dejar el select en blanco.
  const saved = FONT_ROLES
    .map((r) => props.form.site_theme?.typography?.[r.key])
    .filter((key) => key && !STORE_FONT_GROUPS.some((g) => g.keys.includes(key)))
  if (saved.length) groups.push({ label: 'Actual', keys: [...new Set(saved)] })
  return groups
})
const fontSelectGroups = computed(() => fontGroups.value.map((g) => ({
  label: g.label,
  options: g.keys.map((key) => ({
    value: key,
    label: STORE_FONTS[key]?.label || key,
    icon: 'type'
  }))
})))
const currentFont = (key) => props.form.site_theme?.typography?.[key] || ''

function onFontPick(value, key) {
  if (value) ensureStoreFont(value)
  withTheme((theme) => {
    const typography = { ...(theme.typography || {}) }
    if (value) typography[key] = value
    else delete typography[key]
    theme.typography = typography
  })
  // La descripción es el texto corrido de toda la web: además del tema, se
  // escribe `name_font` (el token que ya consumen las plantillas), si no las
  // pieles de cada diseño mantienen su propia familia.
  if (key === 'body' && value) props.form.name_font = value
}

// Fuentes ya elegidas: se cargan al entrar para que los selectboxes muestren
// la familia real y la vista previa no quede en Inter.
onMounted(() => {
  FONT_ROLES.forEach((r) => {
    const key = currentFont(r.key)
    if (key) ensureStoreFont(key)
  })
})
</script>

<template>
  <div class="dmenu">
    <div class="dmenu-grid">
      <div class="dmenu-main">
        <div class="card dmenu-card">
          <header class="dmenu-head">
            <strong><AppIcon name="palette" :size="17" aria-hidden="true" /> Diseño</strong>
            <small>Elegí cada pieza de tu web desde una lista. Se guarda con el botón de abajo.</small>
          </header>

          <div class="dmenu-fields">
            <div class="dmenu-field" @focusin="emit('ring', 'hero')">
              <label>Patrones de diseño</label>
              <DesignSelect
                :model-value="currentPattern" :options="patternSelectOptions" icon="layout-grid"
                aria-label="Patrones de diseño" placeholder="Elegí un patrón…"
                :disabled="!patternOptions.length" @change="onPatternPick"
              />
              <button
                v-if="currentPatternMeta?.has_markup" type="button"
                class="btn ghost btn-auto dmenu-preview" :disabled="previewBusy"
                @click="openPatternPreview"
              >
                <AppIcon name="eye" :size="15" /> {{ previewBusy ? 'Cargando…' : 'Ver este diseño' }}
              </button>
              <p v-if="previewErr" class="dmenu-alert" role="alert">{{ previewErr }}</p>
            </div>

            <div class="dmenu-field" @focusin="emit('ring', 'typo')">
              <label>Estilo</label>
              <DesignSelect
                :model-value="currentStyle" :options="styleSelectOptions" icon="palette"
                aria-label="Estilo" placeholder="Elegí un estilo…"
                :disabled="!styleOptions.length" @change="onStylePick"
              />
            </div>

            <div class="dmenu-field" @focusin="emit('ring', 'buttons')">
              <label>Iconos del menú</label>
              <DesignSelect
                :model-value="currentIconStyle" :options="iconStyleOptions" icon="menu"
                aria-label="Iconos del menú" placeholder="Heredar del diseño…"
                :disabled="!iconStyles.length" @change="onIconStylePick"
              />
              <p class="dmenu-hint">Se pueden cambiar sin tocar el diseño.</p>
            </div>

            <div class="dmenu-field" @focusin="emit('ring', 'buttons')">
              <label>Colores</label>
              <DesignSelect
                :model-value="currentColors" :groups="colorGroups" icon="paintbrush"
                aria-label="Colores" placeholder="Elegí un color…" @change="onColorsPick"
              />
              <p class="dmenu-hint">Tema y color de acento. <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Acento con Premium</span></p>
            </div>

            <div v-for="r in FONT_ROLES" :key="r.key" class="dmenu-field" :class="{ locked: !advanced }" @focusin="emit('ring', r.ring)">
              <label>{{ r.label }}</label>
              <DesignSelect
                :model-value="currentFont(r.key)" :groups="fontSelectGroups" icon="type"
                :aria-label="r.label" placeholder="Elegí una fuente…"
                :disabled="!advanced" @change="(value) => onFontPick(value, r.key)"
              />
            </div>
          </div>

          <p v-if="status === 'error'" class="dmenu-alert" role="alert">
            No pudimos cargar el catálogo de diseño.
            <button type="button" class="btn ghost btn-auto" @click="load(true)">Reintentar</button>
          </p>
          <p v-else-if="status === 'success' && !patternOptions.length && !styleOptions.length" class="dmenu-alert" role="status">
            El catálogo está vacío: corré <code>manage.py seed_design_catalog</code> en el servidor.
          </p>

          <div v-if="!advanced" class="dmenu-lock">
            <AppIcon name="lock" :size="16" aria-hidden="true" />
            <span>Las fuentes vienen con el Plan premium.</span>
            <button type="button" class="btn ghost btn-auto" @click="emit('navigate', 'plans')">Ver planes</button>
          </div>
        </div>
      </div>

      <aside class="dmenu-live">
        <DesignLivePreview :form="form" />
      </aside>
    </div>

    <div v-if="canStudio" class="dmenu-studio">
      <span class="dmenu-studio-ico" aria-hidden="true"><AppIcon name="layout-panel-left" :size="18" /></span>
      <div class="dmenu-studio-txt">
        <strong>Studio</strong>
        <small>Control total con vista previa en vivo, en pantalla completa.</small>
      </div>
      <button type="button" class="btn secondary btn-auto" @click="emit('open-studio')">
        Abrir Studio <AppIcon name="arrow-right" :size="16" />
      </button>
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
          <DesignLivePreview :form="form" initial-device="mobile" />
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <div v-if="patternPreview" class="dpv" role="dialog" aria-modal="true" :aria-label="`Vista previa de ${patternPreview.nombre}`">
      <div class="dpv-head">
        <strong>{{ patternPreview.nombre }}</strong>
        <div class="dpv-theme" role="group" aria-label="Modo de la vista previa">
          <button
            type="button" :aria-pressed="previewTheme === 'light'"
            :class="{ on: previewTheme === 'light' }" @click="setPreviewTheme('light')"
          >Claro</button>
          <button
            type="button" :aria-pressed="previewTheme === 'dark'"
            :class="{ on: previewTheme === 'dark' }" @click="setPreviewTheme('dark')"
          >Noche</button>
        </div>
        <button type="button" class="dpv-close" aria-label="Cerrar la vista previa" @click="closePatternPreview">
          <AppIcon name="x" :size="16" />
        </button>
      </div>
      <iframe
        class="dpv-frame" :srcdoc="previewDoc" sandbox="allow-scripts"
        :title="`Diseño ${patternPreview.nombre}`"
      ></iframe>
    </div>
  </Teleport>
</template>

<style scoped>
.dmenu { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.dmenu-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; min-width: 0; }
.dmenu-main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.dmenu-live { min-width: 0; }
.dmenu-card { padding: 18px; display: flex; flex-direction: column; gap: 16px; container-type: inline-size; }
.dmenu-head { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.dmenu-head strong { display: inline-flex; align-items: center; gap: 7px; font-size: 15px; color: var(--ink); }
.dmenu-head strong .icon { color: var(--brand-600); flex: none; }
.dmenu-head small { font-size: 12.5px; line-height: 1.4; color: var(--muted); }
.dmenu-fields { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px 18px; min-width: 0; align-content: start; }
.dmenu-field { display: grid; gap: 7px; min-width: 0; align-content: start; }
.dmenu-field label { font-size: 13px; font-weight: 600; line-height: 1.3; color: var(--ink-2); }
.dmenu-field .select { width: 100%; min-width: 0; text-overflow: ellipsis; }
.dmenu-field.locked .select { opacity: .6; }
.dmenu-hint { margin: 0; font-size: 12px; line-height: 1.4; color: var(--muted); }
.dmenu-alert { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 0; font-size: 12px; color: var(--danger, #b91c1c); }
.dmenu-alert code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.dmenu-lock {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
  padding: 10px 12px; border-radius: 10px; font-size: 12.5px; color: var(--muted);
  background: var(--surface-2, #f8fafc); border: 1px solid var(--line, #e5e7eb);
}
.dmenu-lock .btn { margin-left: auto; }
.dmenu-studio {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 18px; border-radius: 14px;
  border: 1px solid var(--brand-soft-line, var(--line, #e5e7eb));
  background:
    radial-gradient(120% 160% at 0% 0%, var(--brand-soft, #eef2ff), transparent 65%),
    var(--surface-2, #f8fafc);
}
.dmenu-studio-ico {
  flex: none; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px;
  background: var(--card, #fff); border: 1px solid var(--brand-soft-line, var(--line, #e5e7eb));
  color: var(--brand-ink, #4f46e5);
}
.dmenu-studio-txt { flex: 1 1 auto; min-width: 0; }
.dmenu-studio strong { display: block; font-size: 14px; letter-spacing: -.01em; }
.dmenu-studio small { display: block; font-size: 12px; color: var(--muted, #64748b); }
.dmenu-studio .btn { flex: none; }
@container (min-width: 520px) {
  .dmenu-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
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
@media (max-width: 640px) {
  .dmenu-studio { flex-wrap: wrap; align-items: flex-start; }
  .dmenu-studio-txt { flex-basis: calc(100% - 52px); }
  .dmenu-studio .btn { width: 100%; justify-content: center; }
}
.dmenu-preview { justify-self: start; width: auto; }
/* Vista del HTML fuente del patrón: menú, composición y animaciones reales. */
.dpv {
  position: fixed; inset: 0; z-index: 1200; display: flex; flex-direction: column;
  background: rgba(8, 12, 20, .72); backdrop-filter: blur(6px); padding: 3vh 3vw;
}
.dpv-head {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 0 2px 12px; color: #f8fafc;
}
.dpv-head strong { font-size: 15px; letter-spacing: -.01em; }
.dpv-theme { display: inline-flex; gap: 4px; margin-left: auto; padding: 3px; border-radius: 999px; background: rgba(255, 255, 255, .14); }
.dpv-theme button {
  border: 0; border-radius: 999px; padding: 6px 12px; background: transparent;
  color: #e2e8f0; font-size: 12px; font-weight: 600; cursor: pointer;
}
.dpv-theme button.on { background: #fff; color: #111827; }
.dpv-close {
  display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, .28); background: rgba(255, 255, 255, .12);
  color: #fff; cursor: pointer;
}
.dpv-close:hover { background: rgba(255, 255, 255, .24); }
.dpv-frame {
  flex: 1 1 auto; width: 100%; border: 0; border-radius: 14px; background: #fff;
  box-shadow: 0 30px 80px -30px #000;
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
@media (prefers-reduced-motion: reduce) {
  .dmenu-fab, .dmenu-pv, .dmenu-pv-body { transition: none !important; }
}
</style>
