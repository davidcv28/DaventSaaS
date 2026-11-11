<script setup>
import { ref, reactive, computed, provide, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  storesApi, normalizeSlug, normalizeCatalogParams, storeThemeVars, ensureStoreFont, resolveStoreTemplate, CUSTOMIZATION_DEFAULTS, STORE_TEMPLATES, AI_EXTRA_TEMPLATES, storeSkinOf,
  storeContactLink, hasContactChannel
} from '../api/stores.api.js'
import { env, storeHostSlug, customDomainHost, setStoreHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
import StoreBot from '../components/StoreBot.vue'
import PatternSurface from '../components/store/PatternSurface.vue'
import StoreCartDrawer from '../components/ecommerce/StoreCartDrawer.vue'
import StoreAuthModal from '../components/ecommerce/StoreAuthModal.vue'
import { useCartStore } from '../stores/cart.store.js'
import { useCustomerStore } from '../stores/customer.store.js'
import { vReveal } from '../directives/reveal.js'
import { applySeo } from '../utils/seo.js'
import { readVisitorTheme, persistVisitorTheme, resolveStoreTheme } from '../utils/storeTheme.js'
import { schemaHours } from '../utils/storeHours.js'
import { templateFonts, normalizeLayoutConfig, templatePages, templateBlocks, templateOf } from '../templates/index.js'
import { useDesignCatalog } from '../composables/useDesignCatalog.js'
import { STUDIO_MSG, isStudioMessage, studioReady } from '../studio/contract.js'
import { familyOf } from '../utils/styleIcons.js'
import {
  studioPreviewVars, studioPreviewAttrs, applyFocusRing,
  storeSiteThemeVars, storeSiteThemeAttrs, skinOf, SKIN_FAMILIES,
  sanitizeSiteTheme
} from '../components/studio/previewBridge.js'
import { patternStudioCss, patternStudioFontsCss } from '../studio/patternStudio.js'
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
// Tipo de fallo al cargar la tienda: 'notfound' (404) muestra su propio
// mensaje; 'busy' (429/5xx/red) ofrece el botón Reintentar. Nunca se
// vuelca el `detail` crudo del backend a la UI.
const storeErrorKind = ref('')
// El slug viene del path (dominio de plataforma /<slug>) o del subdominio
// (<slug>.<dominio>, donde la tienda es la raíz y no hay param en la ruta).
const slug = computed(() => normalizeSlug(route.params.slug || storeHostSlug || ''))
const appUrl = env.appUrl

// ---- E-commerce del comprador (customer JWT — independiente de la
// sesión DAVENT del dueño). El carrito y el modal de auth se montan una
// sola vez acá y los usan el header, las tarjetas y las vistas hijas. ----
const cartStore = useCartStore()
const customerStore = useCustomerStore()
// Gate efectivo de venta online: lo calcula el backend en el payload
// público (ecommerce_enabled + perfil fiscal completo) — el front solo
// lo expone, nunca lo recalcula.
const ordersEnabled = computed(() => Boolean(store.value?.orders_enabled))
// Cuentas de compradores (beneficio has_customer_auth del plan del dueño):
// el backend expone customer_auth_enabled en el mismo payload público que
// orders_enabled. REGLA: solo se oculta cuando el campo existe y viene en
// false — si el backend aún no lo manda, la entrada de cuenta sigue como
// antes (comportamiento vigente).
const customerAuthEnabled = computed(() => store.value?.customer_auth_enabled !== false)
// Rutas de autenticación/cuenta del comprador: con el beneficio apagado no
// se sirven — un deep link a /ingresar o /cuenta vuelve a la home (el
// watch de más abajo hace el replace).
const CUSTOMER_AUTH_ROUTES = new Set(['store-auth', 'store-account', 'store-account-verify', 'store-account-reset'])
// Las rutas de comercio NUNCA se sirven como documento de diseño: si el
// patternSurface las mandara al 'landing' del patrón, el checkout y la
// cuenta quedarían tapados por el iframe del diseño.
const ECOMMERCE_ROUTES = new Set([
  'store-checkout', 'store-tracking', 'store-cart', 'store-receipt',
  'store-auth', 'store-plans',
  'store-account', 'store-account-verify', 'store-account-reset',
  'store-legal', 'store-legal-page'
])
const isEcommerceRoute = computed(() => ECOMMERCE_ROUTES.has(route.name))

// Vista previa en vivo del editor de bloques: el panel empuja el
// layout_config del draft por postMessage same-origin y la página lo
// aplica reactivo, sin recargar el iframe.
const layoutOverride = ref(null)
let removeStudioGuard = null
let studioSeenTimer = null
// Identidad/cromo del borrador que el Studio empuja en modo edición
// (tamaño del nombre, portada, logo, copy de secciones): lo que se ve en el
// lienzo es exactamente lo que va a quedar guardado, sin recargar.
const studioCustom = ref(null)
// Catálogo de diseño (patrones + estilos) desde la API: el patrón base y
// su estilo son el fallback de la web cuando la tienda no eligió nada.
const { defaultPattern, defaultStyle, styles: catalogStyles, iconStyles, defaultIconStyle, load: loadDesignCatalog } = useDesignCatalog()
// Layout del patrón de diseño de la base: única fuente de composición de las
// tres superficies cuando la tienda no guardó su propio layout_config.
const patternLayout = computed(() => normalizeLayoutConfig(defaultPattern.value?.layout))
// Diseño del catálogo servido como documento propio (HTML/CSS/JS con las
// variables resueltas por el backend). Solo se usa cuando el patrón ya
// declara su contrato de datos (`ready`); en el Studio se sigue editando
// con la plantilla Vue, que es la que responde a los cambios en vivo.
const patternDoc = ref(null)
// El iframe del documento avisa cuando pintó: mientras tanto se muestra el
// skeleton en vez de la plantilla Vue (el fallback pintaba el diseño viejo
// un instante en cada carga).
const patternFrameReady = ref(false)
// Diseños con identidad propia: su composición canónica y su paleta viven en
// la Template Definition y en la hoja store-<id>.css. El layout y el tema del
// patrón base (esencial/raiz) NO se les aplica: les pisaba variantes firma
// (hero 'centered') y el acento de la tienda con la paleta neutra del estilo.
const SKIN_TEMPLATES = new Set(['mercado', 'gimnasio', 'movimiento', 'sastreria', 'moderntec', 'indumentaria', 'impacto'])
//Superficie que el documento del patrón debe pintar en esta ruta. Si el
//diseño no la declara (`surfaces`), esa ruta sigue con la plantilla Vue.
const patternSurface = computed(() => {
  if (isEcommerceRoute.value) return ''
  return (
    route.name === 'store-catalog' ? 'catalog'
      : route.name === 'store-services' ? 'services'
        : route.name === 'store-product' ? 'product'
          : 'landing'
  )
})
const usePattern = computed(() => Boolean(
  //Sin el payload de la tienda no se conoce el tema/identidad: montar antes
  //cargaba el documento en claro y el cambio a oscuro se veía como flash.
  store.value &&
  //También en el Studio: la vista previa tiene que mostrar el mismo
  //documento que se publica (antes enseñaba la plantilla Vue y la web
  //publicada rompía).
  patternDoc.value?.ready && (patternDoc.value?.has_html || patternDoc.value?.html) &&
  (patternDoc.value?.surfaces || []).includes(patternSurface.value) &&
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
  const ownsSkin = SKIN_TEMPLATES.has(merged.template)
  const baseLayout = ownsSkin ? {} : patternLayout.value
  merged.layout_config = Object.keys(savedLayout).length || Object.keys(baseLayout).length
    ? { ...baseLayout, ...savedLayout }
    : {}
  // Los diseños con piel propia tampoco heredan la paleta del estilo base:
  // sin tema elegido, su acento y sus superficies salen de su hoja.
  if (!studioMode.value && !ownsSkin && (!raw.site_theme || !Object.keys(raw.site_theme).length) && style?.tokens) merged.site_theme = style.tokens
  // Saneo contra el catálogo de la base: un estilo/fuente que ya no existe
  // se descarta y cae al default en vez de renderizar un valor huérfano.
  if (merged.site_theme && typeof merged.site_theme === 'object') {
    merged.site_theme = sanitizeSiteTheme(
      merged.site_theme,
      catalogStyles.value.map((s) => s.slug)
    )
  }
  return merged
})
//La huella del HTML/CSS/JS fuerza una URL nueva cuando cambia el patrón;
//en Studio también incluye logo/portada para no reutilizar el iframe viejo.
const patternRevision = computed(() => (
  JSON.stringify([
    patternDoc.value?.revision || '',
    ...(studioMode.value ? [custom.value.logo?.url || '', custom.value.cover?.url || ''] : [])
  ])
))
//Estilo en ensayo distinto al del borrador: viaja como `?style=` del
//documento (su paleta/fuentes se hornean en el render del lado del
//servidor — el puente no puede recolorear un iframe de origen opaco).
//Sin override el documento renderiza el site_theme del borrador tal cual.
const patternStyleOverride = computed(() => {
  const picked = custom.value?.site_theme?.style?.id || ''
  const saved = store.value?.customization?.site_theme?.style?.id || ''
  return picked !== saved ? picked : ''
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
// "Agregar al carrito" del documento del patrón (postMessage ds-buy): el
// iframe es origen opaco y no puede llamar a la API — acá sí hay sesión
// de comprador; addToCart maneja login pendiente, drawer y toasts.
function onPatternBuy({ id } = {}) {
  if (!ordersEnabled.value || !id) return
  cartStore.addToCart(id, 1)
}
// "Comprar ahora" del documento del patrón (postMessage ds-buy-now):
// alta silenciosa y directo al checkout — buyNow corre `after` también
// post-login, así que un invitado termina en el mismo destino.
function onPatternBuyNow({ id } = {}) {
  if (!ordersEnabled.value || !id) return
  cartStore.buyNow(id, 1, '', () => router.push(cartStore.checkoutRoute()))
}
// Entrada "Mi cuenta" del documento del patrón (postMessage ds-account):
// con sesión de comprador va directo a /cuenta; sin sesión navega a la
// página de auth /ingresar con la cuenta como ?next= (un {route} sí puede
// cruzar la navegación — a diferencia de un {action} pendiente).
function onPatternAccount() {
  if (!customerAuthEnabled.value) return
  if (customerStore.isAuthenticated) {
    router.push(accountTo.value)
    return
  }
  router.push(cartStore.authRoute('login', accountTo.value))
}
function onLayoutMessage(e) {
  if (e.data?.type !== 'davent:layout') return
  if (!studioAllowedOrigins.has(e.origin)) return
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
const studioUpdateSeen = ref(false) // llegó el primer UPDATE del host
// Meta del patrón en ensayo pidiéndose: hasta que resuelve, la rama que
// pinta (documento del diseño o plantilla Vue) no se puede decidir con el
// meta del patrón GUARDADO — mostrarla antes flasheaba el diseño viejo.
const patternMetaBusy = ref(false)
const patternWaiting = computed(() => studioMode.value && (!studioUpdateSeen.value || patternMetaBusy.value))
// Orígenes habilitados para el protocolo Studio (?studio=1): el propio
// origen y la app DAVENT que embebe la vista previa. El referrer NO es
// fallback válido — cualquier sitio que embeba la página con ?studio=1 se
// declaraba "padre" y podía inyectar theme/layout/custom (videos, fondos
// con url()). Solo orígenes de la plataforma pueden hablarle al iframe.
const studioAllowedOrigins = (() => {
  const allowed = new Set([window.location.origin])
  try { allowed.add(new URL(env.appUrl).origin) } catch { /* appUrl inválida en dev */ }
  const pd = String(env.platformDomain || '').toLowerCase()
  if (pd && !pd.includes('localhost')) {
    for (const sub of ['', 'www', 'app', 'api', 'admin', 'panel']) {
      allowed.add(`https://${sub ? `${sub}.` : ''}${pd}`)
    }
  }
  return allowed
})()
function onStudioMessage(e) {
  if (!studioMode.value || !isStudioMessage(e.data)) return
  if (!studioAllowedOrigins.has(e.origin)) return
  const d = e.data
  if (d.type === STUDIO_MSG.UPDATE) {
    studioUpdateSeen.value = true
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
//El meta (ready/superficies/totales) describe el patrón del documento:
//al ensayar otro diseño se repide con `template=` — antes se evaluaba
//usePattern con el meta del GUARDADO y el documento del ELEGIDO, así un
//diseño distinto al guardado podía no montarse o caer al default.
//`patternMetaFor` recuerda de qué template es el meta vigente ('' = el
//del borrador, el que pidió el mount): volver al diseño del borrador
//también repide, porque el meta ya es del último ensayo.
const patternMetaFor = ref('')
watch(studioTemplate, async (tpl) => {
  if (!tpl) return
  const saved = store.value?.customization?.template || ''
  if (tpl === (patternMetaFor.value || saved)) return
  patternMetaBusy.value = true
  //El documento que viene es de OTRO diseño: skeleton hasta que pinte
  //(patternFrameReady quedaba en true del anterior y el swap mostraba un
  //lienzo en blanco mientras el iframe cargaba).
  patternFrameReady.value = false
  try {
    const doc = await storesApi.publicPattern(slug.value, { preview: previewToken.value, meta: true, template: tpl })
    patternDoc.value = doc && (doc.has_html || doc.html) ? doc : null
  } catch {
    patternDoc.value = null
  } finally {
    patternMetaFor.value = tpl
    patternMetaBusy.value = false
  }
})
//El meta se pide al montar solo si la primera ruta es una superficie del
//documento: entrando por cuenta/ingresar/carrito (ecommerce) y navegando
//después al inicio, `patternDoc` quedaba en null para siempre y la landing
//se veía con la plantilla Vue — el diseño viejo — hasta recargar. Al pisar
//una superficie sin meta se repide una vez; el skeleton tapa el hueco.
//`patternMetaDone` corta la repetición cuando la tienda no tiene documento
//(meta `{}` responde ok): solo un fallo de red habilita otro intento.
const patternMetaDone = ref(false)
const patternMetaLoading = ref(false)
watch(patternSurface, async (surface) => {
  if (!surface || patternDoc.value || patternMetaDone.value || patternMetaLoading.value || studioMode.value) return
  patternMetaLoading.value = true
  const params = { preview: previewToken.value, meta: true }
  try {
    const doc = await storesApi.publicPattern(slug.value, params)
      .catch(() => storesApi.publicPattern(slug.value, params))
      .catch(() => null)
    if (doc !== null) patternMetaDone.value = true
    if (!patternDoc.value) patternDoc.value = doc && (doc.has_html || doc.html) ? doc : null
  } finally {
    patternMetaLoading.value = false
  }
})
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
//CSS del Studio para el documento de diseño (DesignPattern): el tema
//efectivo es el borrador en modo Studio/en preview compartido, o el
//publicado (ya filtrado por plan en la API). patternStudioCss es el
//espejo JS de studio_theme_css del backend — mismas reglas sobre los
//hooks compartidos (.btn/.ds-product*/section.hero/...).
//custom.site_theme ya resuelve el borrador en Studio/preview y lo
//publicado (filtrado por plan) en la web pública.
const patternStudioTheme = computed(() => custom.value?.site_theme || null)
const patternStudioCssText = ref('')
let patternStudioSeq = 0
watch([patternStudioTheme, () => usePattern.value, () => custom.value?.accent_custom], async ([theme, isPattern]) => {
  const seq = ++patternStudioSeq
  // theme puede ser null: accent_custom solo ya emite --ds-accent/-ink,
  // igual que theme_css del backend.
  if (!isPattern) {
    patternStudioCssText.value = ''
    return
  }
  const fontsCss = await patternStudioFontsCss(theme && typeof theme === 'object' ? theme : {})
  if (seq !== patternStudioSeq) return
  patternStudioCssText.value = patternStudioCss(theme, fontsCss, custom.value?.accent_custom)
}, { immediate: true })
const themeVars = computed(() => storeThemeVars(custom.value))
// Tema guardado (site_theme): se emite SIEMPRE, no solo en modo Studio, para
// que lo que se ve en el canvas sea exactamente lo que ve el visitante.
// Es parcial: cada variable sale solo si el tema fija ese campo, y sin
// site_theme el objeto queda vacío (la web se ve idéntica a hoy).
// En modo Studio manda el borrador (studioVars/studioAttrs): lo publicado no
// se mezcla para que un campo que el borrador no fija no se cuele en el
// lienzo y preview/publicada queden idénticas.
// Los diseños del catálogo (raiz/sastreria/moderntec/…) consumen los mismos
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
// marca el nivel del plan (Básico: Raíz/Esencial; Estándar suma los diseños
// de rubro). Si el guardado quedó fuera — baja de
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
// Masthead tipo marketplace: solo existía con 'mercado'/'shop' (retirados a
// 'raiz' — el único diseño). Queda como flag apagado por compatibilidad del
// template.
const isShop = computed(() => false)

// Hoja propia del diseño: tiñe también el chrome (barra, pie, dock) en
// páginas que no montan la portada (servicios, ficha). Se carga on-demand y
// una sola vez. Al terminar la carga se re-sincroniza el SEO para tomar el
// theme-color que declare la hoja.
const TEMPLATE_CSS = {
  raiz:      () => import('../assets/store-raiz.css'),
  mercado:   () => import('../assets/store-mercado.css'),
  gimnasio:  () => import('../assets/store-gimnasio.css'),
  movimiento: () => import('../assets/store-movimiento.css'),
  sastreria: () => import('../assets/store-sastreria.css'),
  moderntec: () => Promise.all([
    import('../assets/store-moderntec.css'),
    import('../assets/store-moderntec-auth.css'),
    import('../assets/store-moderntec-account.css'),
    import('../assets/store-moderntec-account-sections.css')
  ]),
  indumentaria: () => import('../assets/store-indumentaria.css'),
  impacto:   () => import('../assets/store-impacto.css')
}
// Diseño del catálogo elegido (slug): tiñe las páginas de comercio que NO
// montan el documento del patrón (ingresar, cuenta, carrito, checkout).
// Cada diseño trae su propia hoja `store-design-<slug>.css`, cargada
// on-demand; si no existe, la página queda con la piel neutra.
const DESIGN_EC_CSS = import.meta.glob('../assets/store-design-*.css')
const designId = computed(() => {
  const raw = String(custom.value.template || custom.value?.site_theme?.style?.id || '').trim().toLowerCase()
  if (!raw || raw === 'raiz') return 'esencial'
  return raw
})
watch(designId, (id) => {
  const load = DESIGN_EC_CSS[`../assets/store-design-${id}.css`]
  if (load) load().catch(() => {})
  // Esencial parte su piel de auth en hoja propia (split con la de cuenta):
  // el modal de auth puede abrirse desde cualquier página de la tienda, así
  // que la hoja se carga on-demand junto a la base, no solo en /ingresar.
  if (id === 'esencial') import('../assets/store-design-esencial-auth.css').catch(() => {})
}, { immediate: true })
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
// Mercado (Bazar) no hereda la preferencia del sistema: el modo noche lo
// decide el visitante desde el interruptor (o el tema fijado por la tienda).
const prefersDark = computed(() => (
  typeof window !== 'undefined' && window.matchMedia && pageTemplate.value !== 'mercado'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false
))
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
  prefersDark: prefersDark.value
}))
// Interruptor de noche: lo habilita el negocio (theme_toggle). Payloads
// viejos sin el campo conservan la regla anterior (sin diseño avanzado el
// visitante ya podía alternarlo).
// Los diseños oscuros (moderntec) arrancan de noche: ahí el
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
// La fuente del nombre (`name_font`) ya no se elige en el dashboard: la
// tipografía de la web la define cada diseño/tema. El binding queda vacío
// para que nombre, titular y marca usen las familias de la piel.
const nameFont = computed(() => ({}))
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
// Un ancla (#nosotros/#galeria/#contacto) solo existe si el bloque quedó
// habilitado en la composición efectiva del diseño (algunos templates no
// lo declaran) — sin esto el link del nav quedaba muerto.
const landingBlockOn = (id) => templateBlocks(pageTemplate.value, 'landing', custom.value?.layout_config)
  .some((b) => b.id === id && b.enabled !== false)
const landingHasAbout = computed(() => landingBlockOn('about'))
const landingHasGallery = computed(() => landingBlockOn('gallery'))
const landingHasContact = computed(() => landingBlockOn('contact'))
const hasAbout = computed(() => custom.value.show_about !== false && landingHasAbout.value && Boolean(
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
// pedido por WhatsApp, 'catalog' = catálogo de productos, 'plans' =
// página de suscripciones/membresías.
const siteTemplates = computed(() => {
  const list = Array.isArray(custom.value.site_templates) ? custom.value.site_templates : ['landing', 'catalog']
  const pages = templatePages(templateOf(custom.value.template))
  return ['landing', 'services', 'catalog', 'plans'].filter((k) => list.includes(k) && pages.includes(k))
})
// Página "Servicios": aparece solo si quedó en el set efectivo del plan.
const showServices = computed(() => status.value === 'success' && siteTemplates.value.includes('services'))
// Página "Suscripciones": ídem — sin flag propio, solo el cupo del plan.
const showPlans = computed(() => status.value === 'success' && siteTemplates.value.includes('plans'))
// Catálogo efectivo: la página existe en el set del plan y el dueño no la
// apagó. Sin esto el prefetch de portada pegaba un 404 en tiendas sin
// catálogo (patrones tipo ruta: landing + servicios nomás).
const catalogPageOn = computed(() => showCatalog.value && siteTemplates.value.includes('catalog'))
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
  if (catalogPageOn.value) links.push({ to: catalogTo.value, label: 'Catálogo' })
  if (showPlans.value) links.push({ to: plansTo.value, label: 'Suscripciones' })
  if (hasAbout.value && !landingOff.value) links.push({ to: anchorTo('#nosotros'), label: 'Nosotros', anchor: true })
  if (showGallery.value && landingHasGallery.value && !landingOff.value) links.push({ to: anchorTo('#galeria'), label: 'Galería', anchor: true })
  if (showContact.value && landingHasContact.value && !landingOff.value) links.push({ to: anchorTo('#contacto'), label: 'Contacto', anchor: true })
  return links
})
// El burger se muestra cuando hay navegación que esconder — Tienda Pro usa
// su propia fila .sp-shop-nav (visible también en móvil).
const hasNavMenu = computed(() => status.value === 'success' && !isShop.value && navMenuLinks.value.length > 0)

// Tema mobile.nav: 'bottom' (default de la web pública) monta la tab bar
// (4 destinos + "Más") en lugar del burger; 'top' conserva el header con
// burger + drawer lateral y 'drawer' deja solo marca + burger.
const mobileNav = computed(() => pageAttrs.value['data-st-nav'] || 'bottom')
// Prioridad de destinos en la tab bar: Inicio → Catálogo → Servicios → Suscripciones → Contacto.
const TAB_PRIORITY = ['Inicio', 'Catálogo', 'Servicios', 'Suscripciones', 'Contacto']
const TAB_ICONS = { Inicio: 'store', Catálogo: 'package', Servicios: 'wrench', Suscripciones: 'crown', Contacto: 'message-circle' }
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
    || (label === 'Suscripciones' && shopCurrent.value === 'plans')
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

const onMenuKey = (e) => {
  if (e.key === 'Escape') { ui.menuOpen = false; return }
  // Trampa de foco del drawer: Tab/Shift+Tab ciclan dentro mientras está
  // abierto (mismo contrato que el sheet "Más").
  if (e.key !== 'Tab' || !ui.menuOpen || !menuDrawer.value) return
  const items = [...menuDrawer.value.querySelectorAll(FOCUSABLE)]
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  const inside = menuDrawer.value.contains(document.activeElement)
  if (e.shiftKey && (!inside || document.activeElement === first)) { last.focus(); e.preventDefault() }
  else if (!e.shiftKey && (!inside || document.activeElement === last)) { first.focus(); e.preventDefault() }
}
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
const isPlans = computed(() => route.name === 'store-plans')
const isProduct = computed(() => route.name === 'store-product')
const isHome = computed(() => route.name === 'store-public')
// Sección activa del menú de Tienda Pro. No alcanza con router-link-active:
// las anclas de la home (#nosotros, #galeria, #contacto) comparten el path y
// quedarían todas marcadas a la vez.
const shopCurrent = computed(() => {
  if (isCatalog.value || isProduct.value) return 'catalog'
  if (isServices.value) return 'services'
  if (isPlans.value) return 'plans'
  if (!isHome.value) return ''
  const hash = route.hash.replace('#', '')
  return ['nosotros', 'galeria', 'contacto'].includes(hash) ? hash : 'home'
})
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${slug.value}/servicios` }))
const plansTo = computed(() => ({ path: storeHostSlug ? '/suscripciones' : `/${slug.value}/suscripciones` }))
const accountTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta` }))
// Deep link a /ingresar o /cuenta con el acceso de clientes apagado
// (customer_auth_enabled === false): vuelve a la home de la tienda.
watch([customerAuthEnabled, () => route.name], ([on, name]) => {
  if (!on && CUSTOMER_AUTH_ROUTES.has(name)) router.replace(homeTo.value)
}, { immediate: true })
const legalTo = (kind) => ({ path: storeHostSlug ? `/legal/${kind}` : `/${slug.value}/legal/${kind}` })
// Página de reemplazo cuando no hay portada: Servicios si está, si no el
// catálogo, si no Suscripciones (la web nunca queda sin destino — el
// backend siempre manda ≥1).
const homeFallbackTo = computed(() => (showServices.value ? servicesTo.value : catalogPageOn.value ? catalogTo.value : plansTo.value))
// Anclas de sección (#nosotros/#galeria/#contacto): van al inicio.
const anchorTo = (hash) => ({ path: homeTo.value.path, hash })
watch([landingOff, isHome], ([off, home]) => { if (off && home) router.replace(homeFallbackTo.value) }, { immediate: true })
// Página pedida por URL pero que el diseño/plan no soporta: el catálogo
// vuelve al inicio (o a la primera página disponible). Servicios y
// Suscripciones NO redirigen en silencio — sus vistas wrapper muestran
// un aviso explícito de "no disponible".
watch([isCatalog, catalogPageOn, landingOff, status], () => {
  if (status.value !== 'success') return
  if (isCatalog.value && !catalogPageOn.value) {
    router.replace(landingOff.value ? homeFallbackTo.value : homeTo.value)
  }
})

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
  if (isServices.value || isPlans.value) {
    if (!landingOff.value) return { to: homeTo.value, icon: 'store', label: 'Inicio' }
    if (catalogPageOn.value) return { to: catalogTo.value, icon: 'package', label: 'Catálogo' }
    return null
  }
  if (catalogPageOn.value) return { to: catalogTo.value, icon: 'package', label: 'Catálogo' }
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
  hasDesignAdvanced, pageTemplate, hasAbout, showGallery, showContact, showCatalog, catalogPageOn, showServices, showPlans, siteTemplates, ui, refreshSeo,
  landingHasGallery, landingHasContact,
  ordersEnabled,
  loadPublicCatalog
})

