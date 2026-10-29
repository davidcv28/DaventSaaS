<script setup>
// Portada firma de BOUTIQUE (moda premium / deco / joyería).
// Composición 50/50: texto a la izquierda, foto con arco a la derecha.
// Variantes:
//   - 'split' (firma, default): texto | imagen en arco.
//   - 'centered': texto centrado y el arco debajo, misma data.
// Datos reales: titular/bajada de la tienda, portada premium o primera imagen
// disponible; sin imagen queda un panel tonal con la inicial (nunca un rótulo
// de "foto de portada"). La última palabra del titular va en serif itálica y
// acento — solo si el dueño cargó un titular con más de una palabra.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, initial, location, showContact, showCatalog, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices
const { featured } = useFeaturedCatalog()

const isCentered = computed(() => props.block?.variant === 'centered')
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Portada/carrusel son contenido premium; sin ellos se usa la primera imagen
// de producto disponible. El arco necesita una foto concreta, no un collage.
const media = computed(() => {
  const pool = [
    hasDesignAdvanced.value ? custom.value.cover || '' : '',
    ...(custom.value.carousel || []).map((i) => i.url),
    ...featured.value.products.map((p) => p.image)
  ]
  return pool.find(Boolean) || ''
})

const hasHeadline = computed(() => Boolean(custom.value.headline?.trim()))
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Palabra acentuada: la última del titular cargado por el dueño. Con el
// nombre de la marca solo (sin titular) no se parte el nombre.
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (!hasHeadline.value || words.length < 2) return { lead: heroTitle.value, accent: '' }
  return { lead: words.slice(0, -1).join(' '), accent: words[words.length - 1] }
})
const eyebrow = computed(() => (hasHeadline.value
  ? shopName.value
  : (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))))
const caption = computed(() => [shopName.value, location.value].filter(Boolean).join(' · '))
</script>

<template>
  <section class="bq-hero" :class="{ 'is-centered': isCentered }" aria-labelledby="bq-hero-title">
    <div class="bq-container bq-hero-grid">
      <div class="bq-hero-copy">
        <p v-reveal class="bq-eyebrow">{{ eyebrow }}</p>
        <h1 id="bq-hero-title" v-reveal="60" class="bq-hero-title">
          {{ titleParts.lead }}<template v-if="titleParts.accent"> <em class="bq-hero-accent">{{ titleParts.accent }}</em></template>
        </h1>
        <p v-if="custom.description" v-reveal="120" class="bq-hero-sub">{{ custom.description }}</p>
        <div v-reveal="180" class="bq-hero-ctas">
          <RouterLink v-if="showCatalog" class="bq-btn" :to="catalogTo">Ver catálogo</RouterLink>
          <RouterLink v-if="servicesPage" class="bq-btn bq-btn--ghost" :to="servicesTo">Servicios</RouterLink>
          <a v-if="showContact" class="bq-btn bq-btn--ghost" href="#contacto">
            Contáctanos <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
          </a>
        </div>
      </div>

      <figure v-reveal="120" class="bq-hero-media">
        <div class="bq-arch">
          <div class="bq-arch-inner">
            <img v-if="media" :src="media" :alt="`Portada de ${shopName}`" fetchpriority="high" decoding="async" />
            <span v-else class="bq-arch-mono" aria-hidden="true">{{ initial }}</span>
            <span class="bq-arch-caption">{{ caption }}</span>
          </div>
        </div>
      </figure>
    </div>
  </section>
</template>
