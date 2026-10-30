<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  CUSTOMIZATION_DEFAULTS, STORE_ACCENTS, STORE_THEMES, STORE_TEMPLATES,
  STORE_FONTS, STORE_FONT_GROUPS, STORE_FONT_PICKER, storeFontFamily, ensureStoreFont, ensureStoreFontPicker,
  NAME_FONT_SIZE_MIN, NAME_FONT_SIZE_MAX, allowedTemplatesFor, storeThemeVars, resolveStoreTemplate,
  validateLogoFile, validateImageFile, LOGO_ACCEPT, formatStorageMB, effectiveAccent
} from '../../api/stores.api.js'
import { extractLogoColors, contrastRatio, deriveAccent, fixAccent, harmonicAccent, normalizeHex, isHex, nearestAccent, hexToRgb } from '../../utils/colorTools.js'
import { PALETTES } from '../../utils/palettes.js'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import AppIcon from '../AppIcon.vue'
import DesignPreview from './DesignPreview.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  // Vista previa embebida (sección Diseño del panel). El Studio ya tiene su
  // propio visor a pantalla completa, así que ahí se apaga.
  preview: { type: Boolean, default: true },
  // La sección Diseño monta los dos selectores del catálogo (patrón +
  // estilo) arriba: se oculta el selector viejo de plantilla para no tener
  // dos controles sobre el mismo campo.
  pickers: { type: Boolean, default: false }
})
const emit = defineEmits(['go-plans', 'ring'])

const store = useStoreStore()
const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const allowedTemplates = computed(() => allowedTemplatesFor(props.benefits || {}))

const steps = [
  { id: 'style', icon: 'layout-grid', title: 'Estilo y portada', ring: 'cover' },
  { id: 'identity', icon: 'image', title: 'Identidad', ring: 'logo' },
  { id: 'colors', icon: 'palette', title: 'Colores', ring: 'accent' },
  { id: 'type', icon: 'type', title: 'Tipografía', ring: 'font', premium: true }
]

const currentLogo = computed(() => store.customization.logo || '')
const currentCover = computed(() => store.customization.cover || '')

// Vista previa embebida: mismos datos y mismas reglas que el panel lateral
// del Dashboard, pero en miniatura y siempre visible mientras se edita.
const IDENTITY_DEFAULTS = { accent_custom: '', logo_scale: 'm', logo_mode: 'logo_name', mono_style: 'accent', cover_overlay: 0 }
const previewVars = computed(() => storeThemeVars(advanced.value ? props.form : { ...props.form, ...IDENTITY_DEFAULTS }))
const previewTemplate = computed(() => resolveStoreTemplate(props.form.template, allowedTemplates.value))
const previewInitial = computed(() => (props.shopName || 'T').slice(0, 1).toUpperCase())
const previewNameFont = computed(() => ({ fontFamily: storeFontFamily(props.form.name_font) }))
const previewCatalogOn = computed(() => props.form.show_catalog !== false)
const previewCarousel = computed(() => store.customization.carousel || [])

const done = computed(() => ({
  identity: Boolean(currentLogo.value),
  colors: props.form.accent !== CUSTOMIZATION_DEFAULTS.accent || isHex(props.form.accent_custom) || props.form.theme !== CUSTOMIZATION_DEFAULTS.theme,
  type: props.form.name_font !== CUSTOMIZATION_DEFAULTS.name_font || Number(props.form.name_font_size) !== CUSTOMIZATION_DEFAULTS.name_font_size,
  style: Boolean(currentCover.value) || props.form.template !== CUSTOMIZATION_DEFAULTS.template || props.form.cover_overlay > 0
}))
const doneCount = computed(() => steps.filter((s) => done.value[s.id]).length)

const open = ref('style')
const headRefs = {}
function setRing(key) { emit('ring', key) }
function stepRing(id) { return steps.find((s) => s.id === id)?.ring || null }
function toggle(id) {
  open.value = open.value === id ? null : id
  setRing(open.value ? stepRing(open.value) : null)
}
function onHeadKey(e, i) {
  const last = steps.length - 1
  const next = e.key === 'ArrowDown' ? (i + 1) % steps.length
    : e.key === 'ArrowUp' ? (i - 1 + steps.length) % steps.length
      : e.key === 'Home' ? 0 : e.key === 'End' ? last : null
  if (next === null) return
  e.preventDefault()
  headRefs[steps[next].id]?.focus()
}

watch(open, (id) => { if (id === 'type') ensureStoreFontPicker() }, { immediate: true })
onMounted(() => setRing(stepRing(open.value)))

const logoInput = ref(null)
const logoBusy = ref(false)
const logoErr = ref('')
const coverInput = ref(null)
const coverBusy = ref(false)
const coverErr = ref('')
const LOGO_ACCEPT_TYPES = LOGO_ACCEPT

const storageText = computed(() => {
  const s = store.storage
  if (!s) return ''
  const used = formatStorageMB(s.used_bytes)
  return s.max_mb === null
    ? `Usás ${used} MB de almacenamiento de imágenes`
    : `Usás ${used} MB de ${s.max_mb} MB de almacenamiento de imágenes`
})

let localLogoUrl = ''
function dropLocalLogo() {
  if (localLogoUrl) URL.revokeObjectURL(localLogoUrl)
  localLogoUrl = ''
}

async function onLogoPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  logoErr.value = validateLogoFile(file)
  if (logoErr.value) return
  dropLocalLogo()
  localLogoUrl = URL.createObjectURL(file)
  logoBusy.value = true
  const ok = await store.uploadLogo(file)
  logoBusy.value = false
  if (!ok) {
    dropLocalLogo()
    logoErr.value = store.fieldErrors.logo || store.lastError
  }
}

async function onRemoveLogo() {
  if (logoBusy.value) return
  logoErr.value = ''
  logoBusy.value = true
  const ok = await store.removeLogo()
  logoBusy.value = false
  if (ok) dropLocalLogo()
  else logoErr.value = store.fieldErrors.logo || store.lastError
}

async function onCoverPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !advanced.value) return
  coverErr.value = validateImageFile(file)
  if (coverErr.value) return
  coverBusy.value = true
  const ok = await store.uploadCover(file)
  coverBusy.value = false
  if (!ok) coverErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
}

async function onRemoveCover() {
  if (coverBusy.value || !advanced.value) return
  coverErr.value = ''
  coverBusy.value = true
  const ok = await store.removeCover()
  coverBusy.value = false
  if (!ok) coverErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
}

