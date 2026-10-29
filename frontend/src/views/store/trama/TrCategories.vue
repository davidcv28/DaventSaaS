<script setup>
// "Comprá por categoría" de TRAMA: 4 placas verticales con la primera foto
// real de cada categoría y su conteo en un chip blanco abajo. Los datos son
// los departamentos que ya resuelve el catálogo público (categorías con
// productos); sin categorías la sección se oculta.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import AppIcon from '../../../components/AppIcon.vue'

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const categories = computed(() => featured.value.categories
  .map((c) => {
    const items = featured.value.products.filter((p) => p.category === c.id)
    return {
      id: c.id,
      name: c.name,
      count: items.length,
      image: items.find((p) => p.image)?.image || ''
    }
  })
  .filter((c) => c.count > 0)
  .slice(0, 4))
const show = computed(() => showCatalog.value && categories.value.length > 0)
const catTo = (id) => ({ ...catalogTo.value, query: { category: id } })
</script>

<template>
  <section v-if="show" class="tr-cats" aria-labelledby="tr-cats-title">
    <div class="tr-container">
      <header class="tr-section-head">
        <h2 id="tr-cats-title" v-reveal class="tr-section-title">Comprá por categoría</h2>
        <RouterLink v-reveal class="tr-link" :to="catalogTo">Ver todo <AppIcon name="arrow-right" :size="14" class="tr-arrow" /></RouterLink>
      </header>
      <div class="tr-cats-grid">
        <RouterLink
          v-for="(c, i) in categories" :key="c.id" v-reveal="(i % 4) * 70"
          class="tr-cat-tile" :to="catTo(c.id)"
        >
          <img v-if="c.image" :src="c.image" alt="" loading="lazy" decoding="async" />
          <span v-else class="tr-cat-ph" aria-hidden="true">{{ c.name.slice(0, 1) }}</span>
          <span class="tr-cat-label">{{ c.name }} ({{ c.count }})</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
