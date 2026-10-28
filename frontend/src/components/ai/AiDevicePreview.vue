<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'
import DesignPreview from '../design/DesignPreview.vue'
import { storeThemeVars } from '../../api/stores.api.js'
import { STUDIO_MSG, isStudioMessage, studioUpdate } from '../../studio/contract.js'

// Vista previa por dispositivo de una propuesta de "Diseñar con IA".
// Monta la LANDING REAL de la tienda en un iframe (?studio=1) y le empuja la
// propuesta por el protocolo del Studio (studio:update): la página se
// renderiza con sus propios componentes, CSS y media queries, así el marco
// móvil/tablet/escritorio es un viewport de verdad y no un mockup.
// Sin slug (tienda sin dirección) cae al mockup de DesignPreview.
const props = defineProps({
  proposal: { type: Object, required: true },
  form: { type: Object, default: () => ({}) },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'classic' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  nameFont: { type: Object, default: () => ({}) },
  nightMode: { type: Object, default: () => ({ enabled: false, default: 'light' }) },
  publicUrl: { type: String, default: '' }
})
const emit = defineEmits(['close'])

const DEVICES = [
  { id: 'mobile', label: 'Móvil', icon: 'smartphone', w: 390, h: 844 },
  { id: 'tablet', label: 'Tablet', icon: 'tablet', w: 834, h: 1112 },
  { id: 'desktop', label: 'Escritorio', icon: 'monitor', w: 1440, h: 900 }
]

// Arranca en escritorio: es el tamaño donde el diseño se ve completo y el
// panel ancho no queda vacío. Móvil/tablet quedan a un click.
const device = ref('desktop')
const dark = ref(props.nightMode?.default === 'dark')
const panel = ref(null)
const area = ref(null)
const frameEl = ref(null)
const loaded = ref(false)
const failed = ref(false)
const scale = ref(0.5)
const current = computed(() => DEVICES.find((d) => d.id === device.value) || DEVICES[0])
const canToggleNight = computed(() => Boolean(props.nightMode?.enabled))
const scalePct = computed(() => Math.round(scale.value * 100))

// Landing real: mismo camino que el lienzo del Studio (/<slug>?studio=1).
const src = computed(() => (props.publicUrl ? `${props.publicUrl}?studio=1` : ''))
const live = computed(() => Boolean(src.value) && !failed.value)
// El subdominio de la tienda puede ser otro origen: se postea al origen real
// del iframe (mismo criterio que el lienzo del Studio).
function targetOrigin() {
  try { return new URL(src.value, window.location.href).origin } catch { return window.location.origin }
}

const previewForm = computed(() => (canToggleNight.value
  ? { ...props.form, theme: dark.value ? 'dark' : 'light' }
  : props.form))
const previewVars = computed(() => props.vars || storeThemeVars(previewForm.value))
watch(() => props.nightMode, (nm) => { dark.value = nm?.default === 'dark' })
const frameStyle = computed(() => ({
  width: `${Math.round(current.value.w * scale.value)}px`,
  height: `${Math.round(current.value.h * scale.value)}px`
}))
const screenStyle = computed(() => ({
  '--aidv-w': `${current.value.w}px`,
  '--aidv-h': `${current.value.h}px`,
  transform: `scale(${scale.value})`
}))

// ---------------------------------------------------------------------------
// studio:update — la propuesta como si fuera el borrador del Studio.
// ---------------------------------------------------------------------------
const clone = (value) => {
  try { return JSON.parse(JSON.stringify(value)) } catch { return null }
}
// Campos del form que NO van como `custom`: el tema y el layout viajan en sus
// propias claves del mensaje.
const CUSTOM_SKIP = new Set(['site_theme', 'site_theme_draft', 'layout_config', 'layout_config_draft', 'template', 'template_draft'])

// copy_draft -> campos de negocio de la web (los nombres cambian: `steps`
// se persiste en service_steps).
function draftFields(draft) {
  if (!draft || typeof draft !== 'object') return {}
  const out = {}
  for (const key of ('about_text', 'about_mission', 'faqs', 'services', 'announcements')) {
    if (draft[key]) out[key] = draft[key]
  }
  if (Array.isArray(draft.steps) && draft.steps.length) out.service_steps = draft.steps
  return out
}

function buildUpdate() {
  const custom = {}
  for (const [key, value] of Object.entries(props.form || {})) {
    if (!CUSTOM_SKIP.has(key)) custom[key] = value
  }
  Object.assign(
    custom,
    props.proposal?.copy || {},
    draftFields(props.proposal?.copy_draft),
    {
      display_name: props.shopName || custom.display_name,
      logo: props.logo || null,
      cover: props.cover || null
    }
  )
  const message = studioUpdate({
    theme: props.proposal?.site_theme || props.form?.site_theme || {},
    layout: clone(props.proposal?.layout_config || {}) || {},
    template: props.template,
    device: device.value
  })
  message.mode = dark.value ? 'dark' : 'light'
  message.custom = clone(custom) || {}
  return message
}

let postTimer = null
function postNow() {
  const win = frameEl.value?.contentWindow
  if (!win || !live.value) return
  win.postMessage(buildUpdate(), targetOrigin())
}
function queuePost() {
  clearTimeout(postTimer)
  postTimer = setTimeout(postNow, 40)
}