const storeThemes = STORE_THEMES
const storeAccents = STORE_ACCENTS
const accentMeta = computed(() => effectiveAccent(props.form))
function pickAccent(key) {
  if (!advanced.value) return
  props.form.accent = key
  props.form.accent_custom = ''
}
function pickTheme(key) {
  props.form.theme = key
}

const hexDraft = ref(props.form.accent_custom || '')
const hexErr = ref('')
watch(() => props.form.accent_custom, (v) => { hexDraft.value = v || ''; hexErr.value = '' })
function setCustom(hex) {
  if (!advanced.value) return
  const n = normalizeHex(hex)
  if (n) props.form.accent_custom = n
}
function onHexInput(e) {
  if (!advanced.value) return
  const raw = e.target.value.trim()
  hexDraft.value = raw
  if (!raw) { hexErr.value = ''; props.form.accent_custom = ''; return }
  const n = normalizeHex(raw)
  hexErr.value = n ? '' : 'Ingresá 6 caracteres hexadecimales, por ejemplo #1a7f5a.'
  if (n) props.form.accent_custom = n
}
function onHexBlur() {
  if (!hexErr.value) hexDraft.value = props.form.accent_custom || ''
}

const logoColors = ref([])
const colorMsg = ref('')
const colorBusy = ref(false)
let analyzedSrc = ''
async function analyzeLogo() {
  const src = localLogoUrl || currentLogo.value
  if (!src || src === analyzedSrc) return
  analyzedSrc = src
  colorBusy.value = true
  colorMsg.value = ''
  try {
    logoColors.value = await extractLogoColors(src)
    if (!logoColors.value.length) colorMsg.value = 'Tu logo no tiene colores para leer. Elegí un acento a mano.'
  } catch {
    analyzedSrc = ''
    logoColors.value = []
    colorMsg.value = 'No pudimos leer los colores de tu logo guardado. Volvé a subirlo desde Identidad o elegí un acento a mano.'
  }
  colorBusy.value = false
}
watch([currentLogo, open], () => {
  if (!currentLogo.value) {
    logoColors.value = []
    colorMsg.value = ''
    analyzedSrc = ''
    return
  }
  if (open.value === 'colors') analyzeLogo()
}, { immediate: true })

function useLogoColor() {
  if (!advanced.value || !logoColors.value.length) return
  const exact = logoColors.value[0]
  const fixed = fixAccent(exact, props.form.theme)
  props.form.accent_custom = fixed.hex
  colorMsg.value = fixed.changed
    ? `Usamos el color de tu logo (${exact}) y lo ajustamos a ${fixed.hex} para que se lea bien.`
    : `Usamos el color exacto de tu logo: ${exact}.`
}

const pageBg = computed(() => (props.form.theme === 'dark' ? '#0d1220' : '#f4f6fb'))
const meters = computed(() => {
  const a = accentMeta.value
  const bg = contrastRatio(a.hex, pageBg.value)
  const btn = contrastRatio('#ffffff', a.ink)
  const dark = props.form.theme === 'dark'
  return [
    {
      key: 'bg', label: 'Acento sobre el fondo', ratio: bg, ok: bg >= 3,
      text: bg >= 3 ? 'Los detalles de color se distinguen bien del fondo.' : `Los detalles cuestan verse sobre este fondo: probá un acento más ${dark ? 'claro' : 'oscuro'} o el otro tema.`
    },
    {
      key: 'btn', label: 'Texto del botón sobre el acento', ratio: btn, ok: btn >= 4.5,
      text: btn >= 4.5 ? 'El texto blanco de los botones se lee con comodidad.' : 'El texto blanco de los botones se lee con esfuerzo: elegí un acento más oscuro.'
    }
  ]
})
const needsFix = computed(() => meters.value.some((m) => !m.ok))
const fixMsg = ref('')
function fixContrast() {
  if (!advanced.value) return
  const fixed = fixAccent(accentMeta.value.hex, props.form.theme)
  props.form.accent_custom = fixed.hex
  const msg = fixed.changed ? `Ajustamos el acento a ${fixed.hex} para que cumpla el contraste AA.` : ''
  nextTick(() => { fixMsg.value = msg })
}
watch(() => [props.form.accent, props.form.accent_custom, props.form.theme], () => { fixMsg.value = '' })

const paletteVars = (p) => {
  const a = deriveAccent(p.accent)
  return { '--pa': a.hex, '--pi': a.ink, '--ps': a.soft }
}
const paletteActive = (p) => props.form.accent_custom === p.accent && props.form.theme === p.theme
function applyPalette(p) {
  if (!advanced.value) return
  props.form.accent_custom = p.accent
  props.form.theme = p.theme
}
const surpriseMsg = ref('')
function surprise() {
  if (!advanced.value) return
  const next = harmonicAccent(accentMeta.value.hex, props.form.theme)
  props.form.accent_custom = next
  surpriseMsg.value = `Probamos ${next}. Si no te convence, deshacelo o sorprendete de nuevo.`
}
watch(() => props.form.accent_custom, (v) => { if (!v) surpriseMsg.value = '' })

const LOGO_SCALE_OPTS = [{ id: 's', label: 'S', name: 'Chico' }, { id: 'm', label: 'M', name: 'Mediano' }, { id: 'l', label: 'L', name: 'Grande' }]
const LOGO_MODE_OPTS = [{ id: 'logo_name', label: 'Logo y nombre', icon: 'panel-top' }, { id: 'logo_only', label: 'Solo logo', icon: 'image' }]
const MONO_OPTS = [{ id: 'accent', label: 'Color de acento' }, { id: 'neutral', label: 'Neutro' }]
function setIdentity(key, value) {
  if (advanced.value) props.form[key] = value
}

const fontFilter = ref('all')
const storeFonts = STORE_FONTS
const fontGroups = computed(() => {
  const groups = STORE_FONT_GROUPS.slice()
  const saved = props.form.name_font
  if (saved && !STORE_FONT_PICKER.includes(saved) && STORE_FONTS[saved]) groups.push({ label: 'Guardada', keys: [saved] })
  return groups
})
const visibleFonts = computed(() => (fontFilter.value === 'all'
  ? fontGroups.value.flatMap((g) => g.keys)
  : fontGroups.value.find((g) => g.label === fontFilter.value)?.keys || []))
watch(fontGroups, (g) => { if (fontFilter.value !== 'all' && !g.some((x) => x.label === fontFilter.value)) fontFilter.value = 'all' })
function pickFont(key) {
  if (!advanced.value) return
  ensureStoreFont(key)
  props.form.name_font = key
}
const fontSample = computed(() => ({ fontFamily: storeFontFamily(props.form.name_font) }))
const sampleName = computed(() => props.shopName || 'Tu negocio')

