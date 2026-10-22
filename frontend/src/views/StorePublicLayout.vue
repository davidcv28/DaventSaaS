<script setup>
import { ref, reactive, computed, provide, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  storesApi, normalizeSlug, storeThemeVars, storeFontFamily, ensureStoreFont, CUSTOMIZATION_DEFAULTS
} from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
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
const slug = computed(() => normalizeSlug(route.params.slug))

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
const themeVars = computed(() => storeThemeVars(custom.value))
// Diseño avanzado (Plan premium): define si la web muestra el carrusel de
// destacados o, en su lugar, un botón de modo claro/oscuro en el nav.
const hasDesignAdvanced = computed(() => Boolean(store.value?.has_design_advanced))
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

// Estado compartido con la vista del catálogo: buscador del header, burger y
// si existe navegación de catálogo (categorías/marcas) para el drawer.
const ui = reactive({ search: '', menuOpen: false, hasCatalogNav: false })
const isCatalog = computed(() => route.name === 'store-catalog')
const homeTo = computed(() => ({ name: 'store-public', params: { slug: slug.value } }))
const catalogTo = computed(() => ({ name: 'store-catalog', params: { slug: slug.value } }))

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
  hasDesignAdvanced, hasAbout, showGallery, showContact, ui
})

// Título de pestaña por página: "<tienda>" en Inicio, "<tienda> · Catálogo"
// en el catálogo. Corre también al volver del catálogo al inicio.
watch([status, () => route.name], ([s, name]) => {
  if (s === 'success') document.title = name === 'store-catalog' ? `${shopName.value} · Catálogo` : shopName.value
}, { immediate: true })

onMounted(async () => {
  try {
    store.value = await storesApi.publicStore(slug.value)
    status.value = 'success'
    ensureStoreFont(custom.value.name_font)
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractApiError(e).nonField || 'Esta tienda no está disponible.'
  }
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="store-page" :data-store-theme="pageTheme" :style="themeVars">
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
          <RouterLink :to="catalogTo">Catálogo</RouterLink>
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
            <RouterLink to="/terminos">Términos y condiciones</RouterLink>
            <RouterLink to="/denuncias">Denunciar contenido</RouterLink>
          </nav>
        </div>
        <div class="sp-foot-bottom">
          <p class="sp-foot-copy">© {{ year }} {{ shopName }}. Todos los derechos reservados.</p>
          <RouterLink to="/register" class="sp-davent-badge">
            <BrandLogo :size="16" /> Publicado con <strong>DAVENT</strong>
          </RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>
