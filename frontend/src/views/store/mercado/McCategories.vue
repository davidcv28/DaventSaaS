<script setup>
// Categorías firma de MERCADO: riel de departamentos con foto circular,
// conteo real de productos y enlace al catálogo filtrado. Se auto-oculta sin
// categorías con productos.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })

const depts = computed(() => shopCatalog.value.categories
  .map((c) => {
    const items = shopCatalog.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 8))
const show = computed(() => showCatalog.value && depts.value.length > 0)
</script>

<template>
  <section v-if="show" class="mc-cats" aria-labelledby="mc-cats-title">
    <div class="mc-wrap">
      <header class="mc-sec-head">
        <h2 id="mc-cats-title" v-reveal class="mc-sec-title">Categorías</h2>
        <RouterLink v-reveal="60" class="mc-sec-link" :to="catalogTo">
          Ver todas <AppIcon name="arrow-right" :size="13" aria-hidden="true" />
        </RouterLink>
      </header>
      <nav class="mc-cats-rail" aria-label="Categorías del catálogo">
        <RouterLink
          v-for="(d, i) in depts" :key="d.id" v-reveal="(i % 8) * 45"
          class="mc-cat" :to="deptTo(d.id)"
        >
          <span class="mc-cat-media">
            <img v-if="d.image" :src="d.image" alt="" loading="lazy" />
            <span v-else class="mc-cat-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="mc-cat-name">{{ d.name }}</span>
          <span class="mc-cat-count">{{ d.count }}</span>
        </RouterLink>
      </nav>
    </div>
  </section>
</template>