// El carrito es por tienda: se (re)apunta cada vez que cambia el slug
// (path /<slug> o subdominio/dominio propio resuelto async).
watch(slug, (s) => cartStore.bindStore(s), { immediate: true })

// Sesión del comprador expirada (customer.http la emite una sola vez por
// refresh fallido): se limpia el estado local y se avisa — la compra en
// curso pide login de nuevo vía el modal.
function onCustomerSessionExpired() {
  customerStore.handleSessionExpired()
  cartStore.onSessionExpired()
  cartStore.flash('err', 'Tu sesión expiró. Ingresá de nuevo para seguir comprando.', 5000)
}
window.addEventListener('davent:customer-session-expired', onCustomerSessionExpired)

// El modal de auth terminó con login/register/google exitoso: corre la
// acción pendiente ("agregar al carrito", "suscribirme") o navega a la
// ruta que la disparó (checkout/cuenta).
async function onCustomerAuthed() {
  const pending = cartStore.takePending()
  if (pending?.action) {
    try { await pending.action() } catch { /* la acción maneja sus errores */ }
  } else if (pending?.route) {
    router.push(pending.route)
  } else {
    await cartStore.refresh()
  }
}

// Título de pestaña por página: "<tienda>" en Inicio, "<tienda> · Catálogo"
// en el catálogo, "<tienda> · Servicios" en la página de servicios.
// Corre también al volver al inicio.
watch([status, () => route.name], ([s, name]) => {
  // Tienda caída: título de fallback neutro (la ficha real no cargó).
  if (s === 'error') { document.title = 'Tienda no disponible'; return }
  if (s !== 'success') return
  document.title = name === 'store-catalog' ? `${shopName.value} · Catálogo`
    : name === 'store-services' ? `${shopName.value} · Servicios`
    : name === 'store-plans' ? `${shopName.value} · Suscripciones`
    : name === 'store-auth' ? `${shopName.value} · Ingresar`
    : shopName.value
}, { immediate: true })

