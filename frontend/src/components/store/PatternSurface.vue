<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useCartStore } from '../../stores/cart.store.js'
import { customerHttp } from '../../api/customer.http.js'
import { storeHostSlug } from '../../config/env.js'

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
  //Estilo en ensayo (slug DesignStyle): viaja en la URL porque el puente
  //no puede recolorear un iframe de origen opaco — la paleta/fuentes del
  //estilo se hornean en el render del documento (theme_css).
  style: { type: String, default: '' },
  //Huella del contenido del patrón y recursos de preview: cambia la URL del
  //iframe para que el navegador no reutilice un documento HTML/CSS obsoleto.
  revision: { type: String, default: '' },
  theme: { type: String, default: 'light' },
  title: { type: String, default: '' },
  //Superficie visible del documento: landing | catalog | services | product.
  //El diseño marca cada bloque con `data-surface` y el resto se oculta.
  surface: { type: String, default: 'landing' },
  //Id del producto cuando la superficie es `product`: el backend resuelve
  //las variables product_* del documento con esa ficha.
  product: { type: [String, Number], default: '' },
  //CSS del Studio (editores finos de site_theme) para documentos de
  //diseño: en la web publicada lo hornea el backend en el documento;
  //en la vista previa del Studio viaja por postMessage porque el iframe
  //es de origen opaco. Vacío = sin reglas del Studio.
  studioCss: { type: String, default: '' },
  //Sesión del comprador: el documento es origen opaco (no lee cookies) —
  //el host se la empuja por `davent:ds-account-state` y el botón del
  //puente cambia de "Ingresar" a "Mi cuenta".
  account: { type: Boolean, default: false },
  //Modo "chrome": el documento se fija arriba de la página como una tira
  //del alto de su cromo (header + barras fijas) sobre las rutas que el
  //diseño no pinta (auth, cuenta, carrito, checkout, seguimiento). Las
  //superficies de contenido quedan ocultas en el propio documento y el
  //iframe crece a pantalla completa solo mientras el diseño tenga una
  //hoja modal abierta (ds-lock) para que el menú sea usable.
  chrome: { type: Boolean, default: false }
})

const frame = ref(null)
const height = ref(0)
//Hoja modal del diseño abierta (ds-lock): en modo chrome la tira crece a
//viewport completo para que el menú/hoja del diseño sea usable.
const chromeLocked = ref(false)
const frameStyle = computed(() => {
  if (props.chrome) {
    if (chromeLocked.value) return { height: '100vh' }
    return { height: `${height.value || 72}px` }
  }
  return height.value ? { height: `${height.value}px` } : null
})
const router = useRouter()
const cartStore = useCartStore()
//Contexto de la tienda que provee StorePublicLayout: venta online y el
//catálogo público compartido (ya trae available_stock fresco — el
//documento es origen opaco y no puede pedirlo por su cuenta).
const storeCtx = inject('storePage', null)
const ordersOn = computed(() => Boolean(storeCtx?.ordersEnabled?.value ?? storeCtx?.ordersEnabled))
/* Stock real por producto para el documento: el host lo trae una vez por
 * el endpoint público (el mismo catálogo que consume la vista Vue) y lo
 * empuja por postMessage; el puente pinta la disponibilidad en las
 * tarjetas y la ficha, y apaga los CTA de lo agotado. */
const stockMap = ref(null)
let stockReq = null
function postStock() {
  /* {...map}: stockMap es ref() — el proxy reactivo de Vue no cruza
   * postMessage (DataCloneError); el spread deja un objeto plano. */
  if (stockMap.value) post('davent:ds-stock', { stock: { ...stockMap.value } })
}
function loadStock() {
  if (!ordersOn.value || stockReq || typeof storeCtx?.loadPublicCatalog !== 'function') return
  stockReq = Promise.resolve(storeCtx.loadPublicCatalog())
    .then((data) => {
      const map = {}
      for (const p of data?.products || []) {
        if (p?.id == null) continue
        const n = p.available_stock == null ? null : Number(p.available_stock)
        if (n === null || Number.isFinite(n)) map[String(p.id)] = n
      }
      stockMap.value = map
      postStock()
    })
    .catch(() => {})
    .finally(() => { stockReq = null })
}
watch(ordersOn, (on) => { if (on) loadStock() }, { immediate: true })
//Overflow del documento previo a un bloqueo de scroll pedido por el diseño
//(hoja modal abierta). null = la página scrollea normal.
let docOverflow = null

