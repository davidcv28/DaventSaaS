<script setup>
import { ref, reactive, computed, provide, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  storesApi, normalizeSlug, normalizeCatalogParams, storeThemeVars, storeFontFamily, ensureStoreFont, resolveStoreTemplate, CUSTOMIZATION_DEFAULTS
} from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { env, storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
import StoreBot from '../components/StoreBot.vue'
import { vReveal } from '../directives/reveal.js'
import { applySeo } from '../utils/seo.js'
import { schemaHours } from '../utils/storeHours.js'
import { templateFonts } from '../templates/index.js'
import '../assets/store-page.css'
// Las hojas de las landing alternativas también definen el cromado
// (topbar/pie) y la ficha de producto de su diseño: se cargan acá para que
// /catalogo y /producto/:id las tengan aunque el visitante no pase por el
// home que las importa (acceso directo por URL al producto).
import '../assets/store-page-v2.css'
import '../assets/store-bloque.css'
import '../assets/store-riso.css'
// Contrato de geometría de la tarjeta de producto unificada (TplProductCard)
// — lo usan todos los catálogos y los rieles de ofertas de las landings.
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
const custom = computed(() => ({
  ...CUSTOMIZATION_DEFAULTS,
  ...(store.value?.customization || {}),
  ...(layoutOverride.value ? { layout_config: layoutOverride.value } : {})
}))
function onLayoutMessage(e) {
  if (e.origin !== window.location.origin || e.data?.type !== 'davent:layout') return
  layoutOverride.value = e.data.layout || null
}
const themeVars = computed(() => storeThemeVars(custom.value))
// Diseño avanzado (Plan premium): define si la web muestra el carrusel de
// destacados o, en su lugar, un botón de modo claro/oscuro en el nav.
const hasDesignAdvanced = computed(() => Boolean(store.value?.has_design_advanced))
// Diseño de la web (template): la whitelist allowed_templates del payload
// marca el nivel del plan (Básico: Clásico/Perspectiva; Estándar suma
// Urbano/Publicidad; Premium, todo). Si el guardado quedó fuera — baja de
// plan o plantilla retirada — se fuerza 'classic'.
const pageTemplate = computed(() => resolveStoreTemplate(custom.value.template, store.value?.allowed_templates))
// Tienda Pro (Premium): masthead de marketplace — el buscador queda visible
// en todas las páginas y fuera del catálogo envía a /catalogo?q=.
const isShop = computed(() => pageTemplate.value === 'shop')

// Terra: la hoja del diseño también tiñe el chrome (barra, pie, dock) en
// páginas que no montan la portada (servicios, ficha). Se carga on-demand y
// una sola vez; la portada y el catálogo ya la importan estáticamente.
watch(pageTemplate, (tpl) => {
  if (tpl === 'terra') import('../assets/store-terra.css')
}, { immediate: true })
// Tema efectivo: el elegido por el dueño; en tiendas sin diseño avanzado el
// visitante puede alternarlo con el botón del nav (solo para esta visita).
const visitorTheme = ref(null) // null = tema de la tienda
const pageTheme = computed(() => visitorTheme.value || custom.value.theme)
const showThemeToggle = computed(() => status.value === 'success' && !hasDesignAdvanced.value)
function togglePageTheme() {
  visitorTheme.value = pageTheme.value === 'dark' ? 'light' : 'dark'
}
const shopName = computed(() => custom.value.display_name || store.value?.business_name || 'Tienda')
const nameFont = computed(() => ({ fontFamily: storeFontFamily(custom.value.name_font) }))
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const location = computed(() => [store.value?.city_name, store.value?.province_name].filter(Boolean).join(', '))
const year = new Date().getFullYear()
const mainAnchor = ref(null)
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
const ui = reactive({ search: '', menuOpen: false, hasCatalogNav: false, searchOpen: false })

// Menú hamburguesa = SOLO navegación de la tienda: los filtros del catálogo
// viven en CatalogFilters (sidebar desktop / bottom sheet móvil), no en el
// drawer. Misma lista de destinos que .sp-top-links.
const navMenuLinks = computed(() => {
  const links = []
  if (!landingOff.value) links.push({ to: homeTo.value, label: 'Inicio' })
  if (showServices.value) links.push({ to: servicesTo.value, label: 'Servicios' })
  if (showCatalog.value) links.push({ to: catalogTo.value, label: 'Catálogo' })
  if (hasAbout.value && !landingOff.value) links.push({ to: anchorTo('#nosotros'), label: 'Nosotros' })
  if (showGallery.value && !landingOff.value) links.push({ to: anchorTo('#galeria'), label: 'Galería' })
  if (showContact.value && !landingOff.value) links.push({ to: anchorTo('#contacto'), label: 'Contacto' })
  return links
})
// El burger se muestra cuando hay navegación que esconder — Tienda Pro usa
// su propia fila .sp-shop-nav (visible también en móvil).
const hasNavMenu = computed(() => status.value === 'success' && !isShop.value && navMenuLinks.value.length > 0)
const onMenuKey = (e) => { if (e.key === 'Escape') ui.menuOpen = false }
watch(() => route.fullPath, () => { ui.menuOpen = false; ui.searchOpen = false })
// Drawer de navegación: mientras está abierto bloquea el scroll del body,
// lleva el foco al botón de cerrar y lo devuelve al burger al cerrarse.
watch(() => ui.menuOpen, async (open) => {
  document.documentElement.classList.toggle('sp-lock', open)
  if (open) {
    await nextTick()
    menuDrawer.value?.querySelector('.sp-drawer-close')?.focus()
  } else if (menuDrawer.value?.contains(document.activeElement)) {
    menuBtn.value?.focus()
  }
})
onBeforeUnmount(() => document.documentElement.classList.remove('sp-lock'))
const isCatalog = computed(() => route.name === 'store-catalog')
const isServices = computed(() => route.name === 'store-services')
const isProduct = computed(() => route.name === 'store-product')
// Opción 2 (/<slug>/v2): prototipo de portada alternativa — se comporta como
// Inicio para el menú, el dock móvil y el redirect de la web sin portada.
const isAlt = computed(() => route.name === 'store-alt')
const isHome = computed(() => route.name === 'store-public' || isAlt.value)
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
// Anclas de sección (#nosotros/#galeria/#contacto): en la vista previa de la
// opción 2 se quedan dentro de la propia página; fuera de ella van al inicio.
const anchorTo = (hash) => ({ path: isAlt.value ? route.path : homeTo.value.path, hash })
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
    : name === 'store-alt' ? `${shopName.value} · Vista previa` : shopName.value
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
// Barra fija móvil: WhatsApp + accesos cruzados a las otras páginas de la
// web (Inicio solo si hay portada, Catálogo y Servicios). No aparece en la
// ficha de producto (ya tiene su propio CTA a WhatsApp).
const dockCatalog = computed(() => showCatalog.value && !isCatalog.value && !isProduct.value)
const dockServices = computed(() => showServices.value && !isServices.value && !isProduct.value)
const dockHome = computed(() => !landingOff.value && !isHome.value && !isProduct.value)
const showDock = computed(() => status.value === 'success' && !isProduct.value && Boolean(whatsappUrl.value || dockCatalog.value || dockServices.value || dockHome.value))

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
    themeColor: themeVars.value['--store-accent-ink'],
    jsonLd: JSON.parse(JSON.stringify(jsonLd))
  })
}
watch([status, () => route.path, custom], syncSeo, { flush: 'post' })

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
  try {
    store.value = await storesApi.publicStore(slug.value)
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
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('keydown', onMenuKey)
  window.removeEventListener('message', onLayoutMessage)
  clearSeo?.()
  applyFavicon(null)
})
</script>