// Título de pestaña en la ficha de producto cuando la página la pinta el
// documento del patrón (iframe): la vista Vue no monta, así que el nombre
// sale del catálogo público ya cacheado. Sin esto la pestaña quedaba con
// el nombre de la tienda.
watch([isProduct, usePattern, () => route.params.productId, status], async () => {
  if (!isProduct.value || !usePattern.value || !catalogPageOn.value || status.value !== 'success') return
  try {
    const data = await loadPublicCatalog()
    const p = (data?.products || []).find((x) => String(x.id) === String(route.params.productId))
    if (p?.name && status.value === 'success') {
      document.title = `${p.name} · ${shopName.value}`
      refreshSeo()
    }
  } catch { /* catálogo caído: queda el título de la tienda */ }
})

// Canales de contacto (pie y barra fija móvil): pasan por el redirect de
// la API — el número y los usuarios de las redes no viajan en payload ni
// en el DOM (anti-scraping).
const whatsappUrl = computed(() => (hasContactChannel(custom.value, 'whatsapp') ? storeContactLink(slug.value, 'whatsapp') : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram' },
  { key: 'tiktok', label: 'TikTok' },
  { key: 'facebook', label: 'Facebook' }
].filter((s) => hasContactChannel(custom.value, s.key))
  .map((s) => ({ ...s, url: storeContactLink(slug.value, s.key) })))
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

