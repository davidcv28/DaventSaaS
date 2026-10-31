<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

// Documento real de un diseño del catálogo (DesignPattern):
// GET /api/stores/public/<slug>/pattern/document/ devuelve el HTML con los
// datos de la tienda y las variables resueltas. Se carga como `src` (no
// `srcdoc`) para que el documento tenga su propia política: el CSP de
// producción (`script-src 'self'`) bloquea los scripts inline y con
// `srcdoc` el iframe heredaba esa política y quedaba sin puente (alto
// roto, secciones `.reveal` ocultas, toggle de tema muerto).
// El alto viaja por postMessage y el modo claro/oscuro también.
const props = defineProps({
  slug: { type: String, required: true },
  preview: { type: String, default: '' },
  //Diseño en ensayo del Studio: el backend solo lo acepta junto al token
  //de vista previa (la web pública nunca lo lee).
  template: { type: String, default: '' },
  //Huella de lo que el documento pinta desde la base (logo/portada): al
  //cambiar, el iframe se recarga con los datos nuevos.
  revision: { type: String, default: '' },
  theme: { type: String, default: 'light' },
  title: { type: String, default: '' },
  //Superficie visible del documento: landing | catalog | services. El
  //diseño marca cada bloque con `data-surface` y el resto se oculta.
  surface: { type: String, default: 'landing' }
})

const frame = ref(null)
const height = ref(0)

const src = computed(() => {
  const params = new URLSearchParams({ theme: props.theme, surface: props.surface })
  if (props.preview) params.set('preview', props.preview)
  if (props.preview && props.template) params.set('template', props.template)
  if (props.revision) params.set('v', props.revision)
  return `/api/stores/public/${encodeURIComponent(props.slug)}/pattern/document/?${params}`
})

const emit = defineEmits(['navigate'])

function onMessage(e) {
  if (e.source !== frame.value?.contentWindow) return
  if (e.data?.type === 'davent:ds-route') {
    const route = String(e.data.route || '')
    if (['home', 'catalog', 'services'].includes(route)) {
      emit('navigate', { route })
    } else if (route === 'product' && e.data.id) {
      emit('navigate', { route, id: String(e.data.id) })
    }
    return
  }
  if (e.data?.type !== 'davent:ds-height') return
  const next = Number(e.data.height) || 0
  if (next > 0) height.value = next
}

function post(type, payload) {
  frame.value?.contentWindow?.postMessage({ type, ...payload }, '*')
}

function syncTheme() {
  post('davent:ds-theme', { theme: props.theme })
  post('davent:ds-measure', {})
}

function onLoad() {
  height.value = 0
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
}

watch(() => props.theme, syncTheme)
watch(() => props.surface, () => {
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
})

if (typeof window !== 'undefined') window.addEventListener('message', onMessage)
onBeforeUnmount(() => window.removeEventListener('message', onMessage))
</script>

<template>
  <iframe
    ref="frame"
    class="ds-surface"
    :src="src"
    :title="title || 'Diseño de la web'"
    :style="height ? { height: `${height}px` } : null"
    sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms"
    loading="lazy"
    @load="onLoad"
  ></iframe>
</template>

<style scoped>
.ds-surface {
  display: block;
  width: 100%;
  min-height: 70vh;
  border: 0;
  background: transparent;
}
</style>
