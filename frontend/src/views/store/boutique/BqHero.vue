<script setup>
// Portada firma de BOUTIQUE (moda premium / deco / joyería).
// Composición 50/50 editorial: columna de texto (kicker, titular, bajada,
// CTAs y ficha de datos reales) + foto en arco con marco desplazado.
// Variantes:
//   - 'split' (firma, default): texto | imagen en arco.
//   - 'centered': texto centrado y el arco debajo, misma data.
// Datos reales: titular/bajada de la tienda, portada premium o primera imagen
// disponible; sin imagen queda un panel tonal con la inicial (nunca un rótulo
// de "foto de portada"). La última palabra del titular va en serif itálica y
// acento — solo si el dueño cargó un titular con más de una palabra.
// La ficha meta y el pie del arco solo muestran datos cargados (años,
// ubicación, cantidad de piezas): nada inventado. El movimiento (entrada,
// marco que se dibuja, parallax scroll-driven) vive en store-boutique-motion.css
// y se apaga con prefers-reduced-motion.
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

// Ficha de datos reales bajo los CTAs: reemplaza el aire vacío por jerarquía
// informativa. Sin datos no se pinta la lista entera.
const metaItems = computed(() => {
  const list = []
  if (custom.value.about_years) {
    list.push({ key: 'years', value: String(custom.value.about_years), label: 'Años de trayectoria' })
  }
  if (location.value) list.push({ key: 'location', value: location.value, label: 'Ubicación' })
  const pieces = featured.value.products.length
  if (pieces) {
    list.push({ key: 'pieces', value: String(pieces), label: pieces === 1 ? 'Pieza en catálogo' : 'Piezas en catálogo' })
  }
  return list.slice(0, 3)
})
</script>

<template>
  <section class="bq-hero" :class="{ 'is-centered': isCentered }" aria-labelledby="bq-hero-title">
    <div class="bq-container bq-hero-grid">
      <div class="bq-hero-copy">
        <p v-reveal class="bq-hero-kicker">
          <span class="bq-eyebrow">{{ eyebrow }}</span>
          <span class="bq-hero-kicker-rule" aria-hidden="true"></span>
        </p>
        <h1 id="bq-hero-title" v-reveal="60" class="bq-hero-title" :aria-label="heroTitle">
          {{ titleParts.lead }}<template v-if="titleParts.accent">{{ ' ' }}<em class="bq-hero-accent">{{ titleParts.accent }}</em></template>
        </h1>
        <p v-if="custom.description" v-reveal="110" class="bq-hero-sub">{{ custom.description }}</p>
        <div v-reveal="160" class="bq-hero-ctas">
          <RouterLink v-if="showCatalog" class="bq-btn" :to="catalogTo">
            Ver catálogo <AppIcon class="bq-btn-arrow" name="arrow-right" :size="15" aria-hidden="true" />
          </RouterLink>
          <RouterLink v-if="servicesPage" class="bq-btn bq-btn--ghost" :to="servicesTo">Servicios</RouterLink>
          <a v-if="showContact" class="bq-btn bq-btn--ghost" href="#contacto">
            Contáctanos <AppIcon class="bq-btn-arrow" name="arrow-right" :size="15" aria-hidden="true" />
          </a>
        </div>
        <ul v-if="metaItems.length" v-reveal="210" class="bq-hero-meta" :class="{ 'is-single': metaItems.length === 1 }">
          <li v-for="m in metaItems" :key="m.key">
            <span class="bq-hero-meta-value">{{ m.value }}</span>
            <span class="bq-hero-meta-label">{{ m.label }}</span>
          </li>
        </ul>
      </div>

      <figure v-reveal="120" class="bq-hero-media">
        <div class="bq-arch-stack">
          <div class="bq-arch">
            <span class="bq-arch-halo" aria-hidden="true"></span>
            <span class="bq-arch-seal" aria-hidden="true">{{ initial }}</span>
            <div class="bq-arch-inner">
              <img v-if="media" :src="media" :alt="`Portada de ${shopName}`" fetchpriority="high" decoding="async" />
              <span v-else class="bq-arch-mono" aria-hidden="true">{{ initial }}</span>
              <span class="bq-arch-veil" aria-hidden="true"></span>
            </div>
          </div>
        </div>
        <figcaption class="bq-arch-foot">
          <span v-if="custom.about_years" class="bq-arch-est">Desde hace {{ custom.about_years }} años</span>
          <span class="bq-arch-foot-rule" aria-hidden="true"></span>
          <span class="bq-arch-caption">{{ caption }}</span>
        </figcaption>
      </figure>
    </div>
    <div class="bq-hero-cue" aria-hidden="true">
      <span class="bq-hero-cue-line"></span>
      <span class="bq-hero-cue-label">Explorar</span>
    </div>
  </section>
</template>
