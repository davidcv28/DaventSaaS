<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  storesApi, normalizeSlug, storeThemeVars, storeFontFamily, CUSTOMIZATION_DEFAULTS
} from '../api/stores.api.js'
import { formatARS } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'
import '../assets/store-page.css'

// Web pública del cliente (sin auth): identidad del negocio + StoreCustomization
// + catálogo (categorías, marcas, productos con buscador).
// Usa su propia paleta (data-store-theme + --store-accent*): no hereda el tema
// claro/oscuro que el visitante haya elegido para el dashboard.
// Estilos en assets/store-page.css (única hoja de la web pública).
const route = useRoute()
const status = ref('loading') // loading | success | error
const store = ref(null)
const errorMsg = ref('')
const copied = ref(false)

const catalog = ref({ categories: [], brands: [], products: [] })
const catalogStatus = ref('idle') // idle | loading | success | error

// --- Filtros de la tienda ---
const search = ref('')
const activeCategory = ref(null)
const activeBrand = ref(null)
const menuOpen = ref(false)
let searchTimer = null

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
const themeVars = computed(() => storeThemeVars(custom.value))
const shopName = computed(() => custom.value.display_name || store.value?.business_name || 'Tienda')
const nameFont = computed(() => ({ fontFamily: storeFontFamily(custom.value.name_font) }))
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const location = computed(() => [store.value?.city_name, store.value?.province_name].filter(Boolean).join(', '))
const year = new Date().getFullYear()

