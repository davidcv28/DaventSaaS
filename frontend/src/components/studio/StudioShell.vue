<script setup>
// StudioShell — contenedor "pro" del diseño: riel de herramientas | panel
// de ajustes | lienzo con la web pública real en vivo (?studio=1 +
// postMessage del contrato, sin recargar ni guardar).
//
// Dos capas de borrador:
//  - `form` (designForm del Dashboard): campos que persisten hoy — el
//    Studio los edita embebido (DesignLookTab en "Estilos") y el dirty/
//    leave-guard/save existentes los cubren.
//  - `theme` (siteTheme del contrato): viaja por studio:update a la vista
//    previa y por `site_theme` en el payload del save (el backend lo limpia
//    y gatea por plan con clean_site_theme).
// Historial: 60 pasos sobre {campos de diseño + theme}, con coalescing.
// Responsive: 3 columnas en escritorio; panel colapsable en tablet; en
// móvil el lienzo va a pantalla completa, el panel es un bottom sheet
// arrastrable de 3 alturas y el riel queda fijo abajo sin tapar contenido.
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick, provide } from 'vue'
import AppIcon from '../AppIcon.vue'
import AppButton from '../AppButton.vue'
import StudioCanvas from './StudioCanvas.vue'
import StudioPanel from './StudioPanel.vue'
import StudioHelp from './StudioHelp.vue'
import StudioSearch from './StudioSearch.vue'
import StudioOnboarding from './StudioOnboarding.vue'
import {
  STUDIO_TOOLS, STUDIO_TOOL_GROUPS, seedStudioTheme, formThemePatch, mergeTheme, clone, toolForTarget
} from './studioModel.js'
import {
  installPreviewBridge, applyFocusRing, syncFontLink
} from './previewBridge.js'
import { useStudioHistory } from './useStudioHistory.js'
import {
  resolveSiteTheme, studioUpdate, STUDIO_MSG, isStudioMessage, themeExplicitKeys, normalizeHex,
  styleColorsBlock, fixContrast
} from '../../studio/contract.js'
import { palettePasses, repairPalette } from './health.js'
import { allowedTemplatesFor, resolveStoreTemplate, ensureStoreFont, STORE_ACCENTS } from '../../api/stores.api.js'
import { nearestAccent, hexToRgb, adaptPalette, deriveAccent } from '../../utils/colorTools.js'
import { presetLock, layoutForTemplate } from '../../studio/presets/index.js'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import { normalizeLayoutConfig } from '../../templates/index.js'
import { blockSpec } from '../../templates/blocks.js'

const { presets: designPresets, defaultPattern, load: loadDesignCatalog } = useDesignCatalog()

const props = defineProps({
  form: { type: Object, required: true },
  customization: { type: Object, default: () => ({}) },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  publicUrl: { type: String, default: '' },
  previewUrl: { type: String, default: '' },
  siteTemplates: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
  dirty: { type: Boolean, default: false }, // dirty de los campos persistibles (designDirty del padre)
  initialTheme: { type: Object, default: null }, // último borrador emitido: el draft sobrevive al cambio de pestaña
  savedTheme: { type: Object, default: null },   // último tema guardado (punto de guardado estable entre montajes)
  initialExtras: { type: Object, default: null }, // último ensayo emitido {layout_config, template} — sobrevive al remontar
  // Flujo borrador → publicar + salud de la web (los maneja el Dashboard).
  healthCtx: { type: Object, default: () => ({}) },
  hasUnpublished: { type: Boolean, default: false },
  versions: { type: Array, default: () => [] },
  versionsLoading: { type: Boolean, default: false },
  actionBusy: { type: String, default: '' },
  shareUrl: { type: String, default: '' },
  shareExpires: { type: String, default: '' },
  // Autoguardado del borrador (lo corre el padre): idle|pending|saving|saved|error.
  autosaveState: { type: String, default: 'idle' }
})
const emit = defineEmits([
  'save', 'discard', 'navigate', 'update:dirty', 'update:theme', 'update:layout',
  'publish', 'discard-draft', 'restore', 'share', 'load-versions'
])

// ---------------------------------------------------------------------------
// Borrador siteTheme
// ---------------------------------------------------------------------------
// Punto de guardado: lo que devuelve el servidor (semilla + el BORRADOR
// persistido — site_theme_draft, con caída al publicado para filas viejas
// sin draft) o, tras un save OK, la copia optimista (savedOverride).
const seed = computed(() => mergeTheme(
  seedStudioTheme(props.customization || {}),
  props.customization?.site_theme_draft || props.customization?.site_theme || {}
))
const savedOverride = ref(null)
// savedTheme viaja parcial (solo lo que el usuario fijó): se resuelve contra
// los defaults para comparar y restaurar con el esquema completo.
const base = computed(() => (
  savedOverride.value
  || (props.savedTheme ? resolveSiteTheme(props.savedTheme) : resolveSiteTheme(seed.value))
))
// draft.layout = layout_config de ensayo (contrato); draft.template =
// plantilla en prueba (puede ser de un nivel superior al plan — la preview
// la muestra igual; el backend gatea al guardar). null = lo guardado.
const savedLayout = ref(clone(
  props.customization?.layout_config_draft || props.customization?.layout_config || null
))
const draft = reactive({
  // initialTheme puede venir parcial (es el emit del mount anterior): se
  // mergea sobre la semilla guardada y se resuelve, así los paneles y el
  // historial trabajan siempre con el esquema completo.
  theme: resolveSiteTheme(mergeTheme(seed.value, props.initialTheme || {})),
  // El ensayo emitido antes del remount (initialExtras) tiene prioridad
  // sobre el guardado: el usuario no pierde un "Probar" al cambiar de tab.
  layout: clone(props.initialExtras?.layout_config ?? savedLayout.value),
  template: props.initialExtras?.template || null
})
// ---------------------------------------------------------------------------
// Campos que el borrador toca DE VERDAD ('seccion.clave'). La vista previa
// solo pisa los tokens de esos campos; el resto conserva el look de la
// plantilla (una tienda sin tema se ve igual que hoy, y un tema parcial no
// aplasta los radios/fuentes propios de riso, bloque, terra…).
// Semilla: lo guardado + los campos que ya persiste el form (acento/fuente)
// + todo lo que difiera de los defaults del contrato.
// ---------------------------------------------------------------------------
const explicit = ref(new Set())
let lastThemeJson = '{}'
// Bloques anidados que viajan como UNA decisión (juego de colores por modo).
const ATOMIC_SECTIONS = new Set(['styleColors', 'style'])
function seedExplicit() {
  const stored = props.customization?.site_theme_draft || props.customization?.site_theme || {}
  const set = themeExplicitKeys(stored)
  ;['palette.primary', 'palette.secondary', 'palette.accent', 'typography.heading', 'typography.body']
    .forEach((k) => set.add(k))
  const defaults = resolveSiteTheme({})
  for (const section of Object.keys(draft.theme || {})) {
    if (ATOMIC_SECTIONS.has(section)) {
      if (draft.theme[section]) set.add(section)
      continue
    }
    for (const key of Object.keys(defaults[section] || {})) {
      if (JSON.stringify(draft.theme[section]?.[key]) !== JSON.stringify(defaults[section][key])) {
        set.add(`${section}.${key}`)
      }
    }
  }
  explicit.value = set
  lastThemeJson = JSON.stringify(draft.theme)
}
seedExplicit()
watch(() => JSON.stringify(draft.theme), () => {
  const prev = lastThemeJson ? JSON.parse(lastThemeJson) : {}
  for (const section of Object.keys(draft.theme || {})) {
    if (ATOMIC_SECTIONS.has(section)) {
      if (JSON.stringify(prev?.[section]) !== JSON.stringify(draft.theme[section])) explicit.value.add(section)
      continue
    }
    for (const key of Object.keys(draft.theme[section] || {})) {
      if (JSON.stringify(prev?.[section]?.[key]) !== JSON.stringify(draft.theme[section]?.[key])) {
        explicit.value.add(`${section}.${key}`)
      }
    }
  }
  lastThemeJson = JSON.stringify(draft.theme)
})
const themeDirty = computed(() => JSON.stringify(draft.theme) !== JSON.stringify(base.value))
const layoutDirty = computed(() =>
  draft.template !== null || JSON.stringify(draft.layout) !== JSON.stringify(savedLayout.value)
)

