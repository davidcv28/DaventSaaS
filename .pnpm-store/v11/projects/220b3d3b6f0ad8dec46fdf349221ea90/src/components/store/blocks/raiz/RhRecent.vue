<script setup>
// Recientes / destacados (§6.5-5): 4-up uniforme 4:5, tarjeta sin borde
// (media + texto), precio tabular y hover mínimo con subrayado del nombre.
// Reusa el renderer compartido TplProductCard; la piel sin borde se resuelve
// con CSS de la portada (.rh-recent .tpc).
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../../../AppIcon.vue'
import TplProductCard from '../../TplProductCard.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, productTo } = useRhLinks()
const { custom, showCatalog } = ctx
const router = useRouter()
const { featured } = useFeaturedCatalog()

const products = computed(() => featured.value.products.slice(0, 4))
const title = computed(() => props.block?.props?.title?.trim() || 'Recién llegados')
const catOf = (p) => featured.value.categories.find((c) => c.id === p.category)?.name || ''
const brandOf = (p) => featured.value.brands.find((b) => b.id === p.brand)?.name || ''
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="showCatalog && products.length" class="rz-section rh-numbered rh-recent" aria-labelledby="rh-recent-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Lo último
          </p>
          <h2 id="rh-recent-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="60" class="rh-link" :to="catalogTo">
          Ver el catálogo <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </header>

      <div class="rh-recent-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="60 * i"
          class="rh-recent-card" :p="p" :cat="catOf(p)" :brand="brandOf(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape=""
          quick="Ver producto" go-label="Ver más" @open="openProduct"
        />
      </div>
    </div>
  </section>
</template>
