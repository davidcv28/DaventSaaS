<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

// Lienzo de un diseño del catálogo (DesignPattern) servido por
// GET /api/stores/public/<slug>/pattern/: el backend interpola las
// variables contra los datos de la tienda y devuelve HTML + CSS + JS.
// Se monta en un iframe sin `allow-same-origin`: el CSS del diseño no
// puede pisar la app y el documento no toca la página que lo embebe.
// El alto viaja por postMessage (el iframe no puede medir el host) y el
// modo claro/oscuro se sincroniza por el mismo canal.
const props = defineProps({
  doc: { type: Object, required: true },
  theme: { type: String, default: 'light' },
  title: { type: String, default: '' }
})

const frame = ref(null)
const height = ref(0)

// Script de puente: mide el documento, avisa el alto al host y escucha el
// cambio de modo (los diseños pintan `html[data-ds-theme]`).
const BRIDGE = `
(function () {
  var root = document.documentElement;
  function send() {
    var h = Math.max(root.scrollHeight, document.body ? document.body.scrollHeight : 0);
    parent.postMessage({ type: 'davent:ds-height', height: h }, '*');
  }
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.type === 'davent:ds-theme') root.setAttribute('data-ds-theme', d.theme);
    if (d.type === 'davent:ds-measure') send();
  });
  window.addEventListener('load', send);
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root);
  else setTimeout(send, 120);
  send();
})();
`

const srcdoc = computed(() => {
  const doc = props.doc || {}
  const css = doc.css || ''
  // El markup del seed ya trae su <script> al final del body: el campo
  // `js` solo se agrega cuando el diseño no lo incluyó.
  const inline = /<script[\s>]/i.test(doc.html || '') ? '' : `<script>${doc.js || ''}<\/script>`
  return `<!doctype html><html lang="es" data-ds-theme="${props.theme}"><head><meta charset="utf-8">`
    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
    + `<style>html,body{margin:0}${css}</style></head><body>`
    + `${doc.html || ''}${inline}<script>${BRIDGE}<\/script></body></html>`
})

function onMessage(e) {
  if (e.source !== frame.value?.contentWindow) return
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

watch(() => props.theme, syncTheme)
watch(() => props.doc, () => { height.value = 0 })

if (typeof window !== 'undefined') window.addEventListener('message', onMessage)
onBeforeUnmount(() => window.removeEventListener('message', onMessage))
</script>

<template>
  <iframe
    ref="frame"
    class="ds-surface"
    :srcdoc="srcdoc"
    :title="title || doc.nombre || 'Diseño de la web'"
    :style="height ? { height: `${height}px` } : null"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-forms"
    loading="lazy"
    @load="syncTheme"
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