// Resumen del valor actual en cada encabezado del acordeón ("Acento · ■ #…"):
// se ve qué hay sin abrir el paso — clave del progressive disclosure.
const logoScaleName = computed(() => LOGO_SCALE_OPTS.find((o) => o.id === props.form.logo_scale)?.name || 'Mediano')
const fontLabel = computed(() => STORE_FONTS[props.form.name_font]?.label || props.form.name_font)
const tplLabel = computed(() => STORE_TEMPLATES[props.form.template]?.label || props.form.template)
const themeLabel = computed(() => STORE_THEMES[props.form.theme]?.label || 'Claro')
const stepSum = computed(() => ({
  identity: currentLogo.value ? `Logo subido · ${logoScaleName.value}` : 'Sin logo todavía',
  colors: `${accentMeta.value.hex} · ${themeLabel.value}`,
  type: `${fontLabel.value} · ${props.form.name_font_size}px`,
  style: `${tplLabel.value} · ${currentCover.value ? 'con portada' : 'sin portada'}`
}))

// Los estilos del selectbox salen del catálogo del dominio design (base de
// datos): nada de listas de plantillas en el front.
const { styles: designStyles, load: loadDesignStyles } = useDesignCatalog()
onMounted(() => loadDesignStyles())
const styleOptions = computed(() => designStyles.value.filter((s) => s.is_active !== false))
const tierLabel = (tpl) => {
  const tier = STORE_TEMPLATES[tpl]?.tier
  return tier === 'plus' ? 'Desde Estándar' : tier === 'advanced' ? 'Premium' : 'Incluido'
}
const currentStyleId = computed(() => {
  const id = props.form.site_theme?.style?.id
  if (id && styleOptions.value.some((s) => s.slug === id)) return id
  return styleOptions.value.find((s) => s.template === props.form.template)?.slug || ''
})
// Selectbox de estilos: escribir el estilo del borrador alcanza para que
// el shell lo mande por `studio:update` y la vista previa cambie al instante.
// El Guardar del Studio ya viaja con `template_draft` al publicar.
function onStylePick(event) {
  const s = styleOptions.value.find((x) => x.slug === event.target.value)
  if (!s) return
  if (!allowedTemplates.value.includes(s.template)) {
    // Opción de otro plan: el <select> no puede quedar mostrando lo que no
    // se aplicó, así que vuelve al estilo vigente.
    event.target.value = currentStyleId.value
    emit('go-plans')
    return
  }
  const tokens = s.tokens || {}
  props.form.site_theme = { ...(props.form.site_theme || {}), style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
  const body = tokens.typography?.body
  if (body) {
    props.form.name_font = body
    ensureStoreFont(body)
  }
  const accent = tokens.palette?.accent
  if (accent && advanced.value) props.form.accent_custom = accent
  else if (accent) {
    const slug = nearestAccent(hexToRgb(accent), STORE_ACCENTS)
    if (slug) props.form.accent = slug
  }
  props.form.template = s.template
}

const HISTORY_FIELDS = ['theme', 'accent', 'accent_custom', 'name_font', 'name_font_size', 'template', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay']
const HISTORY_MAX = 20
const snapshot = () => Object.fromEntries(HISTORY_FIELDS.map((k) => [k, props.form[k]]))
const past = ref([])
const future = ref([])
let current = snapshot()
let resetNext = false
let coalesce = null
let lastKeys = ''
let applying = false
const canUndo = computed(() => past.value.length > 0)
const canRedo = computed(() => future.value.length > 0)
watch(() => store.store, () => {
  resetNext = true
  nextTick(() => { resetNext = false })
})
watch(() => JSON.stringify(snapshot()), () => {
  if (resetNext) {
    past.value = []
    future.value = []
    current = snapshot()
    return
  }
  if (applying) { applying = false; current = snapshot(); return }
  const next = snapshot()
  const keys = HISTORY_FIELDS.filter((k) => next[k] !== current[k]).join()
  if (!coalesce || keys !== lastKeys) {
    past.value = [...past.value, current].slice(-HISTORY_MAX)
    future.value = []
  }
  lastKeys = keys
  clearTimeout(coalesce)
  coalesce = setTimeout(() => { coalesce = null }, 500)
  current = next
})
function applySnapshot(snap) {
  applying = true
  clearTimeout(coalesce)
  coalesce = null
  Object.assign(props.form, snap)
  nextTick(() => { applying = false; current = snapshot() })
}
function undo() {
  if (!canUndo.value) return
  const prev = past.value[past.value.length - 1]
  past.value = past.value.slice(0, -1)
  future.value = [...future.value, current]
  applySnapshot(prev)
}
function redo() {
  if (!canRedo.value) return
  const next = future.value[future.value.length - 1]
  future.value = future.value.slice(0, -1)
  past.value = [...past.value, current].slice(-HISTORY_MAX)
  applySnapshot(next)
}
function onRootKey(e) {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return
  const key = e.key.toLowerCase()
  if (key !== 'z' && key !== 'y') return
  const t = e.target
  if (t instanceof HTMLElement && (t.tagName === 'TEXTAREA' || (t.tagName === 'INPUT' && !['range', 'color', 'checkbox', 'radio', 'file'].includes(t.type)))) return
  e.preventDefault()
  if (key === 'y' || e.shiftKey) redo()
  else undo()
}
onBeforeUnmount(() => clearTimeout(coalesce))

onBeforeUnmount(dropLocalLogo)
</script>

<template>
  <div class="card dsg-card dl-root" @keydown="onRootKey">
    <div class="dl-shell">
      <div class="dl-main">
        <div class="dl-progress">
          <div class="dl-progress-head">
            <div class="dl-progress-title">
              <strong><AppIcon name="badge-check" :size="16" aria-hidden="true" /> Tu diseño</strong>
              <small>Cuatro pasos y tu web queda lista.</small>
            </div>
            <span class="dl-history">
              <button type="button" class="dl-hbtn" :disabled="!canUndo" title="Deshacer (Ctrl+Z)" aria-label="Deshacer el último cambio" @click="undo"><AppIcon name="undo" :size="17" aria-hidden="true" /></button>
              <button type="button" class="dl-hbtn" :disabled="!canRedo" title="Rehacer (Ctrl+Shift+Z)" aria-label="Rehacer el cambio" @click="redo"><AppIcon name="redo" :size="17" aria-hidden="true" /></button>
              <span class="dl-progress-count">{{ doneCount }}/4</span>
            </span>
          </div>

          <div class="dl-bar" role="progressbar" aria-label="Identidad visual completada" aria-valuemin="0" aria-valuemax="4" :aria-valuenow="doneCount">
            <span :style="{ transform: `scaleX(${doneCount / 4})` }"></span>
          </div>
        </div>

        <div class="dl-steps">
      <section v-for="(s, i) in steps" :key="s.id" class="dl-step" :class="{ open: open === s.id, done: done[s.id] }">
        <h4 class="dl-step-h">
          <button
            :id="`dl-h-${s.id}`"
            :ref="(el) => { headRefs[s.id] = el }"
            type="button"
            class="dl-step-btn"
            :aria-expanded="open === s.id"
            :aria-controls="`dl-p-${s.id}`"
            @click="toggle(s.id)"
            @keydown="onHeadKey($event, i)"
          >
            <span class="dl-step-ico" aria-hidden="true"><AppIcon :name="s.icon" :size="18" /></span>
            <span class="dl-step-txt">
              <strong>{{ s.title }}</strong>
              <small class="dl-sum"><i v-if="s.id === 'colors'" class="dl-dot" :style="{ background: accentMeta.hex }" aria-hidden="true"></i>{{ stepSum[s.id] }}</small>
            </span>
            <span v-if="s.premium && !advanced" class="lock-badge dl-step-lock"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span>
            <span class="dl-step-state" :class="{ done: done[s.id] }">
              <AppIcon v-if="done[s.id]" name="circle-check" :size="18" aria-hidden="true" />
              <span v-else class="dl-step-pending" aria-hidden="true"></span>
              <span class="sr-only">{{ done[s.id] ? 'Completo' : 'Pendiente' }}</span>
            </span>
            <AppIcon class="dl-chev" name="chevron-down" :size="16" aria-hidden="true" />
          </button>
        </h4>

        <div v-show="open === s.id" :id="`dl-p-${s.id}`" role="region" :aria-labelledby="`dl-h-${s.id}`" class="dl-panel">
          <template v-if="s.id === 'identity'">
            <div class="field" @focusin="setRing('logo')">
              <label id="design-logo-label"><AppIcon name="image" :size="14" class="label-icon" aria-hidden="true" />Logo</label>
              <div class="logo-box dl-logo-box">
                <span class="logo-thumb">
                  <img v-if="currentLogo" :src="currentLogo" alt="Logo de tu tienda" />
                  <AppIcon v-else name="image" :size="20" aria-hidden="true" />
                </span>
                <div class="logo-actions">
                  <input ref="logoInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-logo-label" @change="onLogoPicked" />
                  <button type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="logoInput?.click()">
                    <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
                    <AppIcon v-else name="upload" :size="16" />
                    {{ currentLogo ? 'Cambiar logo' : 'Subir logo' }}
                  </button>
                  <button v-if="currentLogo" type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="onRemoveLogo">Quitar</button>
                </div>
              </div>
              <p class="hint">PNG, JPG, WebP o GIF de hasta 2 MB. Mejor si es cuadrado.</p>
              <p v-if="storageText" class="hint">{{ storageText }}</p>
              <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('logo')">
              <label id="design-logo-scale-label"><AppIcon name="sliders" :size="14" class="label-icon" aria-hidden="true" />Tamaño del logo <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="dl-seg" role="group" aria-labelledby="design-logo-scale-label">
                <button v-for="o in LOGO_SCALE_OPTS" :key="o.id" type="button" class="dl-seg-btn" :class="{ active: form.logo_scale === o.id }" :aria-pressed="form.logo_scale === o.id" :aria-label="o.name" :title="o.name" :aria-disabled="!advanced" @click="setIdentity('logo_scale', o.id)">{{ o.label }}</button>
              </div>
              <p class="hint">Cambia el logo en la barra y en la portada de tu web.</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('logo')">
              <label id="design-logo-mode-label"><AppIcon name="panel-top" :size="14" class="label-icon" aria-hidden="true" />Cómo se muestra <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="dl-seg wide" role="group" aria-labelledby="design-logo-mode-label">
                <button v-for="o in LOGO_MODE_OPTS" :key="o.id" type="button" class="dl-seg-btn" :class="{ active: form.logo_mode === o.id }" :aria-pressed="form.logo_mode === o.id" :aria-disabled="!advanced" @click="setIdentity('logo_mode', o.id)"><AppIcon :name="o.icon" :size="16" aria-hidden="true" /><span class="dl-ell">{{ o.label }}</span></button>
              </div>
              <p class="hint">{{ currentLogo ? 'Con "Solo logo" el nombre queda oculto junto al logo (lo leen los lectores de pantalla).' : 'Se aplica cuando subas un logo.' }}</p>
            </div>
            <div v-if="!currentLogo" class="field" :class="{ locked: !advanced }" @focusin="setRing('logo')">
              <label id="design-mono-label"><AppIcon name="palette" :size="14" class="label-icon" aria-hidden="true" />Monograma sin logo <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="dl-seg wide" role="group" aria-labelledby="design-mono-label">
                <button v-for="o in MONO_OPTS" :key="o.id" type="button" class="dl-seg-btn" :class="{ active: form.mono_style === o.id }" :aria-pressed="form.mono_style === o.id" :aria-disabled="!advanced" @click="setIdentity('mono_style', o.id)"><span class="dl-ell">{{ o.label }}</span></button>
              </div>
              <p class="hint">La inicial de tu negocio, con tu acento o en gris neutro.</p>
            </div>
            <div v-if="!advanced" class="dl-lock">
              <AppIcon name="lock" :size="16" aria-hidden="true" />
              <span>El tamaño y el modo del logo vienen con el Plan premium.</span>
              <button type="button" class="btn ghost btn-auto" @click="emit('go-plans')">Ver planes</button>
            </div>
          </template>


          <template v-else-if="s.id === 'colors'">
            <div class="field" @focusin="setRing('accent')">
              <label id="design-theme-label"><AppIcon name="sun" :size="14" class="label-icon" aria-hidden="true" />Tema</label>
              <div class="theme-options" role="radiogroup" aria-labelledby="design-theme-label">
                <button
                  v-for="(t, key) in storeThemes" :key="key" type="button"
                  class="theme-option" :class="{ active: form.theme === key }"
                  :aria-pressed="form.theme === key"
                  @click="pickTheme(key)"
                >
                  <span class="theme-thumb" :data-store-theme="key"></span>
                  <span class="dl-ell">{{ t.label }}</span>
                </button>
              </div>
              <p class="hint">Claro u oscuro para la barra, la portada y el catálogo.</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('accent')">
              <label id="design-accent-label"><AppIcon name="palette" :size="14" class="label-icon" aria-hidden="true" />Color de acento <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="swatches dl-swatches" role="group" aria-labelledby="design-accent-label">
                <button
                  v-for="(a, key) in storeAccents" :key="key" type="button"
                  class="swatch" :class="{ active: form.accent === key && !form.accent_custom }"
                  :style="{ '--swatch': a.hex }"
                  :title="a.label" :aria-label="`Color ${a.label}`"
                  :aria-disabled="!advanced"
                  :aria-pressed="form.accent === key && !form.accent_custom"
                  @click="pickAccent(key)"
                >
                  <AppIcon v-if="form.accent === key && !form.accent_custom" name="check" :size="14" :stroke="2.5" />
                </button>
              </div>
              <div class="dl-custom">
                <label class="dl-colorpick" :class="{ active: form.accent_custom }" :style="{ '--swatch': accentMeta.hex }" title="Elegir un color propio">
                  <input type="color" :value="accentMeta.hex" :disabled="!advanced" aria-label="Elegir un color propio" @input="setCustom($event.target.value)" />
                  <AppIcon name="pipette" :size="18" aria-hidden="true" />
                </label>
                <div class="dl-hexbox">
                  <label for="design-accent-hex" class="tpl-label">Color propio (hex)</label>
                  <input id="design-accent-hex" class="dl-hex" type="text" inputmode="text" autocomplete="off" spellcheck="false" maxlength="7" placeholder="#1a7f5a" :value="hexDraft" :disabled="!advanced" :aria-invalid="Boolean(hexErr)" aria-describedby="design-accent-hex-err" @input="onHexInput" @blur="onHexBlur" />
                </div>
                <button type="button" class="btn ghost btn-auto dl-surprise" :disabled="!advanced" @click="surprise"><AppIcon name="refresh" :size="16" /> Sorprendeme</button>
              </div>
              <p v-if="hexErr" id="design-accent-hex-err" class="field-error" role="alert">{{ hexErr }}</p>
              <p v-if="surpriseMsg" class="hint" role="status">{{ surpriseMsg }} <button type="button" class="dl-link" :disabled="!canUndo" @click="undo">Deshacer</button></p>
              <p v-else class="hint">Elegí un preset o cualquier color: calculamos solos los tonos oscuro y suave.</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('accent')">
              <label id="design-palettes-label"><AppIcon name="layout-grid" :size="14" class="label-icon" aria-hidden="true" />Paletas por rubro <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="dl-pals" role="group" aria-labelledby="design-palettes-label">
                <button v-for="p in PALETTES" :key="p.id" type="button" class="dl-pal" :class="{ active: paletteActive(p) }" :data-t="p.theme" :style="paletteVars(p)" :aria-pressed="paletteActive(p)" :aria-disabled="!advanced" @click="applyPalette(p)">
                  <span class="dl-pal-web" aria-hidden="true"><i class="dl-pal-nav"></i><i class="dl-pal-hero"><b></b></i><i class="dl-pal-row"><b></b><b></b></i></span>
                  <span class="dl-pal-name dl-ell">{{ p.label }}</span>
                  <small class="dl-pal-hint">{{ p.hint }}</small>
                </button>
              </div>
              <p class="hint">Aplica el acento y el tema juntos.</p>
            </div>
            <div class="field dl-logo-color" :class="{ locked: !advanced }">
              <label><AppIcon name="pipette" :size="14" class="label-icon" aria-hidden="true" />Color de tu logo</label>
              <template v-if="currentLogo">
                <div class="dl-chips" aria-live="polite">
                  <span v-if="colorBusy" class="spinner" aria-hidden="true"></span>
                  <span v-for="c in logoColors" :key="c" class="dl-chip" :style="{ background: c }" :title="c" role="img" :aria-label="`Color dominante ${c}`"></span>
                  <button type="button" class="btn ghost btn-auto dl-use-logo" :disabled="!advanced || !logoColors.length || colorBusy" @click="useLogoColor">
                    <AppIcon name="pipette" :size="16" /> Usar color de mi logo
                  </button>
                </div>
                <p v-if="colorMsg" class="hint" role="status">{{ colorMsg }}</p>
                <p v-else class="hint">Usamos el color exacto de tu logo y lo ajustamos si hace falta para que se lea.</p>
              </template>
              <p v-else class="hint">Subí tu logo en Identidad y te sugerimos un acento.</p>
            </div>
            <div class="dl-meters" aria-live="polite">
              <div v-for="m in meters" :key="m.key" class="dl-meter" :class="m.ok ? 'ok' : 'warn'">
                <span class="dl-meter-ico"><AppIcon :name="m.ok ? 'circle-check' : 'circle-alert'" :size="18" aria-hidden="true" /></span>
                <div class="dl-meter-body">
                  <strong>{{ m.label }} <span class="dl-meter-ratio">{{ m.ratio.toFixed(1) }}:1</span></strong>
                  <small>{{ m.text }}</small>
                </div>
              </div>
            </div>
            <div v-if="advanced && needsFix" class="dl-fix">
              <button type="button" class="btn ghost btn-auto" @click="fixContrast"><AppIcon name="check" :size="16" /> Corregir automáticamente</button>
            </div>
            <p v-if="fixMsg" class="hint" role="status">{{ fixMsg }}</p>
            <div v-if="!advanced" class="dl-lock">
              <AppIcon name="lock" :size="16" aria-hidden="true" />
              <span>El color de acento viene con el Plan premium.</span>

              <button type="button" class="btn ghost btn-auto" @click="emit('go-plans')">Ver planes</button>
            </div>
          </template>

          <template v-else-if="s.id === 'type'">
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('font')">
              <label id="design-font-label"><AppIcon name="type" :size="14" class="label-icon" aria-hidden="true" />Fuente de tu web <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="dl-filters" role="group" aria-label="Filtrar fuentes por estilo">
                <button type="button" class="dl-filter" :class="{ active: fontFilter === 'all' }" :aria-pressed="fontFilter === 'all'" @click="fontFilter = 'all'">Todas</button>
                <button v-for="g in fontGroups" :key="g.label" type="button" class="dl-filter" :class="{ active: fontFilter === g.label }" :aria-pressed="fontFilter === g.label" @click="fontFilter = g.label">{{ g.label }}</button>
              </div>
              <div class="dl-fonts" role="group" aria-labelledby="design-font-label">
                <button
                  v-for="key in visibleFonts" :key="key" type="button"
                  class="dl-font" :class="{ active: form.name_font === key }"
                  :style="{ fontFamily: storeFontFamily(key) }"
                  :aria-pressed="form.name_font === key"
                  :aria-disabled="!advanced"
                  @click="pickFont(key)"
                >
                  <span class="dl-font-aa" aria-hidden="true">Aa</span>
                  <span class="dl-font-name">{{ storeFonts[key]?.label }}</span>
                  <span v-if="form.name_font === key" class="dl-font-tick" aria-hidden="true"><AppIcon name="check" :size="12" :stroke="3" /></span>
                </button>
              </div>
              <div class="dl-sample" aria-live="polite">
                <span class="pick-preview-eyebrow">{{ storeFonts[form.name_font]?.label }}</span>
                <strong class="dl-sample-name" :style="fontSample">{{ sampleName }}</strong>
                <small class="dl-sample-text" :style="fontSample">Catálogo online. Nuevos ingresos 0123456789</small>
              </div>
              <p class="hint">Se aplica a todo el texto de tu web. Solo tipografías probadas.</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('font')">
              <label for="design-name-size"><AppIcon name="sliders" :size="14" class="label-icon" aria-hidden="true" />Tamaño del nombre <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="size-slider">
                <input id="design-name-size" v-model.number="form.name_font_size" type="range" :min="NAME_FONT_SIZE_MIN" :max="NAME_FONT_SIZE_MAX" step="1" :disabled="!advanced" />
                <span class="size-value">{{ form.name_font_size }} px</span>
              </div>
              <p class="hint">Alto del nombre en la portada ({{ NAME_FONT_SIZE_MIN }} a {{ NAME_FONT_SIZE_MAX }} px).</p>
            </div>
            <div v-if="!advanced" class="dl-lock">
              <AppIcon name="lock" :size="16" aria-hidden="true" />
              <span>La fuente y el tamaño vienen con el Plan premium.</span>
              <button type="button" class="btn ghost btn-auto" @click="emit('go-plans')">Ver planes</button>
            </div>
          </template>

          <template v-else>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('cover')">
              <label id="design-cover-label"><AppIcon name="image" :size="14" class="label-icon" aria-hidden="true" />Imagen de portada <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="cover-box dl-logo-box">
                <span class="cover-thumb" :class="{ empty: !currentCover }">
                  <img v-if="currentCover" :src="currentCover" alt="Portada actual de tu web" />
                  <AppIcon v-else name="image" :size="22" aria-hidden="true" />
                </span>
                <div class="logo-actions">
                  <input ref="coverInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-cover-label" :disabled="!advanced" @change="onCoverPicked" />
                  <button type="button" class="btn ghost btn-auto" :disabled="coverBusy || !advanced" @click="coverInput?.click()">
                    <span v-if="coverBusy" class="spinner" aria-hidden="true"></span>
                    <AppIcon v-else name="upload" :size="16" />
                    {{ currentCover ? 'Cambiar portada' : 'Subir portada' }}
                  </button>
                  <button v-if="currentCover && advanced" type="button" class="btn ghost btn-auto" :disabled="coverBusy" @click="onRemoveCover">Quitar</button>
                </div>
              </div>
              <p class="hint">Foto apaisada y luminosa de hasta 4 MB; la ajustamos sola.</p>
              <p v-if="coverErr" class="field-error" role="alert">{{ coverErr }}</p>
            </div>
            <div class="field" :class="{ locked: !advanced }" @focusin="setRing('cover')">
              <label for="design-cover-overlay"><AppIcon name="moon" :size="14" class="label-icon" aria-hidden="true" />Oscurecer la portada <span v-if="!advanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="size-slider">
                <input id="design-cover-overlay" v-model.number="form.cover_overlay" type="range" min="0" max="80" step="5" :disabled="!advanced" />
                <span class="size-value">{{ form.cover_overlay }}%</span>
              </div>
              <p class="hint">Ayuda a que el texto se lea sobre fotos claras.</p>
            </div>

            <div v-if="!pickers" class="field" @focusin="setRing('cover')">
              <label for="design-style"><AppIcon name="layout-grid" :size="14" class="label-icon" aria-hidden="true" />Estilo de tu web</label>
              <div class="dl-style-row">
                <span class="tpl-thumb dl-style-prev" :data-tpl="form.template" aria-hidden="true"><i><b></b><b></b><b></b></i></span>
                <div class="dl-style-sel">
                  <select id="design-style" class="select" :value="currentStyleId" :disabled="!styleOptions.length" aria-describedby="design-style-help" @change="onStylePick">
                    <option value="" disabled>Elegí un estilo…</option>
                    <option v-for="s in styleOptions" :key="s.slug" :value="s.slug" :disabled="!allowedTemplates.includes(s.template)">
                      {{ s.nombre }} · {{ s.categoria }} · {{ tierLabel(s.template) }}
                    </option>
                  </select>
                  <span class="dl-style-meta">
                    {{ styleOptions.find((s) => s.slug === currentStyleId)?.nombre || '' }}
                    <span class="pick-tier" :class="STORE_TEMPLATES[form.template]?.tier">{{ tierLabel(form.template) }}</span>
                  </span>
                </div>
              </div>
              <p id="design-style-help" class="hint">Estilos del catálogo de diseño. Cambia la piel de tu web sin perder contenido y se ve al instante en la vista previa.</p>
            </div>
            <div v-if="!advanced" class="dl-lock">
              <AppIcon name="lock" :size="16" aria-hidden="true" />
              <span>La portada y los diseños avanzados vienen con otro plan.</span>
              <button type="button" class="btn ghost btn-auto" @click="emit('go-plans')">Ver planes</button>
            </div>
          </template>
        </div>
      </section>
        </div>
      </div>

      <aside v-if="preview && !pickers" class="dl-side" aria-label="Vista previa de tu web">
        <div class="dl-side-head">
          <strong><AppIcon name="eye" :size="15" aria-hidden="true" /> Así se ve</strong>
          <small>Se actualiza mientras editás</small>
        </div>
        <DesignPreview
          compact
          :form="form"
          :vars="previewVars"
          :template="previewTemplate"
          :shop-name="shopName"
          :initial="previewInitial"
          :logo="currentLogo"
          :cover="currentCover"
          :advanced="advanced"
          :catalog-on="previewCatalogOn"
          :carousel="previewCarousel"
          :name-font="previewNameFont"
        />
      </aside>
    </div>
  </div>
</template>

<style>
.dl-root { container-type: inline-size; }
/* Editor + miniatura: en pantallas anchas la vista previa acompaña; abajo de
   1040px pasa arriba para que el resultado se vea antes de tocar nada. */
.dl-shell { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; min-width: 0; }
@media (min-width: 1040px) {
  .dl-shell { grid-template-columns: minmax(0, 1fr) 280px; align-items: start; }
  .dl-side { position: sticky; top: 12px; }
}
.dl-main { display: flex; flex-direction: column; gap: 0; min-width: 0; }
.dl-side {
  display: flex; flex-direction: column; gap: 8px; min-width: 0;
  padding: 12px; border: 1px solid var(--line); border-radius: 14px;
  background: var(--surface);
}
.dl-side-head { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.dl-side-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink); }
.dl-side-head small { color: var(--muted); font-size: 11.5px; }
.dl-progress-title { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.dl-progress-title small { color: var(--muted); font-size: 11.5px; }
.dl-progress { display: grid; gap: 10px; padding: 14px; margin-bottom: 14px; border: 1px solid var(--line); border-radius: 14px; background: linear-gradient(135deg, var(--brand-soft), transparent 70%), var(--card); min-width: 0; }
.dl-progress-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }
.dl-progress-head strong { display: inline-flex; align-items: center; gap: 7px; font-size: 14px; min-width: 0; color: var(--ink); }
.dl-progress-head .icon { color: var(--brand-600); flex: none; }
.dl-progress-count { flex: none; font-size: 13px; font-weight: 800; color: var(--brand-ink); font-variant-numeric: tabular-nums; }
.dl-bar { height: 8px; border-radius: 99px; background: var(--line); overflow: hidden; }
.dl-bar span { display: block; height: 100%; width: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--brand-500), var(--accent)); transform-origin: 0 50%; transition: transform .22s ease; }
.dl-sum { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
.dl-dot { flex: none; width: 10px; height: 10px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(9, 12, 24, .15); }

.dl-steps { display: grid; gap: 10px; min-width: 0; }
.dl-step { position: relative; border: 1px solid var(--line); border-radius: 14px; background: var(--card); min-width: 0; transition: border-color .15s, background .15s; }
.dl-step.open { border-color: color-mix(in srgb, var(--brand-500) 45%, var(--line)); box-shadow: var(--shadow-sm); background: var(--card); }
.dl-step.open::before {
  content: ''; position: absolute; left: 0; top: 14px; bottom: 14px; width: 3px;
  border-radius: 0 3px 3px 0; background: var(--brand-500);
}
@media (hover: hover) { .dl-step:not(.open):hover { border-color: var(--line-strong, var(--line)); } }
.dl-step-h { margin: 0; font-size: inherit; }
.dl-step-btn { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 64px; min-width: 0; padding: 10px 14px; border: 0; border-radius: 14px; background: transparent; font: inherit; text-align: left; color: var(--ink); cursor: pointer; }
.dl-step-btn:hover { background: var(--surface); }
.dl-step-btn:focus-visible, .dl-filter:focus-visible, .dl-font:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.dl-step-ico { flex: none; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px; background: var(--brand-soft); color: var(--brand-600); }
.dl-step.done .dl-step-ico { background: var(--ok-bg); color: var(--ok-ink); }
.dl-step-txt { display: grid; gap: 2px; flex: 1; min-width: 0; }
.dl-step-txt strong { display: flex; align-items: center; gap: 8px; font-size: 14.5px; line-height: 1.25; min-width: 0; }
.dl-step-txt small { color: var(--muted); font-size: 12.5px; line-height: 1.35; overflow-wrap: anywhere; }
.dl-step-lock { flex: none; margin-left: 0; }
.dl-step-state { flex: none; display: grid; place-items: center; width: 22px; height: 22px; color: var(--ok); }
.dl-step-pending { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--line-strong, var(--line)); }
.dl-chev { flex: none; color: var(--muted); transition: transform .18s ease; }
.dl-step.open .dl-chev { transform: rotate(180deg); }
.dl-panel { display: grid; gap: 16px; padding: 4px 14px 16px; min-width: 0; animation: dl-in .18s ease both; }
.dl-panel .field { min-width: 0; margin: 0; }
.dl-panel .hint { overflow-wrap: anywhere; }
@keyframes dl-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
@media (max-width: 520px) {
  .dl-step-btn { gap: 10px; padding: 10px; }
  .dl-step-lock { display: none; }
  .dl-panel { padding: 4px 10px 14px; }
}