// Canonical por página: applySeo cubre meta/OG/JSON-LD pero no el link —
// se gestiona acá con el mismo ciclo de vida (se restaura al desmontar).
let canonicalEl = null
let canonicalPrevHref = null // href que traía el index.html (null = no existía)
function syncCanonical(url) {
  if (!canonicalEl) {
    canonicalEl = document.head.querySelector('link[rel="canonical"]')
    canonicalPrevHref = canonicalEl ? canonicalEl.getAttribute('href') : null
    if (!canonicalEl) {
      canonicalEl = document.createElement('link')
      canonicalEl.setAttribute('rel', 'canonical')
      document.head.appendChild(canonicalEl)
    }
  }
  canonicalEl.setAttribute('href', url)
}
function restoreCanonical() {
  if (!canonicalEl) return
  if (canonicalPrevHref == null) canonicalEl.remove()
  else canonicalEl.setAttribute('href', canonicalPrevHref)
  canonicalEl = null
  canonicalPrevHref = null
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
  const description = c.description?.trim() || `${shopName.value}${location.value ? ` en ${location.value}` : ''}. ${catalogPageOn.value ? 'Mirá el catálogo online y consultá por WhatsApp.' : 'Sitio oficial.'}`
  const image = (hasDesignAdvanced.value && c.cover) || c.carousel?.[0]?.url || c.logo || ''
  // Sin telephone ni sameAs en el JSON-LD: el número y las redes no se
  // exponen en el marcado estructurado (los bots también lo leen).
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': catalogPageOn.value ? 'Store' : 'LocalBusiness',
    name: shopName.value,
    description,
    url,
    image: image ? new URL(image, window.location.origin).href : undefined,
    logo: c.logo ? new URL(c.logo, window.location.origin).href : undefined,
    address: location.value || s?.location_address ? {
      '@type': 'PostalAddress',
      streetAddress: s?.location_address || undefined,
      addressLocality: s?.city_name || undefined,
      addressRegion: s?.province_name || undefined,
      addressCountry: 'AR'
    } : undefined,
    openingHoursSpecification: c.show_hours !== false ? schemaHours(c.hours) : [],
  }
  if (!jsonLd.openingHoursSpecification.length) delete jsonLd.openingHoursSpecification
  clearSeo = applySeo({
    title: document.title,
    description,
    image,
    url,
    themeColor: resolvedThemeColor(),
    jsonLd: JSON.parse(JSON.stringify(jsonLd))
  })
  syncCanonical(url)
}
// Re-emite OG/JSON-LD con el document.title vigente: la ficha de producto
// lo cambia async ("<producto> · <tienda>") y sin esto el preview queda
// con el título de la portada.
function refreshSeo() { syncSeo() }
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