// El borrador del servidor cambió (save propio, discard, restore):
// resembrar completo.
watch(() => JSON.stringify(props.customization?.site_theme_draft || {}), () => {
  savedOverride.value = null
  draft.theme = resolveSiteTheme(seed.value)
  seedExplicit()
})
// Igual cuando el padre marca un nuevo punto de guardado estable.
watch(() => props.savedTheme, (t) => { if (t) savedOverride.value = null })
// Layout del borrador que cambió afuera (otro tab/editor/discard): resembrar
// solo si no hay ensayo en curso — un preset aplicado y todavía no guardado
// no se pisa por un refresh del store.
watch(() => JSON.stringify(props.customization?.layout_config_draft || null), (j) => {
  const wasClean = !layoutDirty.value
  savedLayout.value = j ? JSON.parse(j) : null
  if (wasClean) draft.layout = clone(savedLayout.value)
})
// Cambios guardados de la semilla (acento/fuente): se reinyectan al draft
// sin pisar el resto de las secciones (radios, sombras, botones...).
watch(() => [props.customization?.accent, props.customization?.accent_custom, props.customization?.name_font], () => {
  const s = resolveSiteTheme(seed.value)
  ;['primary', 'secondary', 'accent'].forEach((k) => { draft.theme.palette[k] = s.palette[k] })
  draft.theme.typography.heading = s.typography.heading
  draft.theme.typography.body = s.typography.body
})
// Los campos de diseño ya persistibles (acento, fuente del nombre) se
// editan en Estilos y se reflejan acá: el tema del borrador los sigue.
// Cada campo inyecta solo su grupo: un cambio de acento no toca la
// tipografía (un preset puede llevar heading distinto a la fuente del
// nombre y no se pierde al recolorear).
// suppressFormTheme silencia estas inyecciones un ciclo: al descartar, el
// padre revierte los campos del form y el borrador vuelve al baseline
// guardado — reinyectar ahí desharía esa restauración.
let suppressFormTheme = false
watch(() => [props.form.accent, props.form.accent_custom], () => {
  if (suppressFormTheme) return
  const patch = formThemePatch(props.form)
  Object.assign(draft.theme.palette, patch.palette)
  // El acento elegido en Ajustes rápidos se fusiona con la paleta del
  // estilo: pinta enlaces/primario sin tocar contenedores ni fuentes.
  const block = draft.theme.styleColors
  if (!block) return
  for (const mode of ['light', 'dark']) {
    const set = block[mode]
    if (!set?.containers) continue
    let link = fixContrast(patch.palette.accent, set.containers.bg, 4.5)
    link = fixContrast(link, set.containers.surface, 4.5)
    set.fonts.link = link
  }
})
watch(() => props.form.name_font, (f, prev) => {
  if (suppressFormTheme || !f) return
  // El título sigue a la fuente principal solo mientras no se haya elegido
  // uno distinto en Tipografía (los pares título/cuerpo no se desarman).
  if (draft.theme.typography.heading === prev) draft.theme.typography.heading = f
  draft.theme.typography.body = f
})

// ---------------------------------------------------------------------------
// Historial (60 pasos, coalescing) — snapshots de campos de diseño + tema.
// ---------------------------------------------------------------------------
const LOOK_FIELDS = [
  'display_name', 'headline', 'description', 'show_about', 'show_gallery', 'show_highlights',
  'show_offers', 'show_brands', 'show_countdown', 'contact_email', 'show_contact', 'theme',
  'whatsapp', 'instagram', 'tiktok', 'facebook', 'name_font', 'name_font_size', 'accent',
  'accent_custom', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay', 'cover_focus_x',
  'cover_focus_y', 'template', 'show_location'
]
function snapshot() {
  const f = {}
  LOOK_FIELDS.forEach((k) => { f[k] = clone(props.form[k]) })
  return { f, t: clone(draft.theme), l: clone(draft.layout), pt: draft.template }
}
function applySnapshot(snap) {
  LOOK_FIELDS.forEach((k) => { props.form[k] = clone(snap.f[k]) })
  draft.theme = clone(snap.t)
  draft.layout = clone(snap.l === undefined ? savedLayout.value : snap.l)
  draft.template = snap.pt === undefined ? null : snap.pt
  // El historial restaura el esquema completo: recalcular qué campos fija el
  // borrador para que la preview vuelva a pisar exactamente lo mismo que la
  // web publicada (los cambios deshechos dejan de viajar).
  seedExplicit()
  // El modo del visor sigue al tema restaurado (un preset oscuro no deja
  // la página pintada de noche después de Deshacer).
  viewerTheme.value = props.form.theme === 'dark' ? 'dark' : 'light'
}
const history = useStudioHistory({ max: 60 })
const { canUndo, canRedo } = history
history.reset(snapshot())
watch(() => JSON.stringify(snapshot()), () => history.observe(snapshot()))
function undo() { const s = history.undo(); if (s) applySnapshot(s) }
function redo() { const s = history.redo(); if (s) applySnapshot(s) }
const anyDirty = computed(() => themeDirty.value || layoutDirty.value || props.dirty)
// Estado de la savebar: prioridad a lo que está pasando ahora (guardando /
// error) y después a si hay cambios o borrador sin publicar.
const saveStateLabel = computed(() => {
  if (props.autosaveState === 'saving') return 'Guardando borrador…'
  if (props.autosaveState === 'error') return 'No se pudo guardar: revisá la conexión'
  if (anyDirty.value) return 'Cambios sin guardar'
  if (props.autosaveState === 'saved') return 'Borrador guardado'
  if (props.hasUnpublished) return 'Borrador sin publicar'
  return 'Todo guardado'
})

// Dirty combinado del Studio (tema + ensayo de layout/plantilla) y valores
// vigentes para el payload del padre (saveDesign arma site_theme y, con
// ensayo, layout_config + template).
watch(() => themeDirty.value || layoutDirty.value, (v) => emit('update:dirty', v), { immediate: true })
// Al padre viaja el tema PARCIAL (solo los campos que el usuario fijó): el
// backend mergea sobre lo guardado y la web publicada aplica exactamente los
// mismos tokens que el lienzo. Mandar el tema resuelto completo convertiría
// los defaults en decisiones y aplastaría el look propio de cada plantilla.
function pruneTheme(theme, keys) {
  const out = {}
  for (const [section, content] of Object.entries(theme || {})) {
    if (ATOMIC_SECTIONS.has(section)) {
      if (keys.has(section) && content && Object.keys(content).length) out[section] = content
      continue
    }
    const kept = {}
    for (const [key, value] of Object.entries(content || {})) {
      if (keys.has(`${section}.${key}`)) kept[key] = value
    }
    if (Object.keys(kept).length) out[section] = kept
  }
  return out
}
watch(() => JSON.stringify(draft.theme), () => emit('update:theme', pruneTheme(draft.theme, explicit.value)), { immediate: true })
// Solo se emite layout_config cuando el ensayo difiere de lo guardado:
// reenviar el layout intacto en un save de diseño cualquiera expone los
// bloques canónicos que el borrador preserva verbatim a la poda del backend.
watch(() => JSON.stringify([draft.layout, draft.template]), () => emit('update:layout', {
  layout_config: JSON.stringify(draft.layout) !== JSON.stringify(savedLayout.value) ? clone(draft.layout) : null,
  template: draft.template
}), { immediate: true })

// Vuelta del borrador al baseline guardado (Descartar / cerrar sin
// guardar). La supresión de las inyecciones form->tema dura hasta el
// próximo tick: los watchers del revert del form flushean antes que el
// callback y quedarían pisando el tema recién restaurado.
function resetDraftToBase() {
  suppressFormTheme = true
  draft.theme = clone(base.value)
  draft.layout = clone(savedLayout.value)
  draft.template = null
  trial.value = null
  viewerTheme.value = props.form.theme === 'dark' ? 'dark' : 'light'
  seedExplicit()
  nextTick(() => { suppressFormTheme = false })
}
function discard() {
  emit('discard')                 // el padre revierte los campos de `form`
  savedOverride.value = null
  resetDraftToBase()
  nextTick(() => history.reset(snapshot()))
}
function markSaved() {
  savedOverride.value = clone(draft.theme)
  savedLayout.value = clone(draft.layout)
  draft.template = null
  trial.value = null
  history.reset(snapshot())
}
function discardDraft() {
  resetDraftToBase()
  nextTick(() => history.reset(snapshot()))
}

