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
  //Superficie visible del documento: landing | catalog | services | product.
  //El diseño marca cada bloque con `data-surface` y el resto se oculta.
  surface: { type: String, default: 'landing' },
  //Id del producto cuando la superficie es `product`: el backend resuelve
  //las variables product_* del documento con esa ficha.
  product: { type: [String, Number], default: '' }
})

const frame = ref(null)
const height = ref(0)

//El tema va en la URL solo en la carga inicial: al alternar claro/oscuro
//el puente (`davent:ds-theme`) cambia data-ds-theme sin recargar el
//documento — si theme estuviera en el src reactivo, cada toggle recargaría
//el iframe y la página saltaría.
const mountTheme = props.theme
const src = computed(() => {
  const params = new URLSearchParams({ theme: mountTheme, surface: props.surface })
  if (props.preview) params.set('preview', props.preview)
  if (props.preview && props.template) params.set('template', props.template)
  if (props.revision) params.set('v', props.revision)
  if (props.product) params.set('product', String(props.product))
  return `/api/stores/public/${encodeURIComponent(props.slug)}/pattern/document/?${params}`
})

const emit = defineEmits(['navigate', 'toggle-theme'])

//El iframe va sin `allow-same-origin` (origen opaco): el JS del diseño no
//puede tocar el DOM ni las cookies de la app. Los datos que necesita de la
//API pública (captcha y opiniones del producto) los pide por postMessage y
//los busca este componente, que sí es mismo origen.
//Whitelist cerrada: el documento no elige el endpoint. Solo estas dos
//rutas de la tienda que embebe, y siempre con su slug (nunca el de otra).
const PUBLIC_API_RE = /^\/api\/stores\/public\/[a-z0-9-]+\/(?:reviews\/captcha|contact\/captcha|contact|products\/\d+\/reviews)\/?$/

function publicApiUrl(raw) {
  const url = String(raw || '')
  if (!PUBLIC_API_RE.test(url)) return ''
  return url.replace(/^\/api\/stores\/public\/[a-z0-9-]+\//, `/api/stores/public/${props.slug}/`)
}

async function relayApi(event) {
  const id = String(event.data?.id || '')
  if (!id) return
  const url = publicApiUrl(event.data.url)
  let result = null
  if (url) {
    try {
      const options = event.data.method === 'POST'
        ? {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(event.data.body || {}),
          }
        : undefined
      const res = await fetch(url, options)
      const data = await res.json().catch(() => null)
      result = { ok: res.ok, data }
    } catch {
      result = { ok: false, data: null }
    }
  }
  frame.value?.contentWindow?.postMessage({ type: 'davent:ds-api-result', id, result }, '*')
}

function onMessage(e) {
  if (e.source !== frame.value?.contentWindow) return
  if (e.data?.type === 'davent:ds-api') {
    relayApi(e)
    return
  }
  if (e.data?.type === 'davent:ds-open') {
    /* Link externo del documento (redirect de contacto): se abre desde el
     * host, que es mismo origen y no está sandboxeado. La URL se reescribe
     * al slug de ESTA tienda — el documento nunca elige a dónde navegar. */
    const raw = String(e.data.url || '')
    if (/^\/api\/stores\/public\/[a-z0-9-]+\/r\/[a-z]+\/?(\?[^\s"'<>]*)?$/.test(raw)) {
      const url = raw.replace(/^\/api\/stores\/public\/[a-z0-9-]+\//, `/api/stores/public/${props.slug}/`)
      window.open(url, '_blank', 'noopener')
    }
    return
  }
  if (e.data?.type === 'davent:ds-theme-toggle') {
    emit('toggle-theme')
    return
  }
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
  postFrame()
}

/* El iframe se estira al alto del documento (ds-height): un `position:fixed`
 * dentro queda clavado al documento completo, no al viewport — la barra y la
 * tab bar del diseño terminan una arriba del todo y otra abajo del todo. El
 * puente las corre con top/bottom según este rectángulo del marco. */
let frameRaf = 0
function postFrame() {
  if (frameRaf) return
  frameRaf = requestAnimationFrame(() => {
    frameRaf = 0
    const el = frame.value
    if (!el) return
    const r = el.getBoundingClientRect()
    post('davent:ds-frame', { top: r.top, bottom: r.bottom, vh: window.innerHeight })
  })
}

watch(() => props.theme, syncTheme)
watch(() => props.surface, () => {
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
})

if (typeof window !== 'undefined') {
  window.addEventListener('message', onMessage)
  window.addEventListener('scroll', postFrame, { passive: true })
  window.addEventListener('resize', postFrame)
}
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  window.removeEventListener('scroll', postFrame)
  window.removeEventListener('resize', postFrame)
  if (frameRaf) cancelAnimationFrame(frameRaf)
})
</script>

<template>
  <iframe
    ref="frame"
    class="ds-surface"
    :src="src"
    :title="title || 'Diseño de la web'"
    :style="height ? { height: `${height}px` } : null"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-forms"
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
