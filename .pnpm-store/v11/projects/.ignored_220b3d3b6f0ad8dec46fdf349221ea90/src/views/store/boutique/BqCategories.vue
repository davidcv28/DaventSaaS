<script setup>
// Categorías firma de BOUTIQUE: 3 selecciones enmarcadas con el nombre en
// serif itálica debajo (referencia visual). Datos reales del catálogo:
// categorías con productos, su conteo y la primera foto disponible.
// Variantes: 'row' (firma, 3 columnas) y 'rail' (riel con scroll).
// Jerarquía editorial: encabezado con eyebrow "Colecciones", índice por
// tarjeta y regla hairline; el enlace al catálogo vive en el encabezado.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()
const variant = computed(() => props.block?.variant || 'row')
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })

const depts = computed(() => shopCatalog.value.categories
  .map((c) => {
    const items = shopCatalog.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 3))
const show = computed(() => showCatalog.value && depts.value.length > 0)
const index = (i) => String(i + 1).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="bq-cats" :class="{ 'is-rail': variant === 'rail' }" aria-labelledby="bq-cats-title">
    <div class="bq-container">
      <header class="bq-sec-head">
        <div class="bq-sec-head-copy">
          <p v-reveal class="bq-eyebrow">Colecciones</p>
          <h2 id="bq-cats-title" v-reveal="50" class="bq-sec-title bq-section-title">Nuestras <em>selecciones</em></h2>
        </div>
        <span class="bq-sec-rule" aria-hidden="true"></span>
        <RouterLink v-reveal="90" class="bq-cats-all" :to="catalogTo">
          Ver catálogo <AppIcon name="arrow-right" :size="14" aria-hidden="true" />
        </RouterLink>
      </header>
      <div class="bq-cats-grid">
        <RouterLink v-for="(d, i) in depts" :key="d.id" v-reveal="i * 90" class="bq-cat" :to="deptTo(d.id)">
          <span class="bq-cat-frame">
            <img v-if="d.image" :src="d.image" alt="" loading="lazy" />
            <span v-else class="bq-cat-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
            <span class="bq-cat-idx" aria-hidden="true">{{ index(i) }}</span>
            <span class="bq-cat-arrow" aria-hidden="true"><AppIcon name="arrow-right" :size="14" /></span>
          </span>
          <span class="bq-cat-name">{{ d.name }}</span>
          <span class="bq-cat-count">{{ d.count }} {{ d.count === 1 ? 'producto' : 'productos' }}</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
