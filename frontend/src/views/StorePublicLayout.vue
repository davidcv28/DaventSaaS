<script setup>
import { ref, reactive, computed, provide, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  storesApi, normalizeSlug, normalizeCatalogParams, storeThemeVars, storeFontFamily, ensureStoreFont, resolveStoreTemplate, CUSTOMIZATION_DEFAULTS, STORE_TEMPLATES, AI_EXTRA_TEMPLATES, storeSkinOf
} from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { env, storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
import StoreBot from '../components/StoreBot.vue'
import PatternSurface from '../components/store/PatternSurface.vue'
import { vReveal } from '../directives/reveal.js'
import { applySeo } from '../utils/seo.js'
import { readVisitorTheme, persistVisitorTheme, resolveStoreTheme } from '../utils/storeTheme.js'
import { schemaHours } from '../utils/storeHours.js'
import { templateFonts, normalizeLayoutConfig } from '../templates/index.js'
import { useDesignCatalog } from '../composables/useDesignCatalog.js'
import { STUDIO_MSG, isStudioMessage, studioReady } from '../studio/contract.js'
import { familyOf } from '../utils/styleIcons.js'
import {
  studioPreviewVars, studioPreviewAttrs, applyFocusRing,
  storeSiteThemeVars, storeSiteThemeAttrs, skinOf, SKIN_FAMILIES
} from '../components/studio/previewBridge.js'
import '../assets/store-page.css'
// Capa de movimiento (keyframes + microinteracciones) por familia de piel.
import '../assets/store-motion.css'
// Menú y movimiento propios de cada estilo del catálogo (DesignStyle).
import '../assets/store-style-menus.css'
import '../assets/store-style-motion.css'
// Base de layout de la página Servicios (.rz-sv-* + primitivas .rz-btn /
// .rz-eyebrow / .rz-field), compartida por todos los diseños: la vista
// funcional del embudo es única y su layout no puede vivir solo en la hoja de
// Raíz. Scopeada a :not([data-template='raiz']): la piel de Raíz no cambia.
import '../assets/store-services-base.css'
// Hoja del diseño activo: se carga on-demand (una sola vez por diseño), así
// el CSS de Raíz no viaja en el bundle de Trama/Circuito ni al revés. La
// tarjeta de producto unificada (TplProductCard) conserva su contrato de
// geometría compartido.
import '../assets/store-tpl-card.css'

// Layout de la web pública del cliente (sin auth): barra superior + pie +
// transición suave entre sus páginas (Inicio y Catálogo). Resuelve la tienda
// una sola vez y la comparte a las vistas hijas con provide('storePage').
// Usa su propia paleta (data-store-theme + --store-accent*): no hereda el
// tema claro/oscuro que el visitante haya elegido para el dashboard.
// Estilos en assets/store-page.css (única hoja de la web pública).
const route = useRoute()
const router = useRouter()
const status = ref('loading') // loading | success | error
const store = ref(null)
const errorMsg = ref('')
// El slug viene del path (dominio de plataforma /<slug>) o del subdominio
// (<slug>.<dominio>, donde la tienda es la raíz y no hay param en la ruta).
const slug = computed(() => normalizeSlug(route.params.slug || storeHostSlug || ''))
const appUrl = env.appUrl

// Vista previa en vivo del editor de bloques: el panel empuja el
// layout_config del draft por postMessage same-origin y la página lo
// aplica reactivo, sin recargar el iframe.
const layoutOverride = ref(null)
let removeStudioGuard = null
// Identidad/cromo del borrador que el Studio empuja en modo edición
// (tamaño del nombre, portada, logo, copy de secciones): lo que se ve en el
// lienzo es exactamente lo que va a quedar guardado, sin recargar.
const studioCustom = ref(null)
// Catálogo de diseño (patrones + estilos) desde la API: el patrón base y
// su estilo son el fallback de la web cuando la tienda no eligió nada.
const { defaultPattern, defaultStyle, iconStyles, defaultIconStyle, load: loadDesignCatalog } = useDesignCatalog()
// Layout del patrón de diseño de la base: única fuente de composición de las
// tres superficies cuando la tienda no guardó su propio layout_config.
const patternLayout = computed(() => normalizeLayoutConfig(defaultPattern.value?.layout))
// Diseño del catálogo servido como documento propio (HTML/CSS/JS con las
// variables resueltas por el backend). Solo se usa cuando el patrón ya
// declara su contrato de datos (`ready`); en el Studio se sigue editando
// con la plantilla Vue, que es la que responde a los cambios en vivo.
const patternDoc = ref(null)
//Superficie que el documento del patrón debe pintar en esta ruta. Si el
//diseño no la declara (`surfaces`), esa ruta sigue con la plantilla Vue.
const patternSurface = computed(() => (
  route.name === 'store-catalog' ? 'catalog'
    : route.name === 'store-services' ? 'services'
      : 'landing'
))
const usePattern = computed(() => Boolean(
  !studioMode.value && patternDoc.value?.ready && patternDoc.value?.html &&
  (patternDoc.value.surfaces || []).includes(patternSurface.value) &&
  //El documento trae los productos ya pintados: si no entran todos, el
  //catálogo sigue en la plantilla Vue (que pagina y filtra contra la API).
  (patternSurface.value !== 'catalog' ||
    (patternDoc.value.products_total || 0) <= (patternDoc.value.products_shown || 24))
))
const custom = computed(() => {
  const raw = store.value?.customization || {}
  const merged = {
    ...CUSTOMIZATION_DEFAULTS,
    ...raw,
    ...(studioCustom.value || {}),
    ...(layoutOverride.value ? { layout_config: layoutOverride.value } : {}),
    // En modo Studio el tema del borrador también tiene que ser visible para
    // los componentes de la página que lo leen directo (p. ej. el CTA fijo de
    // Servicios): si no, el control impacta en --st-* pero no en su lógica.
    ...(studioMode.value && studioTheme.value ? { site_theme: studioTheme.value } : {})
  }
  const pattern = defaultPattern.value
  const style = defaultStyle.value
  if (!raw.template && pattern?.template) merged.template = pattern.template
  const savedLayout = merged.layout_config && typeof merged.layout_config === 'object' ? merged.layout_config : {}
  const baseLayout = patternLayout.value
  merged.layout_config = Object.keys(savedLayout).length || Object.keys(baseLayout).length
    ? { ...baseLayout, ...savedLayout }
    : {}
  if (!studioMode.value && (!raw.site_theme || !Object.keys(raw.site_theme).length) && style?.tokens) merged.site_theme = style.tokens
  return merged
})
// Navegación del documento del patrón: sus enlaces de chrome viajan como
// rutas (home/catalog/services) y acá se resuelven con el router de la app.
function onPatternNavigate({ route, id } = {}) {
  if (route === 'product' && id) {
    router.push({ name: 'store-product', params: { slug: slug.value, productId: id } })
    return
  }
  const target = { home: homeTo.value, catalog: catalogTo.value, services: servicesTo.value }[route]
  if (target) router.push(target)
}
function onLayoutMessage(e) {
  if (e.data?.type !== 'davent:layout') return
  if (e.origin !== window.location.origin && e.origin !== parentOrigin) return
  layoutOverride.value = e.data.layout || null
}
// Modo Studio (?studio=1, iframe de la shell): consume el protocolo del
// contrato — studio:update aplica theme/layout/template/modo reactivo sin
// guardar nada; studio:focus dibuja el anillo; studio:ready le avisa al
// host para que reenvíe el estado vigente (handshake).
const studioMode = computed(() => route.query.studio === '1')
// Link temporal "compartir vista previa" (?preview=<token firmado>): la API
// devuelve el borrador del Studio en vez de lo publicado (data.preview=true).
const previewToken = computed(() => String(route.query.preview || ''))
const previewMode = computed(() => Boolean(previewToken.value && store.value?.preview))
const studioTheme = ref(null)      // siteTheme del borrador
const studioExplicit = ref(null)   // campos que el borrador toca de verdad
const studioTemplate = ref(null)   // template del borrador
const studioViewMode = ref(null)   // claro/oscuro del visor (msg.mode)
// En un iframe el referrer es el document del host: se acepta como origen
// válido además del propio (el update llega del Studio que lo embebe).
const parentOrigin = window.parent !== window && document.referrer
  ? new URL(document.referrer).origin
  : window.location.origin
function onStudioMessage(e) {
  if (!studioMode.value || !isStudioMessage(e.data)) return
  if (e.origin !== window.location.origin && e.origin !== parentOrigin) return
  const d = e.data
  if (d.type === STUDIO_MSG.UPDATE) {
    if (d.theme) studioTheme.value = d.theme
    studioExplicit.value = Array.isArray(d.explicit) ? new Set(d.explicit) : null
    if (d.layout) layoutOverride.value = d.layout
    if (d.template) studioTemplate.value = d.template
    if (d.mode === 'light' || d.mode === 'dark') studioViewMode.value = d.mode
    if (d.custom && typeof d.custom === 'object') studioCustom.value = d.custom
  } else if (d.type === STUDIO_MSG.FOCUS) {
    applyFocusRing(document, d.target)
  }
}
// Variables del tema Studio sobre la hoja actual: --st-* del contrato +
// equivalentes --store-*/--sp-* (studioPreviewVars traduce). En oscuro el
// tema propio de la página manda (solo viajan acento/fuente + --st-*).
const studioVars = computed(() => (
  studioMode.value && studioTheme.value
    ? studioPreviewVars(studioTheme.value, pageTheme.value, studioExplicit.value)
    : {}
))
const studioAttrs = computed(() => (
  studioMode.value && studioTheme.value
    ? studioPreviewAttrs(studioTheme.value, studioExplicit.value, pageTheme.value)
    : {}
))
const themeVars = computed(() => storeThemeVars(custom.value))
// Tema guardado (site_theme): se emite SIEMPRE, no solo en modo Studio, para
// que lo que se ve en el canvas sea exactamente lo que ve el visitante.
// Es parcial: cada variable sale solo si el tema fija ese campo, y sin
// site_theme el objeto queda vacío (la web se ve idéntica a hoy).
// En modo Studio manda el borrador (studioVars/studioAttrs): lo publicado no
// se mezcla para que un campo que el borrador no fija no se cuele en el
// lienzo y preview/publicada queden idénticas.
// Los diseños del catálogo (raiz/trama/circuito/…) consumen los mismos
// tokens --sp-*/--st-* que el Studio escribe: aplicar el site_theme también
// fuera del Studio es lo que evita que el lienzo muestre un cambio que la
// web publicada descarta.
const publishedThemeVars = computed(() => (
  studioMode.value ? {} : storeSiteThemeVars(custom.value, pageTheme.value)
))
const publishedThemeAttrs = computed(() => (studioMode.value ? {} : storeSiteThemeAttrs(custom.value, pageTheme.value)))
// Fuentes del tema guardado (título/cuerpo) on-demand: puede elegir una
// familia distinta de la del nombre. Un stack CSS no es slug y no hace nada.
watch(
  () => [custom.value.site_theme?.typography?.heading, custom.value.site_theme?.typography?.body],
  ([heading, body]) => { if (heading) ensureStoreFont(heading); if (body) ensureStoreFont(body) },
  { immediate: true }
)
// v4: cada rol puede pedir su propia familia del catálogo (24 familias).
watch(
  () => {
    const roles = custom.value.site_theme?.typography?.roles
    return roles && typeof roles === 'object'
      ? Object.values(roles).map((r) => r?.font).filter(Boolean).join(',')
      : ''
  },
  (fonts) => { if (fonts) fonts.split(',').forEach((f) => ensureStoreFont(f)) },
  { immediate: true }
)
const pageAttrs = computed(() => ({ ...publishedThemeAttrs.value, ...studioAttrs.value }))
// Diseño avanzado (Plan premium): define si la web muestra el carrusel de
// destacados o, en su lugar, un botón de modo claro/oscuro en el nav.
const hasDesignAdvanced = computed(() => Boolean(store.value?.has_design_advanced))
// Diseño de la web (template): la whitelist allowed_templates del payload
// marca el nivel del plan (Básico: Raíz; Estándar suma Trama; Premium suma Circuito).
// Urbano/Publicidad; Premium, todo). Si el guardado quedó fuera — baja de
// plan o plantilla retirada — se fuerza 'raiz'.
// En modo Studio la plantilla en ensayo se resuelve contra el catálogo
// completo (los presets bloqueados también se pueden probar — el gate de
// allowed_templates solo corre al guardar). Fuera del Studio manda la
// whitelist del plan como siempre.
const pageTemplate = computed(() => {
  if (studioMode.value && studioTemplate.value) {
    return resolveStoreTemplate(studioTemplate.value, [...Object.keys(STORE_TEMPLATES), ...AI_EXTRA_TEMPLATES])
  }
  return resolveStoreTemplate(custom.value.template, store.value?.allowed_templates)
})
// Estilo del catálogo (DesignStyle) aplicado a la tienda: alimenta el menú
// y la firma de movimiento propios de cada estilo. Sin estilo elegido cae
// en `base` (la barra neutra de la plataforma).
const pageStyle = computed(() => {
  const id = custom.value?.site_theme?.style?.id
  return typeof id === 'string' && id ? id : 'base'
})
// Tienda Pro (Premium): masthead de marketplace — el buscador queda visible
// en todas las páginas y fuera del catálogo envía a /catalogo?q=.
const isShop = computed(() => pageTemplate.value === 'shop')

// Hojas propias de un diseño: tiñen también el chrome (barra, pie, dock) en
// páginas que no montan la portada (servicios, ficha). Todos se cargan
// on-demand y una sola vez. Al terminar la carga se re-sincroniza el SEO para
// tomar el theme-color que declare la hoja.
const TEMPLATE_CSS = {
  raiz:      () => import('../assets/store-raiz.css'),
  alimentos: () => import('../assets/store-alimentos.css'),
  trama:     () => import('../assets/store-trama.css'),
  // `indumentaria` comparte la piel de Trama (misma hoja, mismo chunk
  // cacheado); su composición distinta vive en views/store/indumentaria.
  indumentaria: () => import('../assets/store-trama.css'),
  boutique:  () => import('../assets/store-boutique.css'),
  atelier:   () => import('../assets/store-atelier.css'),
  clasico:   () => import('../assets/store-clasico.css'),
  circuito:  () => import('../assets/store-circuito.css'),
  seguridad: () => import('../assets/store-seguridad.css')
}
watch(pageTemplate, (tpl) => {
  const loaded = TEMPLATE_CSS[tpl]?.()
  if (loaded && typeof loaded.then === 'function') {
    loaded.then(() => { syncSeo(); scheduleCanvasColor() }).catch(() => {})
  }
}, { immediate: true })
// Skin v4 (site_theme.skin.family): piel de 18 familias en su propia hoja,
// cargada por import dinámico para no engordar el bundle. Un skin sin
// familia válida deja la tienda como está.
const effectiveSkin = computed(() => {
  const theme = studioMode.value && studioTheme.value ? studioTheme.value : custom.value?.site_theme
  return skinOf(theme)
})
watch(effectiveSkin, (family) => {
  if (SKIN_FAMILIES.includes(family)) import(`../assets/skin-${family}.css`)
}, { immediate: true })
// Tema efectivo: el elegido por el dueño; con customization.theme_toggle
// el visitante puede alternarlo y su elección queda en localStorage
// (clave por tienda). El valor se lee en setup — antes del primer paint —
// así la página no arranca en claro y salta a oscuro.
const prefersDark = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(prefers-color-scheme: dark)').matches
  : false
function readVisitorThemeForStore() {
  return readVisitorTheme(typeof localStorage !== 'undefined' ? localStorage : null, slug.value)
}
// Si el negocio no fijó default, se respeta prefers-color-scheme (lo resuelve
// resolveStoreTheme junto con la elección del visitante y el preview).
const visitorTheme = ref(readVisitorThemeForStore()) // null = tema de la tienda
const pageTheme = computed(() => resolveStoreTheme({
  // `studio` es el tema que manda el lienzo (string); `studioView` es la
  // bandera de que ese tema ya llegó por postMessage.
  studio: studioViewMode.value,
  studioView: studioMode.value && Boolean(studioViewMode.value),
  visitor: visitorTheme.value,
  storeDefault: custom.value.theme,
  prefersDark
}))
// Interruptor de noche: lo habilita el negocio (theme_toggle). Payloads
// viejos sin el campo conservan la regla anterior (sin diseño avanzado el
// visitante ya podía alternarlo).
// Los diseños avanzados (circuito/seguridad) son oscuros por defecto: ahí el
// interruptor depende del switch "Modo noche" del panel (theme_toggle=true).
// En los diseños base se mantiene visible siempre (comportamiento histórico);
// con theme_toggle explícito en true también aparece en cualquier diseño.
// Modo noche universal: TODAS las webs ofrecen el interruptor, sin
// depender del plan ni del switch del panel (theme_toggle solo define el
// modo con el que arranca un visitante nuevo).
const showThemeToggle = computed(() => status.value === 'success')
function togglePageTheme() {
  visitorTheme.value = pageTheme.value === 'dark' ? 'light' : 'dark'
  persistVisitorTheme(typeof localStorage !== 'undefined' ? localStorage : null, slug.value, visitorTheme.value)
}
// Anti-flash del lienzo: el shell del producto (html/body) hereda el fondo del
// panel. Mientras esta web está montada se pinta con el tema efectivo ANTES
// del primer frame (la hoja de la plantilla afina el tono exacto después), así
// una recarga en modo noche no destella claro. Al desmontar se devuelve el
// shell a manos de la app.
const PAGE_CANVAS = { light: '#F6F7FB', dark: '#0D1220' }
let canvasRaf = 0
let canvasTimer = 0
function clearCanvasSync() {
  if (canvasRaf) { cancelAnimationFrame(canvasRaf); canvasRaf = 0 }
  if (canvasTimer) { clearTimeout(canvasTimer); canvasTimer = 0 }
}
// Tono exacto del diseño para el lienzo del documento (el genérico solo cubre
// el primer frame, antes de que la hoja de la plantilla esté aplicada). Se
// congela un instante la transición de fondo del root: si el diseño anima
// `background-color` (p. ej. Raíz, 180 ms), leer el computed durante la
// transición devuelve un tono intermedio y el shell quedaba con ese marco.
function applyCanvasColor() {
  if (typeof document === 'undefined') return
  const root = document.querySelector('.store-page')
  if (!root) return
  const prevTransition = root.style.transition
  root.style.transition = 'none'
  const exact = getComputedStyle(root).backgroundColor
  root.style.transition = prevTransition
  if (!exact || exact === 'rgba(0, 0, 0, 0)') return
  if (document.documentElement.style.backgroundColor !== exact) {
    document.documentElement.style.backgroundColor = exact
  }
  if (document.body) document.body.style.backgroundColor = exact
}
// Re-sync del lienzo tras el render: primer pase síncrono (el getComputedStyle
// de arriba fuerza el recalc con el data-store-theme nuevo), un rAF para hojas
// que se inyectan en este mismo tick (import dinámico) y un timer de guardia
// por si el navegador demora en aplicar el CSS del diseño.
function scheduleCanvasColor() {
  applyCanvasColor()
  if (typeof requestAnimationFrame === 'function') {
    if (canvasRaf) cancelAnimationFrame(canvasRaf)
    canvasRaf = requestAnimationFrame(() => { canvasRaf = 0; applyCanvasColor() })
  }
  if (typeof setTimeout === 'function') {
    if (canvasTimer) clearTimeout(canvasTimer)
    canvasTimer = setTimeout(() => { canvasTimer = 0; applyCanvasColor() }, 300)
  }
}
function applyPageCanvas() {
  if (typeof document === 'undefined') return
  const theme = pageTheme.value === 'dark' ? 'dark' : 'light'
  const bg = PAGE_CANVAS[theme] || PAGE_CANVAS.light
  document.documentElement.style.backgroundColor = bg
  if (document.body) document.body.style.backgroundColor = bg
  document.documentElement.style.colorScheme = theme
  // El watcher corre con flush:'post': el DOM ya tiene el nuevo tema.
  scheduleCanvasColor()
}
// Anti-flash: pinta el lienzo genérico ANTES del primer frame (el root todavía
// no está montado, applyCanvasColor no puede leer nada y no estorba).
applyPageCanvas()
watch([pageTheme, status], () => applyPageCanvas(), { flush: 'post' })
onMounted(() => applyPageCanvas())
onMounted(() => loadDesignCatalog())
onBeforeUnmount(() => {
  clearCanvasSync()
  document.documentElement.style.backgroundColor = ''
  document.documentElement.style.colorScheme = ''
  document.body.style.backgroundColor = ''
})
const shopName = computed(() => custom.value.display_name || store.value?.business_name || 'Tienda')
const nameFont = computed(() => ({ fontFamily: storeFontFamily(custom.value.name_font) }))
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const location = computed(() => [store.value?.city_name, store.value?.province_name].filter(Boolean).join(', '))
const year = new Date().getFullYear()
const mainAnchor = ref(null)
// Raíz del layout: se usa para leer el color de cromo del tema activo
// (--rz-theme-color / --sp-theme-color) al sincronizar <meta theme-color>.
const pageRoot = ref(null)
const topSearchInput = ref(null)
const menuBtn = ref(null)
const menuDrawer = ref(null)
// Buscador colapsable del header (móvil): al abrir lleva el foco al input.
function toggleTopSearch() {
  ui.searchOpen = !ui.searchOpen
  if (ui.searchOpen) nextTick(() => topSearchInput.value?.focus())
}
function skipToContent() {
  const target = document.querySelector('.sp-page-root') || mainAnchor.value
  if (!target) return
  mainAnchor.value?.focus({ preventScroll: true })
  target.scrollIntoView({ block: 'start' })
}

// Visibilidad de las secciones del inicio: alimenta los links del nav.
const hasAbout = computed(() => custom.value.show_about !== false && Boolean(
  custom.value.about_text?.trim()
  || custom.value.about_mission?.trim()
  || custom.value.about_specialties?.trim()
  || custom.value.about_years
))
const gallery = computed(() => custom.value.gallery || [])
const showGallery = computed(() => status.value === 'success' && custom.value.show_gallery !== false && gallery.value.length > 0)
const showContact = computed(() => status.value === 'success' && custom.value.show_contact !== false)
// Catálogo opcional: el dueño puede apagarlo (vidriera sin productos). La
// página /catalogo redirige al inicio y desaparecen todos sus accesos.
const showCatalog = computed(() => status.value === 'success' && custom.value.show_catalog !== false)
// Páginas efectivas de la web (site_templates ya viene filtrado por el
// plan desde el backend): 'landing' = portada, 'services' = servicios con
// pedido por WhatsApp, 'catalog' = catálogo de productos.
const siteTemplates = computed(() => {
  const list = Array.isArray(custom.value.site_templates) ? custom.value.site_templates : ['landing', 'catalog']
  return ['landing', 'services', 'catalog'].filter((k) => list.includes(k))
})
// Página "Servicios": aparece solo si quedó en el set efectivo del plan.
const showServices = computed(() => status.value === 'success' && siteTemplates.value.includes('services'))
// Web sin portada: el home redirige a la primera página disponible
// (Servicios si existe, si no el catálogo) y el menú no ofrece Inicio ni
// las secciones de marketing. Cubre el viejo "modo solo catálogo" y la
// combinación servicios+catálogo sin landing.
const landingOff = computed(() => status.value === 'success' && !siteTemplates.value.includes('landing'))
// Chatbot (beneficio has_chatbot, solo Premium): el serializer público lo manda
// solo si el dueño lo activó y el plan lo incluye — None = sin widget.
const botConfig = computed(() => (status.value === 'success' ? store.value?.chatbot || null : null))

// Estado compartido con la vista del catálogo: buscador del header, burger y
// si existe navegación de catálogo (categorías/marcas) para el drawer.
// searchOpen: buscador colapsado del header en móvil (botón lupa).
const ui = reactive({ search: '', menuOpen: false, hasCatalogNav: false, searchOpen: false, moreOpen: false })

// Menú hamburguesa = SOLO navegación de la tienda: los filtros del catálogo
// viven en CatalogFilters (sidebar desktop / bottom sheet móvil), no en el
// drawer. Misma lista de destinos que .sp-top-links.
const navMenuLinks = computed(() => {
  const links = []
  if (!landingOff.value) links.push({ to: homeTo.value, label: 'Inicio' })
  if (showServices.value) links.push({ to: servicesTo.value, label: 'Servicios' })
  if (showCatalog.value) links.push({ to: catalogTo.value, label: 'Catálogo' })
  if (hasAbout.value && !landingOff.value) links.push({ to: anchorTo('#nosotros'), label: 'Nosotros', anchor: true })
  if (showGallery.value && !landingOff.value) links.push({ to: anchorTo('#galeria'), label: 'Galería', anchor: true })
  if (showContact.value && !landingOff.value) links.push({ to: anchorTo('#contacto'), label: 'Contacto', anchor: true })
  return links
})
// El burger se muestra cuando hay navegación que esconder — Tienda Pro usa
// su propia fila .sp-shop-nav (visible también en móvil).
const hasNavMenu = computed(() => status.value === 'success' && !isShop.value && navMenuLinks.value.length > 0)

// Tema mobile.nav: 'bottom' (default de la web pública) monta la tab bar
// (4 destinos + "Más") en lugar del burger; 'top' conserva el header con
// burger + drawer lateral y 'drawer' deja solo marca + burger.
const mobileNav = computed(() => pageAttrs.value['data-st-nav'] || 'bottom')
// Prioridad de destinos en la tab bar: Inicio → Catálogo → Servicios → Contacto.
const TAB_PRIORITY = ['Inicio', 'Catálogo', 'Servicios', 'Contacto']
const TAB_ICONS = { Inicio: 'store', Catálogo: 'package', Servicios: 'wrench', Contacto: 'message-circle' }
const tabLinks = computed(() => {
  const byLabel = new Map(navMenuLinks.value.map((l) => [l.label, l]))
  return TAB_PRIORITY.filter((label) => byLabel.has(label)).slice(0, 4)
    .map((label) => ({ ...byLabel.get(label), icon: TAB_ICONS[label] }))
})
const moreLinks = computed(() => navMenuLinks.value.filter((l) => !tabLinks.value.some((t) => t.label === l.label)))
const showTabbar = computed(() => status.value === 'success' && mobileNav.value === 'bottom' && tabLinks.value.length > 0)
function isTabActive(label) {
  return (label === 'Inicio' && shopCurrent.value === 'home')
    || (label === 'Catálogo' && shopCurrent.value === 'catalog')
    || (label === 'Servicios' && shopCurrent.value === 'services')
    || (label === 'Contacto' && shopCurrent.value === 'contacto')
}

const moreBtn = ref(null)
const moreSheet = ref(null)
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
function onMoreKey(e) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    ui.moreOpen = false
    return
  }
  if (e.key !== 'Tab' || !moreSheet.value) return
  const items = moreSheet.value.querySelectorAll(FOCUSABLE)
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault() }
  else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault() }
}
// Sheet "Más": mismo contrato que el del dashboard (scroll bloqueado, foco
// al cerrar, foco atrapado y Esc) sobre la paleta de la tienda.
watch(() => ui.moreOpen, async (open) => {
  document.documentElement.classList.toggle('sp-lock', open || ui.menuOpen)
  if (open) {
    document.addEventListener('keydown', onMoreKey, true)
    await nextTick()
    moreSheet.value?.querySelector('.sp-more-close')?.focus()
  } else {
    document.removeEventListener('keydown', onMoreKey, true)
    if (moreSheet.value?.contains(document.activeElement)) moreBtn.value?.focus()
  }
})