//El tema va en la URL solo al montar cada documento: al alternar
//claro/oscuro el puente (`davent:ds-theme`) cambia data-ds-theme sin
//recargar — si theme estuviera en el src reactivo, cada toggle recargaría
//el iframe y la página saltaría. Pero cualquier otro cambio que fuerza un
//documento nuevo (diseño, estilo, revisión, ficha) hornea el tema VIGENTE,
//no el del primer mount: antes quedaba fijado el claro/oscuro viejo y el
//documento arrancaba con el modo equivocado.
const mountTheme = ref(props.theme)
/* El documento sirve TODAS las superficies: cambiar de Inicio a Catálogo o
 * Servicios no necesita recargar el iframe (el puente cambia
 * `data-ds-surface`). Solo la ficha de producto viaja con `product` y
 * obliga a un documento nuevo. `reloadSurface` se actualiza al salir de una
 * ficha para que esa recarga caiga en la ruta destino. */
const mountSurface = props.surface === 'product' ? 'landing' : props.surface
const reloadSurface = ref(mountSurface)
watch(() => props.surface, (next, prev) => {
  if (prev === 'product' && next !== 'product') reloadSurface.value = next
})
const srcSurface = computed(() => (props.product ? props.surface : reloadSurface.value))
watch(
  () => [props.template, props.style, props.revision, props.product, srcSurface.value],
  () => { mountTheme.value = props.theme }
)
const src = computed(() => {
  const params = new URLSearchParams({ theme: mountTheme.value, surface: srcSurface.value })
  if (props.preview) params.set('preview', props.preview)
  if (props.preview && props.template) params.set('template', props.template)
  if (props.preview && props.style) params.set('style', props.style)
  if (props.revision) params.set('v', props.revision)
  if (props.product) params.set('product', String(props.product))
  return `/api/stores/public/${encodeURIComponent(props.slug)}/pattern/document/?${params}`
})

const emit = defineEmits(['navigate', 'toggle-theme', 'load', 'buy', 'buy-now', 'account', 'chrome-height', 'chrome-invalid'])