.dl-ell { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ===== Selectbox de estilos (3 diseños del catálogo) ===== */
.dl-style-row { display: flex; align-items: stretch; gap: 10px; margin-top: 8px; min-width: 0; }
.dl-style-prev { flex: none; width: 92px; border-radius: 9px; }
.dl-style-sel { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 6px; min-width: 0; }
.dl-style-sel .select { width: 100%; min-height: 44px; font-size: 16px; }
.dl-style-sel .pick-tier { justify-self: start; align-self: flex-start; padding: 1px 8px; font-size: 10.5px; }
.dl-style-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 11.5px; line-height: 1.3; color: var(--muted); }

.dl-logo-box .logo-actions { display: flex; flex-wrap: wrap; gap: 8px; min-width: 0; }
.dl-logo-box { min-width: 0; }
.dl-swatches { gap: 8px; }
.dl-panel .swatch { width: 44px; height: 44px; }
.dl-panel .swatch::before { display: none; }
.dl-chips { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; }
.dl-chip { width: 32px; height: 32px; border-radius: 10px; border: 1px solid var(--line); box-shadow: inset 0 0 0 2px rgba(255, 255, 255, .55); flex: none; }
.dl-use-logo { min-height: 44px; white-space: normal; text-align: left; }
.dl-logo-color.locked .dl-chips { opacity: .8; }

