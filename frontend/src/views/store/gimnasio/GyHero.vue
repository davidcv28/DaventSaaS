<script setup>
// Portada firma de GIMNASIO (deporte / fitness, nivel plus).
// Oscura y energética: titular Barlow Condensed gigante con la última frase
// en lima, ficha de sede (horario/zona/contacto) y placa de imagen con
// medidor de intensidad. Debajo, una cinta de disciplinas cierra el hueco.
// Markup propio; reusa helpers comunes (openStatus, vReveal) y la primera
// imagen disponible (portada → galería → catálogo) como en los otros diseños.
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const {
  slug, custom, shopName, initial, location, showContact, showCatalog, showGallery, hasDesignAdvanced
} = ctx
const servicesPage = ctx.showServices
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Titular del dueño; sin titular el nombre del negocio es el h1. Las dos
// últimas palabras se pintan en lima (firma del diseño: "…SIN EXCUSAS").
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value || 'Entrená fuerte, sin excusas.')
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 2) return { head: '', accent: heroTitle.value }
  const cut = words.length >= 3 ? 2 : 1
  return { head: words.slice(0, -cut).join(' '), accent: words.slice(-cut).join(' ') }
})
const text = computed(() => custom.value.description?.trim()
  || 'Musculación, funcional y clases todos los días. Primera clase de prueba gratis.')

// Imagen: portada premium → primera foto de la galería → primera foto de
// producto del catálogo. Sin ninguna, la placa se resuelve con el monograma.
const heroImage = computed(() => {
  if (hasDesignAdvanced.value && custom.value.cover) return { url: custom.value.cover, alt: `Portada de ${shopName.value}` }
  const gallery = Array.isArray(custom.value.gallery) ? custom.value.gallery : []
  if (showGallery.value && gallery[0]?.url) return { url: gallery[0].url, alt: `Imagen de ${shopName.value}` }
  const products = shopCatalog.value.products || []
  const withPhoto = products.find((p) => p.image)
  if (withPhoto) return { url: withPhoto.image, alt: withPhoto.name }
  return null
})

// Estado de atención en vivo, igual criterio que el resto de la web.
const now = ref(new Date())
let clock = null
onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
const meta = computed(() => {
  const items = []
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (location.value) items.push({ key: 'loc', text: location.value })
  if (custom.value.about_years) items.push({ key: 'years', text: `${custom.value.about_years} años entrenando` })
  return items
})
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const centered = computed(() => props.block?.variant === 'centered')
const kicker = computed(() => `Gimnasio${location.value ? ` · ${location.value}` : ' · Centro de entrenamiento'}`)
const metaIcon = { open: 'clock', loc: 'map-pin', years: 'flame' }
</script>

<template>
  <section class="gy-hero" :class="{ 'is-centered': centered }" aria-labelledby="gy-hero-title">
    <div class="gy-wrap gy-hero-grid">
      <div class="gy-hero-copy">
        <p v-reveal class="gy-kicker">{{ kicker }}</p>
        <h1 id="gy-hero-title" v-reveal="50" class="gy-hero-title">
          <span v-if="titleParts.head">{{ titleParts.head }}</span>
          <span class="gy-hero-accent">{{ titleParts.accent }}</span>
        </h1>
        <p v-reveal="110" class="gy-hero-lead">{{ text }}</p>
        <div v-reveal="170" class="gy-hero-ctas">
          <RouterLink v-if="showCatalog" class="gy-btn gy-btn--solid" :to="catalogTo">
            Ver planes y tienda <AppIcon name="arrow-right" :size="17" aria-hidden="true" />
          </RouterLink>
          <a v-else-if="showContact" class="gy-btn gy-btn--solid" href="#contacto">
            Empezar hoy <AppIcon name="arrow-right" :size="17" aria-hidden="true" />
          </a>
          <RouterLink v-if="servicesPage" class="gy-btn gy-btn--ghost" :to="servicesTo">
            Clases y horarios
          </RouterLink>
          <a v-else-if="whatsappUrl" class="gy-btn gy-btn--ghost" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Clase de prueba
          </a>
        </div>
        <ul v-if="meta.length" v-reveal="230" class="gy-hero-meta">
          <li v-for="m in meta" :key="m.key" :class="{ 'is-open': m.state }">
            <span v-if="m.state" class="gy-dot" aria-hidden="true"></span>
            <AppIcon v-else :name="metaIcon[m.key] || 'check'" :size="18" class="gy-meta-ic" aria-hidden="true" />
            {{ m.text }}
          </li>
        </ul>
      </div>

      <figure v-reveal="130" class="gy-hero-plate" :class="{ 'is-empty': !heroImage }">
        <img v-if="heroImage" :src="heroImage.url" :alt="heroImage.alt" loading="eager" decoding="async" fetchpriority="high" />
        <div v-else class="gy-hero-empty">
          <img v-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
          <span v-else class="gy-hero-initial" aria-hidden="true">{{ initial }}</span>
          <strong>{{ shopName }}</strong>
        </div>
        <figcaption class="gy-hero-badge">
          <template v-if="custom.about_years"><b>+{{ custom.about_years }}</b><span>años de trayectoria</span></template>
          <span v-else>Sala principal</span>
        </figcaption>
      </figure>
    </div>
    <div v-reveal="210" class="gy-strip" aria-hidden="true">
      <div class="gy-wrap gy-strip-inner">
        <span>Musculación</span>
        <span>Funcional</span>
        <span>Spinning</span>
        <span>Boxeo</span>
        <span>Yoga</span>
        <span>HIIT</span>
      </div>
    </div>
  </section>
</template>