<template>
  <div class="store-page" :class="{ 'is-home': isHome, 'has-dock': showDock }" :data-store-theme="pageTheme" :data-store-template="pageTemplate" :style="themeVars">
    <button type="button" class="sp-skip" @click="skipToContent">Saltar al contenido</button>
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
          <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')">Nosotros</RouterLink>
          <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')">Galería</RouterLink>
          <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')">Contacto</RouterLink>
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
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')" :class="{ 'is-current': shopCurrent === 'nosotros' }" :aria-current="shopCurrent === 'nosotros' ? 'true' : null">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')" :class="{ 'is-current': shopCurrent === 'galeria' }" :aria-current="shopCurrent === 'galeria' ? 'true' : null">Galería</RouterLink>
            <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')" :class="{ 'is-current': shopCurrent === 'contacto' }" :aria-current="shopCurrent === 'contacto' ? 'true' : null">Contacto</RouterLink>
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
          @click="ui.menuOpen = false"
        ><span>{{ l.label }}</span><AppIcon name="chevron-right" :size="15" aria-hidden="true" /></RouterLink>
      </div>
    </nav>

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

    <!-- ===== Pie ===== -->
    <footer class="sp-foot">
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
            <RouterLink v-if="hasAbout && !landingOff" :to="anchorTo('#nosotros')">Nosotros</RouterLink>
            <RouterLink v-if="showGallery && !landingOff" :to="anchorTo('#galeria')">Galería</RouterLink>
            <RouterLink v-if="showContact && !landingOff" :to="anchorTo('#contacto')">Contacto</RouterLink>
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

    <!-- Barra fija de contacto (solo móvil): el CTA principal siempre a mano -->
    <nav v-if="showDock" class="sp-dock" aria-label="Acciones rápidas">
      <a v-if="whatsappUrl" class="sp-dock-btn is-wa" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="18" /> WhatsApp</a>
      <RouterLink v-if="dockServices" class="sp-dock-btn" :to="servicesTo"><AppIcon name="wrench" :size="18" /> Servicios</RouterLink>
      <RouterLink v-if="dockCatalog" class="sp-dock-btn" :to="catalogTo"><AppIcon name="package" :size="18" /> Catálogo</RouterLink>
      <RouterLink v-if="dockHome" class="sp-dock-btn" :to="homeTo"><AppIcon name="store" :size="18" /> Inicio</RouterLink>
    </nav>

    <!-- Chatbot del negocio (has_chatbot): burbuja robot abajo a la derecha -->
    <StoreBot
      v-if="botConfig"
      :config="botConfig"
      :name="shopName"
      :logo="custom.logo"
      :initial="initial"
    />
  </div>
</template>