// ---------------------------------------------------------------------------
// Vista previa en vivo (postMessage del contrato, debounce 60 ms)
// ---------------------------------------------------------------------------
const canvasRef = ref(null)
const device = ref('desktop')
const rotated = ref(false)
const zoom = ref(100)
const viewerTheme = ref(props.customization?.theme === 'dark' ? 'dark' : 'light')
// El lienzo sigue al tema de la página cuando se cambia desde cualquier
// control (Estilos, Colores, Personalización avanzada). El modo del visor
// del panel Colores no toca form.theme, así que no se pisa solo.
watch(() => props.form.theme, (t) => {
  if (t !== 'light' && t !== 'dark') return
  viewerTheme.value = t
  // Cambiar claro/oscuro reescribe la paleta al modo pedido: sin esto un
  // preset claro con la página en oscuro dejaba el fondo blanco.
  const hasPalette = ['palette.bg', 'palette.surface', 'palette.text']
    .some((k) => explicit.value.has(k))
  if (!hasPalette) return
  const next = adaptPalette(draft.theme.palette, t)
  if (next) Object.assign(draft.theme.palette, next)
})
const comparing = ref(false)
const allowedTemplates = computed(() => allowedTemplatesFor(props.benefits || {}))
// Plantilla vigente del borrador: manda el select de Estilos (`form.template`)
// para que la preview siga al control en vivo; el ensayo (`draft.template`)
// gana si existe y `template_draft` queda solo como respaldo de un borrador
// viejo que el form todavía no refleja.
const liveTemplate = computed(() => resolveStoreTemplate(
  draft.template || props.form.template || props.customization?.template_draft || props.customization?.template,
  allowedTemplates.value
))
const canFlyers = computed(() => Boolean(props.benefits?.has_flyers))
const frameDoc = () => canvasRef.value?.iframeEl?.contentDocument || null

// Campos del form que la web pública pinta en el cromo/identidad. Viajan
// en el update (aditivo al contrato) para que el lienzo muestre al instante
// lo que hasta ahora solo aparecía al guardar: tamaño del nombre, portada,
// velo/punto focal, logo, modo del logo y copy de las secciones.
const PREVIEW_FORM_KEYS = [
  'display_name', 'name_font', 'name_font_size', 'headline', 'description',
  'about_title', 'about_text', 'about_years', 'about_mission', 'about_specialties',
  'show_about', 'theme', 'accent', 'accent_custom', 'logo_scale', 'logo_mode',
  'mono_style', 'cover_overlay', 'cover_focus_x', 'cover_focus_y', 'template',
  'whatsapp', 'instagram', 'tiktok', 'facebook', 'contact_email', 'footer_text',
  'catalog_note', 'show_location', 'show_gallery', 'show_catalog', 'show_contact',
  'show_services', 'services_title', 'show_stats', 'show_testimonials',
  'show_faq', 'show_hours', 'show_cta', 'cta_title', 'cta_text', 'cta_label',
  'show_announcements', 'show_video', 'video_url', 'video_title',
  'show_benefits', 'show_timeline', 'show_team', 'show_offers', 'show_brands',
  'show_countdown', 'show_highlights', 'site_templates'
]
const previewCustom = computed(() => {
  const out = {}
  for (const key of PREVIEW_FORM_KEYS) out[key] = props.form[key]
  // Logo/portada viven en la customization (subida aparte del form).
  out.logo = props.customization?.logo || null
  out.cover = props.customization?.cover || null
  return out
})
// Mismo objeto desde lo GUARDADO: "Comparar" muestra el antes real (campos
// persistidos + layout + tema), no solo el tema del borrador.
const savedCustom = computed(() => {
  const out = {}
  for (const key of PREVIEW_FORM_KEYS) out[key] = props.customization?.[key]
  out.logo = props.customization?.logo || null
  out.cover = props.customization?.cover || null
  return out
})

let postTimer = null
function buildUpdate() {
  const showSaved = comparing.value
  const msg = studioUpdate({
    theme: showSaved ? base.value : draft.theme,
    // clone(): el layout de la store es un proxy reactivo — postMessage no
    // puede structured-clonar proxies (DataCloneError). draft.layout es el
    // layout de ensayo (preset) o el guardado; draft.template permite
    // previsualizar plantillas de otro nivel sin tocar form.template.
    layout: clone((showSaved ? savedLayout.value : draft.layout) || {}),
    template: showSaved
      ? (props.customization?.template || liveTemplate.value)
      : (draft.template || liveTemplate.value),
    device: device.value
  })
  msg.mode = viewerTheme.value // aditivo al contrato: claro/oscuro del visor
  // Aditivo al contrato: campos que el borrador fija. La preview solo pisa
  // esos tokens (fidelidad exacta con la web publicada, que guarda el parcial).
  msg.explicit = [...explicit.value]
  // Aditivo al contrato: identidad/cromo del form para la vista previa.
  msg.custom = clone(showSaved ? savedCustom.value : previewCustom.value)
  return msg
}
function postNow() {
  const el = canvasRef.value?.iframeEl
  const win = el?.contentWindow
  if (!win) return
  // El targetOrigin sale del src real del iframe: si la URL fuera absoluta
  // y de otro origen, postear al origin del host descarta el mensaje mudo.
  const origin = el?.src ? new URL(el.src, window.location.href).origin : window.location.origin
  win.postMessage(buildUpdate(), origin)
}
function queueUpdate() {
  clearTimeout(postTimer)
  postTimer = setTimeout(postNow, 60)
}
watch(
  () => JSON.stringify([
    draft.theme, draft.layout, draft.template, comparing.value, device.value,
    viewerTheme.value, liveTemplate.value, previewCustom.value, savedCustom.value
  ]),
  queueUpdate
)

let cleanupBridge = null
function onFrameLoad(iframe) {
  cleanupBridge?.()
  cleanupBridge = installPreviewBridge(iframe, {
    onPick,
    onBlockedNav: () => showToast('En la vista previa los enlaces no navegan. Usá “Abrir en pestaña nueva”.')
  })
  postNow()
  syncFontLink(frameDoc(), props.form.name_font || draft.theme.typography.heading)
}
watch(() => props.form.name_font, (f) => { ensureStoreFont(f); syncFontLink(frameDoc(), f) })
watch(() => [draft.theme.typography.heading, draft.theme.typography.body], ([h, b]) => {
  syncFontLink(frameDoc(), h)
  if (b && b !== h) syncFontLink(frameDoc(), b)
})

// ---------------------------------------------------------------------------
// Presets ("Estilos"): probar = ensayo deshacible del look completo;
// aplicar = lo mismo pero queda en el borrador (el Guardar de la barra lo
// persiste); combinar = una sola pieza del preset (paleta / tipografía /
// distribución) sin tocar el resto del borrador.
// El `trial` guarda el snapshot previo al primer ensayo de la sesión:
// "Deshacer" vuelve exactamente ahí, "Quedarla" solo cierra el modo prueba.
// ---------------------------------------------------------------------------
const trial = ref(null) // {id, palette, snap}
const tryingId = computed(() => trial.value?.id || null)
const tryingPalette = computed(() => trial.value?.palette || 'original')

async function applyPreset(p, part = 'all') {
  const t = resolveSiteTheme(p.theme)
  const all = part === 'all'
  const advanced = Boolean(props.benefits?.has_design_advanced)
  // (1) Los campos persistibles se escriben primero y en el mismo gesto:
  // el watcher form->theme corre en el siguiente flush, así si el preset
  // se aplica DESPUÉS de nextTick su versión de palette/typography gana.
  if (all) {
    let accent = t.palette.accent
    if (advanced) {
      props.form.accent_custom = accent
    } else {
      // Sin diseño avanzado el acento libre no viaja: se mapea al slug
      // más cercano del catálogo base. accent_custom queda intacto (un
      // valor guardado en otra época de plan se conserva, no se pisa) y
      // sigue mandando: es el que la web publicada va a pintar.
      const slug = nearestAccent(hexToRgb(accent), STORE_ACCENTS)
      if (slug) props.form.accent = slug
      accent = formThemePatch(props.form).palette.accent
    }
    // La vista previa se pinta con el acento que de verdad se persiste: el
    // slug cuando el plan no lleva acento libre (si no, el ensayo se vería
    // con un color que el Guardar descarta).
    if (accent !== t.palette.accent) {
      t.palette = { ...t.palette, primary: accent, accent, secondary: deriveAccent(accent).ink }
    }
    props.form.name_font = t.typography.body
    props.form.theme = p.pageTheme || 'light'
    draft.layout = clone(p.layout)
    draft.template = p.template
  } else if (part === 'layout') {
    // La distribución se re-expande sobre la plantilla vigente (la en
    // ensayo o la guardada): los ids que la plantilla no soporta quedan
    // fuera en vez de ensuciar la config.
    draft.layout = clone(layoutForTemplate(p, draft.template || liveTemplate.value))
  }
  await nextTick()
  if (all || part === 'palette') draft.theme.palette = clone(t.palette)
  if (all || part === 'typography') draft.theme.typography = clone(t.typography)
  if (all) {
    ;['containers', 'buttons', 'background', 'motion', 'mobile'].forEach((k) => {
      draft.theme[k] = clone(t[k])
    })
    // Juego de colores del estilo (fuentes + contenedores) en ambos modos
    // con su paleta original, y el id del preset: es lo único que el plan
    // Básico persiste.
    draft.theme.styleColors = clone(styleColorsBlock(t.palette))
    draft.theme.style = { id: p.id }
    viewerTheme.value = p.pageTheme || 'light'
  }
  if (all || part === 'typography') {
    ensureStoreFont(t.typography.heading)
    ensureStoreFont(t.typography.body)
    syncFontLink(frameDoc(), t.typography.heading)
    syncFontLink(frameDoc(), t.typography.body)
  }
}