const onMenuKey = (e) => { if (e.key === 'Escape') ui.menuOpen = false }
watch(() => route.fullPath, () => { ui.menuOpen = false; ui.searchOpen = false; ui.moreOpen = false })
// Drawer de navegación: mientras está abierto bloquea el scroll del body,
// lleva el foco al botón de cerrar y lo devuelve al burger al cerrarse.
watch(() => ui.menuOpen, async (open) => {
  document.documentElement.classList.toggle('sp-lock', open || ui.moreOpen)
  if (open) {
    await nextTick()
    menuDrawer.value?.querySelector('.sp-drawer-close')?.focus()
  } else if (menuDrawer.value?.contains(document.activeElement)) {
    menuBtn.value?.focus()
  }
})
onBeforeUnmount(() => {
  document.documentElement.classList.remove('sp-lock')
  document.removeEventListener('keydown', onMoreKey, true)
})
const isCatalog = computed(() => route.name === 'store-catalog')
const isServices = computed(() => route.name === 'store-services')
const isProduct = computed(() => route.name === 'store-product')
const isHome = computed(() => route.name === 'store-public')
// Sección activa del menú de Tienda Pro. No alcanza con router-link-active:
// las anclas de la home (#nosotros, #galeria, #contacto) comparten el path y
// quedarían todas marcadas a la vez.
const shopCurrent = computed(() => {
  if (isCatalog.value || isProduct.value) return 'catalog'
  if (isServices.value) return 'services'
  if (!isHome.value) return ''
  const hash = route.hash.replace('#', '')
  return ['nosotros', 'galeria', 'contacto'].includes(hash) ? hash : 'home'
})
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${slug.value}/servicios` }))
// Página de reemplazo cuando no hay portada: Servicios si está, si no el
// catálogo (la web nunca queda sin destino — el backend siempre manda ≥1).
const homeFallbackTo = computed(() => (showServices.value ? servicesTo.value : catalogTo.value))
// Anclas de sección (#nosotros/#galeria/#contacto): van al inicio.
const anchorTo = (hash) => ({ path: homeTo.value.path, hash })
watch([landingOff, isHome], ([off, home]) => { if (off && home) router.replace(homeFallbackTo.value) }, { immediate: true })

// Buscador del masthead (Tienda Pro): en el catálogo filtra en vivo; en el
// resto de las páginas Enter/botón navega al catálogo con ?q= (la vista lo
// toma como búsqueda inicial).
function submitTopSearch() {
  if (isCatalog.value) return
  const q = ui.search.trim()
  router.push(q ? { ...catalogTo.value, query: { q } } : catalogTo.value)
}

// CTA cruzado del topbar: desde una página propone la siguiente más útil.
// En catálogo/producto vuelve al inicio (o a Servicios si no hay portada);
// en la home/portada ofrece Catálogo y después Servicios; en Servicios la
// portada o el catálogo. Null cuando no hay otra página que sugerir.
const topCta = computed(() => {
  if (status.value !== 'success') return null
  if (isCatalog.value || isProduct.value) {
    if (!landingOff.value) return { to: homeTo.value, icon: 'store', label: 'Inicio' }
    if (showServices.value && !isServices.value) return { to: servicesTo.value, icon: 'wrench', label: 'Servicios' }
    return null
  }
  if (isServices.value) {
    if (!landingOff.value) return { to: homeTo.value, icon: 'store', label: 'Inicio' }
    if (showCatalog.value) return { to: catalogTo.value, icon: 'package', label: 'Catálogo' }
    return null
  }
  if (showCatalog.value) return { to: catalogTo.value, icon: 'package', label: 'Catálogo' }
  if (showServices.value) return { to: servicesTo.value, icon: 'wrench', label: 'Servicios' }
  return null
})

// Gate del pie: `status === 'success'` llega con el payload de la tienda, pero
// la superficie de la ruta es un `defineAsyncComponent` que monta unas decenas
// de ms después. Si el pie se pinta en ese hueco queda pegado al header y
// salta al fondo al montar el contenido (CLS ~0.53 medido en las 3 plantillas).
// Esperamos a que exista la raíz de la superficie (main / .sp-page-root) antes
// de mostrarlo; si nunca aparece (chunk roto), un timeout lo libera igual.
const contentReady = ref(false)
let contentObserver = null
let contentFallback = 0
function watchContentMounted() {
  contentObserver?.disconnect()
  contentObserver = null
  clearTimeout(contentFallback)
  contentReady.value = false
  if (status.value !== 'success') return
  const root = document.querySelector('.store-page')
  if (!root) return
  const hasSurface = () => Boolean(root.querySelector('main, .sp-page-root'))
  if (hasSurface()) { contentReady.value = true; return }
  contentObserver = new MutationObserver(() => {
    if (!hasSurface()) return
    contentReady.value = true
    contentObserver?.disconnect()
    contentObserver = null
  })
  contentObserver.observe(root, { childList: true, subtree: true })
  contentFallback = setTimeout(() => { contentReady.value = true }, 2500)
}
watch([status, () => route.fullPath], () => { nextTick(watchContentMounted) }, { immediate: true })

// Barra de progreso de lectura y estado "scrolled" de la barra superior.
const scrolled = ref(false)
const progress = ref(0)
let ticking = false
function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    const max = document.documentElement.scrollHeight - window.innerHeight
    scrolled.value = window.scrollY > 8
    progress.value = max > 0 ? Math.min(1, window.scrollY / max) : 0
    ticking = false
  })
}

// Catálogo público compartido entre las páginas de la tienda: se pide una
// sola vez por combinación de filtros y las vistas hijas lo consumen por
// provide — antes cada página esperaba a la ficha y recién pedía el suyo.
const catalogCache = new Map()
function loadPublicCatalog(params = {}) {
  // La clave es la forma canónica de los params (ids/valores ordenados):
  // {category:[2,1]} y {category:'1,2'} comparten el mismo request.
  const normalized = normalizeCatalogParams(params)
  const key = JSON.stringify(normalized)
  let req = catalogCache.get(key)
  if (!req) {
    req = storesApi.publicCatalog(slug.value, params).catch((e) => {
      catalogCache.delete(key) // un error transitorio no queda cacheado
      throw e
    })
    // El prefetch puede rechazar (catálogo apagado, tienda caída): marca el
    // rechazo como atendido; la vista que lo consuma recibe el error igual.
    req.catch(() => {})
    catalogCache.set(key, req)
  }
  return req
}

// Familia de iconos del estilo activo: la web entera (chrome, portada,
// catálogo, servicios, ficha) dibuja los iconos con el trazo y los alias de
// la familia. En el Studio manda el estilo del borrador; si la tienda no
// eligió estilo, la familia sale de su plantilla.
const iconFamily = computed(() => familyOf({
  styleId: custom.value.site_theme?.style?.id || '',
  template: pageTemplate.value
}))
provide('storeIconFamily', iconFamily)
// Set explícito de iconos de los controles: el elegido por la tienda, si no
// el que trae el diseño, si no el base del catálogo. Cambiarlo no toca el
// diseño: solo redibuja los iconos del menú y los controles.
const storeIconSet = computed(() => {
  const slug = custom.value.icon_style
  if (slug) {
    const chosen = iconStyles.value.find((row) => row.slug === slug)
    if (chosen) return chosen
  }
  const patternSlug = defaultPattern.value?.icon_style
  if (patternSlug) {
    const own = iconStyles.value.find((row) => row.slug === patternSlug)
    if (own) return own
  }
  return defaultIconStyle.value || null
})
provide('storeIconSet', storeIconSet)
// Contexto para el ajuste fino por rubro (styleIcons.js: iconFor).
provide('storeIconContext', computed(() => ({
  styleId: custom.value.site_theme?.style?.id || '',
  template: pageTemplate.value
})))

provide('storePage', {
  slug, store, status, custom, shopName, nameFont, initial, location,
  hasDesignAdvanced, pageTemplate, hasAbout, showGallery, showContact, showCatalog, showServices, siteTemplates, ui,
  loadPublicCatalog
})

// Título de pestaña por página: "<tienda>" en Inicio, "<tienda> · Catálogo"
// en el catálogo, "<tienda> · Servicios" en la página de servicios.
// Corre también al volver al inicio.
watch([status, () => route.name], ([s, name]) => {
  if (s !== 'success') return
  document.title = name === 'store-catalog' ? `${shopName.value} · Catálogo`
    : name === 'store-services' ? `${shopName.value} · Servicios`
    : shopName.value
}, { immediate: true })

// Canales de contacto (pie y barra fija móvil).
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: custom.value.instagram && `https://instagram.com/${custom.value.instagram}` },
  { key: 'tiktok', label: 'TikTok', url: custom.value.tiktok && `https://tiktok.com/@${custom.value.tiktok}` },
  { key: 'facebook', label: 'Facebook', url: custom.value.facebook && `https://facebook.com/${custom.value.facebook}` }
].filter((s) => s.url))
const footAddress = computed(() => store.value?.location_address || '')
const hasFootContact = computed(() => Boolean(whatsappUrl.value || footAddress.value || socials.value.length))

