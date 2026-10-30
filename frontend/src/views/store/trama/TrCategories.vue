<script setup>
// «Explorá la colección» de TRAMA: 4 accesos a los departamentos reales del
// catálogo. Cada placa es un panel `--tr-media` con la línea SVG de la prenda
// que sugiere el nombre de la categoría (remera / buzo / pantalón / gorra; el
// resto cae a remera) y, abajo, el nombre + el conteo real de productos.
// Se auto-oculta sin catálogo o sin categorías con productos.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import GarmentLine from './GarmentLine.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Explorá la colección')
const categories = computed(() => featured.value.categories
  .map((c) => {
    const count = featured.value.products.filter((p) => p.category === c.id).length
    return { id: c.id, name: c.name, count }
  })
  .filter((c) => c.count > 0)
  .slice(0, 4))
const show = computed(() => showCatalog.value && categories.value.length > 0)
const catTo = (id) => ({ ...catalogTo.value, query: { category: id } })
const countLabel = (n) => `${n} ${n === 1 ? 'producto' : 'productos'}`
</script>

<template>
  <section v-if="show" class="tr-cats" aria-labelledby="tr-cats-title">
    <div class="tr-container">
      <header class="tr-section-head">
        <div>
          <p v-reveal class="tr-eyebrow">Categorías</p>
          <h2 id="tr-cats-title" v-reveal="60" class="tr-section-title tr-cats-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="120" class="tr-link" :to="catalogTo">
          Ver todo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>

      <div class="tr-cats-grid">
        <RouterLink
          v-for="(c, i) in categories" :key="c.id" v-reveal="(i % 4) * 70"
          class="tr-cat" :to="catTo(c.id)"
        >
          <span class="tr-cat-media" aria-hidden="true"><GarmentLine :name="c.name" class="tr-cat-svg" /></span>
          <span class="tr-cat-info">
            <strong class="tr-cat-name">{{ c.name }}</strong>
            <span class="tr-cat-count">{{ countLabel(c.count) }} <AppIcon name="arrow-right" :size="14" aria-hidden="true" /></span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