//El iframe va sin `allow-same-origin` (origen opaco): el JS del diseño no
//puede tocar el DOM ni las cookies de la app. Los datos que necesita de la
//API pública (captcha y opiniones del producto) los pide por postMessage y
//los busca este componente, que sí es mismo origen.
//Whitelist cerrada: el documento no elige el endpoint. Solo estas rutas
//de la tienda que embebe, y siempre con su slug (nunca el de otra). La
//raíz (`<slug>/`) es el payload público completo: de ahí el chatbot del
//diseño saca {greeting, qa} (ya viene filtrado por beneficio + switch).
const PUBLIC_API_RE = /^\/api\/stores\/public\/[a-z0-9-]+\/(?:contact\/captcha|contact|products\/\d+\/reviews|pattern\/products)?\/?(\?[^\s"'<>]*)?$/
//El POST de opiniones exige sesión de comprador (Bearer customer_access):
//pasa por customerHttp — adjunta el access en memoria y renueva la sesión
//por la cookie refresh igual que el resto de la API del comprador.
const REVIEW_POST_RE = /\/products\/\d+\/reviews\/?$/

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
      if (event.data.method === 'POST' && REVIEW_POST_RE.test(url)) {
        const { data } = await customerHttp.post(url.replace(/^\/api(?=\/)/, ''), event.data.body || {})
        result = { ok: true, data }
      } else {
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
      }
    } catch (err) {
      result = { ok: false, data: err?.response?.data ?? null }
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
  if (e.data?.type === 'davent:ds-scroll') {
    /* Anchor interno del documento: el iframe va estirado al alto del doc,
     * así que el scroll lo hace la página. top llega en coords del doc y
     * `offset` es el chrome fijo que declara el diseño (72 por defecto). */
    const fr = frame.value?.getBoundingClientRect()
    const offset = Number(e.data.offset) > 0 ? Number(e.data.offset) : 72
    if (fr) window.scrollTo({ top: fr.top + window.scrollY + (Number(e.data.top) || 0) - offset, behavior: 'smooth' })
    return
  }
  if (e.data?.type === 'davent:ds-lock') {
    /* Hoja modal del diseño abierta (m-lock en el documento): el scroll es
     * de la página, así que el candado viaja por postMessage. Se guarda el
     * overflow previo para no pisar un bloqueo que ya existiera. */
    chromeLocked.value = !!e.data.locked
    /* En modo chrome la tira cambia de alto (tira ↔ 100vh) con el lock:
     * hay que re-enviar el rectángulo del marco o el puente posiciona la
     * hoja/barras fijas contra el borde inferior del frame VIEJO. */
    postFrame()
    if (e.data.locked) {
      if (docOverflow == null) {
        docOverflow = document.documentElement.style.overflow
        document.documentElement.style.overflow = 'hidden'
      }
    } else if (docOverflow != null) {
      document.documentElement.style.overflow = docOverflow
      docOverflow = null
    }
    return
  }
  if (e.data?.type === 'davent:ds-theme-toggle') {
    emit('toggle-theme')
    return
  }
  if (e.data?.type === 'davent:ds-buy') {
    /* CTA de carrito inyectado por el puente (tienda con venta online):
     * el documento no puede llamar a la API del carrito — el host resuelve
     * sesión de comprador, alta y drawer. El id lo valida el server. */
    const id = String(e.data.id || '')
    if (/^\d{1,10}$/.test(id)) emit('buy', { id: Number(id) })
    return
  }
  if (e.data?.type === 'davent:ds-buy-now') {
    /* "Comprar ahora" de la ficha (hermano ghost del CTA de carrito):
     * misma validación de id que ds-buy — el host hace alta silenciosa
     * y manda al checkout. */
    const id = String(e.data.id || '')
    if (/^\d{1,10}$/.test(id)) emit('buy-now', { id: Number(id) })
    return
  }
  if (e.data?.type === 'davent:ds-account') {
    /* Entrada "Mi cuenta" inyectada por el puente: el host decide entre
     * abrir el modal de auth del comprador o navegar a /cuenta. */
    emit('account')
    return
  }
  if (e.data?.type === 'davent:ds-cart') {
    /* Píldora de carrito inyectada por el puente (tienda con venta
     * online): navega a la página /carrito de ESTA tienda por path —
     * mismo criterio que checkoutRoute de cart.store (en subdominio o
     * dominio propio es '/carrito'; en la plataforma '/<slug>/carrito'). */
    router.push({ path: storeHostSlug ? '/carrito' : `/${props.slug}/carrito` })
    return
  }
  if (e.data?.type === 'davent:ds-route') {
    const route = String(e.data.route || '')
    if (['home', 'catalog', 'services'].includes(route)) {
      /* El buscador/sugerencias del chrome adjuntan q (texto) y cat
       * (categoría) a la misma señal — el host los vuelca en la query
       * del catálogo (origen opaco: no comparten sessionStorage). */
      emit('navigate', { route, q: e.data.q ? String(e.data.q) : '', cat: e.data.cat ? String(e.data.cat) : '' })
    } else if (route === 'product' && e.data.id) {
      emit('navigate', { route, id: String(e.data.id) })
    }
    return
  }
  if (e.data?.type !== 'davent:ds-height') return
  /* El documento confirma su superficie en cada ds-height. Un backend
   * viejo no conoce 'chrome' y sirve la landing entera: sin el chequeo la
   * tira crecía al alto de la portada y tapaba la página completa. */
  if (props.chrome && e.data.surface !== 'chrome') {
    emit('chrome-invalid')
    return
  }
  const next = Number(e.data.height) || 0
  /* `Math.ceil`: el alto viaja fraccionario (getBoundingClientRect) y un
   * iframe 0.5px más bajo que el documento gana scroll interno — la rueda
   * encadena iframe↔página en el borde y los fijos del diseño se
   * desalinean: se siente como vibración al llegar al fondo. */
  if (next > 0) {
    height.value = Math.ceil(next)
    /* En modo chrome el alto de la tira sale del propio documento: el
     * host lo usa para reservar el hueco del navbar sobre el contenido. */
    if (props.chrome) emit('chrome-height', height.value)
  }
  /* El iframe cambió de alto: el rectángulo del marco quedó viejo y las
   * barras fijas del documento se posicionan con datos de otro alto —
   * repostear el frame para que el puente re-mida con el tamaño real. */
  postFrame()
}

function post(type, payload) {
  frame.value?.contentWindow?.postMessage({ type, ...payload }, '*')
}

function syncTheme() {
  post('davent:ds-theme', { theme: props.theme })
  post('davent:ds-measure', {})
}

function syncStudioCss() {
  post('davent:ds-studio-css', { css: props.studioCss || '' })
}

function syncAccount() {
  post('davent:ds-account-state', { authed: props.account })
}

//El carrito es del comprador (store slug-scoped, ya bindeado por el
//layout): el documento es origen opaco y no puede leerlo — se le empuja
//el contador por postMessage, igual que la sesión de cuenta. El badge
//de `.dsx-cart` dentro del diseño se actualiza sin recargar el iframe.
function syncCart() {
  post('davent:ds-cart-state', { count: cartStore.itemCount })
}

function onLoad() {
  height.value = 0
  emit('load')
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
  syncStudioCss()
  syncAccount()
  syncCart()
  postStock()
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
/* Al estirarse el iframe (ds-height) cambia su rect: si no se reenvía el
 * marco, el puente posiciona los fijos con un rect viejo (~70vh) y la tab
 * bar queda clavada arriba del documento. */
watch(height, postFrame)
watch(() => props.surface, () => {
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
})
//Ediciones del Studio en vivo: el CSS viaja entero (es barato — son unas
//pocas reglas) y el puente lo reemplaza en un <style> dedicado.
watch(() => props.studioCss, syncStudioCss)
//Login/logout del comprador con el documento ya montado: el rótulo del
//botón se actualiza sin recargar el iframe.
watch(() => props.account, syncAccount)
//Agregar/quitar ítems del carrito (acá o en el drawer): el badge de la
//píldora dentro del documento se actualiza en vivo.
watch(() => cartStore.itemCount, syncCart)

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
  if (docOverflow != null) {
    document.documentElement.style.overflow = docOverflow
    docOverflow = null
  }
})
</script>

<template>
  <iframe
    ref="frame"
    class="ds-surface"
    :class="{ 'ds-chrome': chrome, 'ds-locked': chromeLocked }"
    :src="src"
    :title="title || 'Diseño de la web'"
    :style="frameStyle"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-forms"
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
  /* Si el documento llega a tener overflow propio, la rueda no debe
   * rebotar entre el scroll interno del iframe y el de la página. */
  overscroll-behavior: contain;
}

/* Modo chrome: tira fija con el navbar del diseño sobre las páginas que el
 * documento no pinta. z-index bajo el drawer/modales del chrome Vue
 * (.sp-overlay 30 / .sp-modal-overlay 40) pero sobre el contenido; al
 * abrir una hoja del diseño (ds-lock) crece a viewport completo. */
.ds-surface.ds-chrome {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 24;
  min-height: 0;
}

/* Con la hoja del diseño abierta la tira cubre el viewport: sube sobre
 * los fijos propios de la página (bot 44 / lightbox 45 / más-sheet 47 /
 * barra de compra 25) pero queda bajo drawer, modal y toast del host. */
.ds-surface.ds-chrome.ds-locked {
  z-index: 60;
}
</style>
