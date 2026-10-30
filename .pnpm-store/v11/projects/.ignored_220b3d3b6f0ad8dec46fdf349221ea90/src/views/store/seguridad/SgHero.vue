<script setup>
// Portada del diseño SEGURIDAD: hero partido sobre tinta oscura, con el
// titular condensado gigante (una palabra/frase en amarillo), dos CTAs, la
// línea de estado del negocio y la imagen enmarcada con el sello rojo.
// Markup propio (el bloque hero compartido no tiene este marco ni la firma
// hazard); reusa helpers comunes: openStatus, vReveal y el catálogo
// destacado para la foto cuando el dueño no cargó portada/galería.
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import SgHazard from './SgHazard.vue'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const {
  slug, custom, shopName, initial, location, showContact, showCatalog, showGallery, hasDesignAdvanced
} = ctx
const servicesPage = ctx.showServices
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Titular del dueño; sin titular el nombre del negocio es el h1. La última
// frase se pinta en amarillo (firma de la referencia: "…lo que MÁS IMPORTA").
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 2) return { head: '', accent: heroTitle.value }
  const cut = words.length >= 3 ? 2 : 1
  return { head: words.slice(0, -cut).join(' '), accent: words.slice(-cut).join(' ') }
})
const eyebrow = computed(() => (
  location.value ? `Seguridad y protección · ${location.value}` : 'Equipos contra incendio'
))

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
  if (custom.value.about_years) items.push({ key: 'years', text: `${custom.value.about_years} años de trayectoria` })
  return items
})
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
</script>

<template>
  <section class="sg-hero" aria-labelledby="sg-hero-title">
    <div class="sg-wrap sg-hero-grid">
      <div class="sg-hero-copy">
        <p v-reveal class="sg-eyebrow sg-hero-eyebrow">{{ eyebrow }}</p>
        <h1 id="sg-hero-title" v-reveal="60" class="sg-hero-title">
          <span v-if="titleParts.head">{{ titleParts.head }}</span>
          <span class="sg-hero-accent">{{ titleParts.accent }}</span>
        </h1>
        <p v-if="custom.description" v-reveal="130" class="sg-hero-lead">{{ custom.description }}</p>
        <div v-reveal="190" class="sg-hero-ctas">
          <RouterLink v-if="showCatalog" class="sg-btn sg-btn--solid" :to="catalogTo">
            Ver catálogo <AppIcon name="arrow-right" :size="17" aria-hidden="true" />
          </RouterLink>
          <a v-else-if="showContact" class="sg-btn sg-btn--solid" href="#contacto">
            Pedir presupuesto <AppIcon name="message-circle" :size="17" aria-hidden="true" />
          </a>
          <RouterLink v-if="servicesPage" class="sg-btn sg-btn--ghost" :to="servicesTo">
            Recarga y mantenimiento
          </RouterLink>
          <a v-else-if="whatsappUrl" class="sg-btn sg-btn--ghost" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar por WhatsApp
          </a>
        </div>
        <ul v-if="meta.length" v-reveal="250" class="sg-hero-meta">
          <li v-for="m in meta" :key="m.key" :class="{ 'is-open': m.state }">
            <span v-if="m.state" class="sg-dot" aria-hidden="true"></span>
            {{ m.text }}
          </li>
        </ul>
      </div>

      <div v-reveal="140" class="sg-hero-aside">
        <figure class="sg-hero-frame">
          <img v-if="heroImage" :src="heroImage.url" :alt="heroImage.alt" loading="eager" decoding="async" fetchpriority="high" />
          <div v-else class="sg-hero-plate">
            <img v-if="custom.logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sg-hero-initial" aria-hidden="true">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <figcaption class="sg-hero-seal">Norma vigente</figcaption>
        </figure>
      </div>
    </div>
    <SgHazard />
  </section>
</template>