// Paleta de color del estilo activo: pinta contenedores/fuentes y fusiona el
// acento elegido en Ajustes rápidos (no lo pisa).
function applyPalette(p, paletteId = 'original') {
  const t = resolveSiteTheme(p.theme)
  const accent = formThemePatch(props.form).palette.accent
  draft.theme.styleColors = clone(styleColorsBlock(t.palette, paletteId, accent))
  draft.theme.style = { id: p.id, ...(paletteId !== 'original' ? { palette: paletteId } : {}) }
}

function tryPreset(p) {
  if (!trial.value) trial.value = { id: p.id, palette: 'original', snap: snapshot() }
  else trial.value = { ...trial.value, id: p.id, palette: 'original' }
  applyPreset(p, 'all')
}
function tryPalette(p, paletteId) {
  if (!trial.value) trial.value = { id: p.id, palette: paletteId, snap: snapshot() }
  else trial.value = { ...trial.value, id: p.id, palette: paletteId }
  applyPalette(p, paletteId)
}
function revertTrial() {
  if (!trial.value) return
  applySnapshot(trial.value.snap)
  trial.value = null
}
function keepTrial() { trial.value = null }
async function applyAndSave(p) {
  trial.value = null
  await applyPreset(p, 'all')
  emit('save')
}

provide('studioPresets', {
  presets: designPresets,
  tryingId,
  tryingPalette,
  // Estilo y paleta que ya están en el borrador (también después de
  // "Quedarla"): el selector del panel sigue mostrando lo elegido aunque
  // todavía no se haya guardado.
  draftStyleId: computed(() => draft.theme.style?.id || ''),
  draftPalette: computed(() => draft.theme.style?.palette || 'original'),
  lockOf: (p) => presetLock(p, props.benefits),
  tryIt: tryPreset,
  tryPalette,
  apply: applyPreset,
  applyAndSave,
  revertTrial,
  keepTrial,
  goPlans: () => emit('navigate', 'plans')
})

// Handshake del iframe: al montar (o tras recargar) pide el estado vigente.
function onMessage(e) {
  if (e.source !== canvasRef.value?.iframeEl?.contentWindow) return
  if (!isStudioMessage(e.data)) return
  if (e.data.type === STUDIO_MSG.READY) postNow()
}
onMounted(() => {
  window.addEventListener('message', onMessage)
  loadDesignCatalog(true).then(() => {
    // Tienda sin layout propio: el ensayo arranca con el layout del patrón
    // de diseño de la base (las plantillas ya no traen secciones por defecto).
    if (savedLayout.value || draft.layout) return
    const base = normalizeLayoutConfig(defaultPattern.value?.layout)
    if (!Object.keys(base).length) return
    savedLayout.value = clone(base)
    draft.layout = clone(base)
  })
})
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  cleanupBridge?.()
  clearTimeout(postTimer)
  history.dispose()
})

// Click en la preview -> herramienta + control del panel (foco + flash).
const tool = ref('colores')
// El Studio es exclusivo de Premium (has_design_advanced, guard de la ruta):
// el riel muestra todas las herramientas sin candados por plan.
// Riel agrupado (Look / Estructura / Puesta a punto): un solo lugar para
// saber dónde está cada ajuste sin perder las 11 herramientas.
const toolGroups = computed(() => STUDIO_TOOL_GROUPS
  .map((g) => ({ ...g, items: g.tools.map((id) => STUDIO_TOOLS.find((t) => t.id === id)).filter(Boolean) }))
  .filter((g) => g.items.length))
const panelBodyEl = ref(null)
const toolDef = computed(() => (
  STUDIO_TOOLS.find((t) => t.id === tool.value) || STUDIO_TOOLS[0]
))
function onPick(target) {
  // Un click en la preview abre la herramienta del target; si el id no
  // existe caemos a Colores para que el panel nunca quede vacío.
  if (!pickTool(toolForTarget(target))) pickTool('colores')
  nextTick(() => {
    const css = target?.startsWith('blk:') || target?.startsWith('sec:') ? 'blk' : target
    const field = panelBodyEl.value?.querySelector(`[data-focus="${css}"]`)
    if (!field) return
    field.classList.add('sts-flash')
    field.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    field.querySelector('input, select, button, [tabindex]')?.focus({ preventScroll: true })
    setTimeout(() => field.classList.remove('sts-flash'), 1400)
  })
}

// Al editar un control con data-focus -> anillo animado en el elemento.
let lastRing = 0
function ringTarget(target) {
  const now = Date.now()
  if (now - lastRing < 350) return
  lastRing = now
  applyFocusRing(frameDoc(), target)
}
function onPanelEvent(e) {
  const field = e.target?.closest?.('[data-focus]')
  if (field) ringTarget(field.dataset.focus)
}

// ---------------------------------------------------------------------------
// Layout responsive del propio Studio
// ---------------------------------------------------------------------------
const isMobile = ref(false)
const panelOpen = ref(true)
const sheetSize = ref('mid')   // min | mid | max
const fullscreen = ref(false)
let mq = null
function onMq() {
  isMobile.value = mq.matches
  if (!isMobile.value) sheetDrag.value = null
}
onMounted(() => {
  mq = window.matchMedia('(max-width: 768px)')
  onMq()
  mq.addEventListener('change', onMq)
})
onBeforeUnmount(() => mq?.removeEventListener('change', onMq))

// Bottom sheet arrastrable: alturas fijas (mínima=header, media, alta).
const SHEET_PX = { min: 64, mid: 0.45, max: 0.8 }
const sheetPx = computed(() => {
  const vh = window.innerHeight || 800
  const h = sheetSize.value === 'min' ? SHEET_PX.min : Math.round(vh * SHEET_PX[sheetSize.value])
  return sheetDragPx.value ?? h
})
const sheetDragPx = ref(null)
const sheetDrag = ref(null)
function sheetDown(e) {
  if (!isMobile.value || e.target.closest('button')) return
  sheetDrag.value = { y0: e.clientY, h0: sheetPx.value }
  e.currentTarget.setPointerCapture?.(e.pointerId)
}
function sheetMove(e) {
  if (!sheetDrag.value) return
  const vh = window.innerHeight || 800
  const h = sheetDrag.value.h0 - (e.clientY - sheetDrag.value.y0)
  sheetDragPx.value = Math.max(SHEET_PX.min, Math.min(Math.round(vh * SHEET_PX.max), h))
}
function sheetUp() {
  if (!sheetDrag.value) return
  const vh = window.innerHeight || 800
  const stops = [['min', SHEET_PX.min], ['mid', vh * SHEET_PX.mid], ['max', vh * SHEET_PX.max]]
  const h = sheetDragPx.value ?? sheetDrag.value.h0
  sheetSize.value = stops.sort((a, b) => Math.abs(a[1] - h) - Math.abs(b[1] - h))[0][0]
  sheetDrag.value = null
  sheetDragPx.value = null
}
function pickTool(id) {
  const def = STUDIO_TOOLS.find((t) => t.id === id)
  if (!def) return false
  tool.value = id
  panelOpen.value = true
  if (isMobile.value && sheetSize.value === 'min') sheetSize.value = 'mid'
  return true
}
// El panel Móvil siempre edita mirando la vista móvil (requisito del panel:
// la vista previa chica queda visible mientras se ajusta).
watch(tool, (t) => { if (t === 'movil') device.value = 'mobile' })

