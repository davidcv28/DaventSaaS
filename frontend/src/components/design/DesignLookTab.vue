<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  CUSTOMIZATION_DEFAULTS, STORE_ACCENTS, STORE_THEMES, STORE_TEMPLATES, STORE_TEMPLATE_FAMILIES,
  STORE_FONTS, STORE_FONT_GROUPS, STORE_FONT_PICKER, storeFontFamily, ensureStoreFont, ensureStoreFontPicker,
  NAME_FONT_SIZE_MIN, NAME_FONT_SIZE_MAX, allowedTemplatesFor,
  validateLogoFile, validateImageFile, LOGO_ACCEPT, formatStorageMB
} from '../../api/stores.api.js'
import { extractLogoColors, nearestAccent, hexToRgb, contrastRatio } from '../../utils/colorTools.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' }
})
const emit = defineEmits(['go-plans', 'ring'])

const store = useStoreStore()
const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const allowedTemplates = computed(() => allowedTemplatesFor(props.benefits || {}))

const steps = [
  { id: 'identity', icon: 'image', title: 'Identidad', sub: 'Tu logo', rec: 'Subí un logo cuadrado', ring: 'logo' },
  { id: 'colors', icon: 'palette', title: 'Colores', sub: 'Tema y color de acento', rec: 'Elegí un color de acento', ring: 'accent' },
  { id: 'type', icon: 'type', title: 'Tipografía', sub: 'Fuente y tamaño del nombre', rec: 'Elegí una tipografía', ring: 'font', premium: true },
  { id: 'style', icon: 'layout-grid', title: 'Portada y estilo', sub: 'Imagen de portada y diseño', rec: 'Sumá una portada luminosa', ring: 'cover' }
]

const currentLogo = computed(() => store.customization.logo || '')
const currentCover = computed(() => store.customization.cover || '')

const done = computed(() => ({
  identity: Boolean(currentLogo.value),
  colors: props.form.accent !== CUSTOMIZATION_DEFAULTS.accent || props.form.theme !== CUSTOMIZATION_DEFAULTS.theme,
  type: props.form.name_font !== CUSTOMIZATION_DEFAULTS.name_font || Number(props.form.name_font_size) !== CUSTOMIZATION_DEFAULTS.name_font_size,
  style: Boolean(currentCover.value) || props.form.template !== CUSTOMIZATION_DEFAULTS.template
}))
const doneCount = computed(() => steps.filter((s) => done.value[s.id]).length)