// Carga de la tienda — la usa el montaje inicial y el botón "Reintentar"
// del estado de error. Nunca vuelca el `detail` crudo del backend: 404
// tiene su propio mensaje y todo lo demás (429/5xx/red) muestra el aviso
// amigable de "tienda ocupada".
async function loadStore() {
  // Dominio propio (mitienda.com): el host no revela el slug — se resuelve
  // contra la API antes de cualquier fetch y queda en storeHostSlug para
  // que el resto de la página arme sus links como en un subdominio.
  if (customDomainHost && !storeHostSlug) {
    try {
      setStoreHostSlug(await storesApi.resolveDomain(customDomainHost))
    } catch {
      status.value = 'error'
      storeErrorKind.value = 'busy'
      errorMsg.value = 'La tienda está ocupada, reintentá en unos segundos.'
      return
    }
  }
  // El catálogo vuela en paralelo con la ficha de la tienda: en Inicio es la
  // vitrina de destacados ({sort:'recent'}), en Catálogo el listado inicial
  // ({sort:'name'}) y en la ficha de producto el catálogo completo. La vista
  // hija recibe la misma promesa por loadPublicCatalog — cero espera extra.
  if (isHome.value && catalogPageOn.value) loadPublicCatalog({ sort: 'recent' })
  else if (isCatalog.value && catalogPageOn.value) loadPublicCatalog({ sort: 'name' })
  else if (isProduct.value && catalogPageOn.value) loadPublicCatalog()
  // La página Servicios no necesita el catálogo: sus ítems viajan en el
  // payload público de la tienda (service_items).
  // El documento del diseño viaja en paralelo con la ficha: si el patrón
  // todavía no tiene contrato de datos vuelve `{}` y se usa la plantilla Vue.
  let patternReq = Promise.resolve()
  if (isHome.value || isCatalog.value || isServices.value || isProduct.value) {
    const metaParams = { preview: previewToken.value, meta: true }
    //Reintento único: un fallo transitorio del meta dejaba a la web (y a la
    //vista previa) con la plantilla Vue aunque el diseño tenga documento.
    patternReq = storesApi.publicPattern(slug.value, metaParams)
      .catch(() => storesApi.publicPattern(slug.value, metaParams))
      .then((doc) => { patternMetaDone.value = true; patternDoc.value = doc && (doc.has_html || doc.html) ? doc : null })
      .catch(() => { patternDoc.value = null })
  }
  try {
    store.value = await storesApi.publicStore(slug.value, { preview: previewToken.value })
    // Sin esperar el meta, status='success' montaba la plantilla Vue con el
    // template de fallback ('raiz') y el diseño real recién llegaba con el
    // documento del patrón: flash del diseño viejo en cada carga.
    await patternReq
    status.value = 'success'
    storeErrorKind.value = ''
    errorMsg.value = ''
    // Inter queda siempre disponible como cuerpo neutro de las pieles.
    ensureStoreFont('inter')
    // Fuentes propias de la plantilla (titulares y cuerpo): las declara la
    // Template Definition (`fonts` en templates/<id>/index.js). Misma carga
    // on-demand; el resto del texto usa las familias de la piel/tema.
    templateFonts(pageTemplate.value).forEach(ensureStoreFont)
  } catch (e) {
    status.value = 'error'
    const httpStatus = e?.response?.status
    if (httpStatus === 404) {
      storeErrorKind.value = 'notfound'
      errorMsg.value = 'Esta tienda no existe o no está disponible.'
    } else {
      // 429, 5xx o error de red: mensaje amigable + Reintentar, sin `detail`.
      storeErrorKind.value = 'busy'
      errorMsg.value = 'La tienda está ocupada, reintentá en unos segundos.'
    }
  }
}