// 'navigate' con un id de herramienta = saltar dentro del Studio (los CTAs
// de los locks apuntan a paneles p.ej. Avanzado); el resto sube al Dashboard.
const TOOL_IDS = new Set(STUDIO_TOOLS.map((t) => t.id))
function onPanelNav(target) {
  if (TOOL_IDS.has(target)) pickTool(target)
  else emit('navigate', target)
}

// ---------------------------------------------------------------------------
// "Salud de tu web": los arreglos con fix automático se aplican al borrador
// (paleta/tema/bloque); los de contenido navegan a su sección.
// El layout se resuelve con la MISMA caída que usa StudioPanel, y cada fix
// devuelve si hubo un cambio real: sin cambio no hay toast de éxito.
// ---------------------------------------------------------------------------
function resolvedLayout() {
  return draft.layout || props.customization?.layout_config_draft || props.customization?.layout_config || null
}
// ---------------------------------------------------------------------------
// Distribución: reordenar, apagar/encender y cambiar variantes de bloque.
// Escribe `draft.layout` (el ensayo que viaja a la preview por postMessage y
// al save como layout_config_draft). Se sanea con el mismo normalizador que
// usa el front público, así el orden que ves es el que se guarda.
// ---------------------------------------------------------------------------
function draftBlocks(surface) {
  if (!draft.layout) draft.layout = clone(resolvedLayout() || {})
  if (!draft.layout?.[surface]) return []
  if (!Array.isArray(draft.layout[surface].blocks)) draft.layout[surface].blocks = []
  return draft.layout[surface].blocks
}
function commitLayout(surface) {
  // El orden del array es la intención: se reescribe `order` antes de
  // normalizar (normalizeLayoutConfig ordena por ese campo).
  for (const s of Object.values(draft.layout || {})) {
    if (Array.isArray(s?.blocks)) s.blocks = s.blocks.map((b, i) => ({ ...b, order: i }))
  }
  draft.layout = normalizeLayoutConfig(draft.layout)
  // normalizeLayoutConfig descarta superficies sin bloques: si el usuario
  // acaba de dejar una vacía, se conserva el objeto vacío para no perderla
  // de la vista (la preview cae al patrón igual).
  if (!draft.layout[surface]) draft.layout[surface] = { blocks: [] }
}
function moveBlock({ surface, from, to }) {
  const blocks = draftBlocks(surface)
  if (!blocks.length || from === to || to < 0 || to >= blocks.length) return
  const list = blocks.slice()
  const [item] = list.splice(from, 1)
  if (!item) return
  list.splice(to, 0, item)
  draft.layout[surface].blocks = list
  commitLayout(surface)
}
function toggleBlock({ surface, id }) {
  const block = draftBlocks(surface).find((b) => b && b.id === id)
  if (!block) return
  const spec = blockSpec(surface, id)
  if (spec?.locked) { showToast('Esa sección es fija: no se puede ocultar'); return }
  block.enabled = block.enabled === false
  commitLayout(surface)
}
function setBlockVariant({ surface, id, variant }) {
  const block = draftBlocks(surface).find((b) => b && b.id === id)
  if (!block) return
  const spec = blockSpec(surface, id)
  const options = spec?.variants ? Object.keys(spec.variants) : []
  if (!options.includes(variant)) return
  // La primera variante es la default: no se guarda (queda implícita).
  if (variant === options[0]) delete block.variant
  else block.variant = variant
  commitLayout(surface)
}
function resetLayout() {
  draft.layout = clone(savedLayout.value)
  draft.template = null
  showToast('Distribución restaurada al borrador guardado')
}

// El acento/primario tocado por un fix de Salud se espeja al campo
// persistido (como ColorsPanel.setRole): sin plan premium se mapea al slug
// más cercano que siga cumpliendo el contraste.
function syncHealthAccent(palette) {
  const hex = normalizeHex(palette?.primary || palette?.accent)
  if (!hex) return
  if (props.benefits?.has_design_advanced) {
    props.form.accent_custom = hex
    return
  }
  const passing = Object.entries(STORE_ACCENTS).filter(([, a]) =>
    palettePasses({ ...palette, primary: a.hex, accent: a.hex })
  )
  if (!passing.length) return
  const slug = nearestAccent(hexToRgb(hex), Object.fromEntries(passing))
  if (!slug) return
  props.form.accent = slug
  props.form.accent_custom = ''
}
function applyHealthFix(fix) {
  if (!fix) return false
  if (fix.kind === 'palette') {
    // Se recalcula sobre la paleta VIVA (no sobre el snapshot del análisis):
    // si el usuario tocó un color entre el análisis y el click, el arreglo
    // sigue convergiendo y nunca rompe un par que ya cumplía.
    const values = fix.values
      ? repairPalette(draft.theme.palette)
      : (fix.key ? { [fix.key]: fix.value } : null)
    if (!values) return false
    let changed = false
    for (const [key, value] of Object.entries(values)) {
      const hex = normalizeHex(value)
      if (!hex || draft.theme.palette[key] === hex) continue
      draft.theme.palette[key] = hex
      changed = true
    }
    if (!changed) { showToast('La paleta ya estaba corregida'); return false }
    syncHealthAccent(draft.theme.palette)
    showToast('Arreglo aplicado al borrador')
    return true
  }
  if (fix.kind === 'theme') {
    const group = draft.theme[fix.group]
    if (!group || !(fix.key in group)) { showToast('Ese ajuste no existe en este tema'); return false }
    if (group[fix.key] === fix.value) { showToast('Ese ajuste ya estaba aplicado'); return false }
    group[fix.key] = fix.value
    showToast('Arreglo aplicado al borrador')
    return true
  }
  if (fix.kind === 'block') {
    if (!draft.layout) draft.layout = clone(resolvedLayout())
    const block = draft.layout?.[fix.surface]?.blocks?.find((x) => x && x.id === fix.id)
    if (!block) { showToast('No encontramos esa sección en tu diseño'); return false }
    if (block.enabled === false) { showToast('Esa sección ya estaba oculta'); return false }
    block.enabled = false
    showToast('Sección ocultada en el borrador')
    return true
  }
  return false
}

// ---------------------------------------------------------------------------
// Ayuda (?), búsqueda de ajustes (Ctrl+K) y onboarding de primera vez.
// ---------------------------------------------------------------------------
const showHelp = ref(false)
const showSearch = ref(false)
const showOnboard = ref(false)
const ONBOARD_KEY = 'davent.studio.seen.v1'
onMounted(() => {
  try { if (!window.localStorage.getItem(ONBOARD_KEY)) showOnboard.value = true } catch { /* sin storage: no se persiste */ }
})
function closeOnboarding() {
  showOnboard.value = false
  try { window.localStorage.setItem(ONBOARD_KEY, '1') } catch { /* idem */ }
}

