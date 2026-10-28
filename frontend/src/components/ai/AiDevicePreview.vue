<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'
import DesignPreview from '../design/DesignPreview.vue'
import { storeThemeVars } from '../../api/stores.api.js'

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
  nightMode: { type: Object, default: () => ({ enabled: false, default: 'light' }) }
})
const emit = defineEmits(['close'])

const DEVICES = [
  { id: 'mobile', label: 'Móvil', icon: 'smartphone', w: 390, h: 844 },
  { id: 'tablet', label: 'Tablet', icon: 'tablet', w: 834, h: 1112 },
  { id: 'desktop', label: 'Escritorio', icon: 'monitor', w: 1440, h: 900 }
]

const device = ref('mobile')
const dark = ref(props.nightMode?.default === 'dark')
const panel = ref(null)
const area = ref(null)
const scale = ref(0.5)
const current = computed(() => DEVICES.find((d) => d.id === device.value) || DEVICES[0])
const canToggleNight = computed(() => Boolean(props.nightMode?.enabled))

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

let raf = 0
let ro = null
let previousFocus = null
let prevOverflow = ''

function measure() {
  raf = 0
  const el = area.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const s = Math.min((rect.width - 36) / current.value.w, (rect.height - 36) / current.value.h, 1)
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
  ro?.disconnect()
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
      </div>

      <div ref="area" class="aidv-area">
        <div class="aidv-device" :class="`dev-${device}`" :style="frameStyle">
          <div class="aidv-screen" :style="screenStyle">
            <DesignPreview
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
      </div>

      <p class="aidv-size">{{ current.w }} × {{ current.h }}</p>
      <div class="aidv-foot">
        <button class="btn ghost btn-auto" type="button" @click="emit('close')">Cerrar</button>
      </div>
    </div>
  </div>
</template>