// Color de la barra del navegador (meta theme-color). La hoja del diseño
// puede declarar el suyo (--rz-theme-color / --sp-theme-color) y así el
// chrome del navegador sigue al tema claro/oscuro elegido; sin declaración,
// se conserva el comportamiento anterior (tinta del acento).
function resolvedThemeColor() {
  const el = pageRoot.value
  if (el) {
    const cs = getComputedStyle(el)
    const skin = cs.getPropertyValue('--rz-theme-color').trim() || cs.getPropertyValue('--sp-theme-color').trim()
    if (/^#|^rgb/i.test(skin)) return skin
  }
  return themeVars.value['--store-accent-ink']
}

// SEO y previews: Open Graph / Twitter / theme-color + JSON-LD (Store o
// LocalBusiness) con nombre, dirección, horarios y redes.
let clearSeo = null
function syncSeo() {
  clearSeo?.()
  clearSeo = null
  if (status.value !== 'success') return
  const c = custom.value
  const s = store.value
  const url = `${window.location.origin}${route.path}`
  const description = c.description?.trim() || `${shopName.value}${location.value ? ` en ${location.value}` : ''}. ${showCatalog.value ? 'Mirá el catálogo online y consultá por WhatsApp.' : 'Sitio oficial.'}`
  const image = (hasDesignAdvanced.value && c.cover) || c.carousel?.[0]?.url || c.logo || ''
  const phone = c.whatsapp ? `+${c.whatsapp.replace(/\D/g, '')}` : undefined
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': showCatalog.value ? 'Store' : 'LocalBusiness',
    name: shopName.value,
    description,
    url,
    image: image ? new URL(image, window.location.origin).href : undefined,
    logo: c.logo ? new URL(c.logo, window.location.origin).href : undefined,
    telephone: phone,
    address: location.value || s?.location_address ? {
      '@type': 'PostalAddress',
      streetAddress: s?.location_address || undefined,
      addressLocality: s?.city_name || undefined,
      addressRegion: s?.province_name || undefined,
      addressCountry: 'AR'
    } : undefined,
    openingHoursSpecification: c.show_hours !== false ? schemaHours(c.hours) : [],
    sameAs: socials.value.map((x) => x.url)
  }
  if (!jsonLd.openingHoursSpecification.length) delete jsonLd.openingHoursSpecification
  if (!jsonLd.sameAs.length) delete jsonLd.sameAs
  clearSeo = applySeo({
    title: document.title,
    description,
    image,
    url,
    themeColor: resolvedThemeColor(),
    jsonLd: JSON.parse(JSON.stringify(jsonLd))
  })
}
// pageTheme entra en las dependencias: al togglear claro/oscuro se re-emite
// el theme-color con el cromo del tema nuevo (sin flash en la barra).
watch([status, () => route.path, custom, pageTheme], syncSeo, { flush: 'post' })

