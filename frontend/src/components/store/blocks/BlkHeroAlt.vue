<script setup>
// Variantes de composición del bloque 'hero' (centered, split, cinema,
// editorial, search, slides): mismo copy de la portada clásica (badge,
// h1, bajada, CTAs, meta) sobre otra disposición. Una sola piel para
// todas las plantillas (clases .sp-hal-* propias — las .sp-hero-* se
// re-estilan por diseño y romperían la banda de acento) alimentada por
// las variables del tema del sitio (--st-*, con fallback al look actual
// cuando no hay tema).
import { ref, computed, inject, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, showContact, showCatalog, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices
const router = useRouter()

const variant = computed(() => props.block?.variant || 'full')
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const catTo = (id) => ({ ...catalogTo.value, query: { category: id } })

// Pool de imágenes del negocio (contenido premium — sin has_design_advanced
// la portada/carrusel no se usan aunque estén guardados, igual que el hero
// clásico). Sin imágenes la variante queda en la banda de acento.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))
const slideImgs = computed(() => [...new Set([cover.value, ...(custom.value.carousel || []).map((i) => i.url)].filter(Boolean))].slice(0, 6))
const splitImg = computed(() => slideImgs.value[0] || shopCatalog.value.products.find((p) => p.image)?.image || '')

// Datos del encabezado: mismos que el hero clásico.
const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const heroBadge = computed(() => (heroTitleIsName.value ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')) : shopName.value))
const heroBadgeIcon = computed(() => (heroTitleIsName.value ? (location.value ? 'map-pin' : 'store') : ''))
const now = ref(new Date())
let clock = null
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const heroMeta = computed(() => {
  const items = []
  if (!heroTitleIsName.value && location.value) items.push({ key: 'loc', icon: 'map-pin', text: location.value })
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (custom.value.about_years) items.push({ key: 'years', icon: 'clock', text: `+${custom.value.about_years} años de trayectoria` })
  return items
})

// Carrusel de fondo (slides): crossfade cada 5.6s pausado con
// prefers-reduced-motion, al pasar el puntero o al enfocar los controles.
const slide = ref(0)
let slideTimer = null
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
const bgImgs = computed(() => (variant.value === 'slides' ? slideImgs.value : slideImgs.value.slice(0, 1)))
const hasBg = computed(() => Boolean(bgImgs.value.length && ['slides', 'cinema', 'editorial'].includes(variant.value)))
function playSlides() {
  stopSlides()
  if (variant.value === 'slides' && slideImgs.value.length > 1 && !reduceMotion) {
    slideTimer = setInterval(() => { slide.value = (slide.value + 1) % slideImgs.value.length }, 5600)
  }
}
function stopSlides() { clearInterval(slideTimer); slideTimer = null }
function goSlide(i) {
  const n = slideImgs.value.length
  if (!n) return
  slide.value = ((i % n) + n) % n
  playSlides()
}

// Video (cinema): el embed de YouTube/Vimeo se abre en un visor modal;
// de fondo va la imagen de portada con el velo del tema.
const videoUrl = computed(() => (hasDesignAdvanced.value ? custom.value.video_url || '' : ''))
const videoOpen = ref(false)
const videoClose = ref(null)
async function openVideo() {
  videoOpen.value = true
  await nextTick()
  videoClose.value?.focus()
}
const onKey = (e) => { if (e.key === 'Escape' && videoOpen.value) videoOpen.value = false }

// Buscador (search): manda al catálogo con la query; debajo van los
// accesos directos a las primeras categorías.
const q = ref('')
const searchCats = computed(() => shopCatalog.value.categories.slice(0, 4))
function goSearch() {
  router.push({ ...catalogTo.value, query: q.value.trim() ? { q: q.value.trim() } : {} })
}

const copied = ref(false)
async function share() {
  const data = { title: shopName.value, text: custom.value.description?.trim() || `Mirá ${shopName.value}`, url: window.location.href }
  if (navigator.share) {
    try { await navigator.share(data); return } catch (e) { if (e?.name === 'AbortError') return }
  }
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* el link ya está en la barra del navegador */ }
}

watch(variant, () => { slide.value = 0; playSlides() })
onMounted(() => {
  clock = setInterval(() => { now.value = new Date() }, 60000)
  playSlides()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  clearInterval(clock)
  stopSlides()
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <section class="sp-hero sp-hal" :class="`is-${variant}`" :data-blk-variant="variant">
    <!-- Capas de fondo: carrusel con crossfade (slides) o portada fija
         (cinema/editorial); sin imágenes queda la banda de acento. -->
    <div v-if="hasBg" class="sp-hal-bg" aria-hidden="true">
      <img
        v-for="(u, i) in bgImgs" :key="u" :src="u" alt=""
        :class="{ on: i === slide }"
        :loading="i === 0 ? 'eager' : 'lazy'" :fetchpriority="i === 0 ? 'high' : 'auto'"
      />
      <span class="sp-hal-veil"></span>
    </div>

    <div class="sp-container sp-hal-grid">
      <div class="sp-hal-copy">
        <span v-if="variant === 'centered' || variant === 'search'" class="sp-hal-mark" aria-hidden="true">
          <img v-if="custom.logo" :src="custom.logo" alt="" />
          <b v-else>{{ initial }}</b>
        </span>
        <p v-if="variant === 'editorial'" v-reveal class="sp-hal-dateline">
          <span>{{ shopName }}</span><i aria-hidden="true"></i><span>{{ location || 'Tienda online' }}</span><i aria-hidden="true"></i><span>{{ new Date().getFullYear() }}</span>
        </p>
        <p v-else v-reveal class="sp-hal-badge">
          <AppIcon v-if="heroBadgeIcon" :name="heroBadgeIcon" :size="13" />{{ heroBadge }}
        </p>
        <h1 v-reveal="80" class="sp-hal-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">{{ heroTitle }}</h1>
        <p v-if="custom.description" v-reveal="160" class="sp-hal-sub">{{ custom.description }}</p>

        <form v-if="variant === 'search'" v-reveal="200" class="sp-hal-search" role="search" @submit.prevent="goSearch">
          <AppIcon name="search" :size="17" aria-hidden="true" />
          <input v-model="q" type="search" maxlength="80" :placeholder="`Buscá en el catálogo de ${shopName}`" aria-label="Buscar productos" />
          <button type="submit" class="sp-hal-search-btn">Buscar</button>
        </form>
        <div v-if="variant === 'search' && searchCats.length" v-reveal="260" class="sp-hal-cats">
          <RouterLink v-for="c in searchCats" :key="c.id" class="sp-hal-cat" :to="catTo(c.id)">{{ c.name }}</RouterLink>
        </div>

        <div v-reveal="320" class="sp-hal-ctas">
          <RouterLink v-if="showCatalog" class="sp-hal-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-if="servicesPage" class="sp-hal-btn" :class="{ 'is-ghost': showCatalog }" :to="servicesTo">Servicios <AppIcon name="wrench" :size="16" /></RouterLink>
          <button v-if="variant === 'cinema' && videoUrl" type="button" class="sp-hal-btn is-ghost" @click="openVideo"><AppIcon name="play" :size="15" /> Ver video</button>
          <a v-if="showContact && variant !== 'search'" class="sp-hal-btn is-ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
          <button type="button" class="sp-hal-iconbtn" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
            <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
          </button>
        </div>
        <ul v-if="heroMeta.length" v-reveal="400" class="sp-hal-meta">
          <li v-for="m in heroMeta" :key="m.key" :class="{ 'sp-open': m.state, [`is-${m.state}`]: m.state }"><span v-if="m.state" class="sp-live-dot" aria-hidden="true"></span><AppIcon v-else :name="m.icon" :size="14" /> {{ m.text }}</li>
        </ul>
      </div>

      <figure v-if="variant === 'split'" v-reveal="120" class="sp-hal-media">
        <img v-if="splitImg" :src="splitImg" alt="" fetchpriority="high" />
        <span v-else class="sp-hal-initial" aria-hidden="true">{{ initial }}</span>
      </figure>
    </div>

    <!-- Controles del carrusel de fondo -->
    <template v-if="variant === 'slides' && slideImgs.length > 1">
      <button type="button" class="sp-hal-arrow prev" aria-label="Imagen anterior" @click="goSlide(slide - 1)"><AppIcon name="chevron-left" :size="22" /></button>
      <button type="button" class="sp-hal-arrow next" aria-label="Imagen siguiente" @click="goSlide(slide + 1)"><AppIcon name="chevron-right" :size="22" /></button>
      <div class="sp-hal-dots" role="group" aria-label="Imágenes del carrusel">
        <button
          v-for="(u, i) in slideImgs" :key="u" type="button"
          class="sp-hal-dot" :class="{ on: i === slide }"
          :aria-label="`Ir a la imagen ${i + 1}`" :aria-current="i === slide"
          @click="goSlide(i)"
        ></button>
      </div>
    </template>

    <!-- Visor del video de la tienda -->
    <Transition name="sp-modal">
      <div v-if="videoOpen" class="sp-hal-video" role="dialog" aria-modal="true" aria-label="Video de la tienda" @click.self="videoOpen = false">
        <button ref="videoClose" type="button" class="sp-modal-close" aria-label="Cerrar video" @click="videoOpen = false"><AppIcon name="x" :size="18" /></button>
        <div class="sp-hal-video-frame">
          <iframe :src="videoUrl" title="Video de la tienda" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        </div>
      </div>
    </Transition>
  </section>
</template>