async function retryStore() {
  if (status.value === 'loading') return
  status.value = 'loading'
  storeErrorKind.value = ''
  errorMsg.value = ''
  await loadStore()
}

onMounted(async () => {
  // Sesión del comprador: se restaura/valida en segundo plano para que el
  // header muestre "Mi cuenta" (y el postMessage al patrón reciba el estado)
  // sin bloquear la carga de la tienda.
  customerStore.ensureSession().catch(() => {})
  await loadStore()
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
      //El padre real es uno de los orígenes de la plataforma: se postea a
      //todos los habilitados y solo el que embebe la página lo recibe.
      for (const origin of studioAllowedOrigins) {
        window.parent.postMessage(studioReady(), origin)
      }
    }
  }
  if (studioMode.value) {
    //Si el host nunca manda UPDATE (una visita directa con ?studio=1), la
    //espera no puede dejar la página en skeleton para siempre: se pinta
    //con el borrador/publicado después del margen.
    studioSeenTimer = setTimeout(() => { studioUpdateSeen.value = true }, 2500)
  }
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('keydown', onMenuKey)
  window.removeEventListener('message', onLayoutMessage)
  window.removeEventListener('message', onStudioMessage)
  window.removeEventListener('davent:customer-session-expired', onCustomerSessionExpired)
  removeStudioGuard?.()
  contentObserver?.disconnect()
  clearTimeout(contentFallback)
  clearTimeout(studioSeenTimer)
  clearSeo?.()
  restoreCanonical()
  applyFavicon(null)
})
</script>

