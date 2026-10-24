<script setup>
import { ref, reactive, computed, provide, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  storesApi, normalizeSlug, storeThemeVars, storeFontFamily, ensureStoreFont, storeTemplate, CUSTOMIZATION_DEFAULTS
} from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { env, storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
import StoreBot from '../components/StoreBot.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-page.css'

// Layout de la web pública del cliente (sin auth): barra superior + pie +
// transición suave entre sus páginas (Inicio y Catálogo). Resuelve la tienda
// una sola vez y la comparte a las vistas hijas con provide('storePage').
// Usa su propia paleta (data-store-theme + --store-accent*): no hereda el
// tema claro/oscuro que el visitante haya elegido para el dashboard.
// Estilos en assets/store-page.css (única hoja de la web pública).
const route = useRoute()
const status = ref('loading') // loading | success | error
const store = ref(null)
const errorMsg = ref('')
// El slug viene del path (dominio de plataforma /<slug>) o del subdominio
// (<slug>.<dominio>, donde la tienda es la raíz y no hay param en la ruta).
const slug = computed(() => normalizeSlug(route.params.slug || storeHostSlug || ''))
const appUrl = env.appUrl

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
const themeVars = computed(() => storeThemeVars(custom.value))
// Diseño avanzado (Plan premium): define si la web muestra el carrusel de
// destacados o, en su lugar, un botón de modo claro/oscuro en el nav.
const hasDesignAdvanced = computed(() => Boolean(store.value?.has_design_advanced))
// Diseño de la web (template): los diseños alternativos son premium; sin
// has_design_advanced se fuerza 'classic' aunque quede otro valor guardado.
const pageTemplate = computed(() => (hasDesignAdvanced.value ? storeTemplate(custom.value.template) : 'classic'))
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
// Chatbot (beneficio has_chatbot, solo Premium): el serializer público lo manda
// solo si el dueño lo activó y el plan lo incluye — None = sin widget.
const botConfig = computed(() => (status.value === 'success' ? store.value?.chatbot || null : null))

// Estado compartido con la vista del catálogo: buscador del header, burger y
// si existe navegación de catálogo (categorías/marcas) para el drawer.
const ui = reactive({ search: '', menuOpen: false, hasCatalogNav: false })
const isCatalog = computed(() => route.name === 'store-catalog')
const isProduct = computed(() => route.name === 'store-product')
const isHome = computed(() => route.name === 'store-public')
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))

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

provide('storePage', {
  slug, store, status, custom, shopName, nameFont, initial, location,
  hasDesignAdvanced, pageTemplate, hasAbout, showGallery, showContact, showCatalog, ui
})

// Título de pestaña por página: "<tienda>" en Inicio, "<tienda> · Catálogo"
// en el catálogo. Corre también al volver del catálogo al inicio.
watch([status, () => route.name], ([s, name]) => {
  if (s === 'success') document.title = name === 'store-catalog' ? `${shopName.value} · Catálogo` : shopName.value
}, { immediate: true })

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
  try {
    store.value = await storesApi.publicStore(slug.value)
    status.value = 'success'
    ensureStoreFont(custom.value.name_font)
    // Fuentes propias de la plantilla (titulares): serif de pasarela en
    // 'atelier', condensada de letrero en 'perspective', peso pesado de
    // streetwear en 'street' y el par monospace de 'terminal'. Misma carga
    // on-demand que name_font; el resto del texto sigue con la fuente
    // elegida por el dueño.
    const TEMPLATE_FONTS = { atelier: ['fraunces'], perspective: ['oswald', 'poppins'], street: ['archivo-black', 'space-grotesk'], terminal: ['space-mono', 'jetbrains-mono'] }
    TEMPLATE_FONTS[pageTemplate.value]?.forEach(ensureStoreFont)
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractApiError(e).nonField || 'Esta tienda no está disponible.'
  }
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  applyFavicon(null)
})
</script>

<template>
  <div class="store-page" :class="{ 'is-home': isHome }" :data-store-theme="pageTheme" :data-store-template="pageTemplate" :style="themeVars">
    <!-- ===== Barra superior ===== -->
    <header class="sp-top" :class="{ scrolled }">
      <span class="sp-progress" aria-hidden="true" :style="{ transform: `scaleX(${progress})` }"></span>
      <div class="sp-container sp-top-inner">
        <button
          v-if="isCatalog && ui.hasCatalogNav"
          type="button"
          class="sp-burger"
          :aria-label="ui.menuOpen ? 'Cerrar menú' : 'Abrir menú de categorías'"
          :aria-expanded="ui.menuOpen"
          aria-controls="sp-drawer"
          @click="ui.menuOpen = !ui.menuOpen"
        >
          <AppIcon :name="ui.menuOpen ? 'x' : 'menu'" :size="20" />
        </button>
        <RouterLink class="sp-brand" :to="homeTo" aria-label="Ir al inicio">
          <img v-if="custom.logo" class="sp-logo sm" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp-mono sm" aria-hidden="true">{{ initial }}</span>
          <span class="sp-name" :style="nameFont">{{ shopName }}</span>
        </RouterLink>
        <nav v-if="status === 'success'" class="sp-top-links" aria-label="Secciones de la tienda">
          <RouterLink :to="homeTo">Inicio</RouterLink>
          <RouterLink v-if="showCatalog" :to="catalogTo">Catálogo</RouterLink>
          <RouterLink v-if="hasAbout" :to="{ ...homeTo, hash: '#nosotros' }">Nosotros</RouterLink>
          <RouterLink v-if="showGallery" :to="{ ...homeTo, hash: '#galeria' }">Galería</RouterLink>
          <RouterLink v-if="showContact" :to="{ ...homeTo, hash: '#contacto' }">Contacto</RouterLink>
        </nav>
        <label v-if="isCatalog" class="sp-search sp-search-top">
          <AppIcon name="search" :size="16" aria-hidden="true" />
          <input v-model="ui.search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" @keydown.esc.stop="ui.search = ''" />
          <button v-if="ui.search" type="button" class="sp-search-clear" aria-label="Borrar búsqueda" @click="ui.search = ''"><AppIcon name="x" :size="14" /></button>
        </label>
        <div class="sp-top-end">
          <RouterLink v-if="status === 'success' && (isCatalog || isProduct || showCatalog)" class="sp-top-cta" :to="isCatalog ? homeTo : catalogTo">
            <AppIcon :name="isCatalog ? 'store' : 'package'" :size="16" /> {{ isCatalog ? 'Inicio' : 'Catálogo' }}
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
    </header>

    <div v-if="status === 'loading'" class="sp-state">
      <span class="spinner spinner-brand" aria-hidden="true"></span>
      <p>Cargando la tienda…</p>
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
          </div>
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
</template>
