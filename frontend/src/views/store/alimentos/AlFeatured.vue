<script setup>
// AlFeatured — "Lo más pedido": grilla de hasta 4 productos reales del
// catálogo con la tarjeta firma AlProductCard (precio + CTA WhatsApp por
// producto). Variantes: 'grid' (default) y 'rail' (riel con scroll-snap).
// Sin catálogo o sin productos la sección se auto-oculta.
import { computed } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import AlProductCard from './AlProductCard.vue'
import { useStorePage } from '../../../composables/useStorePage.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const { showCatalog, catalogTo, waProduct, openProduct } = useStorePage()
const { featured } = useFeaturedCatalog()

const variant = computed(() => props.block?.variant || 'grid')
const title = computed(() => props.block?.props?.title?.trim() || 'Lo más pedido')
const items = computed(() => featured.value.products.slice(0, 4))
const catOf = (p) => featured.value.categories.find((c) => c.id === p.category)?.name || ''
</script>

<template>
  <section v-if="showCatalog && items.length" class="al-featured" :class="`is-${variant}`" aria-labelledby="al-featured-title">
    <div class="al-container">
      <div class="al-sec-head">
        <div>
          <p class="al-eyebrow">Del menú</p>
          <h2 id="al-featured-title" class="al-sec-title">{{ title }}</h2>
        </div>
        <RouterLink class="al-link" :to="catalogTo">
          Ver todo el menú <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
        </RouterLink>
      </div>
      <div class="al-featured-grid">
        <AlProductCard
          v-for="(p, i) in items" :key="p.id" v-reveal="(i % 4) * 70"
          :p="p" :cat="catOf(p)" :href="waProduct(p)" @open="openProduct"
        />
      </div>
    </div>
  </section>
</template>