<template>
  <div ref="pageRoot" class="store-page" :class="{ 'is-home': isHome, 'is-scrolled': scrolled, 'has-pattern': usePattern, 'has-bot': botConfig && !usePattern }" :data-store-theme="pageTheme" :data-theme="pageTheme" :data-template="pageTemplate" :data-store-template="pageTemplate" :data-design="designId" :data-style="pageStyle" :data-skin="storeSkinOf(pageTemplate)" :data-logo-mode="custom.logo_mode" :data-has-logo="custom.logo ? '' : null" :data-mono="custom.mono_style" :data-st-tabbar="showTabbar && !usePattern && !patternWaiting ? '' : null" :style="[themeVars, publishedThemeVars, studioVars]" v-bind="pageAttrs">
    <button type="button" class="sp-skip" @click="skipToContent">Saltar al contenido</button>
    <span v-if="previewMode" class="sp-preview-badge" role="status">Vista previa — el diseño todavía no se publicó</span>
    <!-- Diseño del catálogo con contrato de datos: se pinta el documento
         del patrón (HTML/CSS/JS) en vez de la plantilla Vue. -->
    <PatternSurface
      v-if="usePattern && !patternWaiting"
      :slug="slug"
      :preview="previewToken"
      :template="studioMode && studioTemplate ? studioTemplate : ''"
      :style="patternStyleOverride"
      :revision="patternRevision"
      :theme="pageTheme"
      :surface="patternSurface"
      :product="patternSurface === 'product' ? route.params.productId : ''"
      :studio-css="patternStudioCssText"
      :title="shopName"
      :account="customerStore.isAuthenticated"
      @navigate="onPatternNavigate"
      @buy="onPatternBuy"
      @buy-now="onPatternBuyNow"
      @account="onPatternAccount"
      @toggle-theme="togglePageTheme"
      @load="patternFrameReady = true"
    />
    <!-- Mientras el documento del diseño baja y pinta, skeleton: la página
         Vue ya no está montada (usePattern) y sin esto quedaba un hueco.
         patternWaiting también lo manda: sin el UPDATE del host o con el
         meta del diseño en ensayo en viaje, la rama no está decidida. -->
    <div v-if="patternWaiting || patternMetaLoading || (usePattern && !patternFrameReady)" class="sp-boot" role="status" aria-live="polite" aria-busy="true">
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
    <div v-if="!usePattern && !patternWaiting && !patternMetaLoading" class="sp-vue-page">
    <!-- ===== Barra superior ===== -->
    <header class="sp-top" :class="{ scrolled }">
      <span class="sp-progress" aria-hidden="true" :style="{ transform: `scaleX(${progress})` }"></span>
      <!-- Movimiento: fila utilitaria fina sobre la barra principal —
           contacto/horarios en mono (el header partido en dos filas es la
           firma de menú del diseño). -->
      <div v-if="pageTemplate === 'movimiento' && status === 'success'" class="sp-top-utility">
        <div class="sp-container sp-top-utility-inner">
          <span class="sp-top-utility-item"><AppIcon name="map-pin" :size="11" aria-hidden="true" /> {{ location || 'Estudio de entrenamiento' }}</span>
          <span v-if="custom.hours?.[0]?.value" class="sp-top-utility-item"><AppIcon name="clock" :size="11" aria-hidden="true" /> {{ custom.hours[0].label }} · {{ custom.hours[0].value }}</span>
          <span class="sp-top-utility-item is-right">Entrenamiento personalizado</span>
        </div>
      </div>
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
              {{ location || (catalogPageOn ? 'Catálogo online' : 'Sitio oficial') }}
            </span>
          </span>
        </RouterLink>
        <nav v-if="status === 'success' && !isShop" class="sp-top-links" aria-label="Secciones de la tienda">
          <RouterLink v-if="!landingOff" :to="homeTo">Inicio</RouterLink>
          <RouterLink v-if="showServices" :to="servicesTo">Servicios</RouterLink>
          <RouterLink v-if="catalogPageOn" :to="catalogTo">Catálogo</RouterLink>
          <RouterLink v-if="showPlans" :to="plansTo">Suscripciones</RouterLink>
          <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
          <RouterLink v-if="showGallery && landingHasGallery && !landingOff" :to="anchorTo('#galeria')" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
          <RouterLink v-if="showContact && landingHasContact && !landingOff" :to="anchorTo('#contacto')" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
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
          <!-- E-commerce: cuenta del comprador con customer_auth_enabled;
               carrito solo con orders_enabled efectivo (ecommerce +
               fiscal del backend). -->
          <RouterLink
            v-if="status === 'success' && customerAuthEnabled"
            :to="accountTo" class="sp-icon-btn" style="position: relative"
            :aria-label="customerStore.isAuthenticated ? `Mi cuenta — ${customerStore.displayName}` : 'Ingresar a mi cuenta'"
            title="Mi cuenta"
          >
            <AppIcon name="user" :size="17" />
          </RouterLink>
          <button
            v-if="status === 'success' && ordersEnabled"
            type="button" class="sp-icon-btn" style="position: relative"
            :aria-label="cartStore.itemCount ? `Carrito, ${cartStore.itemCount} ${cartStore.itemCount === 1 ? 'producto' : 'productos'}` : 'Carrito'"
            title="Carrito"
            @click="cartStore.openDrawer()"
          >
            <AppIcon name="shopping-cart" :size="17" />
            <span v-if="cartStore.itemCount" class="ec-badge" aria-hidden="true">{{ cartStore.itemCount > 99 ? '99+' : cartStore.itemCount }}</span>
          </button>
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
            <RouterLink v-if="catalogPageOn" :to="catalogTo" :class="{ 'is-current': shopCurrent === 'catalog' }" :aria-current="shopCurrent === 'catalog' ? 'page' : null">Catálogo</RouterLink>
            <RouterLink v-if="showPlans" :to="plansTo" :class="{ 'is-current': shopCurrent === 'plans' }" :aria-current="shopCurrent === 'plans' ? 'page' : null">Suscripciones</RouterLink>
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" :class="{ 'is-current': shopCurrent === 'nosotros' }" :aria-current="shopCurrent === 'nosotros' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && landingHasGallery && !landingOff" :to="anchorTo('#galeria')" :class="{ 'is-current': shopCurrent === 'galeria' }" :aria-current="shopCurrent === 'galeria' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
            <RouterLink v-if="showContact && landingHasContact && !landingOff" :to="anchorTo('#contacto')" :class="{ 'is-current': shopCurrent === 'contacto' }" :aria-current="shopCurrent === 'contacto' ? 'true' : null" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
          </div>
          <span class="sp-shop-nav-note">Precios en pesos argentinos</span>
        </div>
      </nav>
    </header>

    <!-- Menú móvil (solo navegación): los filtros del catálogo NO viven
         acá — van en CatalogFilters (bottom sheet propio). -->
    <div v-if="hasNavMenu" class="sp-overlay" :class="{ open: ui.menuOpen }" aria-hidden="true" @click="ui.menuOpen = false"></div>
    <nav v-if="hasNavMenu" ref="menuDrawer" id="sp-drawer" class="sp-drawer sp-navdrawer" :class="{ open: ui.menuOpen }" role="dialog" aria-modal="true" aria-label="Menú de la tienda">
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
      <Transition name="sp-msheet">
      <div
        v-if="ui.moreOpen" id="sp-more-sheet" ref="moreSheet" class="sp-more-sheet"
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
          <RouterLink v-if="catalogPageOn && !isCatalog" class="sp-more-link" :to="catalogTo" @click="ui.moreOpen = false">
            <AppIcon name="search" :size="17" aria-hidden="true" /><span>Buscar productos</span>
          </RouterLink>
          <button v-if="showThemeToggle" type="button" class="sp-more-link" @click="ui.moreOpen = false; togglePageTheme()">
            <AppIcon :name="pageTheme === 'dark' ? 'sun' : 'moon'" :size="17" aria-hidden="true" />
            <span>{{ pageTheme === 'dark' ? 'Modo claro' : 'Modo oscuro' }}</span>
          </button>
        </div>
      </div>
      </Transition>
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
      <span class="sp-state-icon"><AppIcon :name="storeErrorKind === 'notfound' ? 'search' : 'store'" :size="26" /></span>
      <h1>{{ storeErrorKind === 'notfound' ? 'Tienda no encontrada' : 'La tienda está ocupada' }}</h1>
      <p>{{ errorMsg }}</p>
      <button v-if="storeErrorKind !== 'notfound'" type="button" class="sp-btn" @click="retryStore">
        Reintentar
      </button>
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
            <div v-if="status === 'success' && socials.length" class="sp-foot-social">
              <a v-for="s in socials" :key="s.key" :href="s.url" target="_blank" rel="noopener" :aria-label="`${s.label} de ${shopName}`" :title="s.label"><AppIcon :name="s.key" :size="17" /></a>
            </div>
          </div>
          <div v-if="status === 'success' && hasFootContact" class="sp-foot-col" aria-label="Contacto">
            <p class="sp-foot-heading">Contacto</p>
            <ul class="sp-foot-contact">
              <li v-if="footAddress"><AppIcon name="map-pin" :size="14" /> <span>{{ footAddress }}</span></li>
              <li v-if="whatsappUrl"><a :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="14" /> Escribinos por WhatsApp</a></li>
            </ul>
          </div>
          <nav v-if="isShop && status === 'success'" class="sp-foot-col" aria-label="Secciones de la tienda">
            <p class="sp-foot-heading">Tienda</p>
            <RouterLink v-if="!landingOff" :to="homeTo">Inicio</RouterLink>
            <RouterLink v-if="showServices" :to="servicesTo">Servicios</RouterLink>
            <RouterLink v-if="catalogPageOn" :to="catalogTo">Catálogo</RouterLink>
            <RouterLink v-if="showPlans" :to="plansTo">Suscripciones</RouterLink>
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" active-class="sp-anchor" exact-active-class="sp-anchor">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && landingHasGallery && !landingOff" :to="anchorTo('#galeria')" active-class="sp-anchor" exact-active-class="sp-anchor">Galería</RouterLink>
            <RouterLink v-if="showContact && landingHasContact && !landingOff" :to="anchorTo('#contacto')" active-class="sp-anchor" exact-active-class="sp-anchor">Contacto</RouterLink>
          </nav>
          <nav class="sp-foot-col" aria-label="Información del sitio">
            <p class="sp-foot-heading">Información</p>
            <!-- Legales de la TIENDA (dominio legalpages — texto del dueño);
                 las de DAVENT siguen abajo como links de plataforma. -->
            <RouterLink :to="legalTo('terms')">Términos</RouterLink>
            <RouterLink :to="legalTo('privacy')">Privacidad</RouterLink>
            <RouterLink :to="legalTo('returns')">Arrepentimiento y devoluciones</RouterLink>
            <a :href="`${appUrl}/terminos`">Términos y condiciones de DAVENT</a>
            <a :href="`${appUrl}/privacidad`">Privacidad de DAVENT</a>
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

    </div>

    <!-- Chatbot del negocio (has_chatbot): burbuja robot abajo a la derecha.
         Solo en la plantilla Vue: los documentos de diseño montan el suyo
         propio dentro del iframe (pattern_bridge.js, clases .ds-chat-*). -->
    <StoreBot
      v-if="botConfig && !usePattern"
      :config="botConfig"
      :name="shopName"
      :logo="custom.logo"
      :initial="initial"
    />

    <!-- E-commerce del comprador: drawer del carrito, modal de auth y
         toast de avisos. Van fuera del .sp-vue-page: también aplican en
         las rutas de comercio (checkout/cuenta/seguimiento/legal). -->
    <StoreCartDrawer v-if="status === 'success'" :slug="slug" />
    <StoreAuthModal v-if="status === 'success' && customerAuthEnabled" :slug="slug" @done="onCustomerAuthed" />
    <Transition name="ec-toast">
      <div v-if="cartStore.notice" class="ec-toast" :class="cartStore.notice.kind" role="status">
        {{ cartStore.notice.text }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Badge del carrito sobre el icon-btn del header + toast de avisos del
   cart.store (los drawers/modales llevan sus propios estilos). */
.ec-badge {
  position: absolute; top: -5px; right: -5px;
  min-width: 19px; height: 19px; padding: 0 5px;
  display: grid; place-items: center;
  border-radius: 999px; font-size: 10.5px; font-weight: 800;
  background: var(--sp-danger, #dc2626); color: #fff;
  border: 2px solid var(--sp-card, #fff);
  font-variant-numeric: tabular-nums;
}
.ec-toast {
  position: fixed; left: 50%; bottom: calc(20px + env(safe-area-inset-bottom));
  transform: translateX(-50%); z-index: 1300;
  max-width: min(92vw, 460px); padding: 12px 18px;
  border-radius: calc(var(--sp-radius, 16px) * .8); font-size: 13.5px; font-weight: 600; line-height: 1.4;
  background: #111827; color: #fff;
  box-shadow: 0 14px 40px rgba(0,0,0,.3);
}
.ec-toast.ok { background: var(--sp-success, #15803d); }
.ec-toast.err { background: var(--sp-danger, #b91c1c); }
.ec-toast-enter-active, .ec-toast-leave-active { transition: opacity .2s ease, transform .2s ease; }
.ec-toast-enter-from, .ec-toast-leave-to { opacity: 0; transform: translate(-50%, 8px); }
</style>