.dl-meters { display: grid; gap: 8px; min-width: 0; }
.dl-meter { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border: 1px solid var(--ok-line); border-radius: 12px; background: var(--ok-bg); color: var(--ok-ink); min-width: 0; }
.dl-meter.warn { border-color: var(--warn-line); background: var(--warn-bg); color: var(--warn-ink); }
.dl-meter-ico { flex: none; margin-top: 1px; }
.dl-meter-body { display: grid; gap: 2px; min-width: 0; }
.dl-meter-body strong { font-size: 13px; line-height: 1.3; overflow-wrap: anywhere; }
.dl-meter-body small { font-size: 12.5px; line-height: 1.4; overflow-wrap: anywhere; }
.dl-meter-ratio { margin-left: 4px; font-variant-numeric: tabular-nums; font-weight: 800; white-space: nowrap; }

.dl-filters { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.dl-filter { min-height: 44px; padding: 6px 14px; border: 1px solid var(--line); border-radius: 99px; background: var(--card); font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-2); cursor: pointer; }
.dl-filter.active { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.dl-fonts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
@container (min-width: 400px) { .dl-fonts { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@container (min-width: 560px) { .dl-fonts { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.dl-font { position: relative; display: grid; justify-items: center; align-content: center; gap: 2px; min-width: 0; min-height: 84px; padding: 10px 8px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); color: var(--ink); cursor: pointer; transition: border-color .15s, transform .15s; }
@media (hover: hover) { .dl-font:hover { border-color: var(--line-strong, var(--line)); } }
.dl-font.active { border-color: var(--brand-500); box-shadow: var(--ring); background: var(--brand-soft); }
.dl-font-aa { font-size: 28px; line-height: 1.1; }
.dl-font-name { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: var(--font-ui, Inter, system-ui, sans-serif); font-size: 12px; font-weight: 600; color: var(--ink-2); }
.dl-font-tick { position: absolute; top: 6px; right: 6px; display: grid; place-items: center; width: 18px; height: 18px; border-radius: 50%; background: var(--brand-500); color: #fff; }
.field.locked .dl-font { opacity: .6; cursor: default; }
.field.locked .dl-filter, .field.locked .dl-use-logo { opacity: 1; }
.dl-sample { display: grid; gap: 4px; margin-top: 10px; padding: 12px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); min-width: 0; }
.dl-sample-name { font-size: 22px; line-height: 1.2; overflow-wrap: anywhere; }
.dl-sample-text { font-size: 13px; color: var(--muted); overflow-wrap: anywhere; }

.dl-lock { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; padding: 10px 12px; border: 1px dashed var(--line-strong, var(--line)); border-radius: 12px; background: var(--brand-soft); color: var(--brand-ink); font-size: 13px; min-width: 0; }
.dl-lock span { flex: 1 1 160px; min-width: 0; overflow-wrap: anywhere; }
.dl-panel input[type='text'], .dl-panel select, .dl-panel textarea { font-size: 16px; }
.dl-panel .select { min-height: 44px; font-size: 16px; }

@media (prefers-reduced-motion: reduce) {
  .dl-panel { animation: none; }
  .dl-bar span, .dl-chev, .dl-font { transition: none; }
}

.dl-history { display: inline-flex; align-items: center; gap: 6px; flex: none; }
.dl-hbtn { display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--ink-2); cursor: pointer; transition: background .15s, opacity .15s; }
.dl-hbtn:hover:not(:disabled) { background: var(--surface); }
.dl-hbtn:disabled { opacity: .4; cursor: default; }
.dl-hbtn:focus-visible, .dl-seg-btn:focus-visible, .dl-pal:focus-visible, .dl-link:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.dl-seg { display: inline-flex; gap: 4px; padding: 3px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); max-width: 100%; }
.dl-seg.wide { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); width: 100%; }
.dl-seg-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-width: 44px; min-height: 44px; padding: 6px 14px; border: 0; border-radius: 9px; background: transparent; font: inherit; font-size: 13px; font-weight: 700; color: var(--ink-2); cursor: pointer; transition: background .15s, color .15s; }
.dl-seg-btn > span { min-width: 0; }
.dl-seg-btn.active { background: var(--brand-500); color: #fff; }
.field.locked .dl-seg-btn, .field.locked .dl-pal, .field.locked .dl-hex, .field.locked .dl-colorpick { opacity: .6; cursor: default; }

.dl-custom { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 10px; margin-top: 12px; min-width: 0; }
.dl-colorpick { position: relative; display: grid; place-items: center; flex: none; width: 44px; height: 44px; border-radius: 50%; background: var(--swatch); color: #fff; cursor: pointer; overflow: hidden; }
.dl-colorpick.active { box-shadow: 0 0 0 3px var(--card), 0 0 0 5px var(--swatch); }
.dl-colorpick:focus-within { outline: 2px solid var(--brand-500); outline-offset: 4px; }
.dl-colorpick input { position: absolute; inset: 0; width: 100%; height: 100%; padding: 0; border: 0; opacity: 0; cursor: pointer; }
.dl-colorpick .icon { pointer-events: none; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, .55)); }
.dl-hexbox { display: grid; gap: 4px; flex: 1 1 130px; min-width: 0; }
.dl-hex { width: 100%; min-width: 0; min-height: 44px; padding: 8px 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--card); color: var(--ink); font: inherit; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 16px; }
.dl-hex:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 1px; }
.dl-hex[aria-invalid='true'] { border-color: var(--danger); }
.dl-surprise { min-height: 44px; }
.dl-link { display: inline-flex; align-items: center; min-height: 44px; padding: 0 6px; border: 0; background: none; font: inherit; font-weight: 700; color: var(--brand-ink); text-decoration: underline; cursor: pointer; }
.dl-link:disabled { opacity: .5; cursor: default; }
.dl-fix { display: flex; min-width: 0; }
.dl-fix .btn { min-height: 44px; }