// Índice de la búsqueda: herramientas + campos clave con su data-focus (el
// pick enfoca el control exacto como un click en la vista previa).
const SEARCH_INDEX = [
  { tool: 'colores',      focus: 'page',       label: 'Paleta y colores',             hint: 'Colores', kw: 'color paleta acento primario fondo texto' },
  { tool: 'colores',      focus: 'buttons',    label: 'Contraste accesible',          hint: 'Colores', kw: 'contraste aa legibilidad accesible' },
  { tool: 'tipografia',   focus: 'typo',       label: 'Fuentes y tipografía',         hint: 'Tipografía', kw: 'fuente letra tipografia texto peso escala' },
  { tool: 'contenedores', focus: 'card',       label: 'Bordes, sombras y tarjetas',   hint: 'Contenedores', kw: 'borde sombra radio tarjeta contenedor densidad' },
  { tool: 'contenedores', focus: 'buttons',    label: 'Botones',                      hint: 'Contenedores', kw: 'boton forma estilo cta' },
  { tool: 'fondo',        focus: 'page',       label: 'Fondo de la página',           hint: 'Fondo', kw: 'fondo degradado imagen patron mesh' },
  { tool: 'movil',        focus: 'chrome.nav', label: 'Navegación móvil',             hint: 'Móvil', kw: 'movil celular nav menu bottom drawer' },
  { tool: 'movil',        focus: 'hero',       label: 'Portada en celular',           hint: 'Móvil', kw: 'movil hero portada altura grilla' },
  { tool: 'movimiento',   focus: 'page',       label: 'Animaciones y revelado',       hint: 'Movimiento', kw: 'animacion movimiento reveal hover efecto' },
  { tool: 'folletos',     focus: null,         label: 'Folletos imprimibles',         hint: 'Folletos', kw: 'folleto flyer imprimir qr' },
  { tool: 'avanzado',     focus: 'page',       label: 'Tema claro u oscuro',          hint: 'Avanzado', kw: 'oscuro claro modo dark light tema' },
  { tool: 'avanzado',     focus: null,         label: 'Importar o exportar el tema',  hint: 'Avanzado', kw: 'json importar exportar tema backup archivo' },
  { tool: 'salud',        focus: null,         label: 'Salud de tu web',              hint: 'Salud', kw: 'salud revision contraste imagenes accesibilidad chequeo' },
  { tool: 'publicar',     focus: null,         label: 'Publicar, versiones y compartir', hint: 'Publicar', kw: 'publicar version historial restaurar compartir enlace link borrador' }
]
const searchEntries = computed(() => [
  ...STUDIO_TOOLS.map((t) => ({ id: `tool-${t.id}`, label: t.label, hint: t.desc, icon: t.icon, tool: t.id, focus: null, kw: t.label })),
  ...SEARCH_INDEX.map((e, i) => ({ id: `f-${i}`, icon: STUDIO_TOOLS.find((t) => t.id === e.tool)?.icon || 'sliders', ...e }))
])
function onSearchPick(entry) {
  if (!pickTool(entry.tool)) return
  if (!entry.focus) return
  nextTick(() => {
    const field = panelBodyEl.value?.querySelector(`[data-focus="${entry.focus}"]`)
    if (!field) return
    field.classList.add('sts-flash')
    field.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    field.querySelector('input, select, button, [tabindex]')?.focus({ preventScroll: true })
    setTimeout(() => field.classList.remove('sts-flash'), 1400)
  })
}

// ---------------------------------------------------------------------------
// Importar / exportar el tema (JSON validado por el contrato).
// ---------------------------------------------------------------------------
const fileToast = ref('')
let toastTimer = null
function showToast(msg) {
  clearTimeout(toastTimer)
  fileToast.value = msg
  toastTimer = setTimeout(() => { fileToast.value = '' }, 3400)
}
function exportTheme() {
  const payload = { app: 'davent', kind: 'site_theme', version: 1, theme: clone(draft.theme) }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `tema-${props.customization?.template || 'web'}.json`
  a.click()
  URL.revokeObjectURL(a.href)
  showToast('Tema exportado')
}
function importTheme(raw) {
  try {
    const data = JSON.parse(raw)
    const theme = data?.theme ?? data // acepta el formato exportado o un tema pelado
    if (!theme || typeof theme !== 'object' || Array.isArray(theme)) throw new Error('bad theme')
    const known = ['palette', 'containers', 'typography', 'buttons', 'background', 'motion', 'mobile', 'styleColors', 'style']
    if (!known.some((k) => theme[k] && typeof theme[k] === 'object')) throw new Error('empty theme')
    const resolved = resolveSiteTheme(theme)
    draft.theme = resolved
    viewerTheme.value = props.form.theme === 'dark' ? 'dark' : 'light'
    showToast('Tema importado al borrador')
  } catch {
    showToast('El archivo no es un tema válido (.json del Studio)')
  }
}

// ---------------------------------------------------------------------------
// Teclado: Ctrl+Z / Ctrl+Shift+Z (capture — también anula el undo interno de
// los paneles embebidos para que el historial sea único), Ctrl+S guarda el
// borrador, Ctrl+K busca, "?" abre la ayuda y Esc cierra en cascada.
// ---------------------------------------------------------------------------
function onKey(e) {
  if (e.key === 'Escape') {
    if (showSearch.value) { showSearch.value = false; return }
    if (showHelp.value) { showHelp.value = false; return }
    if (showOnboard.value) { showOnboard.value = false; return }
    if (fullscreen.value) { fullscreen.value = false }
    return
  }
  const inField = e.target?.closest?.('input, textarea, select, [contenteditable="true"]')
  if (!inField && e.key === '?') {
    e.preventDefault()
    showHelp.value = !showHelp.value
    return
  }
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return
  const k = e.key.toLowerCase()
  if (k === 'k') {
    e.preventDefault()
    e.stopPropagation()
    showSearch.value = !showSearch.value
    return
  }
  if (k === 's') {
    e.preventDefault()
    e.stopPropagation()
    emit('save')
    return
  }
  if (k !== 'z' && k !== 'y') return
  e.preventDefault()
  e.stopPropagation()
  if (k === 'y' || e.shiftKey) redo()
  else undo()
}
onMounted(() => window.addEventListener('keydown', onKey, true))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey, true)
  clearTimeout(toastTimer)
})

// Comparar antes/después: mantener presionado envía el tema guardado.
function compareStart() { comparing.value = true }
function compareEnd() { comparing.value = false }

function toggleFullscreen() { fullscreen.value = !fullscreen.value }
const rootEl = ref(null)

defineExpose({ markSaved, discardDraft, getTheme: () => clone(draft.theme) })
</script>

