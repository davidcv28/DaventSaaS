<script setup>
// Sección "Equipos por categoría": encabezado condensado propio + la grilla
// compartida de departamentos (BlkCategories), que se auto-oculta sin
// categorías con productos. El encabezado solo se pinta si la grilla tiene
// datos, para no dejar un título huérfano.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const hasCats = computed(() => featured.value.categories.some(
  (c) => featured.value.products.some((p) => p.category === c.id)
))
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Equipos por categoría')
</script>

<template>
  <section v-if="hasCats" class="sg-cats" aria-labelledby="sg-cats-title">
    <div class="sg-wrap sg-sec-head">
      <h2 id="sg-cats-title" class="sg-sec-title">{{ title }}</h2>
      <RouterLink v-if="showCatalog" class="sg-sec-more" :to="catalogTo">
        Ver catálogo completo <span aria-hidden="true">→</span>
      </RouterLink>
    </div>
    <div class="sg-wrap sg-cats-grid">
      <BlkCategories :block="block" />
    </div>
  </section>
</template>