const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const instagramUrl = computed(() => (custom.value.instagram ? `https://instagram.com/${custom.value.instagram}` : ''))
const tiktokUrl = computed(() => (custom.value.tiktok ? `https://tiktok.com/@${custom.value.tiktok}` : ''))
const facebookUrl = computed(() => (custom.value.facebook ? `https://facebook.com/${custom.value.facebook}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: instagramUrl.value },
  { key: 'tiktok', label: 'TikTok', url: tiktokUrl.value },
  { key: 'facebook', label: 'Facebook', url: facebookUrl.value }
].filter((s) => s.url))
const hasContact = computed(() => Boolean(whatsappUrl.value || socials.value.length))

// --- Carrusel de portada ---
const carousel = computed(() => custom.value.carousel || [])
const slide = ref(0)
let slideTimer = null
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

function goSlide(index) {
  const total = carousel.value.length
  if (!total) return
  slide.value = ((index % total) + total) % total
  restartSlideTimer()
}
function pauseSlideTimer() {
  clearInterval(slideTimer)
  slideTimer = null
}
function restartSlideTimer() {
  pauseSlideTimer()
  if (carousel.value.length > 1 && !reduceMotion) {
    slideTimer = setInterval(() => { slide.value = (slide.value + 1) % carousel.value.length }, 5000)
  }
}

// --- Catálogo: buscador + filtros por categoría/marca ---
async function loadCatalog() {
  const slug = normalizeSlug(route.params.slug)
  catalogStatus.value = 'loading'
  try {
    catalog.value = await storesApi.publicCatalog(slug, {
      q: search.value,
      category: activeCategory.value || '',
      brand: activeBrand.value || ''
    })
    catalogStatus.value = 'success'
  } catch {
    catalogStatus.value = 'error'
  }
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadCatalog, 300)
})

function pickCategory(id) {
  activeCategory.value = activeCategory.value === id ? null : id
  loadCatalog()
}
function pickBrand(id) {
  activeBrand.value = activeBrand.value === id ? null : id
  loadCatalog()
}
function clearFilters() {
  activeCategory.value = null
  activeBrand.value = null
  search.value = ''
  loadCatalog()
}

const hasFilters = computed(() => Boolean(activeCategory.value || activeBrand.value || search.value))
const hasCatalogNav = computed(() => Boolean(catalog.value.categories.length || catalog.value.brands.length))
const activeCategoryName = computed(() => catalog.value.categories.find((c) => c.id === activeCategory.value)?.name)
const activeBrandName = computed(() => catalog.value.brands.find((b) => b.id === activeBrand.value)?.name)
const productCount = computed(() => {
  const n = catalog.value.products.length
  return `${n} ${n === 1 ? 'producto' : 'productos'}`
})

function productChat(product) {
  if (!whatsappUrl.value) return ''
  const text = encodeURIComponent(`Hola, me interesa ${product.name} (${formatARS(product.price)})`)
  return `${whatsappUrl.value}?text=${text}`
}

async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Sin clipboard disponible: el link ya está en la barra del navegador.
  }
}

const scrollTop = () => window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })

const onKey = (e) => { if (e.key === 'Escape') menuOpen.value = false }

onMounted(async () => {
  const slug = normalizeSlug(route.params.slug)
  try {
    store.value = await storesApi.publicStore(slug)
    status.value = 'success'
    document.title = shopName.value
    restartSlideTimer()
    loadCatalog()
  } catch (e) {
    status.value = 'error'
    errorMsg.value = extractApiError(e).nonField || 'Esta tienda no está disponible.'
  }
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  clearInterval(slideTimer)
  clearTimeout(searchTimer)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="store-page" :data-store-theme="custom.theme" :style="themeVars">
    <!-- ===== Barra superior ===== -->
    <header class="sp-top">
      <div class="sp-container sp-top-inner">
        <button
          v-if="hasCatalogNav"
          type="button"
          class="sp-burger"
          :aria-label="menuOpen ? 'Cerrar menú' : 'Abrir menú de categorías'"
          :aria-expanded="menuOpen"
          aria-controls="sp-drawer"
          @click="menuOpen = !menuOpen"
        >
          <AppIcon :name="menuOpen ? 'x' : 'menu'" :size="20" />
        </button>
        <a class="sp-brand" href="#" aria-label="Ir al inicio" @click.prevent="scrollTop">
          <img v-if="custom.logo" class="sp-logo sm" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="sp-mono sm" aria-hidden="true">{{ initial }}</span>
          <span class="sp-name" :style="nameFont">{{ shopName }}</span>
        </a>
        <label v-if="status === 'success'" class="sp-search sp-search-top">
          <AppIcon name="search" :size="16" aria-hidden="true" />
          <input v-model="search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" />
        </label>
        <div class="sp-top-end">
          <a v-if="whatsappUrl" class="sp-btn sm" :href="whatsappUrl" target="_blank" rel="noopener" aria-label="Contactar por WhatsApp">
            <AppIcon name="whatsapp" :size="15" /> <span class="sp-hide-xs">Contactar</span>
          </a>
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

    <template v-else>
      <!-- ===== Portada + identidad ===== -->
      <section class="sp-hero">
        <div class="sp-container">
          <div class="sp-banner">
            <div v-if="carousel.length" class="sp-carousel" @mouseenter="pauseSlideTimer" @mouseleave="restartSlideTimer" @focusin="pauseSlideTimer" @focusout="restartSlideTimer">
              <div class="sp-carousel-track" :style="{ transform: `translateX(-${slide * 100}%)` }">
                <img v-for="img in carousel" :key="img.id" class="sp-carousel-img" :src="img.url" alt="" />
              </div>
              <template v-if="carousel.length > 1">
                <button type="button" class="sp-carousel-arrow prev" aria-label="Imagen anterior" @click="goSlide(slide - 1)">
                  <AppIcon name="chevron-left" :size="20" />
                </button>
                <button type="button" class="sp-carousel-arrow next" aria-label="Imagen siguiente" @click="goSlide(slide + 1)">
                  <AppIcon name="chevron-right" :size="20" />
                </button>
                <div class="sp-carousel-dots" role="group" aria-label="Imágenes del carrusel">
                  <button
                    v-for="(img, i) in carousel" :key="img.id" type="button"
                    class="sp-carousel-dot" :class="{ active: i === slide }"
                    :aria-label="`Ir a la imagen ${i + 1}`" :aria-current="i === slide"
                    @click="goSlide(i)"
                  ></button>
                </div>
              </template>
            </div>
            <div v-else class="sp-cover" aria-hidden="true"></div>
          </div>

          <div class="sp-identity">
            <img v-if="custom.logo" class="sp-logo lg" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sp-mono lg" aria-hidden="true">{{ initial }}</span>
            <div class="sp-identity-text">
              <h1 :style="nameFont">{{ shopName }}</h1>
              <p v-if="custom.headline" class="sp-headline">{{ custom.headline }}</p>
              <p v-if="location" class="sp-location"><AppIcon name="map-pin" :size="14" /> {{ location }}</p>
            </div>
            <div class="sp-actions">
              <a v-if="whatsappUrl" class="sp-btn" :href="whatsappUrl" target="_blank" rel="noopener">
                <AppIcon name="whatsapp" :size="16" /> WhatsApp
              </a>
              <a
                v-for="s in socials" :key="s.key" class="sp-icon-btn"
                :href="s.url" target="_blank" rel="noopener" :aria-label="s.label" :title="s.label"
              >
                <AppIcon :name="s.key" :size="17" />
              </a>
              <button type="button" class="sp-icon-btn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
                <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
              </button>
            </div>
          </div>
          <p v-if="custom.description" class="sp-desc">{{ custom.description }}</p>
        </div>
      </section>

      <!-- ===== Catálogo ===== -->
      <main class="sp-container sp-main">
        <div class="sp-layout" :class="{ 'has-nav': hasCatalogNav }">
          <div v-if="hasCatalogNav" class="sp-overlay" :class="{ open: menuOpen }" aria-hidden="true" @click="menuOpen = false"></div>
          <aside v-if="hasCatalogNav" id="sp-drawer" class="sp-drawer" :class="{ open: menuOpen }" aria-label="Categorías y marcas">
            <div class="sp-drawer-head">
              <strong>Explorar</strong>
              <button type="button" class="sp-drawer-close" aria-label="Cerrar menú" @click="menuOpen = false">
                <AppIcon name="x" :size="18" />
              </button>
            </div>
            <nav v-if="catalog.categories.length" class="sp-nav-group" aria-label="Categorías">
              <p class="sp-nav-heading">Categorías</p>
              <button
                v-for="c in catalog.categories" :key="`c-${c.id}`" type="button"
                class="sp-nav-item" :class="{ active: activeCategory === c.id }"
                :aria-pressed="activeCategory === c.id"
                @click="pickCategory(c.id); menuOpen = false"
              >
                <AppIcon name="layout-grid" :size="15" /> <span>{{ c.name }}</span>
              </button>
            </nav>
            <nav v-if="catalog.brands.length" class="sp-nav-group" aria-label="Marcas">
              <p class="sp-nav-heading">Marcas</p>
              <button
                v-for="b in catalog.brands" :key="`b-${b.id}`" type="button"
                class="sp-nav-item" :class="{ active: activeBrand === b.id }"
                :aria-pressed="activeBrand === b.id"
                @click="pickBrand(b.id); menuOpen = false"
              >
                <AppIcon name="tag" :size="15" /> <span>{{ b.name }}</span>
              </button>
            </nav>
            <button v-if="hasFilters" type="button" class="sp-nav-clear" @click="clearFilters(); menuOpen = false">
              <AppIcon name="x" :size="14" /> Limpiar filtros
            </button>
          </aside>

          <section class="sp-catalog" aria-labelledby="sp-catalog-title">
            <div class="sp-toolbar">
              <div class="sp-toolbar-title">
                <h2 id="sp-catalog-title" class="sp-section-title">Catálogo</h2>
                <span v-if="catalogStatus === 'success'" class="sp-count">{{ productCount }}</span>
              </div>
              <label class="sp-search sp-search-inline">
                <AppIcon name="search" :size="16" aria-hidden="true" />
                <input v-model="search" type="search" placeholder="Buscar productos" aria-label="Buscar productos" />
              </label>
            </div>

            <div v-if="hasFilters" class="sp-chips">
              <button v-if="activeCategoryName" type="button" class="sp-chip" @click="pickCategory(activeCategory)">
                {{ activeCategoryName }} <AppIcon name="x" :size="12" />
              </button>
              <button v-if="activeBrandName" type="button" class="sp-chip" @click="pickBrand(activeBrand)">
                {{ activeBrandName }} <AppIcon name="x" :size="12" />
              </button>
              <button type="button" class="sp-chip clear" @click="clearFilters">Limpiar</button>
            </div>

            <div v-if="catalogStatus === 'loading' && !catalog.products.length" class="sp-grid" aria-busy="true">
              <div v-for="n in 8" :key="n" class="sp-card sp-skeleton" aria-hidden="true">
                <div class="sp-card-img"></div>
                <div class="sp-card-body"><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
              </div>
            </div>

            <div v-else-if="catalogStatus === 'error'" class="sp-empty">
              <span class="sp-empty-icon"><AppIcon name="circle-alert" :size="26" /></span>
              <strong>No pudimos cargar el catálogo</strong>
              <p>Revisá tu conexión e intentá de nuevo.</p>
              <button type="button" class="sp-btn ghost" @click="loadCatalog"><AppIcon name="refresh" :size="16" /> Reintentar</button>
            </div>

            <div v-else-if="catalog.products.length" class="sp-grid" :class="{ loading: catalogStatus === 'loading' }">
              <article v-for="p in catalog.products" :key="p.id" class="sp-card">
                <div class="sp-card-img">
                  <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
                  <span v-else class="sp-card-placeholder"><AppIcon name="package" :size="28" /></span>
                </div>
                <div class="sp-card-body">
                  <h3 class="sp-card-name">{{ p.name }}</h3>
                  <p v-if="p.description" class="sp-card-desc">{{ p.description }}</p>
                  <span class="sp-card-price">{{ formatARS(p.price) }}</span>
                  <a
                    v-if="productChat(p)"
                    class="sp-card-cta"
                    :href="productChat(p)"
                    target="_blank" rel="noopener"
                  >
                    <AppIcon name="whatsapp" :size="15" /> Consultar
                  </a>
                </div>
              </article>
            </div>

            <div v-else class="sp-empty">
              <span class="sp-empty-icon"><AppIcon name="package" :size="26" /></span>
              <strong>{{ hasFilters ? 'No hay productos con esos filtros' : 'Todavía no hay productos publicados' }}</strong>
              <p>{{ hasFilters ? 'Probá con otra búsqueda o quitá los filtros.' : 'Cuando el comercio cargue su catálogo, vas a poder verlo acá.' }}</p>
              <button v-if="hasFilters" type="button" class="sp-btn ghost" @click="clearFilters">Ver todo</button>
            </div>
          </section>
        </div>
      </main>
    </template>

    <!-- ===== Pie ===== -->
    <footer class="sp-foot">
      <div class="sp-container">
        <div class="sp-foot-grid">
          <div class="sp-foot-brand">
            <strong :style="nameFont">{{ shopName }}</strong>
            <span v-if="location"><AppIcon name="map-pin" :size="13" /> {{ location }}</span>
          </div>
          <nav v-if="hasContact" class="sp-foot-col" aria-label="Contacto">
            <p class="sp-foot-heading">Contacto</p>
            <a v-if="whatsappUrl" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="14" /> WhatsApp</a>
            <a v-for="s in socials" :key="s.key" :href="s.url" target="_blank" rel="noopener"><AppIcon :name="s.key" :size="14" /> {{ s.label }}</a>
          </nav>
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