<template>
  <div
    ref="rootEl"
    class="sts"
    :class="{ 'is-full': fullscreen, 'panel-closed': !panelOpen, 'is-mobile': isMobile }"
    :style="isMobile ? { '--sheet-h': `${sheetPx}px` } : null"
  >
    <!-- ===== Riel de herramientas ===== -->
    <aside class="sts-rail" aria-label="Herramientas del Studio">
      <button
        type="button" class="sts-tool sts-back" title="Salir del Studio"
        aria-label="Salir del Studio" @click="emit('navigate', 'close')"
      >
        <AppIcon name="arrow-left" :size="19" />
        <span class="sts-tool-lb">Volver</span>
      </button>
      <div class="sts-rail-list" role="tablist" aria-orientation="vertical" aria-label="Herramientas de diseño">
        <template v-for="g in toolGroups" :key="g.id">
          <p class="sts-rail-cap" aria-hidden="true">{{ g.label }}</p>
          <button
            v-for="t in g.items" :key="t.id" type="button" role="tab"
            class="sts-tool" :class="{ active: tool === t.id }"
            :aria-selected="tool === t.id"
            :title="t.desc"
            @click="pickTool(t.id)"
          >
            <AppIcon :name="t.icon" :size="19" />
            <span class="sts-tool-lb">{{ t.label }}</span>
          </button>
        </template>
      </div>
      <button
        type="button" class="sts-tool sts-collapse" :aria-pressed="!panelOpen"
        :title="panelOpen ? 'Ocultar el panel' : 'Mostrar el panel'"
        @click="panelOpen = !panelOpen"
      >
        <AppIcon :name="panelOpen ? 'chevron-left' : 'chevron-right'" :size="18" />
        <span class="sts-tool-lb">{{ panelOpen ? 'Ocultar' : 'Panel' }}</span>
      </button>
    </aside>

    <!-- ===== Panel de ajustes / bottom sheet móvil ===== -->
    <section class="sts-panel" :aria-label="`Ajustes de ${toolDef.label}`">
      <header
        class="sts-panel-head"
        @pointerdown="sheetDown" @pointermove="sheetMove" @pointerup="sheetUp" @pointercancel="sheetUp"
      >
        <span class="sts-grip" aria-hidden="true"></span>
        <div class="sts-panel-title">
          <h2>{{ toolDef.label }}</h2>
          <p>{{ toolDef.desc }}</p>
        </div>
        <div class="sts-sheet-stops" role="group" aria-label="Altura del panel">
          <button
            v-for="s in [['min','Mínimo'],['mid','Medio'],['max','Alto']]" :key="s[0]" type="button"
            class="sts-stop" :class="{ active: sheetSize === s[0] }" :aria-pressed="sheetSize === s[0]"
            :title="`Panel ${s[1].toLowerCase()}`" @click.stop="sheetSize = s[0]"
          ><span class="sr-only">{{ s[1] }}</span></button>
        </div>
        <button type="button" class="sts-panel-x" title="Ocultar el panel" aria-label="Ocultar el panel" @click="panelOpen = false"><AppIcon name="chevron-left" :size="17" /></button>
      </header>
      <div
        ref="panelBodyEl" class="sts-panel-body" role="tabpanel"
        @focusin="onPanelEvent" @input="onPanelEvent" @change="onPanelEvent" @click="onPanelEvent"
      >
        <StudioPanel
          :tool="tool" :form="form" :theme="draft.theme" :benefits="benefits"
          :site-templates="siteTemplates" :layout="draft.layout || customization?.layout_config_draft || customization?.layout_config || null"
          :can-flyers="canFlyers" :shop-name="shopName"
          :customization="customization" :viewer="viewerTheme"
          :health-ctx="healthCtx"
          :has-unpublished="hasUnpublished" :local-dirty="anyDirty"
          :versions="versions" :versions-loading="versionsLoading" :action-busy="actionBusy"
          :share-url="shareUrl" :share-expires="shareExpires"
          @navigate="onPanelNav" @ring="ringTarget"
          @move-block="moveBlock" @toggle-block="toggleBlock"
          @variant-block="setBlockVariant" @reset-layout="resetLayout"
          @set-viewer="(v) => { if (v === 'light' || v === 'dark') viewerTheme = v }"
          @fix="applyHealthFix"
          @publish="emit('publish', $event)" @discard-draft="emit('discard-draft')"
          @restore="emit('restore', $event)" @share="emit('share')"
          @load-versions="emit('load-versions')"
          @export-theme="exportTheme" @import-theme="importTheme"
        />
      </div>
    </section>

    <!-- ===== Lienzo ===== -->
    <section class="sts-canvas" aria-label="Vista previa en vivo">
      <StudioCanvas
        ref="canvasRef"
        v-model:device="device" v-model:rotated="rotated" v-model:zoom="zoom" v-model:theme="viewerTheme"
        :src="previewUrl" :open-url="publicUrl" :fullscreen="fullscreen" :comparing="comparing"
        @load="onFrameLoad" @fullscreen="toggleFullscreen"
      />
    </section>

    <!-- ===== Barra de guardado ===== -->
    <footer class="sts-savebar">
      <p class="sts-state" :class="{ dirty: anyDirty, saving: autosaveState === 'saving', error: autosaveState === 'error' }" role="status" aria-live="polite">
        <span v-if="autosaveState === 'saving'" class="sts-spin" aria-hidden="true"></span>
        <span v-else-if="anyDirty" class="sts-dot" aria-hidden="true"></span>
        <AppIcon v-else name="circle-check" :size="15" aria-hidden="true" />
        <span>{{ saveStateLabel }}</span>
      </p>
      <div class="sts-hist">
        <button type="button" class="sts-opt" :disabled="!canUndo" title="Deshacer (Ctrl+Z)" aria-label="Deshacer" @click="undo"><AppIcon name="undo" :size="16" /></button>
        <button type="button" class="sts-opt" :disabled="!canRedo" title="Rehacer (Ctrl+Shift+Z)" aria-label="Rehacer" @click="redo"><AppIcon name="redo" :size="16" /></button>
        <button
          type="button" class="sts-opt sts-cmp" :disabled="!anyDirty" :aria-pressed="comparing"
          title="Mantené presionado para ver la versión guardada" aria-label="Comparar con la versión guardada"
          @pointerdown="compareStart" @pointerup="compareEnd" @pointerleave="compareEnd" @pointercancel="compareEnd"
          @keydown.space.prevent="compareStart" @keyup.space="compareEnd" @blur="compareEnd"
        ><AppIcon name="eye" :size="16" /><span class="sts-opt-lb">Comparar</span></button>
      </div>
      <div class="sts-hist sts-utils">
        <button type="button" class="sts-opt" title="Buscar ajustes (Ctrl+K)" aria-label="Buscar ajustes" @click="showSearch = true"><AppIcon name="search" :size="16" /></button>
        <button type="button" class="sts-opt" title="Ayuda y atajos (?)" aria-label="Ayuda y atajos" @click="showHelp = true"><AppIcon name="circle-help" :size="16" /></button>
      </div>
      <div class="sts-acts">
        <button type="button" class="btn ghost btn-auto sts-discard" :disabled="busy" @click="discard"><AppIcon name="undo" :size="15" /> <span class="sts-act-lb">Descartar</span></button>
        <button
          v-if="hasUnpublished && !anyDirty" type="button" class="btn secondary btn-auto"
          :disabled="actionBusy === 'publish'" title="Llevar el borrador guardado a tu web"
          @click="emit('publish', '')"
        ><AppIcon name="rocket" :size="15" /> <span class="sts-act-lb">Publicar</span></button>
        <AppButton :loading="busy" type="button" title="Guardar y publicar (Ctrl+S)" @click="emit('save')">
          <span class="sts-act-lb">Guardar y publicar</span><span class="sts-act-lb-short">Guardar</span>
        </AppButton>
      </div>
    </footer>

    <!-- ===== Overlays: ayuda (?), búsqueda (Ctrl+K), onboarding y toast ===== -->
    <StudioHelp v-if="showHelp" @close="showHelp = false" />
    <StudioSearch v-if="showSearch" :entries="searchEntries" @select="onSearchPick" @close="showSearch = false" />
    <StudioOnboarding v-if="showOnboard" @done="closeOnboarding" />
    <Transition name="sts-toast">
      <p v-if="fileToast" class="sts-toast" role="status"><AppIcon name="circle-check" :size="14" /> {{ fileToast }}</p>
    </Transition>
  </div>
</template>

<style scoped>
/* ===== Grid 3 zonas + savebar ===== */
.sts {
  --rail-w: 92px; --panel-w: 320px;
  position: relative; /* ancla de los overlays (ayuda, buscador, onboarding) */
  display: grid;
  grid-template-columns: var(--rail-w) var(--panel-w) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas: 'rail panel canvas' 'save save save';
  height: calc(100dvh - 150px); min-height: 520px;
  border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  background: var(--card);
}
.sts.is-full { position: fixed; inset: 0; z-index: 50; height: auto; min-height: 0; border-radius: 0; border: 0; }
.sts.panel-closed { grid-template-columns: var(--rail-w) 0 minmax(0, 1fr); }
.sts.panel-closed .sts-panel { overflow: hidden; border-right: 0; }

/* ===== Riel ===== */
.sts-rail {
  grid-area: rail; display: flex; flex-direction: column; justify-content: space-between;
  border-right: 1px solid var(--line); background: var(--surface); padding: 8px 6px;
}
.sts-rail-list { display: flex; flex-direction: column; gap: 2px; flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: none; }
.sts-tool {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  min-height: 52px; padding: 7px 2px 5px; border: 0; border-radius: 10px;
  background: transparent; color: var(--ink-2); font: inherit; font-size: 10px;
  font-weight: 600; cursor: pointer; transition: background .15s, color .15s;
}
.sts-tool:hover { color: var(--ink); background: var(--line-soft); }
.sts-tool.active { background: var(--brand-soft); color: var(--brand-ink); }
.sts-tool.locked { color: var(--muted); opacity: .72; }
.sts-tool.locked:hover { color: var(--ink-2); background: var(--line-soft); opacity: 1; }
.sts-tool-lock {
  position: absolute; top: 4px; right: 5px; padding: 1px;
  border-radius: 4px; background: var(--surface); color: var(--muted);
}
.sts-upsell { margin-bottom: 10px; }
.sts-tool:focus-visible { outline: 2px solid var(--brand-500); outline-offset: -2px; }
.sts-rail-cap { margin: 10px 0 2px; padding: 0 2px; font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); text-align: center; overflow-wrap: anywhere; }
.sts-rail-cap:first-child { margin-top: 2px; }
.sts-tool-lb { line-height: 1.1; text-align: center; hyphens: manual; overflow-wrap: anywhere; max-width: 100%; }
.sts-collapse { margin-top: 8px; color: var(--muted); }
.sts-back { display: none; color: var(--muted); }

/* ===== Panel ===== */
.sts-panel {
  grid-area: panel; display: flex; flex-direction: column; min-height: 0; min-width: 0;
  border-right: 1px solid var(--line); background: var(--card); transition: margin .2s ease;
}
.sts-panel-head {
  display: flex; align-items: center; gap: 10px; padding: 14px 14px 12px;
  border-bottom: 1px solid var(--line); flex: none;
}
.sts-grip { display: none; }
.sts-panel-title { min-width: 0; flex: 1; }
.sts-panel-title h2 { margin: 0; font-size: 15px; font-weight: 700; }
.sts-panel-title p { margin: 2px 0 0; font-size: 11.5px; color: var(--muted); line-height: 1.35; }
.sts-panel-x {
  display: none; flex: none; align-items: center; justify-content: center;
  width: 34px; height: 34px; border: 0; border-radius: 8px; background: transparent;
  color: var(--muted); cursor: pointer;
}
.sts-panel-x:hover { background: var(--line-soft); color: var(--ink); }
.sts-sheet-stops { display: none; }
.sts-panel-body { flex: 1; min-height: 0; overflow-y: auto; padding: 14px; overscroll-behavior: contain; }
.sts-flash { outline: 2px solid var(--brand-500); outline-offset: 2px; border-radius: 10px; transition: outline-color .4s; }

