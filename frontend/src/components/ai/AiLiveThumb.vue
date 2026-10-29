<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import DesignPreview from '../design/DesignPreview.vue'
import { STUDIO_MSG, isStudioMessage } from '../../studio/contract.js'
import { buildStudioUpdate, originOf, previewSrc } from './aiPreviewPayload.js'

// Miniatura EXACTA de una propuesta: monta la landing real de la tienda en
// un iframe (?studio=1) a 1280px de ancho y la escala al tamaño de la
// tarjeta. Es la misma página que ve el visitante con la propuesta aplicada,
// no un mockup: si cambia el copy, el layout o el tema, la miniatura cambia.
// Sin slug o si no carga, cae al mockup de DesignPreview.
const props = defineProps({
  proposal: { type: Object, required: true },
  form: { type: Object, default: () => ({}) },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'raiz' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  nameFont: { type: Object, default: () => ({}) },
  publicUrl: { type: String, default: '' }
})

// Ancho lógico del "navegador" de la miniatura: el layout de escritorio real.
const LOGICAL_W = 1280
const LOGICAL_H = 900

const root = ref(null)
const frameEl = ref(null)
const loaded = ref(false)
const failed = ref(false)
const active = ref(false)
const width = ref(0)

const src = computed(() => previewSrc(props.publicUrl))
const live = computed(() => Boolean(src.value) && !failed.value)
const scale = computed(() => (width.value ? width.value / LOGICAL_W : 0))
const frameStyle = computed(() => ({
  width: `${LOGICAL_W}px`,
  height: `${LOGICAL_H}px`,
  transform: `scale(${scale.value})`
}))
const mode = computed(() => (props.proposal?.night_mode?.default === 'dark' ? 'dark' : 'light'))

let io = null
let ro = null
let postTimer = null
let loadTimer = null

function postNow() {
  const win = frameEl.value?.contentWindow
  if (!win || !live.value) return
  win.postMessage(buildStudioUpdate({
    proposal: props.proposal,
    form: props.form,
    template: props.template,
    mode: mode.value,
    device: 'desktop',
    shopName: props.shopName,
    logo: props.logo,
    cover: props.cover
  }), originOf(src.value))
}
function queuePost() {
  clearTimeout(postTimer)
  postTimer = setTimeout(postNow, 60)
}

function onFrameLoad() {
  loaded.value = true
  clearTimeout(loadTimer)
  postNow()
}

function onMessage(e) {
  const win = frameEl.value?.contentWindow
  if (!win || e.source !== win) return
  if (!isStudioMessage(e.data)) return
  if (e.data.type === STUDIO_MSG.READY) postNow()
}

// La miniatura no se carga hasta que la tarjeta entra en pantalla: tres
// iframes de la web completa al abrir la lista sería un costo innecesario.
function activate() {
  if (active.value) return
  active.value = true
  if (!src.value) return
  loadTimer = setTimeout(() => { if (!loaded.value) failed.value = true }, 12000)
  nextTick(postNow)
}

function measure() {
  const el = root.value
  if (!el) return
  width.value = el.clientWidth
}

watch(
  () => [props.proposal, props.form, props.template, props.cover, props.logo],
  () => { if (active.value) queuePost() },
  { deep: true }
)
watch(src, () => {
  loaded.value = false
  failed.value = false
  if (active.value) activate()
})

onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined' && root.value) {
    ro = new ResizeObserver(measure)
    ro.observe(root.value)
  }
  if (typeof IntersectionObserver !== 'undefined' && root.value) {
    io = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        activate()
        io?.disconnect()
        io = null
      }
    }, { rootMargin: '200px' })
    io.observe(root.value)
  } else {
    activate()
  }
  window.addEventListener('message', onMessage)
})

onBeforeUnmount(() => {
  clearTimeout(postTimer)
  clearTimeout(loadTimer)
  io?.disconnect()
  ro?.disconnect()
  window.removeEventListener('message', onMessage)
})
</script>

<template>
  <div ref="root" class="aid-thumb">
    <iframe
      v-if="active && live"
      ref="frameEl"
      class="aid-thumb-frame"
      :src="src"
      :title="`Miniatura de ${proposal.label}`"
      tabindex="-1"
      aria-hidden="true"
      :style="frameStyle"
      @load="onFrameLoad"
    ></iframe>

    <DesignPreview
      v-if="!live"
      class="aid-thumb-mock"
      :form="form"
      :vars="vars"
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

    <span v-if="live && !loaded" class="aid-thumb-skel" aria-hidden="true"></span>
  </div>
</template>