let loadTimer = null
function onFrameLoad() {
  loaded.value = true
  failed.value = false
  clearTimeout(loadTimer)
  postNow()
}
// Si la página no carga (subdominio sin DNS, red caída) se cae al mockup en
// vez de dejar el marco vacío para siempre.
function watchLoad() {
  clearTimeout(loadTimer)
  if (!src.value) return
  loadTimer = setTimeout(() => { if (!loaded.value) failed.value = true }, 12000)
}
watch(src, () => { loaded.value = false; failed.value = false; nextTick(watchLoad) })

function onMessage(e) {
  const win = frameEl.value?.contentWindow
  if (!win || e.source !== win) return
  if (!isStudioMessage(e.data)) return
  // El iframe avisa al montar: recién ahí tiene el listener listo.
  if (e.data.type === STUDIO_MSG.READY) postNow()
}

watch(
  () => [props.proposal, props.form, props.template, props.cover, props.logo, dark.value, device.value],
  queuePost,
  { deep: true }
)

let raf = 0
let ro = null
let previousFocus = null
let prevOverflow = ''

// El marco del dispositivo (::after) crece hacia afuera: se descuenta del
// área disponible (padding del stage + bezel) para que el equipo entre
// completo y lo más grande posible sin recortarse.
const PAD = 24
const CHROME = { mobile: 22, tablet: 26, desktop: 14 }

function measure() {
  raf = 0
  const el = area.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const chrome = CHROME[current.value.id] || 20
  const s = Math.min(
    (rect.width - PAD * 2 - chrome * 2) / current.value.w,
    (rect.height - PAD * 2 - chrome * 2) / current.value.h,
    1
  )
  scale.value = Math.max(0.12, Math.round(s * 1000) / 1000)
}
function schedule() {
  if (raf) cancelAnimationFrame(raf)
  raf = requestAnimationFrame(measure)
}

watch(device, () => nextTick(schedule))

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
function onKey(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
    return
  }
  if (e.key !== 'Tab' || !panel.value) return
  const els = [...panel.value.querySelectorAll(FOCUSABLE)].filter((el) => !el.disabled && el.offsetParent !== null)
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  previousFocus = document.activeElement
  prevOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('message', onMessage)
  watchLoad()
  if (typeof ResizeObserver !== 'undefined' && area.value) {
    ro = new ResizeObserver(schedule)
    ro.observe(area.value)
  }
  window.addEventListener('resize', schedule)
  nextTick(() => {
    panel.value?.focus()
    schedule()
  })
})
onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  clearTimeout(postTimer)
  clearTimeout(loadTimer)
  ro?.disconnect()
  window.removeEventListener('message', onMessage)
  window.removeEventListener('resize', schedule)
  document.body.style.overflow = prevOverflow
  if (previousFocus && typeof previousFocus.focus === 'function') previousFocus.focus()
})
</script>

<template>
  <div class="aid-modal" @click.self="emit('close')">
    <div
      ref="panel"
      class="aidv-box"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aidv-title"
      tabindex="-1"
      @keydown="onKey"
    >
      <header class="aidv-head">
        <div class="aidv-head-text">
          <h2 id="aidv-title">{{ proposal.label }}</h2>
          <p v-if="proposal.why">{{ proposal.why }}</p>
        </div>
        <button class="icon-btn" type="button" aria-label="Cerrar vista previa" @click="emit('close')">
          <AppIcon name="x" :size="18" />
        </button>
      </header>

      <div class="aidv-bar">
        <div class="aidv-seg" role="group" aria-label="Tamaño de pantalla">
          <button
            v-for="d in DEVICES"
            :key="d.id"
            type="button"
            class="aidv-seg-btn"
            :class="{ active: device === d.id }"
            :aria-pressed="device === d.id"
            @click="device = d.id"
          >
            <AppIcon :name="d.icon" :size="17" aria-hidden="true" />
            <span>{{ d.label }}</span>
          </button>
        </div>

        <button
          v-if="canToggleNight"
          type="button"
          class="btn ghost btn-auto"
          :aria-pressed="dark"
          @click="dark = !dark"
        >
          <AppIcon :name="dark ? 'moon' : 'sun'" :size="16" />
          {{ dark ? 'Modo oscuro' : 'Modo claro' }}
        </button>
        <p class="aidv-size">{{ current.w }} × {{ current.h }} px · {{ scalePct }}%</p>
      </div>

      <div ref="area" class="aidv-area">
        <div class="aidv-device" :class="`dev-${device}`" :style="frameStyle">
          <div class="aidv-screen" :style="screenStyle">
            <!-- Landing real de la tienda, con la propuesta aplicada -->
            <iframe
              v-if="live"
              ref="frameEl"
              class="aidv-frame"
              :src="src"
              :title="`Vista previa de ${shopName || 'tu web'}`"
              @load="onFrameLoad"
            ></iframe>
            <!-- Sin dirección web todavía: mockup del diseño -->
            <DesignPreview
              v-else
              :form="previewForm"
              :vars="previewVars"
              :template="template"
              :shop-name="shopName"
              :initial="initial"
              :logo="logo"
              :cover="cover"
              :advanced="advanced"
              :catalog-on="true"
              :show-map="showMap"
              :name-font="nameFont"
            />
          </div>
        </div>
        <div v-if="live && !loaded" class="aidv-loading" aria-live="polite">
          <span class="aidv-skel"></span>
          <span class="aidv-skel mid"></span>
          <span class="aidv-skel short"></span>
          <p>Cargando tu página…</p>
        </div>
      </div>
    </div>
  </div>
</template>