/* ===== Lienzo ===== */
.sts-canvas { grid-area: canvas; min-width: 0; min-height: 0; display: flex; }
.sts-canvas > .stcv { flex: 1; min-width: 0; }

/* ===== Savebar ===== */
.sts-savebar {
  grid-area: save; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--line); background: var(--card);
}
.sts-state { display: inline-flex; align-items: center; gap: 7px; margin: 0; font-size: 12.5px; font-weight: 600; color: var(--ok); }
.sts-state.dirty { color: var(--warn, #b45309); }
.sts-state.saving { color: var(--ink-2); }
.sts-state.error { color: var(--danger, #dc2626); }
.sts-spin {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid var(--line); border-top-color: var(--brand-500);
  animation: sts-spin .7s linear infinite;
}
@keyframes sts-spin { to { transform: rotate(360deg); } }
.sts-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: sts-pulse 1.6s ease-in-out infinite; }
@keyframes sts-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
.sts-hist { display: inline-flex; align-items: center; gap: 2px; }
.sts-opt {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  min-width: 44px; height: 40px; padding: 0 10px; border: 1px solid transparent;
  border-radius: 9px; background: transparent; color: var(--ink-2); font: inherit;
  font-size: 12.5px; font-weight: 600; cursor: pointer; transition: background .15s, color .15s;
}
.sts-opt:hover:not(:disabled) { background: var(--line-soft); color: var(--ink); }
.sts-opt:disabled { opacity: .4; cursor: default; }
.sts-opt[aria-pressed='true'] { background: var(--brand-soft); color: var(--brand-ink); }
.sts-opt:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.sts-cmp { user-select: none; -webkit-user-select: none; touch-action: none; }
.sts-utils { margin-left: auto; }
.sts-utils + .sts-acts { margin-left: 0; }
.sts-acts { margin-left: auto; display: inline-flex; align-items: center; gap: 8px; }
.sts-act-lb-short { display: none; }

/* Toast local del Studio (fixes de salud, exportar/importar tema): sube
   desde la savebar sin tapar el lienzo. */
.sts-toast {
  position: absolute; left: 50%; bottom: 64px; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 7px; margin: 0; padding: 9px 14px;
  border-radius: 10px; background: var(--ink, #0f172a); color: #fff; font-size: 12.5px;
  font-weight: 600; box-shadow: 0 10px 26px -10px rgba(2, 6, 23, .45); z-index: 65;
  white-space: nowrap; max-width: calc(100% - 20px); overflow: hidden; text-overflow: ellipsis;
}
.sts-toast-enter-active, .sts-toast-leave-active { transition: opacity .18s ease, transform .18s ease; }
.sts-toast-enter-from, .sts-toast-leave-to { opacity: 0; transform: translate(-50%, 6px); }

/* ===== Tablet: panel colapsable ===== */
@media (max-width: 1100px) {
  .sts { --panel-w: 300px; }
  .sts-panel-x { display: inline-flex; }
}
@media (max-width: 900px) {
  .sts { --panel-w: 280px; }
}

/* ===== Móvil: lienzo fullscreen + sheet + rail fijo ===== */
@media (max-width: 768px) {
  /* El Studio toma toda la pantalla (overlay): con cabecera + tabs arriba,
     una altura calc(100dvh - offset) dejaba rail/sheet/savebar anclados
     fuera del fold. z-80: por encima del tabbar (70), debajo de
     SupportBot (90) y chat-win (96). */
  .sts, .sts.is-full {
    --rail-h: calc(62px + env(safe-area-inset-bottom, 0px));
    --save-h: 56px;
    position: fixed; inset: 0; z-index: 80;
    display: block; height: auto; min-height: 0; border: 0; border-radius: 0;
  }
  /* El lienzo se reserva solo el espacio de rail + sheet mínimo: al expandir
     la hoja el usuario acepta que tape la vista (la vuelve a achicar). */
  .sts-canvas { position: absolute; inset: 0; padding-bottom: calc(var(--rail-h) + var(--save-h) + 72px); }
  .sts-rail {
    position: absolute; left: 0; right: 0; bottom: 0; z-index: 30; height: var(--rail-h);
    flex-direction: row; align-items: stretch; padding: 6px 8px calc(6px + env(safe-area-inset-bottom, 0px));
    border-right: 0; border-top: 1px solid var(--line); background: var(--card);
    overflow-x: auto; gap: 4px; scrollbar-width: none;
  }
  .sts-rail::-webkit-scrollbar { display: none; }
  .sts-rail-list { flex-direction: row; gap: 4px; flex: 1; overflow-y: visible; }
  .sts-rail-cap { display: none; }
  .sts-tool { flex: 1 0 auto; min-width: 60px; min-height: 50px; flex-direction: column; }
  .sts-collapse { display: none; }
  .sts-back { display: flex; }
  .sts-savebar {
    position: absolute; left: 0; right: 0; z-index: 31;
    bottom: var(--rail-h); height: var(--save-h);
    padding: 0 8px; gap: 6px; border-top: 0; flex-wrap: nowrap; overflow: hidden;
    align-items: center;
    box-shadow: 0 -1px 0 var(--line);
  }
  .sts-state { flex: 0 0 auto; }
  .sts-state span:last-child, .sts-opt-lb { display: none; }
  .sts-hist { flex: 0 0 auto; }
  .sts-utils { margin-left: auto; flex: 0 0 auto; }
  .sts-acts { margin-left: 0; gap: 6px; flex: 0 0 auto; }
  .sts-savebar .sts-opt { width: 38px; min-width: 38px; height: 40px; padding: 0; }
  .sts-cmp { display: none; }
  .sts-discard { width: 40px; min-width: 40px; padding: 0 !important; justify-content: center; }
  .sts-act-lb { display: none; }
  .sts-act-lb-short { display: inline; }
  .sts-panel {
    position: absolute; left: 0; right: 0; z-index: 32;
    bottom: calc(var(--rail-h) + var(--save-h));
    height: var(--sheet-h); border-right: 0; border-top: 1px solid var(--line);
    border-radius: 16px 16px 0 0; box-shadow: 0 -8px 28px rgba(15, 23, 42, .14);
    background: var(--card); overflow: hidden;
  }
  .sts.panel-closed .sts-panel { height: 0; border-top: 0; }
  .sts-panel-head {
    padding: 10px 14px 10px; cursor: grab; touch-action: none;
    align-items: flex-start;
  }
  .sts-panel-head:active { cursor: grabbing; }
  .sts-grip { display: block; position: absolute; top: 6px; left: 50%; transform: translateX(-50%); width: 40px; height: 4px; border-radius: 2px; background: var(--line); }
  .sts-panel-title { padding-top: 4px; }
  .sts-panel-title h2 { font-size: 14px; }
  .sts-panel-title p { display: none; }
  .sts-savebar .sts-opt { height: 40px; }
  .sts-sheet-stops { display: inline-flex; gap: 6px; padding-top: 10px; }
  .sts-stop { width: 44px; height: 44px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); cursor: pointer; position: relative; }
  .sts-stop::after { content: ''; position: absolute; left: 50%; transform: translateX(-50%); width: 18px; bottom: 8px; border-radius: 2px; background: var(--muted); opacity: .5; }
  .sts-stop:nth-child(1)::after { height: 4px; }
  .sts-stop:nth-child(2)::after { height: 9px; }
  .sts-stop:nth-child(3)::after { height: 14px; }
  .sts-stop.active { border-color: var(--brand-500); }
  .sts-stop.active::after { background: var(--brand-500); opacity: 1; }
  .sts-stop:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
  .sts-panel-x { display: none; }
  .sts-panel-body { padding: 12px 14px 18px; }
  .sts-toast { bottom: calc(var(--rail-h) + 118px); }
}

@media (prefers-reduced-motion: reduce) {
  .sts-dot { animation: none; }
  .sts-spin { animation: none; border-top-color: var(--line); }
  .sts-tool, .sts-opt, .sts-panel { transition: none; }
  .sts-toast-enter-active, .sts-toast-leave-active { transition: none; }
}
</style>
