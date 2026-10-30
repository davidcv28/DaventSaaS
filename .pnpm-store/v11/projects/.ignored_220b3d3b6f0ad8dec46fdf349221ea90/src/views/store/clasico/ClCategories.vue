<script setup>
// «Explorá el catálogo» de CLÁSICO: 4 accesos a los departamentos reales del
// catálogo en placas 4/5. Cada placa usa la foto real del primer producto de
// esa categoría y, sin foto, un panel --cl-media con el monograma serif de la
// categoría. Abajo, nombre en serif 20 y el conteo real de productos. La
// numeración editorial de la sección la resuelve el CSS con un contador
// (sobrevive a reordenar la portada en el Studio). Se auto-oculta sin
// catálogo o sin categorías con productos.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Explorá el catálogo')
const categories = computed(() => featured.value.categories
  .map((c) => {
    const count = featured.value.products.filter((p) => p.category === c.id).length
    const image = featured.value.products.find((p) => p.category === c.id && p.image)?.image || ''
    return { id: c.id, name: c.name, count, image, initial: (c.name || '·').trim().charAt(0).toUpperCase() }
  })
  .filter((c) => c.count > 0)
  .slice(0, 4))
const show = computed(() => showCatalog.value && categories.value.length > 0)
const catTo = (id) => ({ ...catalogTo.value, query: { category: id } })
const countLabel = (n) => `${n} ${n === 1 ? 'producto' : 'productos'}`
</script>

<template>
  <section v-if="show" class="cl-categories" aria-labelledby="cl-cats-title">
    <div class="cl-container">
      <header class="cl-sec-head">
        <div>
          <p v-reveal class="cl-eyebrow cl-eyebrow--num"><span class="cl-eyebrow-num" aria-hidden="true"></span>Categorías</p>
          <h2 id="cl-cats-title" v-reveal="60" class="cl-sec-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="120" class="cl-link" :to="catalogTo">
          Ver todo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>

      <div class="cl-categories-grid">
        <RouterLink
          v-for="(c, i) in categories" :key="c.id" v-reveal="(i % 4) * 70"
          class="cl-cat" :to="catTo(c.id)"
        >
          <span class="cl-cat-media">
            <img v-if="c.image" :src="c.image" :alt="`Foto de ${c.name}`" loading="lazy" decoding="async" />
            <span v-else class="cl-cat-mono" aria-hidden="true">{{ c.initial }}</span>
          </span>
          <span class="cl-cat-info">
            <strong class="cl-cat-name">{{ c.name }}</strong>
            <span class="cl-cat-count">{{ countLabel(c.count) }} <AppIcon name="arrow-right" :size="14" aria-hidden="true" /></span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