// Favicon de la pestaña: mientras se visita la web, el icono es el logo de la
// tienda (sin logo queda el de DAVENT). Al salir se restaura el original.
const faviconEl = document.querySelector('link[rel="icon"]')
const faviconDefault = faviconEl ? { href: faviconEl.getAttribute('href'), type: faviconEl.getAttribute('type') } : null
function applyFavicon(logo) {
  if (!faviconEl) return
  if (logo) {
    faviconEl.removeAttribute('type')
    faviconEl.setAttribute('href', logo)
  } else if (faviconDefault) {
    if (faviconDefault.type) faviconEl.setAttribute('type', faviconDefault.type)
    faviconEl.setAttribute('href', faviconDefault.href)
  }
}
watch(() => custom.value.logo, applyFavicon)

onMounted(async () => {
  // El catálogo vuela en paralelo con la ficha de la tienda: en Inicio es la
  // vitrina de destacados ({sort:'recent'}), en Catálogo el listado inicial
  // ({sort:'name'}) y en la ficha de producto el catálogo completo. La vista
  // hija recibe la misma promesa por loadPublicCatalog — cero espera extra.
  if (isHome.value) loadPublicCatalog({ sort: 'recent' })
  else if (isCatalog.value) loadPublicCatalog({ sort: 'name' })
  else if (isProduct.value) loadPublicCatalog()
  // La página Servicios no necesita el catálogo: sus ítems viajan en el
  // payload público de la tienda (service_items).
  // El documento del diseño viaja en paralelo con la ficha: si el patrón
  // todavía no tiene contrato de datos vuelve `{}` y se usa la plantilla Vue.
  if (!studioMode.value && (isHome.value || isCatalog.value || isServices.value)) {
    storesApi.publicPattern(slug.value, { preview: previewToken.value })
      .then((doc) => { patternDoc.value = doc && doc.html ? doc : null })
      .catch(() => { patternDoc.value = null })
  }
  try {
    store.value = await storesApi.publicStore(slug.value, { preview: previewToken.value })
    status.value = 'success'
    ensureStoreFont(custom.value.name_font)
    // Fuentes propias de la plantilla (titulares): las declara la Template
    // Definition (`fonts` en templates/<id>/index.js). Misma carga
    // on-demand que name_font; el resto del texto sigue con la fuente
    // elegida por el dueño.
    templateFonts(pageTemplate.value).forEach(ensureStoreFont)
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractApiError(e).nonField || 'Esta tienda no está disponible.'
  }
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('keydown', onMenuKey)
  window.addEventListener('message', onLayoutMessage)
  window.addEventListener('message', onStudioMessage)
  if (studioMode.value || previewToken.value) {
    // El modo Studio (?studio=1) y el link de vista previa (?preview=<token>)
    // deben sobrevivir a la navegación interna: sin el query, onStudioMessage
    // se apaga en silencio y el link compartido "cae" a lo publicado.
    const keep = {}
    if (studioMode.value) keep.studio = '1'
    if (previewToken.value) keep.preview = previewToken.value
    removeStudioGuard = router.beforeEach((to) => (
      Object.keys(keep).every((k) => to.query[k] === keep[k])
        ? true
        : { path: to.path, query: { ...to.query, ...keep }, hash: to.hash }
    ))
    if (studioMode.value && window.parent !== window) {
      window.parent.postMessage(studioReady(), parentOrigin)
    }
  }
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('keydown', onMenuKey)
  window.removeEventListener('message', onLayoutMessage)
  window.removeEventListener('message', onStudioMessage)
  removeStudioGuard?.()
  contentObserver?.disconnect()
  clearTimeout(contentFallback)
  clearSeo?.()
  applyFavicon(null)
})
</script>