const open = ref('identity')
const headRefs = {}
function setRing(key) { emit('ring', key) }
function stepRing(id) { return steps.find((s) => s.id === id)?.ring || null }
function toggle(id) {
  open.value = open.value === id ? null : id
  setRing(open.value ? stepRing(open.value) : null)
}
function goStep(id) {
  open.value = id
  setRing(stepRing(id))
  document.getElementById(`dl-h-${id}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
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
const accentMeta = computed(() => STORE_ACCENTS[props.form.accent] || STORE_ACCENTS.indigo)
function pickAccent(key) {
  if (advanced.value) props.form.accent = key
}
function pickTheme(key) {
  props.form.theme = key
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
    logoColors.value = await extractLogoColors(src, { cors: src !== localLogoUrl })
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

const closestAccentKey = computed(() => (logoColors.value.length ? nearestAccent(hexToRgb(logoColors.value[0]), STORE_ACCENTS) : null))
function useLogoColor() {
  if (!advanced.value || !closestAccentKey.value) return
  props.form.accent = closestAccentKey.value
  colorMsg.value = `Elegimos ${STORE_ACCENTS[closestAccentKey.value].label}, el preset más parecido a tu logo.`
}

const pageBg = computed(() => (props.form.theme === 'dark' ? '#0d1220' : '#f4f6fb'))
const meters = computed(() => {
  const a = accentMeta.value
  const bg = contrastRatio(a.hex, pageBg.value)
  const btn = contrastRatio('#ffffff', a.ink)
  return [
    {
      key: 'bg', label: 'Acento sobre el fondo', ratio: bg, ok: bg >= 3,
      text: bg >= 3 ? 'Los detalles de color se distinguen bien del fondo.' : 'Los detalles cuestan verse sobre este fondo: probá otro acento o el otro tema.'
    },
    {
      key: 'btn', label: 'Texto del botón sobre el acento', ratio: btn, ok: btn >= 4.5,
      text: btn >= 4.5 ? 'El texto blanco de los botones se lee con comodidad.' : 'El texto blanco de los botones se lee con esfuerzo: elegí un acento más oscuro.'
    }
  ]
})

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

const storeTemplates = STORE_TEMPLATES
const templateFamilies = STORE_TEMPLATE_FAMILIES
const familyAllowed = (f) => f.templates.some((k) => allowedTemplates.value.includes(k))
const familyTier = (f) => (f.templates.some((k) => STORE_TEMPLATES[k]?.tier !== 'advanced') ? 'Desde Estándar' : 'Premium')
const selectedFamilyKey = ref('general')
const selectedFamily = computed(() => templateFamilies.find((f) => f.key === selectedFamilyKey.value) || templateFamilies[0])
const selectedFamilyAllowed = computed(() => selectedFamily.value.templates.filter((k) => allowedTemplates.value.includes(k)))
watch(() => props.form.template, (key) => {
  if (selectedFamily.value.templates.includes(key)) return
  const f = templateFamilies.find((f) => f.templates.includes(key))
  if (f) selectedFamilyKey.value = f.key
}, { immediate: true })
function onFamilyPick() {
  const first = selectedFamilyAllowed.value[0]
  if (first) props.form.template = first
}
function stepTemplate(dir) {
  const list = selectedFamilyAllowed.value
  if (list.length < 2) return
  const i = list.indexOf(props.form.template)
  props.form.template = list[(i + dir + list.length) % list.length]
}
function templatePlanLabel(key) {
  const tier = STORE_TEMPLATES[key]?.tier
  return tier === 'plus' ? 'Estándar' : tier === 'advanced' ? 'Premium' : ''
}
function templateTierLabel(key) {
  const tier = STORE_TEMPLATES[key]?.tier
  return tier === 'plus' ? 'Desde Estándar' : tier === 'advanced' ? 'Premium' : 'Todos los planes'
}

onBeforeUnmount(dropLocalLogo)
</script>

<template>
  <div class="card dsg-card dl-root">
    <h3><AppIcon name="palette" :size="18" /> Logo y colores</h3>

    <div class="dl-progress">
      <div class="dl-progress-head">
        <strong><AppIcon name="badge-check" :size="16" aria-hidden="true" /> Identidad visual</strong>
        <span class="dl-progress-count">{{ doneCount }}/4</span>
      </div>
      <div class="dl-bar" role="progressbar" aria-label="Identidad visual completada" aria-valuemin="0" aria-valuemax="4" :aria-valuenow="doneCount">
        <span :style="{ transform: `scaleX(${doneCount / 4})` }"></span>
      </div>
      <ul class="dl-checks">
        <li v-for="s in steps" :key="s.id">
          <button type="button" class="dl-check" :class="{ done: done[s.id] }" @click="goStep(s.id)">
            <span class="dl-check-ico" aria-hidden="true"><AppIcon v-if="done[s.id]" name="check" :size="12" :stroke="3" /></span>
            <span class="dl-check-txt">{{ s.rec }}</span>
            <span v-if="!advanced && (s.id === 'colors' || s.id === 'type')" class="dl-check-lock"><AppIcon name="lock" :size="11" :stroke="2" aria-hidden="true" /> Premium</span>
            <span class="sr-only">{{ done[s.id] ? '(completo)' : '(pendiente)' }}</span>
          </button>
        </li>
      </ul>
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
              <strong><span class="dl-step-n">{{ i + 1 }}</span>{{ s.title }}</strong>
              <small>{{ s.sub }}</small>
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
                  class="swatch" :class="{ active: form.accent === key }"
                  :style="{ '--swatch': a.hex }"
                  :title="a.label" :aria-label="`Color ${a.label}`"
                  :aria-disabled="!advanced"
                  :aria-pressed="form.accent === key"
                  @click="pickAccent(key)"
                >
                  <AppIcon v-if="form.accent === key" name="check" :size="14" :stroke="2.5" />
                </button>
              </div>
              <p class="hint">Se aplica a la portada, los botones y los detalles.</p>
            </div>
            <div class="field dl-logo-color" :class="{ locked: !advanced }">
              <label><AppIcon name="pipette" :size="14" class="label-icon" aria-hidden="true" />Color de tu logo</label>
              <template v-if="currentLogo">
                <div class="dl-chips" aria-live="polite">
                  <span v-if="colorBusy" class="spinner" aria-hidden="true"></span>
                  <span v-for="c in logoColors" :key="c" class="dl-chip" :style="{ background: c }" :title="c" role="img" :aria-label="`Color dominante ${c}`"></span>
                  <button type="button" class="btn ghost btn-auto dl-use-logo" :disabled="!advanced || !closestAccentKey || colorBusy" @click="useLogoColor">
                    <AppIcon name="pipette" :size="16" /> Usar color de mi logo
                  </button>
                </div>
                <p v-if="colorMsg" class="hint" role="status">{{ colorMsg }}</p>
                <p v-else class="hint">Elegimos el acento más parecido a los colores de tu logo.</p>
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
            <div class="field" @focusin="setRing('cover')">
              <label for="design-family"><AppIcon name="layout-grid" :size="14" class="label-icon" aria-hidden="true" />Diseño de tu web</label>
              <div class="tpl-selects">
                <div class="tpl-field">
                  <label for="design-family" class="tpl-label">Categoría</label>
                  <select id="design-family" v-model="selectedFamilyKey" class="select" @change="onFamilyPick">
                    <option v-for="f in templateFamilies" :key="f.key" :value="f.key" :disabled="!familyAllowed(f)">{{ f.label }}<template v-if="!familyAllowed(f)"> · {{ familyTier(f) }}</template></option>
                  </select>
                </div>
                <div class="tpl-field">
                  <label for="design-template" class="tpl-label">Estilo</label>
                  <select id="design-template" v-model="form.template" class="select">
                    <option v-for="key in selectedFamily.templates" :key="key" :value="key" :disabled="!allowedTemplates.includes(key)">{{ storeTemplates[key]?.label }}<template v-if="!allowedTemplates.includes(key)"> · {{ templatePlanLabel(key) }}</template></option>
                  </select>
                </div>
              </div>
              <div class="pick-preview" aria-live="polite">
                <span class="tpl-thumb pick-preview-thumb" :data-tpl="form.template" aria-hidden="true"><i><b></b><b></b><b></b></i></span>
                <div class="pick-preview-info">
                  <span class="pick-preview-eyebrow">Diseño elegido</span>
                  <strong>{{ storeTemplates[form.template]?.label }}</strong>
                  <small>{{ storeTemplates[form.template]?.desc }}</small>
                  <span class="pick-tier" :class="storeTemplates[form.template]?.tier">{{ templateTierLabel(form.template) }}</span>
                </div>
                <div class="pick-nav">
                  <button type="button" class="icon-btn" aria-label="Diseño anterior" :disabled="selectedFamilyAllowed.length < 2" @click="stepTemplate(-1)"><AppIcon name="chevron-left" :size="15" /></button>
                  <button type="button" class="icon-btn" aria-label="Diseño siguiente" :disabled="selectedFamilyAllowed.length < 2" @click="stepTemplate(1)"><AppIcon name="chevron-right" :size="15" /></button>
                </div>
              </div>
              <p class="hint">Cambia la estructura de tu portada sin perder contenido. Los bloqueados se habilitan con otro plan.</p>
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
</template>

<style>
.dl-root { container-type: inline-size; }
.dl-progress { display: grid; gap: 10px; padding: 14px; margin-bottom: 14px; border: 1px solid var(--line); border-radius: 14px; background: linear-gradient(135deg, var(--brand-soft), transparent 70%), var(--card); min-width: 0; }
.dl-progress-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }
.dl-progress-head strong { display: inline-flex; align-items: center; gap: 7px; font-size: 14px; min-width: 0; color: var(--ink); }
.dl-progress-head .icon { color: var(--brand-600); flex: none; }
.dl-progress-count { flex: none; font-size: 13px; font-weight: 800; color: var(--brand-ink); font-variant-numeric: tabular-nums; }
.dl-bar { height: 8px; border-radius: 99px; background: var(--line); overflow: hidden; }
.dl-bar span { display: block; height: 100%; width: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--brand-500), var(--accent)); transform-origin: 0 50%; transition: transform .22s ease; }
.dl-checks { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.dl-check { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 44px; min-width: 0; padding: 6px 10px; border: 1px solid transparent; border-radius: 10px; background: transparent; font: inherit; font-size: 13px; font-weight: 600; text-align: left; color: var(--ink-2); cursor: pointer; }
.dl-check:hover { background: var(--surface); }
.dl-check-ico { flex: none; display: grid; place-items: center; width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--line-strong, var(--line)); color: #fff; }
.dl-check.done .dl-check-ico { border-color: var(--ok); background: var(--ok); }
.dl-check.done .dl-check-txt { color: var(--muted); text-decoration: line-through; text-decoration-color: color-mix(in srgb, var(--muted) 50%, transparent); }
.dl-check-txt { min-width: 0; flex: 1; overflow-wrap: anywhere; line-height: 1.3; }
.dl-check-lock { flex: none; display: inline-flex; align-items: center; gap: 3px; font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--brand-ink); }
@container (max-width: 440px) { .dl-checks { grid-template-columns: minmax(0, 1fr); } }

.dl-steps { display: grid; gap: 10px; min-width: 0; }
.dl-step { border: 1px solid var(--line); border-radius: 14px; background: var(--card); min-width: 0; }
.dl-step.open { border-color: color-mix(in srgb, var(--brand-500) 45%, var(--line)); box-shadow: var(--shadow-sm); }
.dl-step-h { margin: 0; font-size: inherit; }
.dl-step-btn { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 64px; min-width: 0; padding: 10px 14px; border: 0; border-radius: 14px; background: transparent; font: inherit; text-align: left; color: var(--ink); cursor: pointer; }
.dl-step-btn:hover { background: var(--surface); }
.dl-step-btn:focus-visible, .dl-check:focus-visible, .dl-filter:focus-visible, .dl-font:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.dl-step-ico { flex: none; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px; background: var(--brand-soft); color: var(--brand-600); }
.dl-step.done .dl-step-ico { background: var(--ok-bg); color: var(--ok-ink); }
.dl-step-txt { display: grid; gap: 2px; flex: 1; min-width: 0; }
.dl-step-txt strong { display: flex; align-items: center; gap: 8px; font-size: 14.5px; line-height: 1.25; min-width: 0; }
.dl-step-txt small { color: var(--muted); font-size: 12.5px; line-height: 1.35; overflow-wrap: anywhere; }
.dl-step-n { flex: none; display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 6px; background: var(--ink); color: var(--card); font-size: 11px; font-weight: 800; }
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
</style>
