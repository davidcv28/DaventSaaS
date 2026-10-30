<script setup>
// Categorías (§6.5-4): grilla editorial asimétrica — dos piezas grandes (7/5)
// y hasta tres chicas (4/4/4) con número, caption y flecha al hover. Las
// categorías son reales (con conteo de productos) y la miniatura sale del
// primer producto con imagen; sin foto queda un placeholder tipográfico.
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from './rhLinks.js'

defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, categoryTo } = useRhLinks()
const { showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const depts = computed(() => featured.value.categories
  .map((c) => {
    const items = featured.value.products.filter((p) => p.category === c.id)
    return {
      id: c.id,
      name: c.name,
      count: items.length,
      image: items.find((p) => p.image)?.image || ''
    }
  })
  .filter((d) => d.count > 0)
  .slice(0, 5))

// Reparto asimétrico por cantidad: 7/5 · 7/5/12 · 7/5/6/6 · 7/5/4/4/4.
const SPANS = {
  1: ['12'],
  2: ['7', '5'],
  3: ['7', '5', '12'],
  4: ['7', '5', '6', '6'],
  5: ['7', '5', '4', '4', '4']
}
const spans = computed(() => SPANS[depts.value.length] || SPANS[5])
const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
  <section v-if="depts.length" class="rz-section rh-numbered rh-cats" aria-labelledby="rh-cats-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Catálogo
          </p>
          <h2 id="rh-cats-title" v-reveal class="rh-title">Explorá por categoría</h2>
        </div>
        <RouterLink v-if="showCatalog" v-reveal="60" class="rh-link" :to="catalogTo">
          Ver todo el catálogo <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </header>

      <div class="rh-cats-grid">
        <RouterLink
          v-for="(d, i) in depts" :key="d.id" v-reveal="60 * i"
          class="rh-cat" :class="`is-span-${spans[i]}`"
          :to="categoryTo(d.id)"
        >
          <span class="rh-cat-media">
            <img v-if="d.image" :src="d.image" alt="" loading="lazy" decoding="async" />
            <span v-else class="rh-cat-ph" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="rh-cat-cap">
            <span class="rh-cat-num" aria-hidden="true">{{ pad(i + 1) }}</span>
            <strong class="rh-cat-name">{{ d.name }}</strong>
            <span class="rh-cat-count">{{ d.count }} {{ d.count === 1 ? 'producto' : 'productos' }}</span>
            <span class="rh-cat-arrow" aria-hidden="true"><AppIcon name="arrow-up-right" :size="16" /></span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