.dl-pals { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
@container (min-width: 520px) { .dl-pals { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.dl-pal { display: grid; gap: 5px; align-content: start; min-width: 0; min-height: 44px; padding: 8px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); text-align: left; font: inherit; color: var(--ink); cursor: pointer; }
.dl-pal.active { border-color: var(--brand-500); box-shadow: var(--ring); }
.dl-pal-web { display: flex; flex-direction: column; height: 72px; overflow: hidden; border: 1px solid var(--line); border-radius: 8px; background: #f4f6fb; }
.dl-pal[data-t='dark'] .dl-pal-web { background: #0d1220; border-color: #28304d; }
.dl-pal-nav { display: block; flex: none; height: 9px; background: var(--pi); }
.dl-pal-hero { display: grid; place-items: center; flex: 1 1 auto; background: linear-gradient(120deg, var(--pa), var(--pi)); }
.dl-pal-hero b { width: 38%; height: 6px; border-radius: 9px; background: #fff; }
.dl-pal-row { display: flex; flex: none; gap: 4px; padding: 5px; }
.dl-pal-row b { flex: 1; height: 12px; border-radius: 3px; background: var(--ps); }
.dl-pal[data-t='dark'] .dl-pal-row b { background: rgba(255, 255, 255, .14); }
.dl-pal-name { font-size: 13px; font-weight: 700; }
.dl-pal-hint { color: var(--muted); font-size: 11.5px; line-height: 1.3; overflow-wrap: anywhere; }

@media (prefers-reduced-motion: reduce) { .dl-hbtn, .dl-seg-btn { transition: none; } }
</style>