<template>
  <div ref="pageRoot" class="store-page" :class="{ 'is-home': isHome, 'is-scrolled': scrolled }" :data-store-theme="pageTheme" :data-theme="pageTheme" :data-template="pageTemplate" :data-store-template="pageTemplate" :data-style="pageStyle" :data-skin="storeSkinOf(pageTemplate)" :data-logo-mode="custom.logo_mode" :data-has-logo="custom.logo ? '' : null" :data-mono="custom.mono_style" :data-st-tabbar="showTabbar ? '' : null" :style="[themeVars, publishedThemeVars, studioVars]" v-bind="pageAttrs">
    <button type="button" class="sp-skip" @click="skipToContent">Saltar al contenido</button>
    <span v-if="previewMode" class="sp-preview-badge" role="status">Vista previa — el diseño todavía no se publicó</span>
    <!-- Diseño del catálogo con contrato de datos: se pinta el documento
         del patrón (HTML/CSS/JS) en vez de la plantilla Vue. -->
    <PatternSurface
      v-if="usePattern"
      :doc="patternDoc"
      :theme="pageTheme"
      :surface="patternSurface"
      :title="shopName"
      @navigate="onPatternNavigate"
    />
    <button
      v-if="usePattern && showThemeToggle"
      type="button"
      class="sp-pattern-theme"
      :aria-label="pageTheme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
      :aria-pressed="pageTheme === 'dark'"
      @click="togglePageTheme"
    >
      <AppIcon :name="pageTheme === 'dark' ? 'sun' : 'moon'" :size="17" />
    </button>
    <div v-if="!usePattern" class="sp-vue-page">
    <!-- ===== Barra superior ===== -->
    <header class="sp-top" :class="{ scrolled }">
      <span class="sp-progress" aria-hidden="true" :style="{ transform: `scaleX(${progress})` }"></span>
      <div class="sp-container sp-top-inner">
        <button
          v-if="hasNavMenu"
          ref="menuBtn"
          type="button"
          class="sp-burger"
          :aria-label="ui.menuOpen ? 'Cerrar menú' : 'Abrir menú'"
          :aria-expanded="ui.menuOpen"
          aria-controls="sp-drawer"
          @click="ui.menuOpen = !ui.menuOpen"
        >
          <AppIcon :name="ui.menuOpen ? 'x' : 'menu'" :size="20" />
        </button>
        <RouterLink class="sp-brand" :to="homeTo" aria-label="Ir al inicio">
          <img v-if="custom.logo" class="sp-logo sm" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp-mono sm" aria-hidden="true">{{ initial }}</span>
          <span class="sp-brand-copy">
            <span class="sp-name" :style="nameFont">{{ shopName }}</span>
            <!-- Tienda Pro: la ubicación viaja bajo el nombre (identidad de
                 marketplace) en vez de ocupar una franja propia arriba. -->
            <span v-if="isShop" class="sp-shop-brand-meta">
              <AppIcon :name="location ? 'map-pin' : 'store'" :size="11" />
              {{ location || (showCatalog ? 'Catálogo online' : 'Sitio oficial') }}
            </span>
          </span>
        </RouterLink>
        <nav v-if="status === 'success' && !isShop" class="sp-top-links" aria-label="Secciones de la tienda">
          <RouterLink v-if="!landingOff" :to="homeTo">Inicio</RouterLink>
          <RouterLink v-if="showServices" :to="servicesTo">Servicios</RouterLink>
          <RouterLink v-if="showCatalog" :to="catalogTo">Catálogo</RouterLink>
          <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
          <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
          <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
        </nav>
        <!-- Tienda Pro: el buscador del masthead también existe fuera del
             catálogo — Enter o la lupa navegan a /catalogo?q= -->
        <label v-if="isCatalog || (isShop && showCatalog)" class="sp-search sp-search-top" :class="{ 'is-shop': isShop, open: ui.searchOpen }" id="sp-top-search">
          <AppIcon name="search" :size="16" aria-hidden="true" />
          <input ref="topSearchInput" v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" @keydown.esc.stop="ui.search = ''; ui.searchOpen = false" @keydown.enter="submitTopSearch" />
          <button v-if="ui.search" type="button" class="sp-search-clear" aria-label="Borrar búsqueda" @click="ui.search = ''"><AppIcon name="x" :size="14" /></button>
          <button v-if="isShop && !isCatalog" type="button" class="sp-search-go" aria-label="Buscar en el catálogo" @click="submitTopSearch"><AppIcon name="arrow-right" :size="15" /></button>
        </label>
        <div class="sp-top-end">
          <!-- Buscador colapsable en móvil: la lupa abre la barra bajo el
               header (Esc, Enter o la misma lupa la cierran). -->
          <button
            v-if="isCatalog || (isShop && showCatalog)"
            type="button"
            class="sp-icon-btn sp-search-toggle"
            :aria-label="ui.searchOpen ? 'Cerrar búsqueda' : 'Buscar productos'"
            :aria-expanded="ui.searchOpen"
            aria-controls="sp-top-search"
            @click="toggleTopSearch"
          >
            <AppIcon :name="ui.searchOpen ? 'x' : 'search'" :size="17" />
          </button>
          <RouterLink v-if="topCta" class="sp-top-cta" :to="topCta.to">
            <AppIcon :name="topCta.icon" :size="16" /> {{ topCta.label }}
          </RouterLink>
          <button
            v-if="showThemeToggle"
            type="button"
            class="sp-icon-btn"
            :aria-label="pageTheme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
            :title="pageTheme === 'dark' ? 'Modo claro' : 'Modo oscuro'"
            :aria-pressed="pageTheme === 'dark'"
            @click="togglePageTheme"
          >
            <AppIcon :name="pageTheme === 'dark' ? 'sun' : 'moon'" :size="17" />
          </button>
        </div>
      </div>
      <!-- Tienda Pro: fila de secciones bajo el masthead (el menú clásico
           del marketplace). En móvil sigue visible y scrollea en horizontal. -->
      <nav v-if="isShop && status === 'success'" class="sp-shop-nav" aria-label="Secciones de la tienda">
        <div class="sp-container sp-shop-nav-inner">
          <div class="sp-shop-nav-links">
            <RouterLink v-if="!landingOff" :to="homeTo" :class="{ 'is-current': shopCurrent === 'home' }" :aria-current="shopCurrent === 'home' ? 'page' : null">Inicio</RouterLink>
            <RouterLink v-if="showServices" :to="servicesTo" :class="{ 'is-current': shopCurrent === 'services' }" :aria-current="shopCurrent === 'services' ? 'page' : null">Servicios</RouterLink>
            <RouterLink v-if="showCatalog" :to="catalogTo" :class="{ 'is-current': shopCurrent === 'catalog' }" :aria-current="shopCurrent === 'catalog' ? 'page' : null">Catálogo</RouterLink>
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" :class="{ 'is-current': shopCurrent === 'nosotros' }" :aria-current="shopCurrent === 'nosotros' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')" :class="{ 'is-current': shopCurrent === 'galeria' }" :aria-current="shopCurrent === 'galeria' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
            <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')" :class="{ 'is-current': shopCurrent === 'contacto' }" :aria-current="shopCurrent === 'contacto' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
          </div>
          <span class="sp-shop-nav-note">Precios en pesos argentinos</span>
        </div>
      </nav>
    </header>

    <!-- Menú móvil (solo navegación): los filtros del catálogo NO viven
         acá — van en CatalogFilters (bottom sheet propio). -->
    <div v-if="hasNavMenu" class="sp-overlay" :class="{ open: ui.menuOpen }" aria-hidden="true" @click="ui.menuOpen = false"></div>
    <nav v-if="hasNavMenu" ref="menuDrawer" id="sp-drawer" class="sp-drawer sp-navdrawer" :class="{ open: ui.menuOpen }" aria-label="Menú de la tienda">
      <div class="sp-drawer-head">
        <strong>{{ shopName }}</strong>
        <button type="button" class="sp-drawer-close" aria-label="Cerrar menú" @click="ui.menuOpen = false">
          <AppIcon name="x" :size="18" />
        </button>
      </div>
      <div class="sp-nav-group" role="group">
        <RouterLink
          v-for="l in navMenuLinks" :key="l.label"
          :to="l.to" class="sp-nav-item"
          :active-class="l.anchor ? 'sp-anchor' : 'router-link-active'"
          :exact-active-class="l.anchor ? 'sp-anchor' : 'router-link-exact-active'"
          @click="ui.menuOpen = false"
        ><span>{{ l.label }}</span><AppIcon name="chevron-right" :size="15" aria-hidden="true" /></RouterLink>
      </div>
    </nav>

    <!-- Tab bar móvil (tema mobile.nav = 'bottom'): 4 destinos + "Más",
         calcada del .tabbar del dashboard y por encima del dock de CTA. -->
    <nav v-if="showTabbar" class="sp-tabbar" aria-label="Secciones principales">
      <RouterLink
        v-for="t in tabLinks" :key="t.label" :to="t.to" class="sp-tab"
        :class="{ active: isTabActive(t.label) }"
        :aria-current="isTabActive(t.label) ? 'page' : undefined"
      >
        <AppIcon :name="t.icon" :size="20" />
        <span>{{ t.label }}</span>
      </RouterLink>
      <button
        ref="moreBtn" type="button" class="sp-tab"
        :class="{ active: ui.moreOpen }"
        :aria-expanded="ui.moreOpen" aria-controls="sp-more-sheet"
        @click="ui.moreOpen = !ui.moreOpen"
      >
        <AppIcon name="menu" :size="20" />
        <span>Más</span>
      </button>
    </nav>

    <!-- Sheet "Más": el resto del menú, contacto y tema -->
    <template v-if="showTabbar">
      <div v-if="ui.moreOpen" class="sp-more-scrim" aria-hidden="true" @click="ui.moreOpen = false"></div>
      <div
        id="sp-more-sheet" ref="moreSheet" class="sp-more-sheet" :class="{ open: ui.moreOpen }"
        role="dialog" aria-modal="true" aria-label="Todas las secciones"
      >
        <div class="sp-more-head">
          <span class="sp-more-grab" aria-hidden="true"></span>
          <div class="sp-more-brand">
            <img v-if="custom.logo" class="sp-logo sm" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sp-mono sm" aria-hidden="true">{{ initial }}</span>
            <strong :style="nameFont">{{ shopName }}</strong>
          </div>
          <button type="button" class="sp-more-close" aria-label="Cerrar menú" @click="ui.moreOpen = false">
            <AppIcon name="x" :size="18" />
          </button>
        </div>
        <nav class="sp-more-nav" aria-label="Todas las secciones">
          <RouterLink
            v-for="l in moreLinks" :key="l.label" :to="l.to" class="sp-more-link"
            :active-class="l.anchor ? 'sp-anchor' : 'router-link-active'"
            :exact-active-class="l.anchor ? 'sp-anchor' : 'router-link-exact-active'"
            @click="ui.moreOpen = false"
          >
            <span>{{ l.label }}</span>
            <AppIcon name="chevron-right" :size="16" aria-hidden="true" />
          </RouterLink>
          <p v-if="!moreLinks.length" class="sp-more-empty">No hay más secciones publicadas.</p>
        </nav>
        <div class="sp-more-foot">
          <a v-if="whatsappUrl" class="sp-more-link is-wa" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="17" aria-hidden="true" /><span>WhatsApp</span>
          </a>
          <RouterLink v-if="showCatalog && !isCatalog" class="sp-more-link" :to="catalogTo" @click="ui.moreOpen = false">
            <AppIcon name="search" :size="17" aria-hidden="true" /><span>Buscar productos</span>
          </RouterLink>
          <button v-if="showThemeToggle" type="button" class="sp-more-link" @click="ui.moreOpen = false; togglePageTheme()">
            <AppIcon :name="pageTheme === 'dark' ? 'sun' : 'moon'" :size="17" aria-hidden="true" />
            <span>{{ pageTheme === 'dark' ? 'Modo claro' : 'Modo oscuro' }}</span>
          </button>
        </div>
      </div>
    </template>

    <span id="sp-main" ref="mainAnchor" tabindex="-1" class="sp-main-anchor"></span>

    <div v-if="status === 'loading'" class="sp-boot" role="status" aria-live="polite" aria-busy="true">
      <span class="sp-sr-only">Cargando la tienda…</span>
      <div class="sp-boot-hero" aria-hidden="true">
        <span class="sp-sk-line sp-boot-badge"></span>
        <span class="sp-sk-line sp-boot-title"></span>
        <span class="sp-sk-line sp-boot-sub"></span>
        <span class="sp-boot-ctas"><span class="sp-sk-line"></span><span class="sp-sk-line"></span></span>
      </div>
      <div class="sp-container sp-boot-grid" aria-hidden="true">
        <div v-for="n in 4" :key="n" class="sp-boot-card"><span class="sp-sk-line sp-boot-img"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
      </div>
    </div>

    <div v-else-if="status === 'error'" class="sp-state">
      <span class="sp-state-icon"><AppIcon name="store" :size="26" /></span>
      <h1>Tienda no disponible</h1>
      <p>{{ errorMsg }}</p>
    </div>

    <!-- Página activa (Inicio / Catálogo) con transición suave entre ambas -->
    <RouterView v-else v-slot="{ Component }">
      <Transition name="sp-page" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </Transition>
    </RouterView>

    <!-- ===== Pie =====
         No se pinta durante el estado de carga: el pie aparecía pegado al
         skeleton y saltaba fuera del viewport al llegar el payload (CLS ~0.8
         medido en las 3 plantillas). Con el contenido ya resuelto se monta
         debajo, sin desplazar lo que el visitante está leyendo. -->
    <footer v-if="status !== 'loading' && (contentReady || status === 'error')" class="sp-foot">
      <div v-reveal class="sp-container">
        <div class="sp-foot-grid">
          <div class="sp-foot-brand">
            <strong :style="nameFont">{{ shopName }}</strong>
            <span v-if="location"><AppIcon name="map-pin" :size="13" /> {{ location }}</span>
            <p v-if="isShop && custom.description" class="sp-foot-desc">{{ custom.description }}</p>
            <ul v-if="status === 'success' && hasFootContact" class="sp-foot-contact" aria-label="Contacto">
              <li v-if="footAddress"><AppIcon name="map-pin" :size="14" /> {{ footAddress }}</li>
              <li v-if="whatsappUrl"><a :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="14" /> {{ custom.whatsapp }}</a></li>
            </ul>
            <div v-if="status === 'success' && socials.length" class="sp-foot-social">
              <a v-for="s in socials" :key="s.key" :href="s.url" target="_blank" rel="noopener" :aria-label="`${s.label} de ${shopName}`" :title="s.label"><AppIcon :name="s.key" :size="17" /></a>
            </div>
          </div>
          <nav v-if="isShop && status === 'success'" class="sp-foot-col" aria-label="Secciones de la tienda">
            <p class="sp-foot-heading">Tienda</p>
            <RouterLink v-if="!landingOff" :to="homeTo">Inicio</RouterLink>
            <RouterLink v-if="showServices" :to="servicesTo">Servicios</RouterLink>
            <RouterLink v-if="showCatalog" :to="catalogTo">Catálogo</RouterLink>
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
            <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
          </nav>
          <nav class="sp-foot-col" aria-label="Información del sitio">
            <p class="sp-foot-heading">Información</p>
            <a :href="`${appUrl}/terminos`">Términos y condiciones</a>
            <a :href="`${appUrl}/denuncias`">Denunciar contenido</a>
          </nav>
        </div>
        <div class="sp-foot-bottom">
          <p class="sp-foot-copy">© {{ year }} {{ shopName }}. Todos los derechos reservados.</p>
          <a :href="`${appUrl}/register`" class="sp-davent-badge">
            <BrandLogo :size="16" /> Publicado con <strong>DAVENT</strong>
          </a>
        </div>
        <p v-if="custom.footer_text" class="sp-foot-note">{{ custom.footer_text }}</p>
      </div>
    </footer>

    <!-- Chatbot del negocio (has_chatbot): burbuja robot abajo a la derecha -->
    <StoreBot
      v-if="botConfig"
      :config="botConfig"
      :name="shopName"
      :logo="custom.logo"
      :initial="initial"
    />
    </div>
  </div>
</template>
