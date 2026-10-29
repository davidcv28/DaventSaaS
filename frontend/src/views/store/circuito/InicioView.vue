<script setup>
// Inicio del diseño CIRCUITO (tecnología / electrónica).
// Composición FIJA de 12 secciones (spec §7.1): barra de acento, hero partido
// con tarjeta de producto, franja de 4 garantías, categorías 6 en 3×2,
// destacados, banda de servicios, oferta + cuenta regresiva, marcas,
// testimonios, FAQ y contacto. La vista decide el orden (no layout_config) y
// cada sección se auto-oculta si la tienda no tiene ese contenido.
// La piel vive en assets/store-circuito.css con raíz [data-template="circuito"].
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import CiHero from './CiHero.vue'
import CiGuarantees from './CiGuarantees.vue'
import CiServicesBand from './CiServicesBand.vue'

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
// La sección de categorías (y su encabezado) solo existe si hay categorías con
// productos: el bloque compartido se auto-oculta, el título no.
const { featured } = useFeaturedCatalog()
const hasCats = computed(() => featured.value.categories.some(
  (c) => featured.value.products.some((p) => p.category === c.id)
))
</script>

<template>
  <div class="sp-page-root ci-home">
    <!-- 1. Barra de acento (anuncios reales de la tienda) -->
    <BlkAnnouncements :block="{ id: 'announcements', variant: 'static' }" />
    <!-- 2. Hero partido con tarjeta de producto destacado -->
    <CiHero />
    <!-- 3. Franja de 4 garantías -->
    <CiGuarantees />
    <!-- 4. Categorías (6 en 3×2) -->
    <section v-if="hasCats" class="ci-cats" aria-labelledby="ci-cats-title">
      <div class="ci-container ci-sec-head">
        <div>
          <p class="ci-label">Catálogo</p>
          <h2 id="ci-cats-title">Categorías</h2>
        </div>
        <RouterLink v-if="showCatalog" class="ci-sec-more" :to="catalogTo">Ver todo el catálogo</RouterLink>
      </div>
      <BlkCategories :block="{ id: 'categories' }" />
    </section>
    <!-- 5. Productos destacados -->
    <BlkFeatured :block="{ id: 'featured', variant: 'grid', props: { title: 'Productos destacados' } }" />
    <!-- 6. Banda de servicios -->
    <CiServicesBand />
    <!-- 7. Oferta vigente + cuenta regresiva -->
    <BlkCountdown :block="{ id: 'countdown', variant: 'band' }" />
    <!-- 8. Marcas -->
    <BlkBrands :block="{ id: 'brands', variant: 'logos' }" />
    <!-- 9. Testimonios -->
    <BlkTestimonials :block="{ id: 'testimonials', variant: 'cards' }" />
    <!-- 10. Preguntas frecuentes -->
    <BlkFaq :block="{ id: 'faq', variant: 'accordion' }" />
    <!-- 11. Contacto -->
    <BlkContact :block="{ id: 'contact', variant: 'card' }" />
  </div>
</template>
